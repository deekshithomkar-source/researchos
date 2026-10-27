"""No live credentials or model calls. HTTP envelopes and malicious outputs are mocked."""
import asyncio
import json
import unittest
from unittest.mock import patch
import httpx
from pydantic import BaseModel, ValidationError
from app.core.llm_config import LLMSettings
from app.services.llm_service import LLMService, OpenAIResponsesProvider, ProviderReply, LLMError, Capacity
from app.schemas.llm import EvidenceReview, SynthesisPlan
from app.agents.llm_agents import agent_input, EvidenceReviewAgent, analyze_with_llm, OUTPUT_POLICIES
from app.agents.evidence_analysis import EvidenceExtractor
from app.agents.research_orchestrator import ResearchOrchestrator
from app.agents.search_agent import SearchAgent
from app.schemas.research import ResearchRequest, ResearchResult
from app.services.result_modules import canonical_result
from app.services.execution import execute_research
from app.models.research import ResearchRun
from test_analysis import analysis_paper
from test_retrieval import Stub
import test_foundation

class Input(BaseModel):
    topic: str

class Fake:
    def __init__(self, replies): self.replies=list(replies); self.calls=[]
    async def complete(self, **kwargs):
        self.calls.append(kwargs)
        reply=self.replies.pop(0)
        if isinstance(reply,Exception): raise reply
        return ProviderReply(reply,20,10)

class PolicyModel:
    def __init__(self): self.calls=[]
    async def complete(self, **kwargs):
        data=json.loads(kwargs['data']); self.calls.append(data)
        if 'papers' in data:
            return ProviderReply(json.dumps({'claims':[], 'comparisons':[], 'candidate_gaps':[]}),100,50)
        if 'reviewed_evidence' in data:
            evidence=data['reviewed_evidence']['observations']
            name='methods' if evidence[0]['category']=='method' else 'limitations'
            return ProviderReply(json.dumps({'sections':[{'section':name,'evidence_ids':[e['evidence_id'] for e in evidence]}]}),100,50)
        expected='limitation' if data['academic_level']=='PhD' else 'method'
        selected=[e for e in data['evidence'] if e['kind']==expected][:1]
        return ProviderReply(json.dumps({'observations':[{'evidence_id':e['evidence_id'],'quote':e['text'],'category':e['kind']} for e in selected]}),100,50)

def config(**overrides):
    return LLMSettings(model='test-model',max_retry_delay=0,**overrides)

def result():
    r=ResearchResult(sources=[analysis_paper()]); r.evidence=EvidenceExtractor().extract(r.sources); return r

class LLMServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_json_missing_fields_retry_bounded(self):
        for invalid in ('not json', '{}', '{"observations":[],"invented_url":"https://fake.invalid"}'):
            provider=Fake([invalid, '{"observations":[]}'])
            service=LLMService(provider,config())
            output=await service.generate_structured(instruction='review',data=Input(topic='test'),output_schema=EvidenceReview,agent='review')
            self.assertEqual(output.observations,[]); self.assertEqual(len(provider.calls),2)
            self.assertEqual(service.diagnostics[0].input_tokens,40)

    async def test_invalid_output_exhaustion_and_provider_failure(self):
        for replies,code in [(['bad','bad'],'INVALID_STRUCTURED_OUTPUT'),([LLMError('PROVIDER_UNAVAILABLE',True)]*2,'PROVIDER_UNAVAILABLE'),([RuntimeError('private secret')],'MODEL_ERROR')]:
            service=LLMService(Fake(replies),config())
            with self.assertRaises(LLMError) as error:
                await service.generate_structured(instruction='test',data=Input(topic='test'),output_schema=EvidenceReview,agent='review')
            self.assertEqual(str(error.exception),code)

    async def test_text_and_safe_run_scoped_cache(self):
        provider=Fake(['Explanation'])
        service=LLMService(provider,config(),namespace='unique-test-run')
        for _ in range(2): self.assertEqual(await service.generate_text(instruction='Explain',data=Input(topic='test')),'Explanation')
        self.assertEqual(len(provider.calls),1);self.assertTrue(service.diagnostics[-1].cached)
        other=LLMService(Fake(['Other']),config(),namespace='different-owner-run')
        self.assertEqual(await other.generate_text(instruction='Explain',data=Input(topic='test')),'Other')

    async def test_budget_limits_before_provider_call(self):
        for overrides,code in [({'max_input_tokens':100},'INPUT_TOKEN_LIMIT'),({'run_token_budget':100},'RUN_TOKEN_BUDGET')]:
            provider=Fake([]);service=LLMService(provider,config(**overrides))
            with self.assertRaises(LLMError) as error: await service.generate_text(instruction='text',data=Input(topic='x'*200))
            self.assertEqual(error.exception.code,code);self.assertEqual(provider.calls,[])

    async def test_timeout_and_concurrency(self):
        class Slow:
            active=0;peak=0
            async def complete(self,**kwargs):
                self.active+=1;self.peak=max(self.peak,self.active)
                try:
                    await asyncio.sleep(.03)
                    return ProviderReply('ok')
                finally: self.active-=1
        provider=Slow();gate=Capacity(1)
        services=[LLMService(provider,config(timeout_seconds=.2),capacity=gate) for _ in range(3)]
        await asyncio.gather(*(s.generate_text(instruction='test',data=Input(topic='t')) for s in services))
        self.assertEqual(provider.peak,1);self.assertEqual(gate.active,0)
        service=LLMService(provider,config(timeout_seconds=.01),capacity=gate)
        with self.assertRaises(LLMError) as error: await service.generate_text(instruction='test',data=Input(topic='t'))
        self.assertEqual(error.exception.code,'TIMEOUT');self.assertEqual(gate.active,0)
        self.assertEqual(service.diagnostics[-1].attempts,2)

    async def test_grounding_rejects_fabricated_quote_id_category(self):
        brief=agent_input(ResearchRequest(topic='Deep learning'),result().evidence,5000)
        original=brief.evidence[0]
        for change in [{'evidence_id':'invented'}, {'quote':'Invented 99% accuracy'}, {'category':'finding'}]:
            item={'evidence_id':original.evidence_id,'quote':original.text,'category':original.kind,**change}
            service=LLMService(Fake([json.dumps({'observations':[item]})]*2),config())
            with self.assertRaises(LLMError) as error: await EvidenceReviewAgent(service).execute(brief)
            self.assertEqual(error.exception.code,'UNSUPPORTED_EVIDENCE')

    async def test_mca_phd_and_output_policies(self):
        selected=[]
        for level in ('MCA','PhD'):
            for output in OUTPUT_POLICIES:
                provider=PolicyModel();service=LLMService(provider,config())
                request=ResearchRequest(topic='Deep learning',academic_level=level,report_type=output)
                analysis=await analyze_with_llm(request,result(),service)
                self.assertEqual(analysis.status,'completed',analysis.notice)
                self.assertEqual(provider.calls[0]['output_policy'],OUTPUT_POLICIES[output])
                self.assertEqual(provider.calls[0]['academic_level'],level)
                self.assertNotIn('history',provider.calls[0])
                selected.append(analysis.observations[0].category)
        count = len(OUTPUT_POLICIES)
        self.assertEqual(selected[:count], ['method'] * count); self.assertEqual(selected[count:], ['limitation'] * count)

    async def test_no_evidence_or_disabled_skips_model(self):
        provider=Fake([]);service=LLMService(provider,config())
        value=await analyze_with_llm(ResearchRequest(topic='Deep learning'),ResearchResult(),service)
        self.assertEqual(value.status,'missing_evidence');self.assertEqual(provider.calls,[])
        self.assertEqual((await analyze_with_llm(ResearchRequest(topic='Deep learning'),result(),LLMService(config=config()))).status,'disabled')

    async def test_partial_synthesis_failure_retains_grounded_review(self):
        r=result();e=r.evidence[0]
        provider=Fake([json.dumps({'observations':[{'evidence_id':e.evidence_id,'quote':e.text,'category':e.kind}]}),LLMError('TOKEN_LIMIT')])
        value=await analyze_with_llm(ResearchRequest(topic='Deep learning'),r,LLMService(provider,config()))
        self.assertEqual(value.status,'partial'); self.assertEqual(len(value.observations),1)
        self.assertIn('TOKEN_LIMIT',value.notice)

class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_adapter_request_and_response_shape(self):
        captured=[]
        def handler(request):
            captured.append(json.loads(request.content))
            return httpx.Response(200,json={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"observations":[]}'}]}],'usage':{'input_tokens':42,'output_tokens':9}})
        cfg=config(api_key='test-only-secret')
        service=LLMService(OpenAIResponsesProvider(cfg,httpx.MockTransport(handler)),cfg,capacity=Capacity(2))
        await service.generate_structured(instruction='safe instruction',data=Input(topic='untrusted topic'),output_schema=EvidenceReview,agent='review')
        self.assertFalse(captured[0]['store']);self.assertEqual(captured[0]['tools'],[])
        self.assertEqual(captured[0]['text']['format']['type'],'json_schema')
        self.assertFalse(captured[0]['text']['format']['schema']['additionalProperties'])
        self.assertEqual(captured[0]['instructions'],'safe instruction')
        self.assertNotIn('test-only-secret',json.dumps(captured))

    async def test_http_errors_refusal_truncation_and_retry_after(self):
        for status,payload,headers,expected in [
            (429,{}, {'retry-after':'60'},'RATE_LIMITED'), (401,{}, {},'AUTHENTICATION_ERROR'),
            (400,{}, {},'MODEL_ERROR'), (503,{}, {},'PROVIDER_UNAVAILABLE'),
            (200,{'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'}},{},'TOKEN_LIMIT'),
            (200,{'status':'completed','output':[{'content':[{'type':'refusal'}]}]}, {},'REFUSAL'),
            (200,{'status':'completed','output':[]},{},'INVALID_PROVIDER_RESPONSE')]:
            calls=[]
            def handler(request): calls.append(1);return httpx.Response(status,json=payload,headers=headers)
            cfg=config();service=LLMService(OpenAIResponsesProvider(cfg,httpx.MockTransport(handler)),cfg,capacity=Capacity(2))
            with self.assertRaises(LLMError) as error: await service.generate_text(instruction='test',data=Input(topic='t'))
            self.assertEqual(error.exception.code,expected)
            self.assertLessEqual(len(calls),2)
            if status==429: self.assertEqual(len(calls),1)

    async def test_config_rejects_missing_key_and_schema_extra_fields(self):
        with self.assertRaises(ValidationError): LLMSettings(enabled=True,model='configured')
        with self.assertRaises(ValidationError): EvidenceReview.model_validate({'observations':[],'papers':['invented']})

