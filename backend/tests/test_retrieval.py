"""Offline retrieval regressions; HTTP is mocked and paper fixtures are recorded."""
import asyncio
import copy
import io
import json
import logging
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from app.agents.research_orchestrator import ResearchOrchestrator, NoEvidenceError
from app.agents.search_agent import SearchAgent
from app.core.logging import ResearchJSONFormatter
from app.schemas.research import ResearchRequest, Source
from app.services.paper_normalization import normalize_paper, duplicate, related_to_topic
from app.services.research_provider import (OpenAlexProvider, CrossrefProvider, SemanticScholarProvider,
    ResilientResearchProvider, ResearchProviderError, research_context)
from app.services.search_queries import generate_queries

FIXTURES = Path(__file__).parent / 'fixtures'


def response(data):
    stream = io.BytesIO(json.dumps(data).encode())
    stream.status = 200
    return stream


def crossref_record():
    return json.loads((FIXTURES / 'crossref_deep_learning.json').read_text(encoding='utf-8-sig'))


def known_paper():
    with patch('app.services.research_provider.reserve_request'), patch('app.services.research_provider.urlopen', return_value=response({'message': {'items': [crossref_record()]}})):
        return CrossrefProvider().search('Deep learning', 5)[0]


class Stub:
    name = 'Recorded provider'
    def __init__(self, records=None, error=None):
        self.records, self.error, self.calls = records or [], error, []
    def search(self, query, limit):
        self.calls.append(query)
        if self.error:
            raise self.error
        return copy.deepcopy(self.records)


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.pacing = patch('app.services.research_provider.reserve_request')
        self.pacing.start()
        self.addCleanup(self.pacing.stop)

    def test_queries_cover_topic_objective_level_and_question(self):
        queries = generate_queries('AI adoption in Indian higher education', 'Explore faculty readiness', 'MCA', ['What barriers affect adoption?'])
        self.assertEqual(len(queries), 5)
        self.assertEqual(queries[0], 'AI adoption in Indian higher education')
        self.assertTrue(any('faculty' in q for q in queries))
        self.assertTrue(any('artificial intelligence' in q for q in queries))
        self.assertIn('systematic review', queries[-1])
        self.assertIn('barriers', queries[-1])
        self.assertNotIn('MCA', ' '.join(queries))

    def test_openalex_inverted_abstract_and_optional_fields(self):
        paper = known_paper()
        raw = {'id': paper['url'], 'display_name': paper['title'], 'doi': paper['doi'],
               'abstract_inverted_index': {'Deep': [0], 'learning': [1]},
               'authorships': None, 'cited_by_count': None, 'primary_location': None}
        with patch('app.services.research_provider.urlopen', return_value=response({'results': [raw]})):
            result = OpenAlexProvider().search('Deep learning', 5)
        self.assertEqual(result[0]['abstract'], 'Deep learning')
        self.assertEqual(result[0]['authors'], [])
        self.assertEqual(result[0]['citation_count'], 0)
        serialized = Source.model_validate(result[0]).model_dump()
        for key in ('paper_id', 'title', 'authors', 'year', 'abstract', 'doi', 'url', 'journal', 'source_provider', 'citation_count'):
            self.assertIn(key, serialized)

    def test_missing_optional_metadata_and_one_bad_record_do_not_discard_batch(self):
        record = crossref_record()
        record.update({'abstract': None, 'author': None, 'published': None, 'is-referenced-by-count': None})
        record.pop('DOI', None)  # Retrieved publisher URL alone suffices.
        self.assertTrue(record.get('URL'))
        provider = CrossrefProvider()
        with patch('app.services.research_provider.urlopen', return_value=response({'message': {'items': [None, {}, record]}})):
            papers = provider.search('Deep learning', 5)
        self.assertEqual(len(papers), 1)
        self.assertEqual(provider.last_diagnostic['returned'], 3)
        self.assertEqual(provider.last_diagnostic['valid'], 1)
        self.assertEqual(provider.last_diagnostic['rejected'], 2)
        self.assertEqual(papers[0]['abstract'], '')
        self.assertEqual(papers[0]['citation_count'], 0)

    def test_rate_limit_falls_back_without_retrying_provider(self):
        error = HTTPError('https://example.invalid/?api_key=secret', 429, 'secret', {'Retry-After': '120'}, io.BytesIO())
        fallback = Stub([known_paper()])
        provider = ResilientResearchProvider(providers=[OpenAlexProvider(), fallback])
        with patch('app.services.research_provider.urlopen', side_effect=error) as http:
            papers = provider.search_many(['Deep learning', 'Deep learning review'], 5, 'Deep learning')
        self.assertEqual(http.call_count, 1)
        self.assertEqual(len(papers), 1)
        self.assertEqual(provider.last_status, 'PARTIAL_RESULTS')
        self.assertEqual(provider.last_diagnostics[0]['error_code'], 'RATE_LIMITED')
        self.assertNotIn('secret', json.dumps(provider.last_diagnostics))

    def test_http_error_classes_and_invalid_payload_are_distinct(self):
        cases = [(HTTPError('https://invalid.test', 401, 'hidden', {}, io.BytesIO()), 'PROVIDER_UNAVAILABLE'),
                 (HTTPError('https://invalid.test', 429, 'hidden', {}, io.BytesIO()), 'RATE_LIMITED'),
                 (URLError('hidden credential'), 'PROVIDER_UNAVAILABLE')]
        for error, code in cases:
            with self.subTest(code=code), patch('app.services.research_provider.urlopen', side_effect=error):
                provider = ResilientResearchProvider(providers=[OpenAlexProvider()])
                self.assertEqual(provider.search('Deep learning', 5), [])
                self.assertEqual(provider.last_status, code)
        with patch('app.services.research_provider.urlopen', return_value=response({'wrong': []})):
            provider = ResilientResearchProvider(providers=[OpenAlexProvider()])
            self.assertEqual(provider.search('Deep learning', 5), [])
            self.assertEqual(provider.last_status, 'INVALID_PROVIDER_RESPONSE')

    def test_empty_success_is_not_an_outage_and_unrelated_records_are_insufficient(self):
        empty = ResilientResearchProvider(providers=[Stub()])
        self.assertEqual(empty.search('Deep learning', 5), [])
        self.assertEqual(empty.last_status, 'NO_RESULTS')
        unrelated = ResilientResearchProvider(providers=[Stub([known_paper()])])
        self.assertEqual(unrelated.search('Medieval archaeology', 5), [])
        self.assertEqual(unrelated.last_status, 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(unrelated.last_diagnostics[0]['rejection_reasons'], {'unrelated_to_topic': 1})

    def test_query_variation_is_used_when_exact_query_is_empty(self):
        paper = known_paper()
        provider = Stub()
        provider.search = lambda query, limit: [] if query == 'Deep learning' else [paper]
        resilient = ResilientResearchProvider(providers=[provider])
        self.assertEqual(len(resilient.search_many(['Deep learning', 'Deep learning review'], 5, 'Deep learning')), 1)
        self.assertEqual(len(resilient.last_diagnostics), 2)

    def test_deduplication_doi_title_and_near_identical_long_titles(self):
        paper = known_paper()
        self.assertTrue(duplicate({**paper, 'doi': 'https://doi.org/' + paper['doi'].upper()}, [paper]))
        self.assertTrue(duplicate({**paper, 'doi': None, 'title': '  DEEP learning!! '}, [paper]))
        topics = json.loads((FIXTURES / 'retrieval_topics.json').read_text(encoding='utf-8'))
        long = topics['Machine Learning in Education'][0]
        variant = {**long, 'doi': None, 'title': long['title'].replace('Trends', 'Trend')}
        self.assertTrue(duplicate(variant, [long]))
        self.assertFalse(duplicate({**long, 'doi': None, 'title': long['title'] + ' 2025'}, [long]))

    def test_valid_paper_must_have_safe_link_and_match_application_domain(self):
        paper = known_paper()
        with self.assertRaises(ValueError):
            normalize_paper({**paper, 'doi': None, 'url': 'javascript:alert(1)'}, 'Crossref')
        self.assertFalse(related_to_topic(paper, 'Machine Learning in Education'))

    def test_diagnostics_do_not_log_raw_query_or_keys(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(ResearchJSONFormatter())
        logger = logging.getLogger('researchos.retrieval')
        previous = logger.level
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        token = research_context.set('test-run-id')
        try:
            with patch.dict('os.environ', {'OPENALEX_API_KEY': 'sensitive-api-key'}), patch('app.services.research_provider.urlopen', return_value=response({'results': []})) as http:
                ResilientResearchProvider(providers=[OpenAlexProvider()]).search('alice@example.com private research', 5)
            self.assertEqual(http.call_args.args[0].get_header('Authorization'), 'Bearer sensitive-api-key')
            logs = stream.getvalue()
            self.assertNotIn('alice@example.com', logs)
            self.assertNotIn('sensitive-api-key', logs)
            self.assertIn('test-run-id', logs)
            for line in logs.splitlines():
                diagnostic = json.loads(line)
                for key in ('provider', 'query', 'http_status', 'returned', 'valid', 'rejected', 'rejection_reasons', 'duration_ms', 'error_code'):
                    self.assertIn(key, diagnostic)
        finally:
            research_context.reset(token)
            logger.removeHandler(handler)
            logger.setLevel(previous)

    def test_all_four_topics_complete_with_recorded_real_papers(self):
        topics = json.loads((FIXTURES / 'retrieval_topics.json').read_text(encoding='utf-8'))
        for topic, papers in topics.items():
            with self.subTest(topic=topic):
                result = ResearchOrchestrator(SearchAgent(provider=Stub(papers))).run(topic, 'MCA', source_limit=5)
                self.assertTrue(result['sources'])
                self.assertTrue(result['report'])
                self.assertTrue(result['findings'])
                self.assertTrue(all(s['doi'] or s['url'] for s in result['sources']))

    def test_orchestrator_preserves_failure_code_and_safe_message(self):
        seen = []
        orchestrator = ResearchOrchestrator(SearchAgent(provider=Stub(error=ResearchProviderError('secret', 'RATE_LIMITED'))))
        with self.assertRaisesRegex(NoEvidenceError, 'rate limiting'):
            asyncio.run(orchestrator.run_async(ResearchRequest(topic='Deep learning'), checkpoint=lambda stage, result: seen.append(result.model_dump())))
        self.assertEqual(seen[-1]['retrieval_status'], 'RATE_LIMITED')
        self.assertNotIn('secret', json.dumps(seen))

    def test_transient_http_error_retries_then_succeeds(self):
        error = HTTPError('https://invalid.test', 500, 'hidden', {}, io.BytesIO())
        with patch('app.services.research_provider.urlopen', side_effect=[error, response({'message': {'items': [crossref_record()]}})]) as http:
            provider = ResilientResearchProvider(providers=[CrossrefProvider()])
            self.assertEqual(len(provider.search('Deep learning', 5)), 1)
        self.assertEqual(http.call_count, 2)
        self.assertEqual(provider.last_diagnostics[0]['http_status'], 500)
        self.assertEqual(provider.last_diagnostics[1]['http_status'], 200)

    def test_semantic_scholar_optional_null_fields(self):
        paper = known_paper()
        record = {'paperId': paper['id'], 'title': paper['title'], 'url': paper['url'],
                  'authors': None, 'externalIds': None, 'publicationTypes': None, 'openAccessPdf': None}
        with patch('app.services.research_provider.urlopen', return_value=response({'data': [record]})):
            self.assertEqual(len(SemanticScholarProvider().search('Deep learning', 5)), 1)


if __name__ == '__main__':
    unittest.main()
