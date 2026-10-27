# Structured report engine

The existing synthesis and citation services now produce a typed canonical report with title, academic level, selected format, sections, references, evidence-linked claims and editorial validation warnings. Existing Markdown and API fields remain compatible. Report display and exports are projections of retained results; historical research snapshots are not overwritten.

## Formats and depth

- Academic Report: abstract, introduction, methodology, overview, objectives, questions, analysis approach, literature, findings, gaps, limitations, future scope, discussion and conclusion.
- Literature Review: adds search/selection and methods comparison, with source limitations and future directions.
- Research Proposal (`project_proposal`): evidence background, proposed solution, evaluation protocol and milestones; proposed outcomes are explicitly not achieved results.
- Comparative Analysis (`comparative_analysis`): comparison criteria, source-by-source methods, findings, discussion and limitations. Available through the backend request contract; the existing three-option form is preserved.

Undergraduate, MCA, Master's and PhD policies determine excerpt depth, methodological emphasis and review tasks. Reports remain extractive evidence reviews rather than unverified LLM prose. Recommendations and review procedures are labeled as tasks, not scholarly findings.

## Evidence and citations

Claims retain paper and evidence IDs. The audit checks exact statement text, evidence ownership and offsets into retained source text. Unsupported finding/gap statements are flagged in the canonical report and excluded from synthesized prose. Incomplete sections and missing citation metadata appear in editorial notes. This is traceability validation, not independent verification of a study's correctness.

APA uses author-date labels and alphabetized references; same-author/year suffix assignment is stable across input order. IEEE uses repeated numbered labels in paper appearance order. Names, dates, venues and identifiers come from provider metadata. Missing structured family/given names are flagged rather than guessed. Formatting guidance: [APA author-date system](https://apastyle.apa.org/style-grammar-guidelines/citations/basic-principles/author-date) and [IEEE Reference Guide](https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE_Reference_Guide.pdf).

## Export

Authenticated `GET /api/research/{research_id}/report/export/pdf` and `/docx` endpoints enforce ownership, completion and source availability. Responses are attachments with private/no-store caching. The existing report toolbar adds PDF and DOCX download buttons alongside Markdown. Renderers consume the same canonical report and never retrieve external URLs or call a model.

`report_docx.py` uses python-docx; `report_pdf.py` uses ReportLab with escaped text, an embedded font, pagination and page numbers. `report_rendering.py` supplies shared document traversal. Install the updated backend requirements and restart the backend before using exports.

## Validation and limits

Tests cover four formats, MCA/PhD differences, APA/IEEE labels, stable APA suffixes, supported/unsupported claims, DOCX paragraph content, PDF structure, download authorization and preservation of stored snapshots. Full backend and frontend test suites, frontend type checks and production build are run.

This is a structured draft, not a journal-specific submission template. References depend on incomplete provider metadata, and publication-specific typography may require editing. PDF's embedded Vera font has limited script coverage; DOCX preserves Unicode for rendering with installed fonts. The evidence audit cannot independently establish causality or cross-study consistency. No new live retrieval or live LLM calls are required by the report engine.
