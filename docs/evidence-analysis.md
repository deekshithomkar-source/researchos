# Evidence analysis and cross-paper synthesis

The existing retrieval providers and deterministic analysis remain intact. An additional bounded `evidence_analysis` agent runs after the existing LLM review/synthesis calls, sharing their run token budget, timeout, retry and concurrency controls. It receives the research brief, academic policy, questions, verified paper metadata and a round-robin selection of retained passages. Omitted evidence is counted. Maximum input/output tokens can limit coverage; no minimum finding count is imposed.

## Contracts and grounding

`schemas/evidence_analysis.py` defines claims (text, type, supporting evidence/paper IDs, model confidence and limitations), comparisons and candidate gaps. Types cover methods, populations, datasets, findings, limitations, contradictions and implications. Claims with invalid references, mismatched ownership, irrelevant text or new numeric assertions are rejected. Schema-invalid responses use the existing bounded retries.

Exact source passages classified as findings enter the compatible `key_findings` contract. Their classification is a model judgment; exact quotation is not independent verification of the underlying scientific assertion. Non-exact claims remain uncertain. Cross-paper comparisons require at least two distinct papers and remain uncertain interpretations, not proven agreement or contradiction. Confidence never determines acceptance.

Explicit candidate gaps require exact source text; inferred candidates require a supporting limitation; speculative ideas are separate and never populate established `gaps`. Explicit/inferred classifications are model judgments. Lexical relevance and number checks are conservative screens, not semantic entailment proofs. This design intentionally does not certify paraphrased claims as facts.

Canonical API responses expose `evidence_analysis`. Reports display provisional comparisons and labeled candidate directions with deterministic citations. Existing frontend design is unchanged. Saved analysis is rechecked for reference ownership and exact-excerpt integrity before rendering/persistence.

## Persistence

Migration 7 adds `research_analysis_revisions` keyed by run and content-derived revision. Each snapshot retains analysis, source metadata and evidence; repeated checkpoints do not duplicate it. Regeneration with different inputs/model/output retains prior revisions. Established exact findings continue to use existing normalized findings/evidence relationships. Candidate gaps remain in versioned analysis records, separate from established scholarly gaps. Existing research history is not removed.

## Verification

The saved healthcare fixture contains five papers and 30 passages. The mocked semantic model selects two actual source passages beginning “The findings suggest” and “The findings also indicate”, which the prior finding regex missed. The test traverses retrieval replay, orchestration, synthesis, SQLite artifact/revision persistence and authenticated API readback. It produces two source-exact findings, zero established gaps, one inferred candidate gap and one uncertain comparison, with zero rejected items. Reported 140 input/100 output tokens are test-double counters, not live API consumption.

Other tests cover invalid references, invented numbers, uncertain paraphrases, opposing passages, insufficient evidence, empty model outputs, provider failure, disabled fallback, idempotency and retention of regenerated analysis. No fresh academic search was performed for the replayed fixture. The live LLM diagnostic still returns NOT_CONFIGURED; live extraction quality, latency and token consumption remain unverified until credentials/model are configured.
