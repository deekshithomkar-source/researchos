# Specialized intelligence modules

The research engine and authentication remain intact. Intelligence uses the completed run and preserves the existing version-2 response fields. `module_revision=1` marks the expanded guidance. Saved older payloads receive a read-only presentation upgrade using their retained resource checks; this does not claim fresh verification or overwrite research snapshots.

Independent processors in `app/services/intelligence_modules.py` handle datasets, courses, skills, projects, internship roles/listings, career paths, roadmap and prioritized next steps. The existing `SupportedGapDetector` handles evidence-backed gaps, now including explicitly reported understudied populations. Gap statements retain exact evidence and paper IDs; absence of evidence does not establish a gap.

Each requested module has a Pydantic item schema and a separate run-keyed SQLite table (`intelligence_research_gaps`, `intelligence_datasets`, `intelligence_skills`, `intelligence_courses`, `intelligence_projects`, `intelligence_internships`, `intelligence_career_paths`, `intelligence_next_steps`). Records store structured JSON and module status. New records commit atomically with the compatible aggregate; repeated POSTs do not duplicate records. Migration 6 is additive. Existing aggregate records are retained; POST backfills module snapshots when necessary.

Projects include topic, paper IDs, supported finding IDs, gap IDs, dataset IDs and skills. Career paths link the topic, skills, projects and suggested internship roles. Course metadata includes its suggested level and recommendation reason. Next steps carry ordered priorities and rationale. The existing frontend sections display these fields without layout changes. Malformed course/dataset metadata remains empty with `invalid_response`; failures do not substitute other modules' text.

## Validation

Automated tests cover three unrelated topics across four academic levels, finding references, resource outages and malformed metadata, course reasons, population-gap language (including negation), separate module persistence, idempotency and ownership. Existing analysis, retrieval, LLM, authentication and result-contract tests remain part of the regression suite. Frontend tests cover section mapping, links and empty-state distinctions; TypeScript checks and the production build validate component integration.

## Limits

Guidance is rule-generated, not an assertion of experimental results or employment prospects. Topic specialization currently has explicit rules for healthcare, education, cybersecurity, blockchain, history and solar research, with general research guidance elsewhere. Gap detection uses conservative lexical patterns and cannot establish field-wide novelty or independently reconcile contradictions. Courses use the limited verified MIT OCW catalog, datasets use Hugging Face and live internship coverage uses Remotive. Availability is a timestamped snapshot. No new live-provider checks were performed for this change. Restarting the backend applies the additive tables; existing saved module snapshots are not automatically refreshed from the network.