class PipelineLLMTests(unittest.TestCase):
    def test_pipeline_persists_grounded_analysis_and_read_does_not_regenerate(self):
        fixture=test_foundation.FoundationTests();fixture.setUp()
        try:
            fixture.signup();created=fixture.submit();provider=PolicyModel()
            service=LLMService(provider,config())
            orchestrator=ResearchOrchestrator(SearchAgent(provider=Stub([analysis_paper().model_dump()])),llm_service=service)
            execute_research(created['research_id'],fixture.sessions,lambda:orchestrator)
            response=fixture.client.get('/api/research/'+created['research_id'])
            self.assertEqual(response.status_code,200,response.text)
            saved=response.json();self.assertEqual(saved['llm_analysis']['status'],'completed')
            self.assertIn('LLM-selected, exact source evidence',saved['modules']['report']['markdown'])
            self.assertEqual(len(provider.calls),3)
            with fixture.sessions() as db:
                persisted=json.loads(db.get(ResearchRun,created['id']).result_json)
                self.assertTrue(persisted['llm_analysis']['observations'][0]['evidence_id'])
            fixture.client.get('/api/research/'+created['research_id']);self.assertEqual(len(provider.calls),3)
        finally: fixture.tearDown()

class LLMIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def test_usage_logs_redact_prompts_keys_and_provider_errors(self):
        cfg=config(api_key='private-key-marker')
        service=LLMService(Fake([RuntimeError('private-provider-body-marker')]),cfg)
        with self.assertLogs('researchos.llm',level='INFO') as captured:
            with self.assertRaises(LLMError):
                await service.generate_text(instruction='private-instruction-marker',data=Input(topic='private-topic-marker'))
        text=' '.join(captured.output)+json.dumps([d.model_dump() for d in service.diagnostics])
        self.assertNotIn('private-',text)
        self.assertIn('MODEL_ERROR',text)
        self.assertGreater(service.diagnostics[0].reserved_tokens,0)

    async def test_rate_limit_cooldown_is_shared_across_services(self):
        gate=Capacity(2)
        first=LLMService(Fake([LLMError('RATE_LIMITED',True,60)]),config(),capacity=gate)
        with self.assertRaises(LLMError): await first.generate_text(instruction='test',data=Input(topic='test'))
        second_provider=Fake([]);second=LLMService(second_provider,config(),capacity=gate)
        with self.assertRaises(LLMError) as error: await second.generate_text(instruction='test',data=Input(topic='test'))
        self.assertEqual(error.exception.code,'RATE_LIMITED');self.assertFalse(second_provider.calls)
        self.assertEqual(gate.active,0)

    async def test_cancellation_releases_admission_slot(self):
        started=asyncio.Event()
        class Blocking:
            async def complete(self,**kwargs):
                started.set();await asyncio.sleep(10)
        gate=Capacity(1);service=LLMService(Blocking(),config(),capacity=gate)
        task=asyncio.create_task(service.generate_text(instruction='test',data=Input(topic='test')))
        await started.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertEqual(gate.active,0)

    async def test_synthesis_cannot_invent_ids_or_directions(self):
        from app.agents.llm_agents import synthesis_validator
        observation={'evidence_id':'e','quote':'Methods in a recorded test excerpt.','category':'method'}
        check=synthesis_validator(EvidenceReview(observations=[observation]))
        for section,ids in [('overview',['invented']),('findings',['e']),('directions',['e'])]:
            with self.assertRaises(LLMError): check(SynthesisPlan(sections=[{'section':section,'evidence_ids':ids}]))

    async def test_truncated_response_still_records_billed_usage(self):
        def handler(request):
            return httpx.Response(200,json={'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'},'usage':{'input_tokens':60,'output_tokens':2000}})
        cfg=config();service=LLMService(OpenAIResponsesProvider(cfg,httpx.MockTransport(handler)),cfg,capacity=Capacity(1))
        with self.assertRaises(LLMError): await service.generate_text(instruction='test',data=Input(topic='test'))
        self.assertEqual(service.diagnostics[-1].input_tokens,60)
        self.assertEqual(service.diagnostics[-1].output_tokens,2000)
