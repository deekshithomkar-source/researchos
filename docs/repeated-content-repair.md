# Repeated-content repair

## Root cause (audited before edits)

1. ResearchWorkspace rendered Papers and Sources with the same `sources` array and the same JSX condition. This was an exact frontend duplication.
2. IntentAnalyzer collapsed MCA, Master's and PhD into one advanced setting. Evidence synthesis ignored that depth when selecting passages or assigning analysis tasks.
3. Academic reports and literature reviews shared all report sections; proposals added only one generic paragraph.
4. Intelligence generation used fixed project and career templates without academic-level input. Its persisted version-1 snapshots had no presentation upgrade path.
5. APA/IEEE formatting already worked, but paper cards omitted formatted citations. The form and database retained all settings correctly. Source target already reached discovery and final ranking.
6. The active engine has no configured generative LLM: it extracts and organizes provider metadata and abstract excerpts. No malformed LLM response was being reused across modules, and provider failures were not replaced with one generic report.

## Changes and compatibility

`ResearchResponse.modules` is a canonical, typed result object with overview, research_questions, papers, sources, research_gaps, datasets, skills, courses, projects, internships, career_paths, next_steps, roadmap, module_status and report. Each module has its own Pydantic schema. Legacy `sources`, `report`, `summary`, and other response fields remain unchanged for existing clients. The frontend uses the new module fields, including the canonical report for copy/download.

Papers display bibliographic records, abstracts, relevance scores and APA/IEEE citations. Sources display provider identities, provider record IDs, metadata availability and paper links. Other tabs map only to their named module, with empty states and provider status messages. Reports contain structured sections and formatted references.

Undergraduate tasks focus on concepts and guided replication; MCA on tested software implementation and baseline evaluation; Master's on methods comparison and sensitivity analysis; PhD on falsifiability, validity and novelty audits. These policies change research questions, passage budgets, analysis instructions, skills, project deliverables and roadmap specialization. They do not modify retrieved facts or pretend that source text proves novelty.

Academic reports organize findings and implications; literature reviews organize search/selection, study comparison and limitations; proposals organize evidence, a proposed investigation, evaluation protocol and milestones. APA and IEEE remain distinct formatting choices. `output_type` is accepted as an alias for existing `report_type`; `source_target` remains an alias for `source_limit`. The existing form gains explicit Undergraduate, Master's and PhD choices without a redesign.

Saved runs are projected into the new presentation using their retained evidence. Version-1 intelligence is adapted using its saved resource listings, without new network calls or changing verification timestamps. Original research JSON, reports and evidence remain untouched. New intelligence snapshots include the canonical typed modules. GET research includes saved enrichment when available.

## Files changed

Backend:
- `app/schemas/modules.py`: canonical module schemas (new).
- `app/schemas/research.py`: additive typed modules and output alias.
- `app/services/depth_policy.py`: four depth policies (new).
- `app/services/result_modules.py`: canonical projection and historical adapter (new).
- `app/services/research_runs.py`: add canonical result when serializing.
- `app/services/intelligence.py`: level-aware skills, tasks and roadmap; version 2.
- `app/agents/evidence_analysis.py`: level-aware intent and questions.
- `app/agents/evidence_synthesis.py`: distinct report structures and evidence depth.
- `app/api/research_routes.py`: typed enrichment response and saved-result projection.
- `tests/test_module_flow.py`: regression matrix and historical preservation checks (new).
- `scripts/generate_result_contract.py`, `scripts/verify_saved_module_flow.py`: contract generation and retained-real-evidence replay (new).

Frontend:
- `src/components/ResearchWorkspace.jsx`: separate paper/provenance renderers and canonical overview, gaps and report.
- `src/components/IntelligenceSections.jsx`: explicit canonical mappings and empty states.
- `src/components/ResearchBrief.jsx`, `ResearchForm.jsx`: academic level options.
- `src/services/result-mapping.js`, `result-contract.d.ts`: typed mapping and generated contract (new).
- `tests/result-mapping.test.js`: per-tab mapping regressions (new).
- `tsconfig.results.json`, `package.json`, `package-lock.json`: result-component type checks and test scripts.
- `scripts/verify-module-flow-browser.mjs`: browser flow assertions (new).

## Validation

- 54 backend tests passed, including a 24-case matrix: four levels x three output types x two citation styles.
- Eight frontend tests passed, including section isolation and no cross-module fallback.
- `npm run typecheck` passed for result components, mapping and their imported dependencies; this JavaScript application has not been migrated wholesale to TypeScript.
- `npm run build` passed.
- 24 settings combinations replayed against five real retained provider papers, preserving exact abstracts. Evidence is in `module-flow-live-replay.json`; this replay is not 24 independent live retrievals.
- Browser verification passed: a real PhD / project proposal / IEEE run retrieved five papers; paper citations and source provenance rendered separately; all intelligence tabs rendered; saved history survived refresh; signup, sign-in and sign-out passed. Discovery retained six verified dataset pages, two course pages and zero matching internship listings.

## Remaining limitations

Analysis is deterministic and extractive, not an LLM-generated critical review. Greater depth means different review tasks and more available evidence, not additional unsupported findings. Identical topics can correctly retrieve the same papers across levels and citation styles. Resource discovery retains the existing limited catalogs and verification-at-check-time semantics. Missing source metadata remains missing. Original saved reports remain available in legacy API fields; the UI uses the corrected canonical presentation. No historical research was deleted.
