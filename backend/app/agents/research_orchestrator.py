from app.agents.planner_agent import PlannerAgent
from app.agents.search_agent import SearchAgent
from app.agents.summarizer_agent import SummarizerAgent
from app.agents.report_agent import ReportAgent


class ResearchOrchestrator:
    def __init__(self, searcher: SearchAgent | None = None):
        self.planner = PlannerAgent()
        self.searcher = searcher or SearchAgent()
        self.summarizer = SummarizerAgent()
        self.reporter = ReportAgent()

    def run(
        self,
        topic: str,
        academic_level: str,
        objective: str | None = None,
        report_type: str = "academic_report",
        citation_style: str = "apa",
        source_limit: int = 10,
    ) -> dict:
        questions = self.planner.create_sub_questions(
            topic,
            academic_level,
            report_type,
        )
        findings, sources, provider_warning = self.searcher.collect_findings(
            topic,
            questions,
            source_limit,
        )
        summary = self.summarizer.summarize(topic, sources)
        report = self.reporter.generate_report(
            topic=topic,
            academic_level=academic_level,
            objective=objective,
            questions=questions,
            findings=findings,
            sources=sources,
            summary=summary,
            report_type=report_type,
            citation_style=citation_style,
            provider_warning=provider_warning,
        )

        return {
            "sub_questions": questions,
            "findings": findings,
            "sources": sources,
            "summary": summary,
            "report": report,
            "provider_warning": provider_warning,
        }
