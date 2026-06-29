import json
import os
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ResearchProviderError(RuntimeError):
    pass


class ResearchProvider(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[dict]:
        ...


@dataclass
class SemanticScholarProvider:
    """Retrieve real scholarly metadata without requiring a paid service."""

    name: str = "Semantic Scholar"
    endpoint: str = "https://api.semanticscholar.org/graph/v1/paper/search"

    def search(self, query: str, limit: int) -> list[dict]:
        fields = (
            "paperId,title,abstract,year,authors,venue,url,citationCount,"
            "externalIds,openAccessPdf,publicationTypes"
        )
        params = urlencode({"query": query, "limit": limit, "fields": fields})
        headers = {
            "Accept": "application/json",
            "User-Agent": "ResearchOS/1.0 (academic project)",
        }
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key

        request = Request(f"{self.endpoint}?{params}", headers=headers)
        try:
            with urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ResearchProviderError(
                f"Semantic Scholar returned HTTP {exc.code}."
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ResearchProviderError("Semantic Scholar is currently unavailable.") from exc

        sources = []
        for paper in payload.get("data", []):
            title = (paper.get("title") or "").strip()
            if not title:
                continue

            abstract = " ".join((paper.get("abstract") or "").split())
            authors = [
                author.get("name", "").strip()
                for author in paper.get("authors", [])
                if author.get("name")
            ]
            external_ids = paper.get("externalIds") or {}
            doi = external_ids.get("DOI")
            source_url = f"https://doi.org/{doi}" if doi else paper.get("url")
            open_access = paper.get("openAccessPdf") or {}
            publication_types = paper.get("publicationTypes") or []
            sources.append(
                {
                    "id": paper.get("paperId") or doi or source_url,
                    "title": title,
                    "url": source_url,
                    "authors": authors,
                    "year": paper.get("year"),
                    "venue": paper.get("venue") or "Unknown venue",
                    "abstract": abstract,
                    "snippet": _make_snippet(abstract),
                    "citation_count": paper.get("citationCount") or 0,
                    "doi": doi,
                    "open_access_pdf": open_access.get("url"),
                    "source_type": publication_types[0] if publication_types else "Scholarly work",
                    "provider": self.name,
                    "is_demo": False,
                }
            )
        return sources


@dataclass
class CrossrefProvider:
    """Credential-free scholarly metadata fallback."""

    name: str = "Crossref"
    endpoint: str = "https://api.crossref.org/works"

    def search(self, query: str, limit: int) -> list[dict]:
        fields = (
            "DOI,title,author,published,container-title,URL,abstract,"
            "is-referenced-by-count,type"
        )
        params = urlencode(
            {
                "query.bibliographic": query,
                "rows": limit,
                "select": fields,
            }
        )
        contact_email = os.getenv("RESEARCH_CONTACT_EMAIL")
        user_agent = "ResearchOS/1.0"
        if contact_email:
            user_agent += f" (mailto:{contact_email})"
        request = Request(
            f"{self.endpoint}?{params}",
            headers={"Accept": "application/json", "User-Agent": user_agent},
        )

        try:
            with urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ResearchProviderError(f"Crossref returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ResearchProviderError("Crossref is currently unavailable.") from exc

        sources = []
        for work in payload.get("message", {}).get("items", []):
            titles = work.get("title") or []
            title = titles[0].strip() if titles else ""
            doi = work.get("DOI")
            if not title or not doi:
                continue

            authors = [
                " ".join(
                    part
                    for part in [author.get("given", ""), author.get("family", "")]
                    if part
                ).strip()
                for author in work.get("author", [])
            ]
            date_parts = work.get("published", {}).get("date-parts") or []
            year = date_parts[0][0] if date_parts and date_parts[0] else None
            containers = work.get("container-title") or []
            abstract = _clean_markup(work.get("abstract") or "")
            sources.append(
                {
                    "id": doi,
                    "title": title,
                    "url": f"https://doi.org/{doi}",
                    "authors": [author for author in authors if author],
                    "year": year,
                    "venue": containers[0] if containers else "Unknown venue",
                    "abstract": abstract,
                    "snippet": _make_snippet(abstract),
                    "citation_count": work.get("is-referenced-by-count") or 0,
                    "doi": doi,
                    "open_access_pdf": None,
                    "source_type": work.get("type") or "Scholarly work",
                    "provider": self.name,
                    "is_demo": False,
                }
            )
        return sources


@dataclass
class DemoResearchProvider:
    """Honest offline fallback that is never presented as real citation data."""

    name: str = "Demo dataset"

    def search(self, query: str, limit: int) -> list[dict]:
        templates = [
            (
                "Foundational overview",
                "Defines the topic, its core concepts, and the context needed to frame a research problem.",
            ),
            (
                "Applications and implementation",
                "Surveys practical applications, implementation patterns, and factors that influence adoption.",
            ),
            (
                "Risks, limitations, and research opportunities",
                "Reviews common limitations, ethical or operational risks, and areas requiring further study.",
            ),
        ]
        return [
            {
                "id": f"demo-{index}",
                "title": f"{label}: {query}",
                "url": None,
                "authors": ["ResearchOS demo dataset"],
                "year": None,
                "venue": "Offline demonstration",
                "abstract": description,
                "snippet": description,
                "citation_count": 0,
                "doi": None,
                "open_access_pdf": None,
                "source_type": "Demo record",
                "provider": self.name,
                "is_demo": True,
            }
            for index, (label, description) in enumerate(templates[:limit], start=1)
        ]


class ResilientResearchProvider:
    name = "Semantic Scholar with offline fallback"

    def __init__(
        self,
        primary: ResearchProvider | None = None,
        secondary: ResearchProvider | None = None,
        fallback: ResearchProvider | None = None,
    ):
        self.primary = primary or SemanticScholarProvider()
        self.secondary = secondary or CrossrefProvider()
        self.fallback = fallback or DemoResearchProvider()
        self.last_warning: str | None = None

    def search(self, query: str, limit: int) -> list[dict]:
        primary_error = None
        try:
            results = self.primary.search(query, limit)
            if results:
                self.last_warning = None
                return results
        except ResearchProviderError as exc:
            primary_error = str(exc)

        try:
            results = self.secondary.search(query, limit)
            if results:
                self.last_warning = (
                    f"{primary_error} Crossref evidence was used instead."
                    if primary_error
                    else "Semantic Scholar returned no results; Crossref evidence was used."
                )
                return results
        except ResearchProviderError as exc:
            secondary_error = str(exc)
        else:
            secondary_error = "Crossref returned no results."

        details = " ".join(filter(None, [primary_error, secondary_error]))
        self.last_warning = f"{details} Demo evidence is shown instead."
        return self.fallback.search(query, min(limit, 3))


def _make_snippet(text: str, max_length: int = 420) -> str:
    if not text:
        return "No abstract was supplied by the source."
    if len(text) <= max_length:
        return text
    shortened = text[:max_length].rsplit(" ", 1)[0]
    return f"{shortened}..."


def _clean_markup(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", text)
    return " ".join(without_tags.split())
