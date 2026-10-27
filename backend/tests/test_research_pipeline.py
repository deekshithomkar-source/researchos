import unittest

from app.agents.research_orchestrator import ResearchOrchestrator
from app.agents.search_agent import SearchAgent


from test_foundation import RecordedProvider


class ResearchPipelineTests(unittest.TestCase):
    def test_pipeline_generates_traceable_report(self):
        searcher = SearchAgent(provider=RecordedProvider())
        result = ResearchOrchestrator(searcher=searcher).run(
            topic="Deep learning",
            academic_level="MCA",
            report_type="project_proposal",
            citation_style="ieee",
            source_limit=5,
        )

        self.assertEqual(len(result["sub_questions"]), 5)
        self.assertEqual(len(result["sources"]), 1)
        self.assertGreater(result["sources"][0]["credibility_score"], 0)
        persisted_source_ids = {
            source["id"]
            for finding in result["findings"]
            for source in finding["sources"]
        }
        self.assertEqual(persisted_source_ids, {"10.1038/nature14539"})
        self.assertIn("Proposed Solution", result["report"])
        self.assertIn("[1]", result["report"])
        self.assertIn("Research Integrity Note", result["report"])


if __name__ == "__main__":
    unittest.main()
