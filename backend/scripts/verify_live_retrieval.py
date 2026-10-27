"""Opt-in real network verification; never included in unittest discovery.
Run from backend: python scripts/verify_live_retrieval.py
Writes public paper metadata and counts; uses only a temporary database/account.
"""
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import get_db
from app.db.migrations import migrate
from app.services.research_provider import OpenAlexProvider, CrossrefProvider, SemanticScholarProvider, ResilientResearchProvider
from app.core.logging import configure_logging
from app.agents.evidence_analysis import validate_traceability
from app.schemas.research import ResearchResult
from app.models.analysis import ResearchPaper, ResearchEvidence, ResearchReport

TOPICS = ['Artificial Intelligence in Healthcare', 'Machine Learning in Education',
          'Cybersecurity using Blockchain', 'AI adoption in Indian higher education']
report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'provider_checks': [], 'flows': []}
configure_logging()
for cls in (OpenAlexProvider, CrossrefProvider, SemanticScholarProvider):
    provider = ResilientResearchProvider(providers=[cls()])
    papers = provider.search(TOPICS[0], 5)
    report['provider_checks'].append({'provider': cls.name, 'status': provider.last_status,
                                    'papers': papers, 'diagnostics': provider.last_diagnostics})
    print(f'{cls.name}: {provider.last_status}; {len(papers)} accepted', flush=True)

with tempfile.TemporaryDirectory() as folder:
    engine = create_engine(f'sqlite:///{Path(folder) / "live.db"}', connect_args={'check_same_thread': False})
    sessions = sessionmaker(bind=engine)
    migrate(engine, Path(folder) / 'no-users.json')
    def db_override():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = db_override
    client = TestClient(app, headers={'X-ResearchOS-Client': 'web', 'Origin': 'http://localhost:5173'})
    try:
        signup = client.post('/api/auth/signup', json={'name': 'Retrieval Verification', 'email': 'retrieval-check@example.com', 'password': 'Temporary verification password! 23'})
        assert signup.status_code == 201, signup.text
        client.headers['X-CSRF-Token'] = signup.json()['csrf_token']
        for topic in TOPICS:
            with patch('app.services.execution.SessionLocal', sessions):
                submitted = client.post('/api/research', json={'topic': topic, 'objective': 'Review applications and empirical evidence', 'academic_level': 'MCA', 'source_target': 5})
            assert submitted.status_code == 202, submitted.text
            run = client.get('/api/research/' + submitted.json()['research_id']).json()
            diagnostics = run['provider_diagnostics']
            entry = {'topic': topic, 'status': run['status'], 'retrieval_status': run['retrieval_status'],
                     'returned': sum(d['returned'] for d in diagnostics),
                     'valid': sum(d['valid'] for d in diagnostics),
                     'rejected': sum(d['rejected'] for d in diagnostics),
                     'duplicates': sum(d['duplicates'] for d in diagnostics),
                     'saved': len(run['sources']), 'evidence_passages': len(run['evidence']),
                     'supported_findings': len(run['key_findings']), 'supported_gaps': len(run['gaps']),
                     'missing_sections': run['missing_sections'], 'diagnostics': diagnostics, 'papers': run['sources']}
            report['flows'].append(entry)
            print(json.dumps({k:v for k,v in entry.items() if k not in ('papers','diagnostics')}), flush=True)
            assert run['status'] == 'completed', run.get('error_message')
            assert run['sources'] and run['report'] and run['findings'] and run['progress'] == 100
            validate_traceability(ResearchResult.model_validate(run))
            assert run['intent'] and run['citations'] and run['report_sections']
            with sessions() as db:
                assert db.query(ResearchPaper).filter_by(run_id=run['id']).count() == len(run['sources'])
                assert db.query(ResearchEvidence).filter_by(run_id=run['id']).count() == len(run['evidence'])
                assert db.get(ResearchReport, run['id']).content == run['report']
            assert client.get('/api/research/' + str(run['id'])).json()['report'] == run['report']
        assert len(client.get('/api/research/history').json()) == len(TOPICS)
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()
        target = Path(__file__).resolve().parents[2] / 'docs' / 'analysis-live-results.json'
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'Report: {target}', flush=True)
