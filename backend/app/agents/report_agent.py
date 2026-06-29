from collections import Counter


class ReportAgent:
    def generate_report(
        self,
        topic: str,
        academic_level: str,
        objective: str | None,
        questions: list[str],
        findings: list[dict],
        sources: list[dict],
        summary: str,
        report_type: str,
        citation_style: str,
        provider_warning: str | None = None,
    ) -> str:
        objective_text = objective or (
            f"To critically study {topic}, synthesize available scholarly evidence, "
            "and identify practical implications and research opportunities."
        )
        source_mode = (
            "demo evidence"
            if sources and all(source.get("is_demo") for source in sources)
            else "scholarly metadata and abstracts"
        )
        sections = [
            f"# {self._title(topic, report_type)}",
            "",
            "## Abstract",
            "",
            summary,
            "",
            "## 1. Introduction",
            "",
            (
                f"This {report_type.replace('_', ' ')} was prepared for the {academic_level} level. "
                f"It examines {topic} through a reproducible pipeline that plans research questions, "
                "retrieves evidence, evaluates metadata quality, and links findings to references."
            ),
            "",
            "## 2. Research Objective",
            "",
            objective_text,
            "",
            "## 3. Methodology",
            "",
            (
                f"The system searched for literature related to “{topic}”, deduplicated the results, "
                f"and ranked {len(sources)} source(s) using transparent signals such as abstract "
                f"availability, DOI, venue, open-access status, and citation count. The synthesis uses "
                f"{source_mode}; it does not claim to replace full-text critical reading."
            ),
            "",
            "## 4. Research Questions",
            "",
            *[f"{index}. {question}" for index, question in enumerate(questions, start=1)],
            "",
            "## 5. Evidence-Based Findings",
            "",
        ]

        for question_index, item in enumerate(findings, start=1):
            sections.extend([f"### 5.{question_index} {item['question']}", ""])
            if not item["sources"]:
                sections.extend(["No relevant source was retrieved for this question.", ""])
                continue
            for source in item["sources"]:
                source_number = self._source_number(source, sources)
                sections.append(
                    f"- [{source_number}] **{source['title']}** "
                    f"({source.get('year') or 'year unavailable'}): {source['snippet']} "
                    f"_Quality: {source['credibility_label']} "
                    f"({source['credibility_score']}/100)._"
                )
            sections.append("")

        sections.extend(self._analysis_sections(topic, sources, report_type))
        sections.extend(
            [
                "## References",
                "",
                *[
                    self._format_reference(index, source, citation_style)
                    for index, source in enumerate(sources, start=1)
                ],
                "",
                "## Research Integrity Note",
                "",
                (
                    provider_warning
                    or "Source metadata was retrieved from Semantic Scholar. Verify important claims against the full paper before academic submission."
                ),
            ]
        )
        return "\n".join(sections).strip()

    def _analysis_sections(
        self,
        topic: str,
        sources: list[dict],
        report_type: str,
    ) -> list[str]:
        years = [source["year"] for source in sources if source.get("year")]
        venues = [source["venue"] for source in sources if source.get("venue")]
        recent_count = sum(1 for year in years if year >= 2021)
        common_venue = Counter(venues).most_common(1)
        landscape = (
            f"The evidence pool contains {len(sources)} distinct source(s). "
            f"{recent_count} were published from 2021 onward. "
            + (
                f"The most frequently represented venue is {common_venue[0][0]}."
                if common_venue
                else "Venue information was limited."
            )
        )

        sections = [
            "## 6. Literature Landscape",
            "",
            landscape,
            "",
            "## 7. Research Gap",
            "",
            (
                f"This preliminary evidence map suggests that work on {topic} should be evaluated "
                "with clearer comparative baselines, context-specific datasets, reproducible methods, "
                "and longer-term outcome measures. These are candidate gaps inferred from the retrieved "
                "metadata and abstracts; full-text review is required to confirm them."
            ),
            "",
        ]

        if report_type == "project_proposal":
            sections.extend(
                [
                    "## 8. Proposed Solution",
                    "",
                    (
                        f"Develop a modular system for {topic} with separate input, processing, evidence, "
                        "evaluation, and presentation layers. The prototype should record assumptions, "
                        "preserve source provenance, and expose measurable evaluation criteria."
                    ),
                    "",
                    "## 9. Suggested Architecture",
                    "",
                    "User Interface → API Layer → Research Planner → Source Retrieval → "
                    "Evidence Verification → Synthesis → Report and History Storage",
                    "",
                ]
            )
            next_number = 10
        else:
            next_number = 8

        sections.extend(
            [
                f"## {next_number}. Limitations",
                "",
                "- Results depend on the relevance and metadata completeness of retrieved sources.",
                "- Abstract-level synthesis cannot capture every method, result, or limitation in full papers.",
                "- Credibility scores are transparent heuristics, not peer-review judgments.",
                "- Generated text should be reviewed and edited before academic submission.",
                "",
                f"## {next_number + 1}. Future Scope",
                "",
                "- Add full-text PDF ingestion with permission-aware extraction.",
                "- Add optional LLM synthesis with claim-level citations.",
                "- Generate literature survey tables and viva questions from verified evidence.",
                "- Add user workspaces only after the core research workflow is validated.",
                "",
                f"## {next_number + 2}. Conclusion",
                "",
                (
                    f"The research pipeline provides a traceable starting point for studying {topic}. "
                    "Its strongest value is not automatic prose generation alone, but the connection "
                    "between research questions, evidence quality, synthesized findings, and references."
                ),
                "",
            ]
        )
        return sections

    def _format_reference(self, index: int, source: dict, style: str) -> str:
        if source.get("is_demo"):
            return f"{index}. Demo record — not a citable source: {source['title']}."

        authors = source.get("authors") or ["Unknown author"]
        year = source.get("year") or "n.d."
        venue = source.get("venue") or "Unknown venue"
        url = source.get("url") or source.get("open_access_pdf") or ""
        if style == "ieee":
            author_text = ", ".join(authors[:3])
            if len(authors) > 3:
                author_text += ", et al."
            return (
                f"[{index}] {author_text}, “{source['title']},” "
                f"*{venue}*, {year}. {url}".strip()
            )

        author_text = ", ".join(authors[:6])
        if len(authors) > 6:
            author_text += ", et al."
        return (
            f"{index}. {author_text} ({year}). {source['title']}. "
            f"*{venue}*. {url}".strip()
        )

    def _source_number(self, source: dict, sources: list[dict]) -> int:
        source_id = source.get("id")
        return next(
            (
                index
                for index, candidate in enumerate(sources, start=1)
                if candidate.get("id") == source_id
            ),
            1,
        )

    def _title(self, topic: str, report_type: str) -> str:
        labels = {
            "academic_report": "Academic Research Report",
            "literature_review": "Structured Literature Review",
            "project_proposal": "Research-Informed Project Proposal",
        }
        return f"{labels.get(report_type, 'Research Report')}: {topic}"
