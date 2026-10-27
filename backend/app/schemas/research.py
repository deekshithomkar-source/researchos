from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_serializer, field_validator, computed_field
from app.schemas.scholarly import Scholar, AuthorIdentifier, FullText, RetrievalMetadata
from app.schemas.llm import LLMAnalysis
from app.schemas.evidence_analysis import EvidenceAnalysis
from app.schemas.modules import CanonicalResearchResult
from app.schemas.analysis import ResearchIntent, PaperRanking, EvidencePassage, SupportedFinding, SupportedGap, Citation, ReportSection


class ResearchStatus(str, Enum):
    queued = 'queued'
    planning = 'planning'
    searching = 'searching'
    evaluating = 'evaluating'
    validating = 'validating'
    extracting = 'extracting'
    analyzing = 'analyzing'
    synthesizing = 'synthesizing'
    completed = 'completed'
    failed = 'failed'


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    topic: str = Field(min_length=3, max_length=255)
    academic_level: str = Field(default='MCA', min_length=2, max_length=100)
    objective: str | None = Field(default=None, max_length=1000)
    report_type: Literal['academic_report', 'literature_review', 'project_proposal', 'comparative_analysis'] = Field(default='academic_report', validation_alias=AliasChoices('report_type', 'output_type'))
    citation_style: Literal['apa', 'ieee'] = 'apa'
    source_limit: int = Field(default=10, ge=5, le=20, validation_alias=AliasChoices('source_limit', 'source_target'))

    @field_validator('topic', 'academic_level', mode='before')
    @classmethod
    def strip_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('objective', mode='before')
    @classmethod
    def clean_optional_text(cls, value):
        return (value.strip() or None) if isinstance(value, str) else value


class Source(BaseModel):
    model_config = ConfigDict(extra='allow')
    retrieved_at: str | None = None
    author_identifiers: list[AuthorIdentifier] = Field(default_factory=list)
    scholar_records: list[Scholar] = Field(default_factory=list)
    full_text: FullText | None = None
    id: str
    title: str = Field(min_length=1)
    url: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ''
    abstract: str = ''
    snippet: str = ''
    citation_count: int = Field(default=0, ge=0)
    doi: str | None = None
    open_access_pdf: str | None = None
    provider: str
    is_demo: Literal[False] = False
    credibility_score: int = Field(default=0, ge=0, le=100)
    credibility_label: str = 'Unscored'
    quality_signals: list[str] = Field(default_factory=list)
    provenance: Literal['retrieved_metadata'] = 'retrieved_metadata'
    ranking: PaperRanking | None = None

    @computed_field
    @property
    def paper_id(self) -> str:
        return self.id

    @computed_field
    @property
    def journal(self) -> str:
        return self.venue

    @computed_field
    @property
    def source_provider(self) -> str:
        return self.provider

    @field_validator('url', 'open_access_pdf')
    @classmethod
    def safe_url(cls, value):
        if value and not value.lower().startswith(('https://', 'http://')):
            raise ValueError('Source links must use HTTP or HTTPS')
        return value


class Finding(BaseModel):
    question: str
    sources: list[Source] = Field(default_factory=list)


RetrievalStatus = Literal['SUCCESS', 'NO_RESULTS', 'PROVIDER_UNAVAILABLE', 'RATE_LIMITED',
                          'INVALID_PROVIDER_RESPONSE', 'INSUFFICIENT_EVIDENCE', 'PARTIAL_RESULTS']


class ProviderDiagnostic(BaseModel):
    provider: str
    query: str = '[redacted]'
    query_hash: str
    http_status: int | None = None
    returned: int = 0
    valid: int = 0
    rejected: int = 0
    duplicates: int = 0
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    duration_ms: int = 0
    error_code: str | None = None
    error_type: str | None = None


class ResearchResult(BaseModel):
    scholars: list[Scholar] = Field(default_factory=list)
    full_text_diagnostics: list[RetrievalMetadata] = Field(default_factory=list)
    llm_analysis: LLMAnalysis | None = None
    evidence_analysis: EvidenceAnalysis | None = None
    intent: ResearchIntent | None = None
    evidence: list[EvidencePassage] = Field(default_factory=list)
    key_findings: list[SupportedFinding] = Field(default_factory=list)
    gaps: list[SupportedGap] = Field(default_factory=list)
    gap_assessment: dict[str, str] = Field(default_factory=dict)
    citations: list[Citation] = Field(default_factory=list)
    report_sections: list[ReportSection] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    sub_questions: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    summary: str = ''
    report: str = ''
    provider_warning: str | None = None
    partial: bool = False
    retrieval_status: RetrievalStatus | None = None
    provider_diagnostics: list[ProviderDiagnostic] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)
    synthesis_method: Literal['extractive_template'] = 'extractive_template'
    recommendation_basis: str = 'Template guidance, not established findings or AI-verified claims.'


class ResearchResponse(ResearchResult):
    modules: CanonicalResearchResult | None = None
    model_config = ConfigDict(from_attributes=True)
    id: int
    research_id: str
    topic: str
    academic_level: str
    objective: str | None
    report_type: str
    citation_style: str
    source_target: int
    status: ResearchStatus
    progress: int = Field(ge=0, le=100)
    current_stage: str
    status_message: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None

    @field_serializer('created_at', 'updated_at', 'completed_at')
    def utc_timestamp(self, value):
        return value.replace(tzinfo=timezone.utc).isoformat() if value is not None else None


class ResearchHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    research_id: str
    topic: str
    academic_level: str
    status: ResearchStatus
    progress: int
    created_at: datetime
    partial: bool = False

    @field_serializer('created_at')
    def utc_timestamp(self, value):
        return value.replace(tzinfo=timezone.utc).isoformat()
