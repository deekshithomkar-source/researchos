class PlannerAgent:
    QUESTION_TEMPLATES = {
        "academic_report": [
            "How is {topic} defined, and what are its foundational concepts?",
            "What are the major approaches, technologies, or models used in {topic}?",
            "What evidence exists about the applications and outcomes of {topic}?",
            "What limitations, risks, or ethical concerns are reported for {topic}?",
            "What research gaps and future directions remain for {topic}?",
        ],
        "literature_review": [
            "What themes and theoretical foundations dominate the literature on {topic}?",
            "Which methods and datasets are commonly used to study {topic}?",
            "Where do published findings about {topic} agree or conflict?",
            "What limitations recur across the existing literature on {topic}?",
            "Which unanswered questions form a research gap in {topic}?",
        ],
        "project_proposal": [
            "What real-world problem related to {topic} should the proposed system solve?",
            "What existing systems or research approaches address {topic}?",
            "Which functional and technical requirements follow from the evidence?",
            "What risks, constraints, and evaluation criteria should be considered?",
            "What architecture and future extensions are suitable for a project on {topic}?",
        ],
    }

    def create_sub_questions(
        self,
        topic: str,
        academic_level: str,
        report_type: str = "academic_report",
    ) -> list[str]:
        del academic_level
        templates = self.QUESTION_TEMPLATES.get(
            report_type,
            self.QUESTION_TEMPLATES["academic_report"],
        )
        return [template.format(topic=topic.strip()) for template in templates]
