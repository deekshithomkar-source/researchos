import unittest

from app.agents.research_orchestrator import ResearchOrchestrator
from app.agents.search_agent import SearchAgent


class FakeProvider:
    name = "Test provider"
    last_warning = None

    def search(self, query: str, limit: int) -> list[dict]:
        base_source = {
            "url": "https://doi.org/10.1000/test",
            "authors": ["A. Researcher"],
            "year": 2024,
            "venue": "Journal of Test Evidence",
            "abstract": "The study evaluates practical applications and identifies implementation constraints.",
            "snippet": "The study evaluates practical applications and identifies implementation constraints.",
            "citation_count": 25,
            "open_access_pdf": None,
            "source_type": "JournalArticle",
            "provider": self.name,
            "is_demo": False,
        }
        return [
            {
                **base_source,
                "id": "paper-1",
                "title": f"Evidence about {query}",
                "doi": "10.1000/test",
            },
            {
                **base_source,
                "id": "paper-2",
                "title": f"Secondary perspective on {query}",
                "url": "https://doi.org/10.1000/test-2",
                "doi": "10.1000/test-2",
            },
        ][:limit]


class ResearchPipelineTests(unittest.TestCase):
    def test_pipeline_generates_traceable_report(self):
        searcher = SearchAgent(provider=FakeProvider())
        result = ResearchOrchestrator(searcher=searcher).run(
            topic="AI in education",
            academic_level="MCA",
            report_type="project_proposal",
            citation_style="ieee",
            source_limit=5,
        )

        self.assertEqual(len(result["sub_questions"]), 5)
        self.assertEqual(len(result["sources"]), 2)
        self.assertGreater(result["sources"][0]["credibility_score"], 0)
        persisted_source_ids = {
            source["id"]
            for finding in result["findings"]
            for source in finding["sources"]
        }
        self.assertEqual(persisted_source_ids, {"paper-1", "paper-2"})
        self.assertIn("Proposed Solution", result["report"])
        self.assertIn("[1]", result["report"])
        self.assertIn("Research Integrity Note", result["report"])


if __name__ == "__main__":
    unittest.main()
