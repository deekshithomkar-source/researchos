"""Strict agent contracts. Model-generated facts are limited to verifiable excerpts."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class EvidenceInput(StrictModel):
    evidence_id: str
    paper_id: str
    text: str
    kind: str

class ResearchAgentInput(StrictModel):
    topic: str
    objective: str | None
    academic_level: str
    academic_policy: str
    output_type: str
    output_policy: str
    citation_style: str
    source_target: int
    evidence: list[EvidenceInput]

class GroundedObservation(StrictModel):
    evidence_id: str
    quote: str = Field(min_length=1, max_length=4000)
    category: Literal['finding', 'method', 'limitation', 'context']

class EvidenceReview(StrictModel):
    observations: list[GroundedObservation] = Field(max_length=12)

class SynthesisInput(StrictModel):
    brief: ResearchAgentInput
    reviewed_evidence: EvidenceReview

class SectionSelection(StrictModel):
    section: Literal['overview', 'findings', 'methods', 'limitations', 'directions']
    evidence_ids: list[str] = Field(min_length=1, max_length=12)

class SynthesisPlan(StrictModel):
    sections: list[SectionSelection] = Field(min_length=1, max_length=5)

class LLMCallDiagnostic(BaseModel):
    agent: str
    status: str
    model: str
    attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    reserved_tokens: int = 0
    cached: bool = False
    duration_ms: int = 0

class LLMAnalysis(BaseModel):
    status: Literal['disabled', 'completed', 'partial', 'failed', 'missing_evidence'] = 'disabled'
    method: Literal['llm_selected_verified_excerpts'] = 'llm_selected_verified_excerpts'
    observations: list[GroundedObservation] = Field(default_factory=list)
    sections: list[SectionSelection] = Field(default_factory=list)
    diagnostics: list[LLMCallDiagnostic] = Field(default_factory=list)
    omitted_evidence_count: int = 0
    notice: str = ''
