# Evidence-linked research pipeline upgrade

## Architecture and behavior

The existing React, FastAPI, SQLite, authentication, ownership checks, submission,
progress polling and history endpoints are preserved. ResearchOrchestrator now
coordinates these independent stages:

1. IntentAnalyzer extracts the explicit topic/objective, investigation type,
   concepts, academic depth and requested output. Its lexical method is disclosed.
2. ResearchQuestionGenerator produces five focused questions using that intent.
3. The existing query planner combines topic, objective, level and questions.
4. OpenAlex, Crossref and Semantic Scholar search concurrently, bounded by
   PROVIDER_CONCURRENCY (default 3), a process-wide semaphore, existing provider
   pacing/cooldowns and a shared search deadline. Every provider has isolated
   diagnostics; failures retain useful results from other providers.
5. Normalization preserves optional metadata. DOI/title deduplication merges provider
   origins. The bounded candidate pool is ranked before applying the source target.
6. RelevanceEvaluator exposes topic overlap (45%), objective overlap (20%), metadata
   credibility (15%), recency (10%) and abstract availability (10%). Missing objectives
   redistribute their weight. These are transparent heuristics, not scientific quality
   judgments or validated semantic relevance scores.
7. EvidenceExtractor selects at most 16 passages per abstract, prioritizing result,
   method and limitation passages. Every passage retains paper ID, exact text,
   abstract offsets and source URL. Missing abstracts produce no invented passages.
8. SupportedGapDetector classifies only explicit author-reported limitations,
   unresolved questions, conflicts, dataset shortages, methodological limitations
   and future recommendations. Negated claims and study designs without explicit
   limiting language do not create gaps. It does not infer field-wide novelty or
   independently adjudicate contradictions between studies.
9. Synthesis organizes overview, objective, questions, literature review, key findings,
   supported gaps, research limitations and future scope. Excerpts remain attributed.
   Unsupported sections carry explicit incompleteness notices. Metadata-only results
   are labeled literature catalogs, not substantive findings. Zero sources fail before
   report generation. Project-proposal output does not invent a validated solution.
10. CitationGenerator formats APA/IEEE references and inline labels using only supplied
    metadata. DOI links are preferred. APA references are alphabetized. Structured
    given/family names are used when available; otherwise provider display names are
    retained and incomplete metadata is flagged. Missing authors, dates and venues
    are not fabricated. Abstract statements have not been independently replicated.
11. Traceability validation runs before persistence/synthesis: passages must match exact
    abstract slices; findings and gaps must reference existing passages and reproduce
    their text; gap category support and citation membership are checked.

## Database and compatibility

Additive migration version 3 creates research_papers, research_sources,
research_evidence, research_findings, research_gaps and research_reports, plus
finding/evidence and gap/evidence join tables. ResearchRun remains in the original
research_sessions table. Composite foreign keys scope each evidence link to its run.

Stage checkpoints and completion atomically write both the existing JSON snapshot
and normalized records. Repeated checkpoint writes are idempotent. Failed synthesis
retains already-extracted evidence without inventing a completed report. Existing
historical runs are preserved and remain readable; they are not automatically
re-analyzed or backfilled into the new tables. Existing unassigned historical data
is not assigned to new accounts.

Existing endpoints and fields remain. New response fields are intent, evidence,
key_findings, gaps, gap_assessment, citations, report_sections and missing_sections.
Each source may expose ranking and provider origins. The old question/source
`findings` field is retained for existing clients; `key_findings` holds explicitly
supported result statements. No frontend component was changed.

Stages now use planning, searching, validating, extracting, analyzing, synthesizing,
completed/failed. The old evaluating state is still accepted for historical records.
Admission limits and restart recovery recognize both evaluating and validating.

## Verified results

- 41 backend tests pass, including 10 new analysis/persistence tests.
- Tests cover provider failure, concurrent bounded execution, duplicate merging,
  missing abstracts, invalid metadata, objective-dependent relevance, exact evidence
  traceability, all six gap categories, conservative gap suppression, APA/IEEE,
  missing citation fields, partial results, normalized records, foreign-key checks,
  checkpoint idempotency, report reopening and failed-synthesis preservation.
- Frontend production build and all 3 existing API URL tests pass.
- Python compilation and dependency checks pass.
- A separate real-provider integration exercised all four topics through authenticated
  submission, background execution, saved reports and history reopening in a temporary
  database. It also checked normalized table counts and passage traceability.
- Final conservative gap rules were replayed against the exact live paper snapshots;
  final_analysis_check records the final findings/gaps, including removal of weak
  gap classifications. Provider retrieval was not simulated in the live run.

| Topic | Saved papers | Exact passages | Supported findings | Supported gaps |
| --- | ---: | ---: | ---: | ---: |
| Artificial Intelligence in Healthcare | 5 | 30 | 0 | 0 |
| Machine Learning in Education | 5 | 0 | 0 | 0 |
| Cybersecurity using Blockchain | 5 | 33 | 1 | 0 |
| AI adoption in Indian higher education | 5 | 45 | 1 | 1 |

Zero findings/gaps mean that this conservative extractor did not identify explicitly
supported statements, not that no findings/gaps exist in the literature. Education
results were metadata-only in this run because the successful provider records
lacked abstracts. OpenAlex and Semantic Scholar returned rate-limit responses during
parts of the test; Crossref sustained partial retrieval.

Live records and final traceability checks are in
[analysis-live-results.json](analysis-live-results.json).
Run backend tests with `python -m unittest discover -s tests -v`.
Run separate network verification with `python scripts/verify_live_retrieval.py`.

## Files

New:
- app/schemas/analysis.py: typed intent, ranking, evidence, findings, gaps and citations.
- app/agents/evidence_analysis.py: intent/questions, ranking, extraction and gap analysis.
- app/agents/evidence_synthesis.py: evidence-linked sections and report rendering.
- app/services/citations.py: metadata-only APA/IEEE formatting.
- app/models/analysis.py: normalized database records and evidence links.
- app/services/research_artifacts.py: atomic, validated artifact persistence.
- tests/test_analysis.py: analysis and persistence regression tests.

Updated backend files: agents/research_orchestrator.py, agents/report_agent.py,
services/research_provider.py, services/paper_normalization.py,
services/research_runs.py, services/execution.py, schemas/research.py,
core/config.py, db/migrations.py, .env.example, scripts/verify_live_retrieval.py.

## Limits

This implementation is deterministic and extractive; no LLM provider was introduced.
Full-text fetching is not enabled; evidence comes from provider-returned abstracts.
Lexical intent/relevance and gap classifiers can miss valid semantic relationships.
Citation completeness depends on provider metadata; display-only author names are
not guessed into family/given name structure. Provider budgets and cooldowns can
reduce completeness. Concurrency/rate limits are process-local; distributed workers
need shared coordination. The existing background worker remains non-durable.

## Local rollout verification

The existing database was backed up before rollout, and no active runs were present.
The local backend was restarted and applied additive migration 3. Chrome verification
passed signup, dashboard authentication, submission, visible progress, five real
sources, additive intent/citation/report-section fields, exact abstract offsets,
refresh, saved-report reopening, sign-in and signout. One review account and its
successful research run remain in local history. The local frontend and backend
are left running for review.
