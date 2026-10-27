"""Integration tests use an isolated SQLite file, real cookie handling, and recorded metadata."""
import asyncio
import hashlib
import io
import json
import tempfile
import threading
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.api.background import get_executor
from app.core.config import Settings, settings
from app.core.security import verify_password
from app.db.database import get_db
from app.db.migrations import migrate
from app.main import app
from app.models.research import ResearchRun
from app.models.user import AuthSession, User, utcnow
from app.agents.research_orchestrator import ResearchOrchestrator
from app.agents.search_agent import SearchAgent
from app.services.execution import execute_research, recover_interrupted_runs
from app.services.provider_services import AcademicSearchService, LLMService
from app.services.research_provider import CrossrefProvider, ResearchProviderError, ResilientResearchProvider

PASSWORD = 'a strong test password 123!'


def recorded_sources():
    record = json.loads((Path(__file__).parent / 'fixtures/crossref_deep_learning.json').read_text(encoding='utf-8-sig'))
    payload = json.dumps({'message': {'items': [record]}}).encode()
    with patch('app.services.research_provider.urlopen', return_value=io.BytesIO(payload)):
        return CrossrefProvider().search('deep learning', 5)


class RecordedProvider:
    name = 'Crossref recorded fixture'
    last_warning = None
    def search(self, query, limit):
        return recorded_sources()[:limit]


