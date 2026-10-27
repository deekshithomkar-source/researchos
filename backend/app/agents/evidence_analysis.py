"""Deterministic analysis of the brief and retrieved abstracts; no model claims."""
import hashlib
import re
from datetime import datetime, timezone

from app.services.depth_policy import depth_policy
from app.schemas.analysis import (ResearchIntent, PaperRanking, EvidencePassage,
                                  SupportedFinding, SupportedGap)
from app.services.search_queries import terms
from app.services.paper_normalization import duplicate, related_to_topic
from app.agents.verifier_agent import VerifierAgent


def stable_id(*parts):
    return hashlib.sha256('\x1f'.join(map(str, parts)).encode()).hexdigest()[:32]


class IntentAnalyzer:
    def analyze(self, request):
        objective = request.objective or ''
        lowered = objective.lower()
        kind = ('comparison' if re.search(r'\bcompar|\bversus\b', lowered) else
                'evaluation' if re.search(r'\bevaluat|\bassess|\bimpact|\beffect', lowered) else
                'implementation' if re.search(r'\bbuild|\bdesign|\bimplement|\bdevelop', lowered) else 'exploration')
        advanced = any(t in request.academic_level.lower() for t in ('mca', 'master', 'phd', 'research', 'doctoral'))
        return ResearchIntent(topic=request.topic, objective=request.objective,
                              academic_level=request.academic_level, output_format=request.report_type,
                              investigation_type=kind, concepts=sorted(terms(request.topic)),
                              objective_terms=sorted(terms(objective)),
                              depth=depth_policy(request.academic_level).focus)


class ResearchQuestionGenerator:
    def generate(self, intent):
        topic = intent.topic
        focus = intent.objective or f'understand the evidence about {topic}'
        approach = {
            'comparison': f'Which approaches to {topic} have been compared, using which outcomes?',
            'evaluation': f'Which measured outcomes support evaluations of {topic}?',
            'implementation': f'Which evaluated methods inform the design or implementation of {topic}?',
            'exploration': f'Which concepts and applications are established in the retrieved literature on {topic}?',
        }[intent.investigation_type]
        methods = depth_policy(intent.academic_level).question
        return [approach, f'What retrieved evidence addresses this objective: {focus.rstrip(".?")}?',
                methods, f'What limitations or conflicting findings do authors explicitly report about {topic}?',
                f'Which unresolved questions and future investigations do authors identify for {topic}?']


class RelevanceEvaluator:
    def evaluate(self, sources, request):
        scored = VerifierAgent().evaluate([s.model_dump() for s in sources])
        topic_terms, objective_terms = terms(request.topic), terms(request.objective or '')
        year_now = datetime.now(timezone.utc).year
        results = []
        for paper in scored:
            if not related_to_topic(paper, request.topic) or duplicate(paper, results):
                continue
            text_terms = terms(paper['title'] + ' ' + paper.get('abstract', ''))
            topic = len(topic_terms & text_terms) / max(1, len(topic_terms))
            objective = len(objective_terms & text_terms) / len(objective_terms) if objective_terms else None
            credibility = paper['credibility_score'] / 100
            year = paper.get('year')
            recency = 1 / (1 + max(0, year_now - year) / 5) if year and year <= year_now + 1 else 0
            availability = 1.0 if paper.get('abstract') else 0.0
            weights = [(topic, .45), (credibility, .15), (recency, .10), (availability, .10)]
            if objective is not None:
                weights.append((objective, .20))
            total = sum(v*w for v,w in weights) / sum(w for _,w in weights)
            paper['ranking'] = PaperRanking(topic_relevance=topic, objective_alignment=objective,
                credibility=credibility, recency=recency, evidence_availability=availability,
                total=total, explanation='Lexical topic/objective overlap, metadata quality, age decay and abstract availability; not a peer-review judgment.').model_dump()
            results.append(paper)
        return sorted(results, key=lambda p: (-p['ranking']['total'], p['id']))[:request.source_limit]


# Categories indicate what authors explicitly state, never an inferred field-wide gap.
GAP_PATTERNS = {
    'understudied_population': r'\b(?:understudied|underrepresented|under-represented)\s+(?:populations?|groups?|communities|patients?|students?|participants?)\b',
    'missing_dataset': r'\b(?:lack|absence|unavailab\w*|scarcity|limited access)\b.{0,70}\b(?:data|datasets|benchmarks)\b',
    'methodological_limitation': r'(?=.*\b(?:limit\w*|bias|confound\w*|cannot|unable|lack|restrict\w*)\b).*\b(?:small sample|selection bias|confounding|cross-sectional|lack of validation|limited generalizability|limited generalisability)\b',
    'conflicting_findings': r'\b(?:conflicting findings|contradictory results|inconsistent findings|mixed evidence|mixed results)\b',
    'unresolved_question': r'\b(?:remains? unclear|remain unresolved|remains unresolved|open question|not yet understood|unknown whether)\b',
    'future_opportunity': r'\b(?:future research|future studies|further research|further studies|further investigation)\b.{0,90}\b(?:need\w*|should|could|must|requir\w*|warrant\w*|explor\w*|address\w*)\b',
    'study_limitation': r'\b(?:limitation(?:s)? (?:of|include|is|are|was|were)|limited by|restricted to|cannot generalize|cannot generalise)\b',
}
NEGATED_GAP = re.compile(r'\b(?:no|without|not|neither)\b.{0,35}\b(?:limitation|lack|conflicting|contradictory|mixed evidence|mixed results|understudied|underrepresented|under-represented)', re.I)
FINDING = re.compile(r'\b(?:results? (?:show|suggest|indicat|demonstrat|reveal)|we (?:found|observed)|was associated|were associated|outperformed|improved|reduced|increased|achieved|conclude)\w*', re.I)
METHOD = re.compile(r'\b(?:method|survey|experiment|participants|sample|randomized|randomised|interview|dataset)\w*', re.I)


