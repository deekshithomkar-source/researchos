"""Evidence-organized report sections, never free-form unsupported claims."""
from app.services.depth_policy import depth_policy
from app.schemas.analysis import ReportSection
from app.services.citations import CitationGenerator
from app.agents.evidence_analysis import validate_traceability


def synthesize_sections(request, result):
    policy = depth_policy(request.academic_level)
    result.citations = CitationGenerator().generate(result.sources, request.citation_style)
    labels = {c.paper_id: c.label for c in result.citations}
    papers = {p.id: p for p in result.sources}
    def quoted(item):
        return f'> {item.text}\n\n{labels[item.paper_id]} — {item.locator.replace('_', ' ')} excerpt; evidence `{item.evidence_id}`.'
    result.summary = (f'Retrieved {len(result.sources)} scholarly records for {request.topic}. '
                      f'{sum(bool(p.abstract) for p in result.sources)} contain abstracts and {sum(bool(p.full_text) for p in result.sources)} have licensed full-text bodies. '
                      'The following is an extractive evidence review; author statements have not been independently replicated.')
    literature = []
    for paper in result.sources:
        passages = [e for e in result.evidence if e.paper_id == paper.id]
        detail = '\n\n'.join(quoted(e) for e in passages[:policy.excerpts]) if passages else 'No abstract was retrieved. Metadata only; no study findings are inferred.'
        literature.append(f'### {paper.title} {labels[paper.id]}\n\n{detail}')
    evidence_by_id = {e.evidence_id: e for e in result.evidence}
    findings = '\n\n'.join(quoted(evidence_by_id[f.evidence_ids[0]]) for f in result.key_findings)
    gaps = '\n\n'.join(f'**{g.category.replace("_", " ").title()} — reported by this source, not established across the field:**\n\n' + quoted(evidence_by_id[g.evidence_ids[0]]) for g in result.gaps)
    future = [g for g in result.gaps if g.category == 'future_opportunity']
    limitations = [g for g in result.gaps if g.category in ('study_limitation', 'methodological_limitation')]
    section = lambda name, content, ids=(), complete=True: ReportSection(name=name, content=content, evidence_ids=list(dict.fromkeys(ids)), complete=complete)
    result.report_sections = [
        section('Research overview', result.summary),
        section('Research objective', request.objective or 'No additional objective supplied; analysis is scoped to the topic.'),
        section('Research questions', '\n'.join(f'{i}. {q}' for i,q in enumerate(result.sub_questions,1))),
        section('Literature review', '\n\n'.join(literature), [e.evidence_id for e in result.evidence], bool(result.evidence)),
        section('Key findings', findings or 'No explicit result statements were extracted. This does not establish that the studies have no findings.', [e for f in result.key_findings for e in f.evidence_ids], bool(result.key_findings)),
        section('Research gaps', gaps or 'No evidence-supported research gaps were identified in the retained source passages. Missing metadata is not a research gap.', [e for g in result.gaps for e in g.evidence_ids], bool(result.gaps)),
        section('Research limitations', '\n\n'.join(quoted(evidence_by_id[g.evidence_ids[0]]) for g in limitations) + '\n\n' + '\n'.join('- '+note for note in result.coverage_notes), [e for g in limitations for e in g.evidence_ids], bool(limitations)),
        section('Future scope', '\n\n'.join(quoted(evidence_by_id[g.evidence_ids[0]]) for g in future) or 'No explicit future research recommendation was identified. No opportunity is asserted without source support.', [e for g in future for e in g.evidence_ids], bool(future)),
    ]
    by_name = {item.name: item for item in result.report_sections}
    depth = section('Analysis approach', f'{request.academic_level}: {policy.focus}.\n\nReview task: {policy.task}.\n\nExpected deliverable: {policy.outcome}')
    methods = section('Methods comparison', '\n\n'.join(
        f"### {p.title}\n\n" + ('\n\n'.join(quoted(e) for e in result.evidence if e.paper_id == p.id and e.kind == 'method') or 'No explicit methods passage available; comparison remains incomplete.')
        for p in result.sources), [e.evidence_id for e in result.evidence if e.kind == 'method'], any(e.kind == 'method' for e in result.evidence))
    if request.report_type == 'literature_review':
        result.report_sections = [by_name[n] for n in ('Research overview', 'Research objective', 'Research questions')]
        result.report_sections += [depth, section('Search and selection', '\n'.join(result.search_queries) or 'Search queries were not retained for this historical run.'), by_name['Literature review'], methods, by_name['Research gaps'], by_name['Research limitations']]
    elif request.report_type == 'project_proposal':
        result.report_sections = [by_name[n] for n in ('Research objective', 'Research questions', 'Literature review', 'Research gaps')]
        result.report_sections += [depth, section('Proposed Solution', policy.task + ': ' + request.topic + '. This is a proposed investigation, not a validated solution.'),
            section('Evaluation protocol', policy.outcome + '\n\nDefine baseline measures against: ' + (request.objective or request.topic) + '. Verify dataset eligibility and licenses before implementation.'),
            section('Milestones', '1. Review the cited evidence.\n2. Select and validate study inputs.\n3. Execute the proposed evaluation.\n4. Document negative results and limitations.'), by_name['Research limitations']]
    else:
        result.report_sections.insert(3, depth)
        if policy.key != 'undergraduate':
            result.report_sections.insert(5, methods)
    # Document framing is procedural guidance; scholarly statements remain cited excerpts.
    introduction = section('Introduction', 'This review investigates ' + request.topic +
        '. Its scope is limited to the retained papers and source passages; it does not establish exhaustive coverage.')
    methodology = section('Methodology', 'Review procedure: search the retained queries, normalize and deduplicate provider records, '
        'rank against the topic and objective, then extract traceable passages. This is not a systematic review protocol.\n\n'
        + 'Academic emphasis: ' + policy.focus + '.\n\n' + policy.question + '\n\n'
        + ('Queries: ' + '; '.join(result.search_queries) if result.search_queries else 'Historical search queries are unavailable.'))
    discussion = section('Discussion', 'Interpretation task: ' + policy.task + '. ' + policy.outcome +
        '\n\nAssess whether methods and study populations justify transfer to the objective. '
        'No pooled effect or causal conclusion is inferred from these excerpts.\n\n' +
        (gaps or 'No explicit source-supported limitations were available for critical comparison.'),
        [e for g in result.gaps for e in g.evidence_ids], bool(result.evidence))
    conclusion = section('Conclusion', result.summary + '\n\n' +
        'The retained evidence supports source-level reading and study planning, not independent validation. '
        'Resolve the flagged incomplete sections before treating this as a submission-ready manuscript.', complete=bool(result.evidence))
    if request.report_type == 'comparative_analysis':
        result.report_sections = [by_name['Research objective'], by_name['Research questions'], depth,
            section('Comparison criteria', 'Compare study design, populations, evidence availability and reported limitations. '
                'Absent methods or incompatible measures must remain unknown; no numerical ranking is invented.'),
            by_name['Literature review'], methods, by_name['Key findings'], discussion,
            by_name['Research gaps'], by_name['Research limitations'], by_name['Future scope']]
    else:
        result.report_sections.append(discussion)
        if request.report_type == 'academic_report':
            pass
        else:
            result.report_sections.append(by_name['Future scope'])
    result.report_sections = [section('Abstract', result.summary), introduction, methodology] + result.report_sections + [conclusion]
    # Policy tasks describe review requirements, never new empirical findings.
    checks = []
    if not any(e.kind == 'method' for e in result.evidence):
        checks.append('No explicit methods passage is available; methodology assessment is incomplete.')
    if policy.key in ('masters', 'doctoral') and len({e.paper_id for e in result.evidence}) < 2:
        checks.append('Fewer than two papers have retained evidence; cross-study conclusions are unsupported.')
    if policy.key == 'doctoral' and not any(p.full_text for p in result.sources):
        checks.append('No licensed full text is retained; a detailed validity or reproducibility audit remains incomplete.')
    result.report_sections.insert(-1, section(policy.report_heading,
        'Review guidance, not study results.\n\n' + policy.explanation_style + '\n\n' +
        '\n'.join('- ' + task for task in policy.methodology) + '\n\nEvidence requirements:\n' +
        '\n'.join('- ' + task for task in policy.evidence_requirements) + '\n\nGap assessment: ' + policy.gap_review +
        ('\n\nCoverage limitations:\n' + '\n'.join(checks) if checks else ''), complete=not checks))
    from app.agents.llm_agents import append_llm_sections
    append_llm_sections(result)
    if result.evidence_analysis:
        analysis = result.evidence_analysis
        # These do not populate established gaps or overwrite source findings.
        for comparison in analysis.comparisons:
            refs = ' '.join(labels[p] for p in comparison.supporting_paper_ids)
            result.report_sections.append(section('Provisional cross-paper ' + comparison.relation.replace('_', ' '),
                'UNCERTAIN MODEL INTERPRETATION: ' + comparison.conclusion + '\n\n' + refs +
                '\nLimitations: ' + '; '.join(comparison.limitations), comparison.supporting_evidence_ids))
        for gap in analysis.candidate_gaps:
            refs = ' '.join(labels[p] for p in gap.supporting_paper_ids)
            result.report_sections.append(section('Candidate research direction (' + gap.basis + ')',
                gap.grounding.upper() + ': ' + gap.description + '\n\n' + refs +
                '\nLimitations: ' + '; '.join(gap.limitations), gap.supporting_evidence_ids))
    result.missing_sections = [s.name for s in result.report_sections if not s.complete]
    if result.missing_sections:
        result.partial = True
    validate_traceability(result)


def render_report(topic, report_type, result):
    if not result.sources:
        return ''
    title = ('Metadata-only literature catalog' if not result.evidence else
             'Literature review' if report_type == 'literature_review' else
             'Research proposal evidence review' if report_type == 'project_proposal' else
             'Comparative analysis' if report_type == 'comparative_analysis' else 'Academic research evidence review')
    sections = [f'# {title}: {topic}']
    sections.extend(f'## {s.name}\n\n{s.content}' for s in result.report_sections)
    sections.append('## References\n\n' + '\n\n'.join(c.reference for c in result.citations))
    notes = ['Only retrieved metadata and exact source excerpts are presented as evidence; passage locators distinguish abstract and licensed full-text analysis.',
             'Gap categories are lexical classifications of author statements; cross-study contradiction adjudication is not performed.',
             'Author display names are retained when structured name metadata is unavailable; missing reference fields are not guessed.']
    if result.provider_warning:
        notes.append(result.provider_warning)
    if result.missing_sections:
        notes.append('Incomplete sections: ' + ', '.join(result.missing_sections) + '.')
    sections.append('## Research Integrity Note\n\n' + '\n'.join('- ' + note for note in notes))
    return '\n\n'.join(sections)
