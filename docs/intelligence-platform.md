# Research, learning, project and career intelligence

Implemented as an additive enrichment of completed, owned research runs. Existing research requests, responses and form fields are preserved.

## API and storage

- `GET /api/research/{id}/intelligence` reads the saved snapshot or returns `not_generated`.
- `POST /api/research/{id}/intelligence` discovers and saves recommendations, or returns the existing snapshot. Requires the existing session and CSRF token. Incomplete runs and runs without scholarly sources return 409; other users receive 404.
- Migration 4 adds `research_intelligence`, with a primary/foreign key to the research run. The JSON snapshot stores paper, gap, dataset, skill and project relationships. The original research tables and snapshots are retained.
- Opening a completed run automatically starts enrichment. Navigation between result sections does not cancel enrichment. Reload reads the persisted snapshot. Failed HTTP requests expose a retry action.

## Modules and provenance

Datasets use the Hugging Face API and a live repository-page check. Dataset licenses are provider-reported, not inferred. Courses use a small MIT OpenCourseWare catalog and live official-page checks. Suggested course difficulty and skill mapping are explicitly labeled. Unknown duration remains null.

Skills include foundational, technical, research and advanced groups, with domain additions for healthcare, education, cybersecurity and blockchain. Roadmaps cover four levels. Projects, career pathways and next steps are rule-generated guidance and contain links by identifier to the completed run's papers, supported gaps and verified datasets. No research finding or supported gap is invented.

Suggested internship roles are separate from verified listings. Listings require an explicit internship title in the Remotive feed and a live page without a recognized closure marker. This is a listing-at-check-time verification, not an employer guarantee. Remotive attribution and original links are shown. The feed is cached for six hours to limit requests.

Network requests use HTTPS and an exact host allowlist, reject redirects, limit response sizes and have six-second timeouts. Discovery uses three workers; no more than two enrichment requests run concurrently per process. Errors expose only exception classes, never raw URLs with credentials or request details. Each resource section distinguishes unavailable providers, no matches, partial results and verified resources.

## Verification

- 50 backend tests cover existing research/auth plus recommendation traceability, ownership, persistence/idempotence, missing evidence, invalid URLs/metadata, provider failures, partial resources, course verification and expired internships.
- Six frontend Node tests cover API host resolution, safe links, statuses and section identifiers; production build passes.
- Headless Chrome verified signup -> dashboard -> real five-paper research -> enrichment -> all new tabs -> reload/history -> saved roadmap -> sign-in/sign-out.
- Live healthcare/AI check returned six verified dataset pages and two verified course pages; zero matching active internships. This is an observed result, not a fabricated vacancy count.

Run backend tests from `backend`: `../.tmp/local-venv/Scripts/python.exe -m unittest discover -s tests`.
Run frontend tests from `frontend`: `node --test tests/*.test.js src/services/*.test.js`, then `npm.cmd run build`.
Optional network check: `python scripts/verify_live_intelligence.py` from backend.
Browser check from repository root: `node scripts/verify-intelligence-browser.mjs` with backend 8000 and frontend 5173 running. Creates a local review account and retains its research record.

## Remaining limitations

Discovery coverage is limited to Hugging Face, two MIT foundation courses and the Remotive remote-job feed. Recommendations are transparent rules, not personalized competency assessment. Search relevance does not guarantee dataset suitability; licenses and data ethics still need review. Saved resources are historical snapshots with timestamps and are not automatically reverified. Internship availability can change after verification. No matching listing is preferable to inventing a vacancy. Multi-process deployments need shared admission/rate limiting. The browser verification uses locally installed Chrome on Windows.
