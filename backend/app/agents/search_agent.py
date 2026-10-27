import re
import asyncio

from app.agents.verifier_agent import VerifierAgent
from app.services.research_provider import ResearchProvider
from app.services.provider_services import AcademicSearchService

class SearchAgent:
    def __init__(
        self,
        provider: ResearchProvider | None = None,
        verifier: VerifierAgent | None = None,
    ):
        self.service = AcademicSearchService(provider)
        self.verifier = verifier or VerifierAgent()

    def collect_findings(
        self,
        topic: str,
        questions: list[str],
        source_limit: int = 10,
    ) -> tuple[list[dict], list[dict], str | None]:
        discovered = asyncio.run(self.discover(topic, source_limit))
        verified_sources = self.evaluate([source.model_dump() for source in discovered.sources])
        return self.extract(questions, verified_sources), verified_sources, discovered.warning

    async def discover(self, query: str, limit: int):
        return await self.service.search(query, limit)

    async def discover_many(self, queries: list[str], limit: int, topic: str):
        return await self.service.search_many(queries, limit, topic)

    def evaluate(self, sources: list[dict]) -> list[dict]:
        return self.verifier.evaluate(sources)

    def extract(self, questions: list[str], sources: list[dict]) -> list[dict]:
        findings = [{'question': question, 'sources': self._best_matches(question, sources)}
                    for question in questions]
        if findings:
            self._preserve_source_catalog(findings, sources)
        return findings

    def _best_matches(
        self,
        question: str,
        sources: list[dict],
        per_question: int = 3,
    ) -> list[dict]:
        question_terms = _meaningful_terms(question)

        def relevance(source: dict) -> tuple[int, int, int]:
            searchable = " ".join(
                [
                    source.get("title", ""),
                    source.get("abstract", ""),
                    source.get("venue", ""),
                ]
            )
            overlap = len(question_terms & _meaningful_terms(searchable))
            return (
                overlap,
                source.get("credibility_score", 0),
                source.get("citation_count", 0),
            )

        return sorted(sources, key=relevance, reverse=True)[:per_question]

    def _preserve_source_catalog(
        self,
        findings: list[dict],
        sources: list[dict],
    ) -> None:
        """Ensure every retrieved source remains available after a session reload."""
        assigned_ids = {
            source.get("id")
            for finding in findings
            for source in finding["sources"]
        }
        missing_sources = [
            source for source in sources if source.get("id") not in assigned_ids
        ]
        for index, source in enumerate(missing_sources):
            findings[index % len(findings)]["sources"].append(source)


def _meaningful_terms(text: str) -> set[str]:
    stop_words = {
        "about", "across", "and", "are", "for", "from", "how", "into",
        "its", "the", "their", "these", "what", "which", "with",
    }
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) > 2 and word not in stop_words
    }