def gap_categories(text):
    if NEGATED_GAP.search(text):
        return []
    return [category for category, pattern in GAP_PATTERNS.items() if re.search(pattern, text, re.I)]


class EvidenceExtractor:
    def extract(self, sources):
        evidence = []
        for paper in sources:
            text_source = paper.full_text.text if paper.full_text else paper.abstract
            locator = 'full_text' if paper.full_text else 'abstract'
            source_url = paper.full_text.url if paper.full_text else paper.url
            # Offsets reference the exact retained source text, not generated text.
            matches = list(re.finditer(r'\S[\s\S]*?(?:[.!?](?=\s+[A-Z]|$)|$)', text_source))
            candidates = []
            for match in matches:
                text = match.group().rstrip()
                if not text:
                    continue
                categories = gap_categories(text)
                kind = 'limitation' if categories else 'finding' if FINDING.search(text) else 'method' if METHOD.search(text) else 'context'
                candidates.append(EvidencePassage(evidence_id=stable_id(paper.id, locator, match.start(), text),
                    paper_id=paper.id, text=text, start=match.start(), end=match.start()+len(text),
                    source_url=source_url, kind=kind, locator=locator))
            # Preserve supporting/limitation passages before contextual text in long abstracts.
            selected = sorted(candidates, key=lambda e: (e.kind == 'context', e.start))[:16]
            evidence.extend(sorted(selected, key=lambda e: e.start))
        return evidence


class SupportedGapDetector:
    def analyze(self, evidence):
        gaps = []
        for item in evidence:
            for category in gap_categories(item.text):
                gaps.append(SupportedGap(gap_id=stable_id(item.evidence_id, category), category=category,
                    statement=item.text, evidence_ids=[item.evidence_id], paper_ids=[item.paper_id]))
        assessment = {category: ('author_reported_support_found' if any(g.category == category for g in gaps)
                                else 'not_established_by_retrieved_abstracts') for category in GAP_PATTERNS}
        return gaps, assessment


def extract_findings(evidence):
    return [SupportedFinding(finding_id=stable_id(e.evidence_id, 'finding'), statement=e.text,
            evidence_ids=[e.evidence_id], paper_ids=[e.paper_id]) for e in evidence if e.kind == 'finding']


def validate_traceability(result):
    papers = {p.id: p for p in result.sources}
    evidence = {e.evidence_id: e for e in result.evidence}
    if len(papers) != len(result.sources) or len(evidence) != len(result.evidence):
        raise ValueError('Duplicate provenance identifiers')
    for item in evidence.values():
        paper = papers.get(item.paper_id)
        full = paper.full_text if paper else None
        content = (full.text if full else '') if item.locator == 'full_text' else (paper.abstract if paper else '')
        url = (full.url if full else None) if item.locator == 'full_text' else (paper.url if paper else None)
        if paper is None or item.end > len(content) or content[item.start:item.end] != item.text or item.source_url != url:
            raise ValueError('Evidence does not match its source')
    for item in [*result.key_findings, *result.gaps]:
        supporting = [evidence.get(key) for key in item.evidence_ids]
        if any(e is None for e in supporting) or set(item.paper_ids) != {e.paper_id for e in supporting}:
            raise ValueError('Missing evidence support')
        if not any(item.statement == e.text for e in supporting):
            raise ValueError('Claim is not an author-reported excerpt')
    for gap in result.gaps:
        if gap.category not in gap_categories(gap.statement):
            raise ValueError('Gap category lacks explicit support')
    semantic = result.evidence_analysis
    if semantic:
        for item in [*semantic.claims, *semantic.comparisons, *semantic.candidate_gaps]:
            passages = [evidence.get(eid) for eid in item.supporting_evidence_ids]
            if not passages or any(e is None for e in passages) or set(item.supporting_paper_ids) != {e.paper_id for e in passages}:
                raise ValueError('Semantic analysis references missing evidence')
            if item.grounding in ('exact_excerpt', 'explicit_excerpt'):
                claim = getattr(item, 'claim_text', None) or getattr(item, 'description', '')
                if not any(claim == e.text for e in passages):
                    raise ValueError('Semantic excerpt changed')
    for section in result.report_sections:
        if any(key not in evidence for key in section.evidence_ids):
            raise ValueError('Report section has missing evidence')
    if result.citations and {c.paper_id for c in result.citations} != set(papers):
        raise ValueError('Citation catalog does not match papers')
