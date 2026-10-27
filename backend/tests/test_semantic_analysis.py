import asyncio
import json
import time
import unittest
from pathlib import Path
from app.schemas.research import ResearchRequest, ResearchResult, Source
from app.schemas.evidence_analysis import AnalysisOutput
from app.agents.evidence_analysis import EvidenceExtractor, validate_traceability
from app.agents.semantic_analysis import analyze_evidence, grounded, build_input
from app.agents.research_orchestrator import ResearchOrchestrator
from app.agents.search_agent import SearchAgent
from app.services.llm_service import LLMService, LLMError, ProviderReply, Capacity
from app.core.llm_config import LLMSettings
from test_retrieval import Stub

FIXTURE = Path(__file__).resolve().parents[2] / 'docs' / 'scholarly-live-results.json'


def healthcare():
    papers = json.loads(FIXTURE.read_text(encoding='utf-8-sig'))['flows'][0]['papers']
    result = ResearchResult(sources=[Source.model_validate(p) for p in papers])
    result.evidence = EvidenceExtractor().extract(result.sources)
    return result


def item(e, kind='finding'):
    return dict(claim_text=e.text, claim_type=kind, supporting_evidence_ids=[e.evidence_id],
                supporting_paper_ids=[e.paper_id], confidence=.9, limitations=['Abstract-only author statement; not independently verified.'])


class SemanticFixtureProvider:
    """Deterministic test double; never presented as live model quality validation."""
    async def complete(self, **kwargs):
        data = json.loads(kwargs['data'])
        if 'reviewed_evidence' in data:
            return ProviderReply(json.dumps({'sections':[{'section':'overview','evidence_ids':[data['brief']['evidence'][0]['evidence_id']]}]}), 10, 10)
        if 'papers' not in data:
            e=data['evidence'][0]
            return ProviderReply(json.dumps({'observations':[{'evidence_id':e['evidence_id'],'quote':e['text'],'category':e['kind']}]}),10,10)
        from types import SimpleNamespace
        evidence = [SimpleNamespace(**e) for e in data['evidence']]
        findings = [item(e) for e in evidence if e.text.startswith(('The findings suggest', 'The findings also indicate'))]
        limits = [item(e, 'limitation') for e in evidence if e.text.startswith('Nevertheless, this science')]
        first = next(e for e in evidence if e.text.startswith('The findings suggest'))
        other = next(e for e in evidence if e.text.startswith('Several types of AI'))
        output = dict(claims=findings+limits, comparisons=[dict(conclusion='These sources describe applications of AI in healthcare, with different application emphases.',
            relation='agreement', supporting_evidence_ids=[first.evidence_id, other.evidence_id], supporting_paper_ids=[first.paper_id, other.paper_id],
            limitations=['Reviews do not establish comparable effect sizes.'])], candidate_gaps=[])
        if limits:
            output['candidate_gaps']=[dict(description='Investigate privacy and safety challenges in healthcare AI implementation.',basis='inferred',
                supporting_evidence_ids=limits[0]['supporting_evidence_ids'], supporting_paper_ids=limits[0]['supporting_paper_ids'],
                limitations=['Candidate direction, not established field-wide novelty.'])]
        return ProviderReply(json.dumps(output), 120, 80)


def service(provider=None):
    return LLMService(provider=provider, config=LLMSettings(model='mock-semantic',max_input_tokens=64000,
        run_token_budget=200000,max_attempts=1), capacity=Capacity(1))


