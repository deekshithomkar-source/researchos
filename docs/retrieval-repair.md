# Scholarly retrieval repair — 2026-10-26

## Root cause and evidence

The four most recent failed database records had provider warnings stating that
both Semantic Scholar and Crossref were unavailable after retries. The orchestrator
converted every empty source list into the same "No scholarly evidence" message,
misrepresenting retrieval failures as a lack of literature. Old diagnostics did
not retain HTTP status or underlying error type, so the historical Crossref
failure cannot be identified more precisely.

Direct reproduction found Semantic Scholar returning HTTP 429. OpenAlex and
Crossref both returned HTTP 200 and real records. Running these same probes in
the restricted execution environment failed with Windows socket error 10013 for
all providers. The local backend had also remained an old process; it was restarted
with the new implementation and permitted outbound network access. Provider
credentials alone cannot fix an environment that denies outbound sockets.

Additional weaknesses found: one exact topic query only; no OpenAlex adapter;
one malformed provider record could abort an entire batch; optional null metadata
was not consistently handled; no topic relevance guard; deduplication preferred
DOI/URL instead of also comparing normalized titles. The old Crossref request
worked during diagnosis; no unsupported-parameter failure was reproduced.

## Changes

The existing route, background executor, authentication, SQLite tables, React
layout and result fields are preserved. No runtime dependencies or deployment
configuration were added.

- Provider order: OpenAlex, Crossref, then Semantic Scholar. Query variations are
  attempted when the target is not met. Retrieval stops when enough unique papers
  are available, avoiding unnecessary provider calls.
- Query planning considers exact topic, broader keywords, objective/domain terms,
  related terminology and a research question. Academic level controls review
  depth rather than appending a restrictive degree name. Duplicate queries are
  collapsed; at most five are executed.
- Common normalization retains id/venue/provider for the UI and exposes aliases
  paper_id/journal/source_provider, alongside title, authors, year, abstract, DOI,
  URL and citation count. Missing optional metadata is allowed. OpenAlex inverted
  abstracts are reconstructed by token position.
- Per-record parsing preserves valid records when others are malformed. Validation
  checks a title and usable HTTP(S) link or DOI, omits retracted/non-paper records,
  and applies a broad lexical relevance guard with application-domain vocabulary.
- DOI, normalized title and conservative near-identical long-title deduplication
  run across providers and query variants. Conflicting numbers/negation prevent
  fuzzy merging. No source is fabricated to meet a target.
- Each provider attempt logs name, HTTP status, raw/valid/rejected counts,
  rejection reasons, duplicates, duration, safe error type/code and research_id.
  Two event types distinguish HTTP normalization from topic validation/deduplication;
  aggregate only academic_provider_evaluation events to avoid double counting.
- Query text is deliberately redacted in logs because student prompts may contain
  personal information. A query fingerprint correlates attempts; the actual query
  plan is saved in the owner-protected research result. Keys, headers, full URLs,
  provider response bodies and raw exception messages are never logged.
- Timeouts, bounded retry, process-wide request pacing and Retry-After cooldowns
  prevent rapid repeated calls. Authentication failures, 429 and invalid responses
  move to another provider. The configurable search budget stops new attempts;
  an already-running request may finish after that budget up to its socket timeout.

## Result/error contract

`retrieval_status` and `provider_diagnostics` are persisted in result_json and
returned by the existing status/result API, without a database migration:

| Code | Meaning |
| --- | --- |
| SUCCESS | Target met with no observed provider failures |
| NO_RESULTS | Successful searches returned no records |
| PROVIDER_UNAVAILABLE | Network, authentication or server failure prevented retrieval |
| RATE_LIMITED | A provider refused requests or is in cooldown |
| INVALID_PROVIDER_RESPONSE | Response shape/JSON or all returned records were unusable |
| INSUFFICIENT_EVIDENCE | No relevant eligible records, or only metadata with no abstracts for synthesis |
| PARTIAL_RESULTS | Usable papers retained despite a shortfall, provider failure, or missing abstracts |

Provider-specific diagnostics retain all causes even when one aggregate code is
selected. A nonempty metadata-only result can complete with partial=true; it is
not presented as an abstract-based or full-text synthesis. Zero usable records fail
with a cause-specific message. Existing React warning/error components show these
messages without a frontend redesign.

## Files

Modified:
- backend/app/services/research_provider.py
- backend/app/services/provider_services.py
- backend/app/agents/research_orchestrator.py
- backend/app/agents/search_agent.py
- backend/app/core/config.py
- backend/app/core/logging.py
- backend/app/schemas/research.py
- backend/.env.example
- backend/tests/test_foundation.py
- backend/tests/test_research_pipeline.py (use the actual subject of its recorded paper)

Created:
- backend/app/services/search_queries.py
- backend/app/services/paper_normalization.py
- backend/tests/test_retrieval.py
- backend/tests/fixtures/retrieval_topics.json (recorded real provider results)
- backend/scripts/verify_live_retrieval.py
- docs/retrieval-live-results.json
- docs/retrieval-repair.md

## Verification

Offline: `python -m unittest discover -s tests -v` from backend. The 31 tests cover
existing auth/ownership/progress/persistence and retrieval-specific null metadata,
malformed batches, 429 fallback, 401/network failure, invalid responses, 500 retry,
query variation, DOI/title deduplication, relevance, redacted diagnostics, all four
requested topics with recorded papers, and safe error persistence.

Live (explicit, separate from unittest discovery):
`python scripts/verify_live_retrieval.py` from backend. It probes all three providers
and submits all four topics through authenticated API routes and the real background
adapter, using a temporary SQLite database. Assertions cover queued response,
completed processing, real source records, report/findings, numeric-ID reopening
and history. Results, paper titles, DOI values and provider counts are recorded in
[retrieval-live-results.json](retrieval-live-results.json).

The local Chrome check passed signup, dashboard authentication, research submission,
visible progress, five actual healthcare papers, report rendering, refresh, history
reopening, sign-in and signout. One local review account and its successful research
run were retained. Existing user data and earlier failed runs were preserved.

Frontend build and its three API URL regression tests pass. Python compilation and
pip dependency checks pass. No frontend lint/typecheck scripts are configured.

## Configuration and limitations

Server-only optional variables: OPENALEX_API_KEY, SEMANTIC_SCHOLAR_API_KEY,
RESEARCH_CONTACT_EMAIL. SEARCH_BUDGET_SECONDS defaults to 90; existing provider
attempt/timeout controls remain. Never place these keys in VITE_ variables.

OpenAlex basic anonymous search worked in this verification. Its current
[authentication documentation](https://help.openalex.org/api/authentication/)
explains the higher budget available with a key. Crossref anonymous retrieval
worked; its [REST API guidance](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/)
documents filtering/query options. Semantic Scholar returned 429; its
[official API documentation](https://webflow.semanticscholar.org/product/api)
describes shared anonymous limits and API-key access.

Rate-limit coordination is process-local, matching the existing development
worker. Distributed workers need a shared limiter. Provider availability and result
ordering can change. Lexical relevance is deliberately permissive and does not
establish that a paper answers a question. Near-identical titles can occasionally
represent distinct publications. Source completeness, full-text extraction and
claim-level synthesis remain limitations, not fabricated capabilities.
