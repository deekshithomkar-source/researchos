# Scholarly retrieval and scholar metadata

## What changed

The existing OpenAlex, Crossref and Semantic Scholar adapters, five-candidate query planner, bounded concurrent provider fallback, DOI/title deduplication and multi-signal relevance ranking were retained. Official documentation confirmed OpenAlex's bearer-key support and current anonymous use; Crossref supports anonymous metadata and a contact-address polite pool; Semantic Scholar supports optional API keys but anonymous requests may be heavily throttled.

Normalization now retains provider-supplied author IDs, checksum-valid ORCIDs, publication-associated affiliations and UTC retrieval timestamps. Canonical papers expose paper_id, title, authors, author_identifiers, year, journal, DOI, URL, abstract, citation count, provider, retrieved_at and evidence_scope. Duplicate merging preserves scholar records and identifier/affiliation metadata across providers.

Scholar discovery returns provider-reported authorship records with identifiers, affiliations and related_paper_ids. Related publications are limited to the verified papers retrieved for this run; this is not a complete author bibliography. Authors are joined by a verified identifier when present, never by name alone. For unidentified authors, internal IDs remain paper/position-scoped. Missing affiliations/identifiers remain empty. Provider assertions are not independent identity or employment verification; publication affiliations may be historical.

Migration 5 adds research_authors and research_paper_authors, with run/paper/author foreign keys. Papers, source provenance, evidence offsets and full-text metadata use existing normalized tables and JSON snapshots. Retrieval diagnostics remain stored in the run snapshot. Persistence is idempotent and preserves historical research.

## Full-text evidence

Set `RESEARCH_FULLTEXT_ENABLED=true` in the backend environment and restart to enable automatic full-text enrichment. Default is false to preserve abstract-only operation and avoid extra provider requests without configuration. At most two DOI-bearing papers are checked per run.

Europe PMC DOI lookup must match the paper DOI, report open access, and return a valid PMC identifier. The XML article DOI is checked again. Only bodies with explicit supported CC-BY, CC-BY-SA or CC0 license URLs are retained; other licenses or missing license metadata are not guessed. Requests use a fixed official HTTPS endpoint, disable redirects, impose timeouts/size limits, and honor rate-limit cooldowns. XML entity declarations are rejected. No arbitrary publisher/PDF downloads or paywall bypasses are attempted.

Full-text bodies are normalized paragraph text, bounded to 100,000 characters with an explicit truncation flag. Evidence records retain `locator=full_text`, exact offsets, source URL and paper ID. Abstract-only evidence retains `locator=abstract`. Reports label the locator. Full-text failure preserves abstract evidence and returns a diagnostic. Stored text, license URL and retrieval timestamp allow exact replay and attribution. Selected excerpts are not an exhaustive analysis of the whole article.

## Live verification

Actual provider requests on this implementation produced:

| Provider | Result |
|---|---|
| OpenAlex | HTTP 200; five accepted papers in the independent healthcare probe |
| Crossref | HTTP 200; five records normalized, two distinct papers after deduplication in the independent probe |
| Semantic Scholar | HTTP 429; rate limited, zero accepted. Live success is **not** claimed |
| Europe PMC | HTTP 200; DOI-matched licensed body, followed by successful evidence and SQLite verification |

Authenticated API -> worker -> provider retrieval -> normalization -> scholar discovery -> evidence -> SQLite -> result/history completed for three unrelated topics:

| Topic | Saved papers | Run-scoped scholars | Identifiers | Evidence passages |
|---|---:|---:|---:|---:|
| Artificial Intelligence in Healthcare | 5 | 14 | 20 | 30 |
| Solar photovoltaic energy storage | 5 | 25 | 41 | 36 |
| Medieval trade networks | 5 | 4 | 1 | 16 |

These flows were partial because one provider was unavailable/rate-limited or evidence sections were incomplete; no papers were invented to fill missing coverage. All three reached the requested five-paper target. Counts are per run, not deduplicated global person counts.

Full-text verification used real paper DOI `10.1093/nar/gku1061`: [Europe PMC full-text XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4383902/fullTextXML), [CC-BY 4.0 license](https://creativecommons.org/licenses/by/4.0/). It retained 19,065 body characters and 16 exact evidence passages, verified their source offsets, and persisted/reloaded the body and evidence in an isolated SQLite database.

Public metadata, diagnostics and results are saved in `docs/scholarly-live-results.json`. Live checks use temporary databases/accounts and do not change users' saved research.

## Automated verification

79 backend tests passed, including provider conversion, malformed/missing metadata, identifier checks, same-name author separation, repeated normalization, deduplication, full-text identity/license checks, entity rejection, source offsets, provider failure and author-link persistence. Existing authentication, research, intelligence and LLM regressions remain covered. Frontend result-contract type checks and production build passed.

Commands:

- Backend: `../.tmp/local-venv/Scripts/python.exe -m unittest discover -s tests` from backend.
- Optional live providers/API: `python scripts/verify_live_scholarly.py` from backend.
- Optional licensed-body/persistence check: `python scripts/verify_live_fulltext.py` from backend.
- Frontend: `npm.cmd run typecheck` and `npm.cmd run build`.

## Files

New: `backend/app/schemas/scholarly.py`, `backend/app/services/scholar_discovery.py`, `backend/app/services/full_text.py`, `backend/app/models/scholarly.py`, `backend/tests/test_scholarly.py`, and both live-check scripts.

Updated: academic provider conversion/merging, paper normalization, research/canonical schemas, evidence extraction/validation/synthesis, orchestrator, artifact persistence, migrations, configuration, backend environment example, and the generated frontend result contract.

## Remaining limitations

Semantic Scholar needs a successful later integration check before it can be called verified working in this environment; configure its server-side API key where available. Metadata completeness depends on provider deposits. Relevance/credibility use transparent lexical and metadata signals, not independent peer-review assessment, and citation count is only one signal. Full-text coverage is limited to licensed Europe PMC bodies and is opt-in. Scholar profiles and complete external bibliographies are not crawled. Rate limiting and concurrency remain process-local; distributed deployments require shared coordination.

Official references: [OpenAlex authentication](https://help.openalex.org/api/authentication/), [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), [Semantic Scholar API](https://api.semanticscholar.org/api-docs/), [Europe PMC REST API](https://europepmc.org/RestfulWebService).
