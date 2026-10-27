"""Same verified evidence and resource records; different review obligations."""
import copy
import unittest
from types import SimpleNamespace
from app.services.depth_policy import depth_policy
from app.services.result_modules import canonical_result
from app.services.intelligence import build_intelligence
from app.agents.semantic_analysis import build_input
from app.agents.llm_agents import agent_input
from app.schemas.research import ResearchRequest, ResearchResult
from test_report_engine import fixture_result
from test_intelligence import resources


class AcademicPolicyTests(unittest.TestCase):
    def test_all_frontend_levels_define_complete_policies(self):
        for level in ('Undergraduate','MCA',"Master's",'PhD'):
            policy=depth_policy(level)
            for name in ('focus','technical_complexity','explanation_style','methodology','evidence_requirements',
                         'difficulty','learning_recommendations','report_heading','gap_review','career_preparation'):
                self.assertTrue(getattr(policy,name), (level,name))
            self.assertIn('Never invent',policy.instruction())

    def test_same_evidence_changes_tasks_not_verified_records(self):
        result=fixture_result(); original=result.model_dump_json()
        outputs={}
        def discovery(terms):
            value=resources(terms)
            value['courses']['items']=[dict(id='fixture-course',title='Fixture introductory course',provider='Fixture provider',
                difficulty='Beginner',skills=['Python'],url='https://example.org/course',checked_at='2026-01-01T00:00:00Z',
                classification_basis='Test fixture')]
            return value
        for level in ('Undergraduate','MCA',"Master's",'PhD'):
            request=ResearchRequest(topic='AI in healthcare',objective='Compare evaluation methods',academic_level=level)
            run=SimpleNamespace(**request.model_dump(),research_id='fixture')
            enrichment=build_intelligence(run,result.model_dump(),discovery)
            output=canonical_result(request,result,enrichment);outputs[level]=output
            self.assertEqual(result.model_dump_json(),original)
            self.assertEqual(output.courses[0].difficulty,'Beginner')
            self.assertEqual(str(output.courses[0].url),'https://example.org/course')
            self.assertEqual(output.research_gaps,outputs['Undergraduate'].research_gaps)
            self.assertEqual(output.papers,outputs['Undergraduate'].papers)
            self.assertIn(depth_policy(level).report_heading,[s.name for s in output.report.sections])
            semantic=build_input(request,result,50000)
            review=agent_input(request,result.evidence,50000)
            self.assertEqual(semantic.academic_policy,depth_policy(level).instruction())
            self.assertEqual(review.academic_policy,semantic.academic_policy)
        self.assertEqual(len({o.projects[1].problem_statement for o in outputs.values()}),4)
        self.assertEqual(len({tuple(o.career_paths[0].pathway) for o in outputs.values()}),4)
        self.assertEqual(len({o.courses[0].reason_for_recommendation for o in outputs.values()}),4)
        self.assertIn('Dataset validation',[s.name for s in outputs['MCA'].skills])
        phd=next(s for s in outputs['PhD'].report.sections if s.name==depth_policy('PhD').report_heading)
        self.assertFalse(phd.complete)
        self.assertIn('No licensed full text',phd.content)

    def test_missing_evidence_never_fills_requirements_with_claims(self):
        for level in ('Undergraduate','MCA',"Master's",'PhD'):
            result=fixture_result();result.evidence=[];result.key_findings=[];result.gaps=[]
            for paper in result.sources: paper.abstract=''
            report=canonical_result(ResearchRequest(topic='Healthcare AI',academic_level=level),result)
            self.assertEqual(report.research_gaps,[])
            self.assertEqual(report.report.claims,[])
            review=next(s for s in report.report.sections if s.name==depth_policy(level).report_heading)
            self.assertFalse(review.complete)
            self.assertIn('No explicit methods passage',review.content)
