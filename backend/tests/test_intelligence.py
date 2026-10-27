import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import test_foundation
from app.services.intelligence import build_intelligence
from app.services.resource_discovery import discover, fetch
from app.models.research import ResearchRun
from app.models.intelligence import ResearchIntelligence, MODULE_MODELS

def resources(terms):
    return {k: {'status': 'no_verified_matches', 'items': [], 'checked_at': '2026-01-01T00:00:00Z'} for k in ['datasets','courses','active_internships']}

class IntelligenceTests(unittest.TestCase):
    def test_traceability_and_no_fabricated_vacancies(self):
        result=build_intelligence(SimpleNamespace(topic='AI in healthcare', objective='Evaluate bias', research_id='r'), {'sources':[{'id':'p','title':'Paper'}], 'gaps':[{'gap_id':'g'}]}, resources)
        self.assertEqual(result['projects'][0]['paper_ids'], ['p'])
        self.assertEqual(result['projects'][0]['gap_ids'], ['g'])
        self.assertEqual(result['resources']['active_internships']['items'], [])
        self.assertEqual(len(result['roadmap']), 4)
        self.assertFalse(any('url' in role for role in result['suggested_internship_roles']))
    def test_no_evidence(self):
        with self.assertRaises(ValueError):
            build_intelligence(SimpleNamespace(), {}, resources)
    def test_resource_failures(self):
        with patch('app.services.resource_discovery.fetch', side_effect=TimeoutError):
            self.assertEqual(discover('datasets', ['healthcare'])['status'], 'provider_unavailable')
    def test_dataset_verification(self):
        with patch('app.services.resource_discovery.fetch', side_effect=[[{'id':'org/healthcare','cardData':{'license':'mit'}}], '<html>org/healthcare</html>']):
            result=discover('datasets',['healthcare'])
        self.assertEqual(result['items'][0]['license'],'mit')
        self.assertEqual(result['status'],'verified')
    def test_invalid_url_and_metadata(self):
        with self.assertRaises(ValueError): fetch('http://127.0.0.1/private')
        with patch('app.services.resource_discovery.fetch', return_value=[{'id':'../../private'}]):
            self.assertEqual(discover('datasets',['healthcare'])['items'], [])
    def test_saved_api_and_ownership(self):
        fixture=test_foundation.FoundationTests(); fixture.setUp()
        try:
            fixture.signup(); run=fixture.submit(); url='/api/research/'+run['research_id']+'/intelligence'
            self.assertEqual(fixture.client.post(url).status_code,409)
            with fixture.sessions() as db:
                row=db.get(ResearchRun,run['id']); row.status='completed'
                row.result_json=json.dumps({'sources':[{'id':'p','title':'Recorded paper','provider':'Crossref'}]}); db.commit()
            with patch('app.services.intelligence.discover_resources', resources):
                # Default discovery dependency is captured at definition; patch at route boundary instead.
                with patch('app.api.research_routes.build_intelligence', side_effect=lambda r,v: build_intelligence(r,v,resources)) as build:
                    first=fixture.client.post(url); self.assertEqual(first.status_code,200,first.text)
                    self.assertEqual(fixture.client.post(url).json(),first.json()); self.assertEqual(build.call_count,1)
            self.assertEqual(fixture.client.get(url).json(),first.json())
            with fixture.sessions() as db:
                self.assertEqual(db.query(ResearchIntelligence).count(),1)
                for name, model in MODULE_MODELS.items():
                    rows = db.query(model).all()
                    self.assertEqual(len(rows), 1, name)
                    self.assertEqual(rows[0].run_id, run['id'])
                    self.assertEqual(json.loads(rows[0].payload), first.json()['modules'][name])
            fixture.client.post('/api/auth/signout'); fixture.signup(email='other@example.com')
            self.assertEqual(fixture.client.get(url).status_code,404)
            self.assertEqual(fixture.client.post(url).status_code,404)
        finally: fixture.tearDown()

    def test_unverified_course_not_returned(self):
        with patch('app.services.resource_discovery.fetch', return_value='<html>Not a course</html>'):
            self.assertEqual(discover('courses',['healthcare'])['items'], [])

    def test_live_internships_are_separate_and_expired_rejected(self):
        jobs=[{'id':1,'title':'Healthcare intern','url':'https://remotive.com/remote-jobs/1','company_name':'Provider fixture company'},
              {'id':2,'title':'Healthcare internship','url':'https://remotive.com/remote-jobs/2'},
              {'id':3,'title':'Healthcare engineer','url':'https://remotive.com/remote-jobs/3'}]
        with patch('app.services.resource_discovery._job_cache', (0, [])), patch('app.services.resource_discovery.fetch', side_effect=[{'jobs':jobs},'<html>Healthcare intern</html>','Healthcare internship position is closed']):
            found=discover('active_internships',['healthcare'])
        self.assertEqual(len(found['items']),1)
        self.assertEqual(found['items'][0]['id'],'1')

    def test_partial_resources_retained(self):
        with patch('app.services.resource_discovery.fetch', side_effect=[[{'id':'org/healthcare'}], '<html>org/healthcare</html>', TimeoutError()]):
            found=discover('datasets',['healthcare','education'])
        self.assertEqual(found['status'],'partial')
        self.assertEqual(len(found['items']),1)
