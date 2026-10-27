from pydantic import BaseModel, Field
from typing import Literal

class AuthorIdentifier(BaseModel):
    scheme: Literal['orcid','openalex','semantic_scholar']
    value: str

class Scholar(BaseModel):
    author_id: str
    name: str
    identifiers: list[AuthorIdentifier] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    provider: str
    related_paper_ids: list[str] = Field(default_factory=list)
    retrieved_at: str | None = None
    provenance: Literal['provider_reported_authorship'] = 'provider_reported_authorship'
    publication_scope: Literal['retrieved_run_only'] = 'retrieved_run_only'

class FullText(BaseModel):
    truncated: bool = False
    text: str
    url: str
    license_url: str
    provider: Literal['Europe PMC'] = 'Europe PMC'
    retrieved_at: str

class RetrievalMetadata(BaseModel):
    provider: str
    status: str
    paper_id: str
    http_status: int | None = None
    duration_ms: int = 0
