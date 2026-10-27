"""Same retained paper evidence, different settings: facts must not be manufactured."""
import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pydantic import ValidationError
from app.schemas.research import ResearchRequest, ResearchResult
from app.schemas.modules import CanonicalResearchResult
from app.services.result_modules import canonical_result
from app.services.intelligence import build_intelligence
from app.agents.research_orchestrator import ResearchOrchestrator
from app.agents.search_agent import SearchAgent
from app.services.research_runs import serialize_run
from app.api.research_routes import intelligence_view
from app.models.research import ResearchRun
import test_foundation
from test_analysis import analysis_paper
from test_retrieval import Stub
from test_intelligence import resources

class ModuleFlowTests(unittest.TestCase):
    def test_same_evidence_four_levels_three_outputs_two_citation_styles(self):
        depths, tasks, structures, citations = {}, {}, {}, {}
        paper=analysis_paper()
        for level in ['Undergraduate','MCA',"Master's",'PhD']:
            for output in ['academic_report','literature_review','project_proposal']:
                for style in ['apa','ieee']:
                    request=ResearchRequest(topic='Deep learning', objective='Compare validation methods', academic_level=level, output_type=output, citation_style=style, source_target=5)
                    result=ResearchOrchestrator(SearchAgent(provider=Stub([paper.model_dump()]))).run('Deep learning',level,request.objective,output,style,5)
                    run=SimpleNamespace(**request.model_dump(),research_id='test')
                    enrichment=build_intelligence(run,result,resources)
                    modules=canonical_result(request,ResearchResult.model_validate(result),enrichment)
                    depths[level]=modules.overview.analysis_depth
                    tasks[level]=modules.projects[1].expected_outcome
                    structures[output]=tuple(s.name for s in modules.report.sections)
                    citations[style]=modules.papers[0].citation.reference
                    self.assertEqual(modules.papers[0].abstract,paper.abstract)
                    self.assertEqual(modules.sources[0].provider,'Recorded provider')
                    self.assertNotIn('abstract',modules.sources[0].model_dump())
                    self.assertIn('abstract',modules.papers[0].model_dump())
                    self.assertEqual(modules.overview.source_target,5)
                    for gap in modules.research_gaps:
                        self.assertIn(gap.description,paper.abstract)
                    self.assertEqual(modules.datasets,[])
        self.assertEqual(len(set(depths.values())),4)
        self.assertEqual(len(set(tasks.values())),4)
        self.assertEqual(len(set(structures.values())),3)
        self.assertNotEqual(citations['apa'],citations['ieee'])
        self.assertTrue(citations['ieee'].startswith('[1]'))

    def test_wrong_module_shape_rejected(self):
        request=ResearchRequest(topic='Deep learning')
        view=canonical_result(request,ResearchResult()).model_dump()
        view['datasets']=[{'title':'Repeated overview text'}]
        with self.assertRaises(ValidationError): CanonicalResearchResult.model_validate(view)

    def test_old_saved_run_is_adapted_without_overwriting_evidence(self):
        fixture=test_foundation.FoundationTests(); fixture.setUp()
        try:
            fixture.signup(); created=fixture.submit()
            paper=analysis_paper()
            old={'sources':[paper.model_dump()], 'summary':'Historical summary', 'report':'Historical original report'}
            with fixture.sessions() as db:
                run=db.get(ResearchRun,created['id']);run.status='completed';run.academic_level='PhD';run.result_json=json.dumps(old);db.commit()
                original=run.result_json
                response=serialize_run(run)
                self.assertEqual(response.report,old['report'])
                self.assertIn('critical novelty',response.modules.overview.analysis_depth)
                legacy=build_intelligence(run,old,resources);legacy['version']=1
                with patch('app.services.resource_discovery.fetch',side_effect=AssertionError('No network on old snapshot read')):
                    adapted=intelligence_view(run,legacy)
                self.assertEqual(adapted['version'],2)
                self.assertEqual(adapted['modules']['papers'][0]['abstract'],paper.abstract)
                db.refresh(run); self.assertEqual(run.result_json,original)
        finally: fixture.tearDown()

    def test_source_target_reaches_search_and_caps_papers(self):
        for target in (5,10,15):
            provider=Stub([analysis_paper().model_dump()])
            original_search=provider.search
            requested_limits=[]
            def search(query, limit):
                requested_limits.append(limit)
                return original_search(query,limit)
            provider.search=search
            result=ResearchOrchestrator(SearchAgent(provider=provider)).run('Deep learning','MCA',source_limit=target)
            self.assertLessEqual(len(result['sources']),target)
            self.assertTrue(provider.calls)
            self.assertIn(target,requested_limits)