class DeferredExecutor:
    def __init__(self):
        self.jobs = []
    def enqueue(self, research_id):
        self.jobs.append(research_id)


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = create_engine(f'sqlite:///{Path(self.temp.name) / "test.db"}', connect_args={'check_same_thread': False})
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        migrate(self.engine, Path(self.temp.name) / 'no-users.json')
        self.executor = DeferredExecutor()
        def test_db():
            with self.sessions() as session:
                yield session
        app.dependency_overrides[get_db] = test_db
        app.dependency_overrides[get_executor] = lambda: self.executor
        self.client = TestClient(app, headers={'X-ResearchOS-Client': 'web', 'Origin': 'http://localhost:5173'})

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp.cleanup()

    def signup(self, client=None, email='alice@example.com'):
        client = client or self.client
        response = client.post('/api/auth/signup', json={'name': 'Test User', 'email': email, 'password': PASSWORD})
        self.assertEqual(response.status_code, 201, response.text)
        client.headers['X-CSRF-Token'] = response.json()['csrf_token']
        return response

    def submit(self):
        response = self.client.post('/api/research', json={'topic': 'Deep learning', 'source_target': 5})
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def worker(self, research_id, searcher=None):
        execute_research(research_id, self.sessions, lambda: ResearchOrchestrator(searcher=searcher or SearchAgent(provider=RecordedProvider())))

    def test_full_flow_with_visible_background_progress_and_reopen(self):
        signup = self.signup()
        self.assertIn('HttpOnly', signup.headers['set-cookie'])
        self.assertIn('SameSite=lax', signup.headers['set-cookie'])
        self.assertEqual(self.client.post('/api/auth/signout').status_code, 204)
        signin = self.client.post('/api/auth/signin', json={'email': 'alice@example.com', 'password': PASSWORD})
        self.assertEqual(signin.status_code, 200)
        self.client.headers['X-CSRF-Token'] = signin.json()['csrf_token']
        run = self.submit()
        self.assertEqual(run['status'], 'queued')
        self.assertEqual(self.executor.jobs, [run['research_id']])
        self.assertEqual(self.client.get(f"/api/research/{run['research_id']}").json()['progress'], 0)
        entered, release = threading.Event(), threading.Event()
        class SlowRecordedProvider(RecordedProvider):
            def search(self, query, limit):
                entered.set()
                if not release.wait(5):
                    raise TimeoutError('test worker was not released')
                return super().search(query, limit)
        thread = threading.Thread(target=self.worker, args=(run['research_id'], SearchAgent(provider=SlowRecordedProvider())))
        thread.start()
        try:
            self.assertTrue(entered.wait(3))
            progress = self.client.get(f"/api/research/{run['research_id']}").json()
            self.assertEqual(progress['status'], 'searching')
            self.assertEqual(progress['progress'], 35)
        finally:
            release.set()
            thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        saved = self.client.get(f"/api/research/{run['research_id']}").json()
        self.assertEqual(saved['status'], 'completed', saved)
        self.assertEqual(saved['progress'], 100)
        self.assertTrue(saved['partial'])
        self.assertIn('10.1038/nature14539', saved['report'])
        self.assertTrue(saved['completed_at'])
        history = self.client.get('/api/research/history').json()
        self.assertEqual([item['research_id'] for item in history], [run['research_id']])
        self.assertEqual(self.client.get(f"/api/research/{run['id']}").json()['report'], saved['report'])
        with self.sessions() as db:
            user = db.query(User).one()
            self.assertTrue(user.password_hash.startswith('$argon2id$'))
            self.assertNotIn(PASSWORD, user.password_hash)
            self.assertTrue(verify_password(PASSWORD, user.password_hash))

    def test_ownership_and_unauthenticated_access(self):
        self.signup()
        run = self.submit()
        bob = TestClient(app, headers={'X-ResearchOS-Client': 'web'})
        anonymous = TestClient(app)
        try:
            self.signup(bob, 'bob@example.com')
            self.assertEqual(bob.get('/api/research/history').json(), [])
            for identifier in (run['research_id'], run['id']):
                self.assertEqual(bob.get(f'/api/research/{identifier}').status_code, 404)
                self.assertEqual(anonymous.get(f'/api/research/{identifier}').status_code, 401)
            self.assertEqual(anonymous.get('/api/research/history').status_code, 401)
            self.assertEqual(bob.post('/api/research', json={'topic': 'Deep learning', 'user_id': 'alice'}).status_code, 422)
        finally:
            bob.close()
            anonymous.close()

    def test_csrf_logout_expiry_and_password_errors(self):
        self.signup()
        cookie = self.client.cookies.get('researchos_session')
        self.assertEqual(self.client.post('/api/research', json={'topic': 'Deep learning'}, headers={'X-CSRF-Token': 'wrong'}).status_code, 403)
        self.assertEqual(self.client.post('/api/research', json={'topic': 'Deep learning'}, headers={'Origin': 'https://untrusted.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/signout').status_code, 204)
        self.client.cookies.set('researchos_session', cookie, path='/api')
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        bad = self.client.post('/api/auth/signin', json={'email': 'alice@example.com', 'password': 'wrong'})
        self.assertEqual(bad.status_code, 401)
        invalid = self.client.post('/api/auth/signup', json={'name': 'Bad', 'email': 'bad@example.com', 'password': 'secret'})
        self.assertEqual(invalid.status_code, 422)
        self.assertNotIn('secret', invalid.text)
        self.assertEqual(self.client.post('/api/auth/reset-password', json={'email': 'alice@example.com', 'password': PASSWORD}).status_code, 501)
        login = self.client.post('/api/auth/signin', json={'email': 'alice@example.com', 'password': PASSWORD})
        self.assertEqual(login.status_code, 200)
        with self.sessions() as db:
            db.query(AuthSession).update({'expires_at': utcnow() - timedelta(seconds=1)})
            db.commit()
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_oversized_numeric_identifier_returns_not_found(self):
        self.signup()
        for identifier in ('9223372036854775808', '9' * 5000):
            self.assertEqual(self.client.get(f'/api/research/{identifier}').status_code, 404)

    def test_owned_legacy_result_reopens_without_snapshot(self):
        self.signup()
        run = self.submit()
        sources = recorded_sources()
        with self.sessions() as db:
            saved = db.query(ResearchRun).filter_by(research_id=run['research_id']).one()
            saved.status = 'completed'
            saved.progress = 100
            saved.sub_questions = json.dumps(['What evidence is available?'])
            saved.findings = json.dumps([{'question': 'What evidence is available?', 'sources': sources}])
            saved.summary = 'Original saved summary'
            saved.report = 'Original saved report'
            saved.result_json = None
            db.commit()
        reopened = self.client.get(f"/api/research/{run['research_id']}").json()
        self.assertEqual(reopened['summary'], 'Original saved summary')
        self.assertEqual(reopened['report'], 'Original saved report')
        self.assertEqual(reopened['sources'][0]['doi'], '10.1038/nature14539')
        self.assertEqual(len(reopened['findings']), 1)
        self.assertEqual(reopened['sub_questions'], ['What evidence is available?'])

    def test_provider_failure_never_fabricates_evidence(self):
        class FailedProvider:
            name = 'Unavailable provider'
            def search(self, query, limit):
                raise ResearchProviderError('internal provider detail must not reach clients')
        self.signup()
        run = self.submit()
        provider = ResilientResearchProvider(FailedProvider(), FailedProvider())
        self.worker(run['research_id'], SearchAgent(provider=provider))
        result = self.client.get(f"/api/research/{run['research_id']}").json()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['sources'], [])
        self.assertEqual(result['retrieval_status'], 'PROVIDER_UNAVAILABLE')
        self.assertTrue(result['provider_diagnostics'])
        self.assertNotIn('No scholarly evidence', result['error_message'])
        self.assertNotIn('internal provider detail', json.dumps(result))
        self.assertIn('No substitute evidence', result['provider_warning'])

    def test_failure_preserves_partial_sources_and_duplicate_worker_is_noop(self):
        self.signup()
        run = self.submit()
        orchestrator = ResearchOrchestrator(searcher=SearchAgent(provider=RecordedProvider()))
        with patch.object(orchestrator.reporter, 'generate_report', side_effect=RuntimeError('secret-value')):
            execute_research(run['research_id'], self.sessions, lambda: orchestrator)
        result = self.client.get(f"/api/research/{run['research_id']}").json()
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['sources'])
        self.assertTrue(result['partial'])
        self.assertNotIn('secret-value', json.dumps(result))
        self.worker(run['research_id'])
        self.assertEqual(self.client.get(f"/api/research/{run['research_id']}").json()['status'], 'failed')

    def test_restart_recovery_and_admission_limit(self):
        self.signup()
        runs = [self.submit() for _ in range(settings.max_active_runs)]
        self.assertEqual(self.client.post('/api/research', json={'topic': 'Deep learning'}).status_code, 429)
        recover_interrupted_runs(self.sessions)
        for run in runs:
            self.assertEqual(self.client.get(f"/api/research/{run['research_id']}").json()['status'], 'failed')

    def test_real_background_adapter(self):
        self.signup()
        del app.dependency_overrides[get_executor]
        with patch('app.services.execution.SessionLocal', self.sessions), patch('app.services.execution.ResearchOrchestrator', lambda: ResearchOrchestrator(searcher=SearchAgent(provider=RecordedProvider()))):
            run = self.submit()
        self.assertEqual(run['status'], 'queued')
        self.assertEqual(self.client.get(f"/api/research/{run['research_id']}").json()['status'], 'completed')

    def test_rate_limit_and_missing_client_header(self):
        client = TestClient(app)
        try:
            self.assertEqual(client.post('/api/auth/signin', json={'email': 'x@example.com', 'password': 'x'}).status_code, 403)
            with patch.object(settings, 'auth_attempts', 1):
                self.signup()
                self.assertEqual(self.client.post('/api/auth/signin', json={'email': 'alice@example.com', 'password': PASSWORD}).status_code, 429)
        finally:
            client.close()


