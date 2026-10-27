"""Versioned semantic analysis, distinct from source-reported excerpt contracts."""
from typing import Literal
from pydantic import Field
from app.schemas.llm import StrictModel, LLMCallDiagnostic


class Claim(StrictModel):
    claim_text: str = Field(min_length=1, max_length=4000)
    claim_type: Literal['method', 'population', 'dataset', 'finding', 'limitation', 'contradiction', 'implication']
    supporting_evidence_ids: list[str] = Field(min_length=1, max_length=12)
    supporting_paper_ids: list[str] = Field(min_length=1, max_length=12)
    confidence: float = Field(ge=0, le=1)
    limitations: list[str] = Field(max_length=10)


class Comparison(StrictModel):
    conclusion: str = Field(min_length=1, max_length=2000)
    relation: Literal['agreement', 'method_difference', 'conflict', 'limitation', 'knowledge_gap']
    supporting_evidence_ids: list[str] = Field(min_length=2, max_length=12)
    supporting_paper_ids: list[str] = Field(min_length=2, max_length=12)
    limitations: list[str] = Field(max_length=10)


class CandidateGap(StrictModel):
    description: str = Field(min_length=1, max_length=2000)
    basis: Literal['explicit', 'inferred', 'speculative']
    supporting_evidence_ids: list[str] = Field(min_length=1, max_length=12)
    supporting_paper_ids: list[str] = Field(min_length=1, max_length=12)
    limitations: list[str] = Field(max_length=10)


class AnalysisOutput(StrictModel):
    claims: list[Claim] = Field(max_length=24)
    comparisons: list[Comparison] = Field(max_length=10)
    candidate_gaps: list[CandidateGap] = Field(max_length=10)


class AcceptedClaim(Claim):
    grounding: Literal['exact_excerpt', 'uncertain']


class AcceptedComparison(Comparison):
    grounding: Literal['uncertain'] = 'uncertain'


class AcceptedGap(CandidateGap):
    grounding: Literal['explicit_excerpt', 'uncertain', 'speculative']


class EvidenceAnalysis(StrictModel):
    schema_version: Literal[1] = 1
    revision: str = ''
    status: Literal['disabled', 'missing_evidence', 'completed', 'partial', 'failed'] = 'disabled'
    claims: list[AcceptedClaim] = Field(default_factory=list)
    comparisons: list[AcceptedComparison] = Field(default_factory=list)
    candidate_gaps: list[AcceptedGap] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)
    diagnostics: list[LLMCallDiagnostic] = Field(default_factory=list)
    omitted_evidence_count: int = 0
    duration_ms: int = 0
    notice: str = ''