class SemanticTests(unittest.IsolatedAsyncioTestCase):
    async def test_healthcare_finds_source_reported_results_without_trigger_words(self):
        r=healthcare();request=ResearchRequest(topic='Artificial Intelligence in Healthcare')
        output=await analyze_evidence(request,r,service(SemanticFixtureProvider()))
        self.assertEqual(len(r.evidence),30)
        self.assertEqual(len(r.key_findings),2)
        self.assertEqual(output.status,'completed')
        self.assertEqual(output.comparisons[0].grounding,'uncertain')
        self.assertEqual(output.candidate_gaps[0].basis,'inferred')
        self.assertEqual(r.gaps,[])
        validate_traceability(r)

    async def test_end_to_end_saved_retrieval_fixture(self):
        r=healthcare(); start=time.monotonic()
        llm=service(SemanticFixtureProvider())
        engine=ResearchOrchestrator(SearchAgent(provider=Stub([p.model_dump() for p in r.sources])),llm_service=llm)
        result=await engine.run_async(ResearchRequest(topic='Artificial Intelligence in Healthcare',source_target=5),'semantic-fixture')
        self.assertEqual(len(result.key_findings),2)
        self.assertIn('Provisional cross-paper',result.report)
        validate_traceability(result)
        import test_foundation
        from app.models.research import ResearchRun
        from app.models.analysis import ResearchAnalysisRevision, ResearchFinding
        from app.services.research_artifacts import persist_artifacts
        fixture=test_foundation.FoundationTests(); fixture.setUp()
        try:
            fixture.signup(); created=fixture.submit()
            with fixture.sessions() as db:
                run=db.get(ResearchRun,created['id'])
                persist_artifacts(db,run,result); db.commit()
                persist_artifacts(db,run,result); db.commit()
                self.assertEqual(db.query(ResearchAnalysisRevision).count(),1)
                self.assertEqual(db.query(ResearchFinding).count(),2)
                saved=json.loads(db.query(ResearchAnalysisRevision).one().payload)
                self.assertEqual(len(saved['evidence']),30)
                changed=result.model_copy(deep=True)
                changed.evidence_analysis.revision='new-revision-fixture'
                persist_artifacts(db,run,changed); db.commit()
                self.assertEqual(db.query(ResearchAnalysisRevision).count(),2)
                run.result_json=result.model_dump_json(); run.status='completed'; db.commit()
            response=fixture.client.get('/api/research/'+created['research_id'])
            self.assertEqual(response.status_code,200)
            self.assertEqual(len(response.json()['modules']['evidence_analysis']['claims']),3)
        finally: fixture.tearDown()
        print(json.dumps(dict(test='saved_healthcare_e2e',mode='mocked_llm_and_replayed_retrieval',papers=len(result.sources),
            evidence=len(result.evidence),supported_findings=len(result.key_findings),established_gaps=len(result.gaps),
            candidate_gaps=len(result.evidence_analysis.candidate_gaps),rejected=len(result.evidence_analysis.rejected),
            input_tokens=sum(d.input_tokens for d in llm.diagnostics),output_tokens=sum(d.output_tokens for d in llm.diagnostics),
            duration_ms=round((time.monotonic()-start)*1000))))

    async def test_missing_evidence_and_failure_preserve_fallback(self):
        class Failed:
            async def complete(self, **kw): raise LLMError('PROVIDER_UNAVAILABLE')
        request=ResearchRequest(topic='Healthcare AI')
        self.assertEqual((await analyze_evidence(request,ResearchResult(),service(Failed()))).status,'missing_evidence')
        r=healthcare(); original=list(r.key_findings)
        self.assertEqual((await analyze_evidence(request,r,service(Failed()))).status,'failed')
        self.assertEqual(r.key_findings,original)
        self.assertEqual((await analyze_evidence(request,r,service())).status,'disabled')

    async def test_invalid_ids_numbers_and_uncertain_paraphrase(self):
        r=healthcare();brief=build_input(ResearchRequest(topic='Healthcare AI'),r,50000)
        e=r.evidence[0]
        invalid=item(e);invalid['supporting_evidence_ids']=['not-real']
        numeric=item(e);numeric['claim_text']='AI healthcare improved by 99.97 percent.'
        paraphrase=item(e);paraphrase['claim_text']='AI applications may transform healthcare.'
        output=grounded(AnalysisOutput(claims=[invalid,numeric,paraphrase],comparisons=[],candidate_gaps=[]),brief)
        self.assertEqual(len(output.rejected),2)
        self.assertEqual(output.claims[0].grounding,'uncertain')

    async def test_conflicts_need_two_papers_and_remain_uncertain(self):
        r=healthcare(); brief=build_input(ResearchRequest(topic='Healthcare AI'),r,50000)
        a=r.evidence[0]; b=next(e for e in r.evidence if e.paper_id!=a.paper_id)
        comparison=dict(conclusion='AI healthcare findings may conflict across applications.',relation='conflict',
            supporting_evidence_ids=[a.evidence_id,b.evidence_id],supporting_paper_ids=[a.paper_id,b.paper_id],limitations=['Different applications; no established contradiction.'])
        output=grounded(AnalysisOutput(claims=[],comparisons=[comparison],candidate_gaps=[]),brief)
        self.assertEqual(output.comparisons[0].grounding,'uncertain')
        comparison['supporting_paper_ids']=[a.paper_id,a.paper_id]
        self.assertTrue(grounded(AnalysisOutput(claims=[],comparisons=[comparison],candidate_gaps=[]),brief).rejected)

    async def test_empty_model_output_does_not_force_findings(self):
        class Empty:
            async def complete(self, **kw):
                return ProviderReply('{"claims":[],"comparisons":[],"candidate_gaps":[]}',1,1)
        r=healthcare()
        output=await analyze_evidence(ResearchRequest(topic='Healthcare AI'),r,service(Empty()))
        self.assertEqual(output.claims,[])
        self.assertEqual(r.key_findings,[])

    async def test_actual_opposing_passages_remain_provisional(self):
        a=Source(id='a',provider='Synthetic test fixture',title='Trial A',abstract='Treatment improved patient survival.',url='https://example.org/a')
        b=Source(id='b',provider='Synthetic test fixture',title='Trial B',abstract='Treatment did not improve patient survival.',url='https://example.org/b')
        r=ResearchResult(sources=[a,b]);r.evidence=EvidenceExtractor().extract(r.sources)
        brief=build_input(ResearchRequest(topic='Patient survival'),r,50000)
        comparison=dict(conclusion='Treatment effects on patient survival differ between these trials.',relation='conflict',
            supporting_evidence_ids=[e.evidence_id for e in r.evidence], supporting_paper_ids=['a','b'],
            limitations=['Population and treatment comparability require verification.'])
        output=grounded(AnalysisOutput(claims=[],comparisons=[comparison],candidate_gaps=[]),brief)
        self.assertEqual(output.comparisons[0].grounding,'uncertain')
        self.assertEqual(r.gaps,[])