class MigrationTests(unittest.TestCase):
    def test_legacy_research_preserved_and_credentials_upgraded(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = create_engine(f'sqlite:///{Path(folder) / "legacy.db"}')
            try:
                with engine.begin() as connection:
                    connection.execute(text('CREATE TABLE research_sessions (id INTEGER PRIMARY KEY, topic TEXT NOT NULL, academic_level TEXT NOT NULL, objective TEXT, sub_questions TEXT NOT NULL, findings TEXT NOT NULL, summary TEXT NOT NULL, report TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)'))
                    connection.execute(text("INSERT INTO research_sessions VALUES (7,'Historical topic','MCA',NULL,'[]','[]','Original summary','Original report',CURRENT_TIMESTAMP)"))
                users_file = Path(folder) / 'users.json'
                digest = hashlib.sha256(f'salt:{PASSWORD}'.encode()).hexdigest()
                users_file.write_text(json.dumps({'users': [{'id': 'legacy-user', 'name': 'Legacy User', 'email': 'legacy@example.com', 'password_salt': 'salt', 'password_hash': digest}]}))
                migrate(engine, users_file)
                migrate(engine, users_file)
                sessions = sessionmaker(bind=engine)
                from app.services.user_store import authenticate_user
                with sessions() as db:
                    run = db.query(ResearchRun).one()
                    self.assertEqual(run.id, 7)
                    self.assertEqual(run.report, 'Original report')
                    self.assertIsNone(run.user_id)
                    self.assertEqual(run.status, 'completed')
                    self.assertIsNotNone(run.research_id)
                    user = authenticate_user(db, 'legacy@example.com', PASSWORD)
                    self.assertTrue(user.password_hash.startswith('$argon2id$'))
                    self.assertEqual(db.query(User).count(), 1)
                    from app.services.research_runs import create_run, serialize_run
                    from app.schemas.research import ResearchRequest
                    new_run = create_run(db, user.id, ResearchRequest(topic='Deep learning'), 3)
                    self.assertIsNotNone(new_run.updated_at)
                    self.assertEqual(serialize_run(new_run).status, 'queued')
            finally:
                engine.dispose()


class ServiceTests(unittest.TestCase):
    def test_retries_are_bounded_and_real_fallback_is_used(self):
        class FailingProvider:
            name = 'Primary'
            calls = 0
            def search(self, query, limit):
                self.calls += 1
                raise ResearchProviderError('Unavailable')
        primary = FailingProvider()
        provider = ResilientResearchProvider(primary, RecordedProvider())
        result = asyncio.run(AcademicSearchService(provider).search('Deep learning', 5))
        self.assertEqual(primary.calls, settings.provider_attempts)
        self.assertEqual(result.sources[0].doi, '10.1038/nature14539')
        self.assertIsNotNone(result.warning)

    def test_llm_timeout_is_bounded(self):
        class SlowProvider:
            calls = 0
            async def generate(self, **kwargs):
                self.calls += 1
                await asyncio.sleep(1)
                raise AssertionError('Timeout should cancel this call')
        provider = SlowProvider()
        with patch.object(settings, 'provider_timeout', 0.01), patch.object(settings, 'provider_attempts', 2):
            with self.assertRaises(TimeoutError):
                asyncio.run(LLMService(provider).generate(instruction='test', evidence=[]))
        self.assertEqual(provider.calls, 2)

    def test_production_rejects_insecure_cookie_configuration(self):
        with self.assertRaises(ValueError):
            Settings(environment='production', cookie_secure=False)
        with self.assertRaises(ValueError):
            Settings(cookie_samesite='none', cookie_secure=False)

    def test_missing_abstract_is_not_presented_as_an_excerpt(self):
        from app.agents.summarizer_agent import SummarizerAgent
        summary = SummarizerAgent().summarize('Deep learning', [{'abstract': '', 'snippet': 'No abstract was supplied by the source.'}])
        self.assertIn('metadata only', summary)
        self.assertNotIn('Abstract excerpts:', summary)

    def test_unconfigured_llm_fails_explicitly(self):
        with self.assertRaises(NotImplementedError):
            asyncio.run(LLMService().generate(instruction='test', evidence=[]))


if __name__ == '__main__':
    unittest.main()
