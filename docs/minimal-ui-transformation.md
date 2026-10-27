# Minimal ResearchOS UI transformation

## Scope and architecture

The existing React route switch still serves `/`, `/auth`, and `/dashboard`. The dashboard retains its authentication boot, submission payload, polling, history retrieval, result mapping, recommendation loading, and export service. No backend, database schema, environment secrets, dependency versions, or deployment configuration changed.

The former landing component is retained on disk but replaced at the route entry by `MinimalLanding`. Existing research components are reused. A final stylesheet layer scopes workspace changes under `.ros-app` and landing changes under `.ros-*`, preserving legacy components.

## Files

Created:
- `frontend/src/components/MinimalLanding.jsx`: responsive navigation, original SVG illustrations, clearly labelled interactive demonstration, capabilities, workflow, about, CTA and footer.
- `frontend/src/components/WorkspaceNavigation.jsx`: collapsible desktop sidebar, mobile modal drawer, focus containment, Escape dismissal and focus restoration, real profile and sign-out.
- `frontend/src/minimal.css`: visual tokens, responsive layouts, focus styles and reduced-motion handling.
- `scripts/verify-minimal-ui-browser.mjs`: live browser verification and responsive screenshots.
- `docs/minimal-ui-transformation.md`: this report.

Modified:
- `frontend/src/App.jsx`: landing route and page-specific metadata.
- `frontend/src/main.jsx`: design stylesheet import.
- `frontend/src/pages/Dashboard.jsx`: existing state wrapped in navigation; user greeting, section anchors and new-research focus action; removed scroll-driven scaling.
- `frontend/src/pages/AuthPage.jsx`: Sign In link selects existing sign-in mode via query parameter.
- `frontend/src/components/ResearchBrief.jsx`: accessible selected states and source-target group label.
- `frontend/src/components/ResearchWorkspace.jsx`: arrow/Home/End result navigation and clipboard failure feedback.
- `frontend/index.html`: Manrope font and absolute social image URL.

## Design system

Background `#F0EDE4`, ink/action `#020D19`, white surfaces, secondary surface `#F8F7F4`, accent `#536F8B`, borders `#E5E4DE`, muted text `#66717A`. Manrope headings and Inter body with system fallbacks; responsive heading sizes; 8px spacing tokens; 5–8px control/card radii; restrained borders and shadows. Simple CSS transitions, with reduced motion respected. No new dependencies.

## Verification

- Frontend unit tests: 9 passed.
- Existing result-component TypeScript check: passed. This configuration checks selected result components and services, not every JSX file.
- Vite production build: passed; approximately 90.56 kB compressed JS and 13.43 kB compressed CSS.
- Real Chrome workflow: signup, authenticated API, submission/progress, five scholarly sources, PhD/project-proposal/IEEE response, distinct paper/source sections, all recommendation tabs, persistence after reload, sign-in and sign-out passed.
- Live enrichment: six verified datasets, two verified courses, zero verified internship listings. Suggested roles remain separate.
- Responsive browser assertions at 320, 390, 780 and 1440 pixels; mobile menu, desktop collapse, drawer focus containment and Escape restoration checked.
- Screenshots saved locally under `.tmp/ui-*.png`; test accounts and their research runs are retained rather than deleting history.
- Browser workflow followed the `vercel:verification` skill at `C:/Users/ndeek/.codex/plugins/cache/openai-curated-remote/vercel/0.54.1/skills/verification/SKILL.md`.

## Limits and manual review

This is local Chrome validation, not a production deployment or cross-browser/accessibility certification. Real provider availability can vary. No real LLM call is claimed. The browser test verifies export controls and report content but does not inspect downloaded PDF/DOCX files or exercise the clipboard permission dialog. Backend tests were not rerun for these frontend-only changes. Fonts use Google Fonts with local system fallbacks. Existing CSS is retained beneath the new design layer to avoid breaking legacy components; a future dedicated cleanup can remove unused rules.

Review at `http://127.0.0.1:5173/`. Open Sign In or Get Started, submit a topic with your selected options, explore results and exports, then reload and reopen it from Research History. On mobile, open the workspace menu, use Research results to jump to the report area, and check keyboard navigation and reduced-motion preferences. Production deployment remains a separate action.
