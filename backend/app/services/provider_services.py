"""Provider-independent service boundaries. No unconfigured service fabricates output."""
import asyncio
from typing import Protocol

from pydantic import BaseModel, Field
from app.core.config import settings
from app.schemas.research import Source, ProviderDiagnostic, RetrievalStatus
from app.services.research_provider import ResearchProvider, ResilientResearchProvider


class SearchResult(BaseModel):
    sources: list[Source] = Field(default_factory=list)
    warning: str | None = None
    status: RetrievalStatus = 'SUCCESS'
    diagnostics: list[ProviderDiagnostic] = Field(default_factory=list)


from app.services.llm_service import LLMProvider, LLMService


class SearchService:
    def __init__(self, provider: ResearchProvider):
        self.provider = provider if isinstance(provider, ResilientResearchProvider) else ResilientResearchProvider(providers=[provider])

    async def search(self, query: str, limit: int) -> SearchResult:
        return await self.search_many([query], limit, query)

    async def search_many(self, queries: list[str], limit: int, topic: str) -> SearchResult:
        # The provider owns bounded HTTP attempts, cooldown and a total search budget.
        # Avoid wait_for(to_thread): cancelling that await cannot stop the HTTP thread
        # and would discard evidence already collected from earlier providers.
        records = await asyncio.to_thread(self.provider.search_many, queries, limit, topic)
        return SearchResult(sources=[Source.model_validate(record) for record in records],
                            warning=self.provider.last_warning, status=self.provider.last_status,
                            diagnostics=self.provider.last_diagnostics)


class AcademicSearchService(SearchService):
    def __init__(self, provider: ResearchProvider | None = None):
        super().__init__(provider or ResilientResearchProvider())
