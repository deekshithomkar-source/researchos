# LLM integration

## Inspection and implementation

The previous `provider_services.LLMService` accepted an injected legacy `generate()` provider but had no production provider configured. Research used deterministic extraction. Its import location and injected compatibility method are preserved; the reusable implementation now lives in `app/services/llm_service.py`.

The new OpenAI Responses API adapter implements `LLMProvider.complete()`. `LLMService.generate_structured()` supplies a strict JSON schema and validates returned JSON with Pydantic and an optional semantic validator. `generate_text()` is available for non-evidentiary text tasks; research findings never use unvalidated free text.

Provider implementation follows the official [structured output documentation](https://developers.openai.com/api/docs/guides/structured-outputs). Requests use `text.format`, a separate instruction channel, no tools, disabled automatic truncation and `store=false`. Authentication remains server-side. No frontend credential fields or new UI options were introduced.

## Backend configuration

Copy the LLM entries from `backend/.env.example` into your existing backend environment without replacing its database/auth configuration:

```dotenv
LLM_ENABLED=true
LLM_PROVIDER=openai
LLM_MODEL=<a Responses structured-output model available to your account>
OPENAI_API_KEY=<server-only credential>
LLM_TIMEOUT_SECONDS=25
LLM_MAX_ATTEMPTS=2
LLM_CONCURRENCY=2
LLM_MAX_INPUT_TOKENS=16000
LLM_MAX_OUTPUT_TOKENS=2000
LLM_RUN_TOKEN_BUDGET=72000
LLM_CACHE_SECONDS=300
LLM_MAX_RETRY_DELAY_SECONDS=5
```

Restart the backend after configuration. Disabled is the default. Enabled configuration without a model/key fails startup explicitly; no credentials are sent to React. The adapter currently supports OpenAI only; additional implementations can satisfy the same provider protocol. Install backend requirements, which now explicitly include `httpx`.

## Agents and grounding

- `EvidenceReviewAgent`: `ResearchAgentInput -> EvidenceReview`. Selects relevant exact passages under the academic/output policies. Every observation contains an evidence ID, exact quote and existing evidence category.
- `EvidenceSynthesisAgent`: `SynthesisInput -> SynthesisPlan`. Organizes reviewed IDs into overview, findings, methods, limitations or supported future directions. Unsupported categories, duplicate sections and unknown IDs are rejected.
- `ResearchAgentInput` includes topic, objective, academic level/policy, output type/policy, citation style, source target and bounded evidence. It contains no account data or previous research history.

Academic policies cover Undergraduate foundations, MCA implementation/evaluation, Master's comparative methodology, and PhD validity/limitations/novelty scrutiny. Output policies cover the three existing UI options: academic report, literature review and project proposal. No unsupported Comparative Analysis UI option was added.

Retrieved text and user brief fields are explicitly untrusted data. Models have no tools. Schemas have no fields for new papers, authors, DOIs, URLs, datasets or job listings. Quotes must exactly equal retained evidence and keep their original category. The synthesis agent can only reference reviewed IDs; future directions require an explicit future-opportunity passage. Existing metadata and citation generation remain authoritative.

This is deliberately an extractive LLM integration: the model selects and organizes actual evidence, but cannot publish unconstrained factual paraphrases. This makes factual grounding mechanically checkable. It does not claim independent scientific validation, comprehensive conflict adjudication or proven research novelty.

## Pipeline, persistence and failures

The orchestrator invokes the agents after evidence extraction/analysis and before report rendering. Results are stored in `ResearchResult.llm_analysis` inside the existing research JSON, with evidence IDs, selection status and diagnostics. Existing report-section persistence stores the selected excerpts. Reopening a run validates and renders the stored selections; it does not call the LLM. LLM selections replace corresponding report sections instead of appending duplicate findings sections.

LLM-disabled runs retain deterministic behavior with an explicit coverage note. No abstract evidence means no model call. Provider/schema/grounding failures leave existing verified research intact and mark LLM analysis failed or partial with a sanitized code. A successful review followed by failed synthesis retains reviewed observations but does not invent synthesis sections.

Codes include NOT_CONFIGURED, MISSING_EVIDENCE, INPUT_TOKEN_LIMIT, RUN_TOKEN_BUDGET, TOKEN_LIMIT, TIMEOUT, RATE_LIMITED, AUTHENTICATION_ERROR, MODEL_ERROR, MODEL_INCOMPLETE, REFUSAL, INVALID_PROVIDER_RESPONSE, INVALID_STRUCTURED_OUTPUT and UNSUPPORTED_EVIDENCE.

## Cost, concurrency and privacy

Each attempt reserves a conservative UTF-8-byte upper bound for input tokens (including schema and overhead), plus configured maximum output tokens, against the run budget. Reservations are not refunded after failed/ambiguous attempts. This is deliberately conservative, not an exact tokenizer or currency estimate. Actual provider usage is recorded where returned. Excerpts are round-robin selected across papers, with level-specific passage limits and an omitted-evidence count.

Concurrency is process-wide and thread-safe across the worker's separate asyncio loops. Requests and admission waits have bounded timeouts. Transient transport, timeout, schema and grounding failures get bounded retries. Refusals, invalid credentials, model configuration errors and truncated outputs are not blindly retried. Retry-After is never shortened; long cooldowns are surfaced, and a shared process-local cooldown suppresses new requests.

Only successful, validated results are cached, for at most 300 seconds by default and 128 entries per process. Cache keys include the research-run namespace, model, instructions, schema and evidence payload. Empty namespaces disable caching. No cross-run response sharing occurs. Logs contain fixed event/agent names, model, attempt count, token counts, durations, cache flags and sanitized error codes; they do not contain prompts, evidence text, credentials or raw provider error bodies.

## Verification

Automated calls use `httpx.MockTransport` or injected fake providers. They cover wire-format requests, strict schema validation, invalid/missing fields, failure/retry limits, rate-limit cooldowns, refusals, token truncation, concurrency, cancellation, budgets, cache isolation, logging redaction, altered evidence, MCA/PhD policies, output types, missing evidence, partial results and worker -> SQLite -> authenticated API -> canonical report persistence.

Verified locally: **72 backend tests passed**, including 18 LLM-specific tests. Frontend production build and result-component type checks passed. `pip check` found no broken requirements. No live authenticated model call was performed because no API credential is configured.

Run from backend: `../.tmp/local-venv/Scripts/python.exe -m unittest discover -s tests`.
Run from frontend: `npm.cmd run build` and `npm.cmd run typecheck`.
An optional paid live verification is available after configuration: `python scripts/verify_live_llm.py --research-id <completed-run-uuid>` from backend. It sends the selected run's brief and bounded evidence, prints only status/counts/usage, and does not mutate saved research.

## Limitations

No API key is configured in this workspace, so live authenticated model behavior, account access and billing have not been verified. The default remains disabled. Tests validate integration behavior with mocked calls, not model reasoning quality. Model-specific structured-output support must match the configured model. Concurrency, cooldown and response cache are per process; multi-process deployment needs shared quotas. Default provider-side data policies still apply even with `store=false`. Extractive grounding prevents invented factual prose but cannot establish that a paper's original claims are true or that a model's selection is unbiased.
