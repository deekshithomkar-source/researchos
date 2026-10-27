# Academic-level policies

`app/services/depth_policy.py` is the single source for Undergraduate, MCA, Master's and PhD processing. The existing policy fields remain compatible; explicit complexity, explanation, methodology, evidence requirements, learning recommendations, gap review and career preparation have been added.

| Level | Review task | Evidence obligation | Learning/project emphasis |
|---|---|---|---|
| Undergraduate | Guided interpretation, glossary and a supervised example | Trace observations and avoid generalizing an example | Prerequisites, introductory exercises, annotated portfolio |
| MCA | Algorithms, architecture and evaluation planning | Identify implementation details; mark missing datasets/metrics unknown | Tested baseline, data checks, integration and reproducibility |
| Master's | Comparative methods and robustness | Multiple studies and comparable populations/outcomes | Study-design matrix and sensitivity analysis |
| PhD | Validity, competing explanations and experimental design | Full methods, reproducibility checks and broader review before novelty claims | Falsifiable protocol and research proposal |

The same policy text reaches both LLM agent paths, including semantic gap analysis. Deterministic reports include a level-specific review section with actual evidence-coverage checks. These are explicitly guidance rather than new findings. Missing methods, insufficient cross-paper coverage and absent full text are flagged when relevant. A PhD selection does not automatically produce conflicts, new gaps or claims of novelty.

Projects, skill ordering, learning roadmaps, course study recommendations and career portfolio preparation use these policies. Course title, URL, provider and difficulty remain unchanged; an introductory course does not become advanced because the user selected PhD. Career preparation describes portfolio work, not qualification or a guaranteed role. Verified papers, source evidence, citations and established gaps remain unchanged across levels for the same retained evidence.

Guidance revision 2 refreshes older aggregate responses from retained resources without new network checks or overwriting historical research. Existing per-module snapshots remain historical snapshots; this change does not introduce a refresh endpoint.

Tests use identical source evidence across all four frontend levels and verify invariant metadata, differing methodology/structure/recommendations, consistent agent policies, and honest missing-evidence behavior. Live LLM prose quality remains unverified without configured credentials; deterministic policy behavior is testable independently.
