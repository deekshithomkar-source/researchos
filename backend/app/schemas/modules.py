"""Versioned module contract. Legacy response fields remain available to old clients."""
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl
from app.schemas.scholarly import Scholar, AuthorIdentifier
from app.schemas.evidence_analysis import EvidenceAnalysis
from app.schemas.analysis import Citation, ReportSection, ReportClaim

class Overview(BaseModel):
    summary: str = ''
    objective: str | None = None
    academic_level: str
    analysis_depth: str
    output_type: str
    citation_style: str
    source_target: int
    paper_count: int
    coverage_notes: list[str] = Field(default_factory=list)

class Paper(BaseModel):
    author_identifiers: list[AuthorIdentifier] = Field(default_factory=list)
    journal: str = ""
    provider: str = ""
    citation_count: int = 0
    retrieved_at: str | None = None
    evidence_scope: Literal["abstract_only", "full_text", "metadata_only"] = "metadata_only"
    paper_id: str
    title: str
    authors: list[str]
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str = ''
    relevance_score: float | None = None
    citation: Citation | None = None

class RetrievedSource(BaseModel):
    source_id: str
    paper_id: str
    provider: str
    provider_paper_id: str
    url: str | None = None
    metadata_available: list[str]
    provenance: Literal['retrieved_metadata'] = 'retrieved_metadata'

class ResearchGap(BaseModel):
    gap_id: str
    description: str
    gap_type: str
    supporting_paper_ids: list[str]
    evidence_ids: list[str]
    confidence: Literal['author_reported_excerpt'] = 'author_reported_excerpt'

class Dataset(BaseModel):
    id: str
    name: str
    provider: str
    description: str
    url: HttpUrl
    license: str | list[str] | None = None
    research_relevance: str
    checked_at: str

class Skill(BaseModel):
    category: str
    name: str
    basis: Literal['generated_guidance'] = 'generated_guidance'

class Course(BaseModel):
    level: str = ""
    reason_for_recommendation: str = ""
    id: str
    title: str
    provider: str
    difficulty: str
    skills: list[str]
    duration: str | None = None
    url: HttpUrl
    checked_at: str
    classification_basis: str

class Project(BaseModel):
    topic: str = ""
    finding_ids: list[str] = Field(default_factory=list)
    id: str
    title: str
    problem_statement: str
    technologies: list[str]
    difficulty: str
    expected_outcome: str
    skills: list[str]
    paper_ids: list[str]
    gap_ids: list[str]
    dataset_ids: list[str]
    prerequisite: str | None = None

class Internship(BaseModel):
    kind: Literal['suggested_role', 'verified_listing']
    title: str
    required_skills: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=list)
    url: HttpUrl | None = None
    provider: str | None = None
    company: str | None = None
    checked_at: str | None = None
    availability_note: str | None = None

class CareerPath(BaseModel):
    topic: str = ""
    internship_roles: list[str] = Field(default_factory=list)
    title: str
    required_skills: list[str]
    project_ids: list[str]
    pathway: list[str]

class NextStep(BaseModel):
    priority: int = Field(default=1, ge=1)
    reason: str = ""
    action: str
    kind: Literal['paper', 'skill', 'course', 'project', 'gap', 'suggested_role']
    target_id: str

class RoadmapStage(BaseModel):
    stage: str
    skills: list[str]
    milestone: str

class RequestedReport(BaseModel):
    title: str = ''
    academic_level: str = ''
    claims: list[ReportClaim] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    generation_method: str = 'extractive_evidence_review'

    output_type: str
    citation_style: str
    sections: list[ReportSection]
    citations: list[Citation]
    markdown: str

class CanonicalResearchResult(BaseModel):
    evidence_analysis: EvidenceAnalysis | None = None
    scholars: list[Scholar] = Field(default_factory=list)
    schema_version: Literal[2] = 2
    overview: Overview
    research_questions: list[str]
    papers: list[Paper]
    sources: list[RetrievedSource]
    research_gaps: list[ResearchGap]
    datasets: list[Dataset] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    courses: list[Course] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    internships: list[Internship] = Field(default_factory=list)
    career_paths: list[CareerPath] = Field(default_factory=list)
    next_steps: list[NextStep] = Field(default_factory=list)
    roadmap: list[RoadmapStage] = Field(default_factory=list)
    module_status: dict[str, str] = Field(default_factory=dict)
    report: RequestedReport
