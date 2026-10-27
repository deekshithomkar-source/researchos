# Research engine foundation

## Current architecture

The existing React + FastAPI + SQLAlchemy/SQLite application is extended in place.
The dashboard, existing report layouts, and the existing research_sessions table remain.

```text
React signup/signin -> FastAPI auth -> Argon2id + SQLite session -> HttpOnly cookie
React brief -> POST /api/research -> owned ResearchRun (queued) -> 202 + research_id
                                 -> ResearchExecutor.enqueue(research_id)
                                    -> FastAPI background thread (development)
                                       -> execute_research(research_id)
                                          -> ResearchOrchestrator
                                             -> explicit intent from brief
                                             -> existing question planner
                                             -> topic query
                                             -> academic discovery service
                                             -> metadata evaluation
                                             -> abstract/question mapping
                                             -> evidence coverage checks
                                             -> extractive summary + report
                                          -> SQLite checkpoints/result
React polling -> GET /api/research/{research_id} -> status + progress + result
React history -> owned runs only -> reopen the persisted result
```

### Inspection findings

Before this change: the current Dashboard already used services/api.js; POST
/api/research/run synchronously invoked ResearchOrchestrator; PlannerAgent,
SearchAgent, VerifierAgent, SummarizerAgent and ReportAgent existed. Providers were
Semantic Scholar and Crossref with generated demo records as a final fallback.
ResearchSession stored reports in research_sessions without ownership. AuthPage
stored plaintext passwords in localStorage. Backend auth stored salted SHA-256
hashes in data/users.json and returned user details without a session. Password
reset accepted an email and replacement password without proof of ownership.

## Authentication changes

- Existing signup/signin routes now establish random 256-bit opaque sessions.
- Only a SHA-256 digest of each session token is stored in SQLite. The browser's
  session credential is an HttpOnly cookie; no credential is available to React.
- Passwords use argon2-cffi's Argon2id implementation (64 MiB, 3 iterations,
  parallelism 1). Signup requires 12-128 characters; legacy passwords can sign in.
- Sessions expire after SESSION_HOURS (default 12), rotate at login, and are
  revoked at logout. Expired sessions are purged during session creation.
- CSRF protection combines a session-bound token on authenticated writes,
  mandatory custom client headers on all API writes, exact Origin checks, and
  explicit credentialed CORS origins. Tokens are kept only in React memory.
- /auth/me restores a session and supplies the CSRF token on reload.
- Authentication attempts are bounded by a persistent per-peer-IP window.
- All research reads and writes require authentication. Queries include user_id;
  another user's ID returns 404, including old numeric links.
- Prototype localStorage credential entries are deleted when the app opens. They
  are not imported as trusted accounts. Existing backend accounts are migrated.
- Password reset is intentionally unavailable (501). It must be replaced with a
  verified, expiring, single-use email recovery flow, not the old unsafe reset.
- Validation responses omit rejected input so password values are never echoed.

