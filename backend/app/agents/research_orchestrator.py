"""Incremental research pipeline, independent of HTTP, database, and worker choice."""
import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.agents.contracts import Agent, AgentContext
from app.agents.planner_agent import PlannerAgent
from app.agents.report_agent import ReportAgent
from app.agents.search_agent import SearchAgent
from app.agents.summarizer_agent import SummarizerAgent
from app.schemas.research import Finding, ResearchRequest, ResearchResult, Source
from app.services.search_queries import generate_queries
from app.services.research_provider import research_context
from app.agents.evidence_analysis import (IntentAnalyzer, ResearchQuestionGenerator, RelevanceEvaluator,
    EvidenceExtractor, SupportedGapDetector, extract_findings, validate_traceability)
from app.agents.evidence_synthesis import synthesize_sections
from app.services.scholar_discovery import discover_scholars
from app.services.full_text import FullTextService
from app.core.config import settings
from app.services.llm_service import LLMService
from app.agents.llm_agents import analyze_with_llm
from app.agents.semantic_analysis import analyze_evidence


class NoEvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PipelineStage:
    status: str
    name: str
    progress: int
    message: str
    execute: Callable[[AgentContext], Awaitable[None]]


Checkpoint = Callable[[PipelineStage, ResearchResult], None]


class ResearchOrchestrator:
    def __init__(self, searcher: SearchAgent | None = None, *, gap_agent: Agent | None = None, llm_service: LLMService | None = None, fulltext_service=None):
        self.fulltext_service = fulltext_service or FullTextService(enabled=settings.fulltext_enabled)
        self._injected_llm_service = llm_service
        self.llm_service = llm_service
        self.planner = PlannerAgent()
        self.searcher = searcher or SearchAgent()
        self.summarizer = SummarizerAgent()
        self.reporter = ReportAgent()
        self.gap_agent = gap_agent  # An optional real implementation; no fabricated fallback.

    def stages(self) -> list[PipelineStage]:
        return [
            PipelineStage('planning', 'intent', 5, 'Reading the research brief', self.intent),
            PipelineStage('planning', 'research_plan', 10, 'Planning research questions', self.plan),
            PipelineStage('planning', 'query_generation', 20, 'Preparing the topic search query', self.queries),
            PipelineStage('searching', 'searching_sources', 35, 'Searching relevant scholarly sources', self.discover),
            PipelineStage('validating', 'source_evaluation', 55, 'Evaluating source metadata', self.evaluate),
            PipelineStage('extracting', 'source_evidence', 65, 'Extracting traceable source passages', self.extract),
            PipelineStage('analyzing', 'evidence_coverage', 75, 'Analyzing author-reported findings and gaps', self.analyze),
            PipelineStage('synthesizing', 'report_generation', 85, 'Preparing the evidence summary and report', self.synthesize),
        ]

    async def run_async(self, request: ResearchRequest, research_id: str = '', checkpoint: Checkpoint | None = None) -> ResearchResult:
        self.llm_service = self._injected_llm_service or LLMService(namespace=research_id)
        token = research_context.set(research_id)
        try:
            return await self._run_stages(request, research_id, checkpoint)
        finally:
            research_context.reset(token)

    async def _run_stages(self, request, research_id, checkpoint):
        context = AgentContext(research_id=research_id, request=request)
        for stage in self.stages():
            if checkpoint:
                checkpoint(stage, context.result)
            try:
                await stage.execute(context)
            finally:
                if checkpoint:
                    checkpoint(stage, context.result)
        return context.result

    def run(self, topic, academic_level, objective=None, report_type='academic_report', citation_style='apa', source_limit=10):
        """Compatibility entry point for existing synchronous integrations/tests."""
        request = ResearchRequest(topic=topic, academic_level=academic_level, objective=objective,
                                  report_type=report_type, citation_style=citation_style, source_limit=source_limit)
        return asyncio.run(self.run_async(request)).model_dump()

    async def intent(self, context):
        context.result.intent = IntentAnalyzer().analyze(context.request)
        context.result.coverage_notes.append('Intent and retrieval relevance use explicit brief terms and transparent lexical rules. Optional LLM analysis is applied only after evidence extraction.')

    async def plan(self, context):
        context.result.sub_questions = ResearchQuestionGenerator().generate(context.result.intent)

    async def queries(self, context):
        context.queries = generate_queries(context.request.topic, context.request.objective,
                                          context.request.academic_level, context.result.sub_questions)
        context.result.search_queries = context.queries

    async def discover(self, context):
        discovery = await self.searcher.discover_many(context.queries, context.request.source_limit, context.request.topic)
        context.result.sources = discovery.sources
        context.result.provider_warning = discovery.warning
        context.result.retrieval_status = discovery.status
        context.result.provider_diagnostics = discovery.diagnostics
        context.result.partial = discovery.status != 'SUCCESS'
        if not discovery.sources:
            # Persist a provider notice via the next checkpoint in the exception path.
            messages = {
                'NO_RESULTS': 'Academic providers returned no matching papers. Try a broader topic.',
                'PROVIDER_UNAVAILABLE': 'Academic providers could not be reached. Please retry later; this is a retrieval service failure, not a lack of research.',
                'RATE_LIMITED': 'Academic providers are rate limiting requests. Please retry after their cooldown period.',
                'INVALID_PROVIDER_RESPONSE': 'Academic providers returned unusable responses. Please retry later.',
                'INSUFFICIENT_EVIDENCE': 'Retrieved records did not contain usable, relevant scholarly metadata. Try a broader topic.',
            }
            raise NoEvidenceError(messages[discovery.status])

    async def evaluate(self, context):
        evaluated = RelevanceEvaluator().evaluate(context.result.sources, context.request)
        context.result.sources = [Source.model_validate(source) for source in evaluated]
        context.result.partial = context.result.partial or len(evaluated) < context.request.source_limit
        if not evaluated:
            context.result.retrieval_status = 'INSUFFICIENT_EVIDENCE'
            raise NoEvidenceError('No usable scholarly metadata remained after source evaluation.')

    async def extract(self, context):
        context.result.scholars = discover_scholars(context.result.sources)
        context.result.full_text_diagnostics = await asyncio.to_thread(self.fulltext_service.enrich, context.result.sources)
        context.result.evidence = EvidenceExtractor().extract(context.result.sources)
        context.result.key_findings = extract_findings(context.result.evidence)
        findings = self.searcher.extract(context.result.sub_questions, [source.model_dump() for source in context.result.sources])
        context.result.findings = [Finding.model_validate(finding) for finding in findings]

    async def analyze(self, context):
        missing = sum(not source.abstract and not source.full_text for source in context.result.sources)
        full_count=sum(bool(p.full_text) for p in context.result.sources)
        context.result.coverage_notes.append(f'{missing} records have neither abstracts nor retrieved full text. {full_count} papers have licensed full-text bodies; remaining evidence is abstract-only. Full-text retrieval is bounded to two eligible papers per run when enabled.')
        if missing:
            context.result.partial = True
            if context.result.retrieval_status == 'SUCCESS':
                context.result.retrieval_status = ('INSUFFICIENT_EVIDENCE' if missing == len(context.result.sources)
                                                   else 'PARTIAL_RESULTS')
        context.result.coverage_notes.append('Matching a source to a question does not establish that the paper answers it.')
        context.result.gaps, context.result.gap_assessment = SupportedGapDetector().analyze(context.result.evidence)
        context.result.coverage_notes.append('Only author-reported gaps in retained source passages are classified. Unreported datasets, cross-study conflicts and field-wide novelty are not inferred.')
        if self.gap_agent is not None:
            output = await self.gap_agent.execute(context)
            context.result.coverage_notes.extend(output.notes)
        validate_traceability(context.result)
        context.result.llm_analysis = await analyze_with_llm(context.request, context.result, self.llm_service)
        context.result.coverage_notes.append(context.result.llm_analysis.notice)
        context.result.evidence_analysis = await analyze_evidence(context.request, context.result, self.llm_service)
        context.result.coverage_notes.append(context.result.evidence_analysis.notice)
        if context.result.evidence_analysis.status in ('partial', 'failed'):
            context.result.partial = True
        validate_traceability(context.result)
        if context.result.llm_analysis.status in ('partial','failed'):
            context.result.partial = True

    async def synthesize(self, context):
        request, result = context.request, context.result
        sources = [source.model_dump() for source in result.sources]
        synthesize_sections(request, result)
        result.report = self.reporter.generate_report(
            topic=request.topic, academic_level=request.academic_level, objective=request.objective,
            questions=result.sub_questions, findings=[finding.model_dump() for finding in result.findings],
            sources=sources, summary=result.summary, report_type=request.report_type,
            citation_style=request.citation_style, provider_warning=result.provider_warning, analysis=result,
        )
        result.report += '\n\n## Evidence coverage\n\n' + '\n'.join(f'- {note}' for note in result.coverage_notes)
