"""Analysis contracts. Synthetic abstract text is confined to explicit test fixtures."""
import asyncio
import copy
import threading
import time
import unittest
from unittest.mock import patch
from sqlalchemy import select, text

from app.agents.evidence_analysis import (IntentAnalyzer, ResearchQuestionGenerator, RelevanceEvaluator,
    EvidenceExtractor, SupportedGapDetector, extract_findings, validate_traceability)
from app.agents.evidence_synthesis import synthesize_sections
from app.agents.research_orchestrator import ResearchOrchestrator, NoEvidenceError
from app.agents.search_agent import SearchAgent
from app.core.config import settings
from app.schemas.research import Source, ResearchRequest, ResearchResult
from app.services.citations import CitationGenerator
from app.services.research_provider import ResilientResearchProvider, ResearchProviderError
from app.services.execution import execute_research
from app.services.research_artifacts import persist_artifacts
from app.models.research import ResearchRun
from app.models.analysis import (ResearchPaper, ResearchSource, ResearchEvidence, ResearchFinding,
    ResearchGap, ResearchReport, finding_evidence, gap_evidence)
import test_foundation
from test_retrieval import known_paper, Stub

MOCK_ABSTRACT = ('We evaluated deep learning methods using interviews and experiments. '
                 'Results show improved outcomes for the measured task. '
                 'Limitations include a small sample and selection bias. '
                 'The lack of datasets restricted validation. '
                 'Prior studies report conflicting findings. '
                 'It remains unclear whether outcomes generalize. '
                 'Future research should evaluate independent samples.')


def analysis_paper():
    # Actual paper metadata, intentionally synthetic abstract for classifier tests.
    return Source.model_validate({**known_paper(), 'abstract': MOCK_ABSTRACT})


class AnalysisTests(unittest.TestCase):
    def test_intent_questions_use_objective_level_and_output(self):
        request = ResearchRequest(topic='Deep learning', objective='Compare validation methods', academic_level='MCA', report_type='literature_review')
        intent = IntentAnalyzer().analyze(request)
        self.assertEqual(intent.investigation_type, 'comparison')
        self.assertEqual(intent.output_format, 'literature_review')
        questions = ResearchQuestionGenerator().generate(intent)
        self.assertIn('Compare validation methods', questions[1])
        self.assertIn('datasets', questions[2])
        introductory = IntentAnalyzer().analyze(request.model_copy(update={'academic_level': 'BCA'}))
        self.assertIn('main methods', ResearchQuestionGenerator().generate(introductory)[2])

    def test_evidence_and_all_gap_categories_have_exact_source_support(self):
        paper = analysis_paper()
        result = ResearchResult(sources=[paper])
        result.evidence = EvidenceExtractor().extract(result.sources)
        result.key_findings = extract_findings(result.evidence)
        result.gaps, result.gap_assessment = SupportedGapDetector().analyze(result.evidence)
        self.assertTrue(result.key_findings)
        self.assertEqual(len({g.category for g in result.gaps}), 6)
        validate_traceability(result)
        for evidence in result.evidence:
            self.assertEqual(paper.abstract[evidence.start:evidence.end], evidence.text)
        result.gaps[0].statement = 'Unsupported invented conclusion'
        with self.assertRaises(ValueError):
            validate_traceability(result)

    def test_negative_gap_statements_and_missing_abstracts_do_not_create_gaps(self):
        paper = analysis_paper().model_copy(update={'abstract': 'No conflicting findings were observed. No limitations were identified.'})
        gaps, _ = SupportedGapDetector().analyze(EvidenceExtractor().extract([paper]))
        self.assertEqual(gaps, [])
        design = paper.model_copy(update={'abstract': 'We used a cross-sectional design with a small sample.'})
        self.assertEqual(SupportedGapDetector().analyze(EvidenceExtractor().extract([design]))[0], [])
        empty = paper.model_copy(update={'abstract': ''})
        self.assertEqual(EvidenceExtractor().extract([empty]), [])
        result = ResearchOrchestrator(SearchAgent(provider=Stub([empty.model_dump()]))).run('Deep learning', 'MCA', source_limit=5)
        self.assertTrue(result['partial'])
        self.assertEqual(result['evidence'], [])
        self.assertEqual(result['key_findings'], [])
        self.assertEqual(result['gaps'], [])
        self.assertIn('Metadata-only literature catalog', result['report'])
        self.assertIn('Key findings', result['missing_sections'])

    def test_objective_changes_ranking_and_all_factors_are_exposed(self):
        first = analysis_paper()
        second = first.model_copy(update={'id': 'test-only-second', 'doi': None,
            'title': 'Deep learning validation in external populations',
            'abstract': 'Validation of deep learning using external populations.', 'year': 2025})
        first = first.model_copy(update={'title': 'Deep learning architecture', 'abstract': 'Deep learning architecture.'})
        request = ResearchRequest(topic='Deep learning', objective='validation external populations')
        ranked = RelevanceEvaluator().evaluate([first, second], request)
        self.assertEqual(ranked[0]['id'], second.id)
        score = ranked[0]['ranking']
        for key in ('topic_relevance', 'objective_alignment', 'credibility', 'recency', 'evidence_availability', 'total'):
            self.assertTrue(0 <= score[key] <= 1)

    def test_apa_ieee_use_metadata_and_missing_fields_are_not_invented(self):
        paper = analysis_paper()
        apa = CitationGenerator().generate([paper], 'apa')[0]
        ieee = CitationGenerator().generate([paper], 'ieee')[0]
        self.assertIn('LeCun, Y.', apa.reference)
        self.assertIn('2015', apa.reference)
        self.assertIn('10.1038/nature14539', apa.reference)
        self.assertEqual(ieee.label, '[1]')
        self.assertIn('Y. LeCun', ieee.reference)
        sparse = Source(id='metadata-test', title='Test record', provider='Test', url='https://example.org/paper')
        reference = CitationGenerator().generate([sparse], 'apa')[0]
        self.assertIn('n.d.', reference.reference)
        self.assertNotIn('Unknown author', reference.reference)
        self.assertEqual(reference.metadata_missing, ['authors', 'year', 'venue'])

    def test_citation_disambiguation_and_report_section_traceability(self):
        paper = analysis_paper()
        other = paper.model_copy(update={'id': 'second', 'title': 'Second test title'})
        citations = CitationGenerator().generate([paper, other], 'apa')
        self.assertTrue(citations[0].label.endswith('2015a)'))
        self.assertTrue(citations[1].label.endswith('2015b)'))
        result = ResearchResult(sources=[paper], evidence=EvidenceExtractor().extract([paper]))
        result.key_findings = extract_findings(result.evidence)
        result.gaps, result.gap_assessment = SupportedGapDetector().analyze(result.evidence)
        synthesize_sections(ResearchRequest(topic='Deep learning'), result)
        validate_traceability(result)
        result.evidence[0].end += 1
        with self.assertRaises(ValueError):
            validate_traceability(result)

    def test_discovery_is_concurrent_bounded_and_preserves_partial_results(self):
        lock = threading.Lock()
        active = 0
        peak = 0
        barrier = threading.Barrier(2)
        paper = known_paper()
        class ConcurrentProvider:
            def __init__(self, name): self.name = name
            def search(self, query, limit):
                nonlocal active, peak
                with lock:
                    active += 1
                    peak = max(peak, active)
                try:
                    barrier.wait(timeout=3)
                    time.sleep(.02)
                    return [paper]
                finally:
                    with lock: active -= 1
        bad = Stub(error=ResearchProviderError('safe failure', 'RATE_LIMITED'))
        bad.name = 'Unavailable'
        with patch.object(settings, 'provider_concurrency', 2):
            provider = ResilientResearchProvider(providers=[ConcurrentProvider('A'), ConcurrentProvider('B'), bad])
            result = provider.search('Deep learning', 5)
        self.assertEqual(peak, 2)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['origins']), 2)
        self.assertEqual(provider.last_status, 'PARTIAL_RESULTS')
        self.assertEqual(len(provider.last_diagnostics), 3)

    def test_no_sources_never_produces_report(self):
        snapshots = []
        orchestrator = ResearchOrchestrator(SearchAgent(provider=Stub()))
        with self.assertRaises(NoEvidenceError):
            asyncio.run(orchestrator.run_async(ResearchRequest(topic='Deep learning'),
                        checkpoint=lambda stage,result: snapshots.append(result.model_dump())))
        self.assertEqual(snapshots[-1]['report'], '')
        self.assertEqual(snapshots[-1]['key_findings'], [])


class AnalysisPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_foundation.FoundationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.signup()

    def test_complete_worker_stores_traceable_graph_and_reopens_unchanged(self):
        run = self.fixture.submit()
        stages = []
        class ObservedOrchestrator(ResearchOrchestrator):
            async def run_async(self, request, research_id='', checkpoint=None):
                def observe(stage,result):
                    stages.append(stage.status)
                    checkpoint(stage,result)
                return await super().run_async(request,research_id,observe)
        execute_research(run['research_id'], self.fixture.sessions,
            lambda: ObservedOrchestrator(SearchAgent(provider=Stub([analysis_paper().model_dump()]))))
        saved = self.fixture.client.get('/api/research/' + run['research_id']).json()
        self.assertEqual(saved['status'], 'completed', saved.get('error_message'))
        self.assertIn('validating', stages)
        self.assertTrue(saved['evidence'])
        self.assertTrue(saved['gaps'])
        with self.fixture.sessions() as db:
            for model in (ResearchPaper, ResearchSource, ResearchEvidence, ResearchFinding, ResearchGap, ResearchReport):
                self.assertGreater(db.query(model).filter_by(run_id=run['id']).count(), 0)
            report = db.get(ResearchReport, run['id'])
            self.assertEqual(report.content, saved['report'])
            self.assertEqual(len(db.execute(select(gap_evidence)).all()), len(saved['gaps']))
            self.assertEqual(db.execute(text('PRAGMA foreign_key_check')).all(), [])
            stored = db.get(ResearchRun, run['id'])
            result = ResearchResult.model_validate(saved)
            persist_artifacts(db, stored, result)
            db.commit()
            self.assertEqual(db.query(ResearchEvidence).count(), len(saved['evidence']))
        self.assertEqual(self.fixture.client.get('/api/research/' + str(run['id'])).json()['evidence'], saved['evidence'])

    def test_failure_after_extraction_preserves_normalized_evidence(self):
        run = self.fixture.submit()
        orchestrator = ResearchOrchestrator(SearchAgent(provider=Stub([analysis_paper().model_dump()])))
        with patch.object(orchestrator.reporter, 'generate_report', side_effect=RuntimeError('private error')):
            execute_research(run['research_id'], self.fixture.sessions, lambda: orchestrator)
        result = self.fixture.client.get('/api/research/' + run['research_id']).json()
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['partial'])
        self.assertTrue(result['evidence'])
        self.assertEqual(result['report'], '')
        with self.fixture.sessions() as db:
            self.assertEqual(db.query(ResearchEvidence).count(), len(result['evidence']))
            self.assertEqual(db.query(ResearchReport).count(), 0)


if __name__ == '__main__':
    unittest.main()