Security references: [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
and [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

## Database changes

app/db/migrations.py records numbered additive migrations in schema_migrations.
Startup runs them before accepting requests; migration errors stop startup.

1. Extends research_sessions with research_id (UUID), user_id, report_type,
   citation_style, source_target, status, progress, current_stage, status_message,
   updated_at, completed_at, error_message, result_json and partial. Existing id,
   report, findings and other columns remain intact. ResearchRun uses the existing
   table; ResearchSession remains an import alias.
2. Imports backend/data/users.json once into users. Legacy SHA-256 digests are
   wrapped in Argon2id during migration and replaced with direct Argon2id hashes
   after a successful sign-in. The source JSON is retained, never rewritten.

New tables: users, auth_sessions, auth_rate_limits, schema_migrations.
New research ownership/UUID indexes support scoped lookups.
Historical runs have user_id=NULL because ownership was never recorded. They
remain preserved but inaccessible through user APIs. Do not guess their owners.
The local database was backed up to .tmp/before-foundation-migration.db.

For another environment, back up its database first, preserve its DATABASE_URL,
then run from backend: `python -m app.db.migrations` (or start the API). Migration
is idempotent. Avoid running several migration processes concurrently. Keep the
old users.json and backups private; after verifying the migrated accounts,
archive or remove the old weak-hash file through your normal data-retention process.

## API changes

| Method and route | Behavior |
| --- | --- |
| POST /api/auth/signup | 201; creates account and session |
| POST /api/auth/signin | 200; validates password and rotates session |
| GET /api/auth/me | 200 authenticated user + CSRF token, otherwise 401 |
| POST /api/auth/signout | 204; revokes session and clears cookie |
| POST /api/auth/reset-password | 501; unsafe recovery removed |
| POST /api/research | 202; persists queued run and schedules it |
| POST /api/research/run | Compatibility alias with the new 202/polling behavior |
| GET /api/research/history | Owned runs; limit (1-200), offset |
| GET /api/research/{research_id} | Owned status/result; numeric legacy IDs also accepted |

POST accepts existing fields topic, objective, academic_level, report_type,
citation_style and source_limit; source_target is accepted as an alias.
Unknown input fields are rejected, including caller-supplied user_id.
POST returns queued metadata immediately; it no longer returns a finished report.
GET keeps existing top-level result fields (id, sub_questions, findings, sources,
summary, report, provider_warning), with the new run-state fields added:

```json
{
  "research_id": "server-generated-uuid",
  "status": "searching",
  "progress": 35,
  "current_stage": "searching_sources",
  "status_message": "Searching relevant scholarly sources"
}
```

Run states: queued, planning, searching, evaluating, extracting, analyzing,
synthesizing, completed, failed. Progress is a stage checkpoint, not a prediction
of remaining time. UTC timestamps include their timezone in JSON.
A completed run may have partial=true when evidence is limited. A failed run can
still contain retrieved sources and findings; those snapshots remain reopenable.

## Orchestrator and agent contracts

ResearchOrchestrator.run_async is independent of FastAPI and persistence. Typed
ResearchRequest, ResearchResult, Source, Finding and AgentContext models define
boundaries. The synchronous run method remains available for existing callers.
PipelineStage describes each stage; a checkpoint callback persists progress.

Only existing, bounded capabilities execute: explicit intent, template planning,
a topic query, real metadata retrieval, heuristic evaluation, abstract mapping,
coverage checks, extractive synthesis and report formatting. Coverage analysis
does not claim to identify research gaps. Template proposal guidance is labelled;
retrieved metadata has provenance='retrieved_metadata'. No LLM is configured.

agents/contracts.py defines Protocols for IntentAgent, PlannerAgent, SearchAgent,
PaperAgent, SourceEvaluator, EvidenceAgent, GapAgent, DatasetAgent, SkillAgent,
CourseAgent, ProjectAgent, CareerAgent, SynthesisAgent and ReportAgent. These are
interfaces, not agents returning invented records. A real optional gap_agent can
be injected; additional stages can be added through the stage registry.

## Provider services and reliability

Agent -> AcademicSearchService/SearchService/LLMService -> provider -> external API.
Existing Semantic Scholar and Crossref adapters remain in research_provider.py.
Synchronous HTTP work runs through asyncio.to_thread. HTTP timeouts and service
budgets are bounded; attempts are configurable (maximum 3). Real-source fallback
can preserve available evidence. Invalid/unsafe source records are omitted.
Provider failure never inserts generated demo sources. Missing evidence is
reported explicitly. No fabricated papers, authors, DOI values or URLs are used.

Worker logs are JSON records containing research_id and stage/progress or a safe
error type. Client failures do not receive raw provider exceptions or secrets.
Each stage checkpoints its partial result, including on failure. Duplicate worker
delivery is ignored after the queued run has been claimed. Per-user admission
limits prevent unbounded active submissions. SQLite count/insert is serialized.

## Background processing

FastAPIResearchExecutor is a small development adapter around BackgroundTasks.
The independent execute_research(research_id) owns its database sessions and runs
the orchestrator. A future Celery/RQ/Arq adapter need only enqueue this ID and call
the same worker entry point; routes and research logic do not move into the queue.

This development executor requires a single API process. It is not a durable
queue. During development startup, unfinished runs are marked failed with a clear
restart message and preserved snapshots. It does not silently resume or retry an
entire research job. With APP_ENV=production, automatic development recovery is
disabled. A durable worker/recovery policy is required before a multiworker rollout.
See [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/).

## Environment and local operation

All new settings are documented in backend/.env.example. No provider secret goes
in a VITE_ variable. Production configuration rejects insecure session cookies or
non-HTTPS frontend origins. For cross-site frontends, configure secure SameSite=None
cookies or use a same-site API proxy. Some browsers block third-party cookies.

Use the same hostname on both local services: 127.0.0.1 with 127.0.0.1, or
localhost with localhost. ALLOWED_ORIGINS must list the exact frontend URL.
Do not change DATABASE_URL while upgrading unless deliberately migrating data.

Install backend runtime dependencies with `pip install -r requirements.txt`.
Tests additionally require `pip install -r requirements-dev.txt`. Only Argon2 is a
new runtime dependency; httpx is a test dependency. The current review environment
uses .tmp/local-venv because the bundled backend/.venv referred to another computer.

## Files created

- backend/app/core/config.py, security.py, logging.py
- backend/app/models/user.py
- backend/app/db/migrations.py
- backend/app/api/dependencies.py, background.py
- backend/app/agents/contracts.py
- backend/app/services/provider_services.py, research_runs.py, execution.py
- backend/requirements-dev.txt
- backend/tests/test_foundation.py
- backend/tests/fixtures/crossref_deep_learning.json (retrieved Crossref metadata)
- docs/engine-foundation.md

## Files modified

- backend/app/main.py, db/database.py, models/research.py
- backend/app/api/auth_routes.py, research_routes.py
- backend/app/schemas/auth.py, research.py
- backend/app/services/user_store.py, research_provider.py
- backend/app/agents/research_orchestrator.py, search_agent.py, summarizer_agent.py, report_agent.py
- backend/requirements.txt, .env.example, tests/test_research_pipeline.py
- frontend/src/services/api.js, App.jsx
- frontend/src/pages/AuthPage.jsx, Dashboard.jsx
- frontend/src/components/ResearchWorkspace.jsx, ResearchHistory.jsx
- frontend/.env.example
- README.md, .gitignore

## Validation

From backend: `python -m unittest discover -s tests -v`.
The isolated database tests cover cookie signup/sign-in/logout, password hashing,
CSRF, expiry, cross-user UUID and numeric access, asynchronous queued submission,
observable searching progress, completion, history/reopening, real background
adapter execution, partial failure, provider fallback, admission limits, restart
recovery, migration idempotency and legacy password upgrades. Tests use recorded
real Crossref metadata, never a live provider dependency.

From frontend: `npm run build`. No TypeScript/typecheck or lint configuration
exists in this JavaScript repository; no claim of those checks is made.

### Previous implementation validation (historical)

- 15 backend tests pass, including new submissions against a migrated database.
- Python compilation and `pip check` pass.
- `npm run build` passes; no typecheck/lint scripts are configured.
- Chrome verification passed: signup -> logout -> sign-in -> submission -> visible
  searching progress at 35% -> completed result -> reload -> saved-result reopen.
- The live run retrieved five real Crossref records after Semantic Scholar was
  unavailable. It completed at 100% with partial=true because none included an
  abstract. Provider failure and missing evidence remained visible.
- Browser error checks were empty after the successful flow.
- One local verification account and its runs were created. The failed run from
  the migrated-timestamp regression is retained as history; the bug is fixed and
  covered by a regression test.

## Known limitations and next implementation

- Durable distributed jobs, crash recovery and multiworker coordination remain
  work for a production worker integration; the development adapter is intentional.
- Verified email recovery and email verification are not implemented.
- Legacy research ownership cannot be inferred; historical records remain private
  and unassigned pending an audited ownership migration.
- Provider availability/relevance varies. Empty results are failures; incomplete
  evidence is labelled. This is metadata/abstract research, not full-text analysis.
- LLM synthesis and advanced agents are contracts only. No course, internship,
  dataset, career, knowledge-graph or opportunity features were implemented.
- Behind a reverse proxy, configure trusted forwarding appropriately before
  relying on per-peer-IP authentication throttling.

Next: replace the development executor with a durable worker and add verified
account recovery before a public multiuser deployment. Then add one real agent
at a time with provenance and evaluation tests.

## Foundation review — 2026-10-23

The requested foundation was already present when this review began. The existing
React/FastAPI/SQLite architecture, authentication, staged orchestrator, provider
services, agent contracts, migrations and polling UI were inspected and retained.
No advanced agents or deployment changes were added.

Changes in this review:
- `backend/app/services/research_runs.py`: reopen pre-snapshot results from their
  original stored columns, including their source catalog. Ownership filtering
  still applies; unassigned historical records are not assigned to any user.
- The same service now returns not-found for numeric identifiers outside SQLite's
  signed 64-bit range rather than allowing an overflow to produce a server error.
- `backend/tests/test_foundation.py`: regression coverage for both cases.
- `docs/engine-foundation.md`: this review record; no new files or schema changes.

Validation: 17 backend unittest cases pass, including signup, sign-in, queued
submission, observed searching progress, completion, persistence, history reopening,
cross-user isolation, actual BackgroundTasks execution, provider failures and
migration compatibility. These tests use an isolated SQLite database and recorded
Crossref metadata. Python compilation and pip dependency checks pass. Frontend
`npm.cmd run build` passes. No frontend typecheck or lint scripts are configured;
this repository uses JavaScript/JSX. No fresh browser or live-provider verification
was performed in this review; the browser results above are historical.

The next recommended implementation remains a durable worker adapter with explicit
recovery semantics before a public multiworker deployment. Account recovery still
requires a verified email flow. Advanced research agents remain outside this scope.
