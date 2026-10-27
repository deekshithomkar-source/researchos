"""Traceable, additive analysis contracts for the existing result API."""
from typing import Literal
from pydantic import BaseModel, Field


class ResearchIntent(BaseModel):
    topic: str
    objective: str | None = None
    academic_level: str
    output_format: str
    investigation_type: Literal['comparison', 'evaluation', 'implementation', 'exploration']
    concepts: list[str]
    objective_terms: list[str]
    depth: str
    method: Literal['explicit_brief_lexical'] = 'explicit_brief_lexical'


class PaperRanking(BaseModel):
    topic_relevance: float = Field(ge=0, le=1)
    objective_alignment: float | None = Field(default=None, ge=0, le=1)
    credibility: float = Field(ge=0, le=1)
    recency: float = Field(ge=0, le=1)
    evidence_availability: float = Field(ge=0, le=1)
    total: float = Field(ge=0, le=1)
    explanation: str


class EvidencePassage(BaseModel):
    evidence_id: str
    paper_id: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    locator: Literal['abstract', 'full_text'] = 'abstract'
    source_url: str | None
    kind: Literal['finding', 'method', 'limitation', 'context']


class SupportedFinding(BaseModel):
    finding_id: str
    statement: str
    evidence_ids: list[str] = Field(min_length=1)
    paper_ids: list[str] = Field(min_length=1)
    basis: Literal['author_reported_excerpt'] = 'author_reported_excerpt'


GapCategory = Literal['study_limitation', 'unresolved_question', 'conflicting_findings',
                      'missing_dataset', 'methodological_limitation', 'future_opportunity', 'understudied_population']


class SupportedGap(BaseModel):
    gap_id: str
    category: GapCategory
    statement: str
    evidence_ids: list[str] = Field(min_length=1)
    paper_ids: list[str] = Field(min_length=1)
    scope: Literal['author_reported_in_source'] = 'author_reported_in_source'


class Citation(BaseModel):
    paper_id: str
    style: Literal['apa', 'ieee']
    label: str
    reference: str
    metadata_missing: list[str] = Field(default_factory=list)


class ReportSection(BaseModel):
    name: str
    content: str
    evidence_ids: list[str] = Field(default_factory=list)
    complete: bool = True


class ReportClaim(BaseModel):
    claim_id: str
    statement: str
    evidence_ids: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)
    support: Literal['supported_excerpt', 'unsupported']
    warning: str | None = None
