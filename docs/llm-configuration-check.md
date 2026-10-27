# Verify the existing OpenAI integration

Configuration loads from `backend/.env` via the existing application config. Process environment variables take precedence. Copy `backend/.env.example` to `backend/.env` locally if needed. The `.env` file is gitignored. No credentials were generated or populated by this task.

Required for activation:

- `LLM_ENABLED=true`
- `LLM_PROVIDER=openai` (default)
- `LLM_MODEL`: an API model accessible to your project with Responses structured-output support
- `OPENAI_API_KEY`: your backend-only API credential

Existing optional controls and defaults:

| Variable | Default |
|---|---:|
| LLM_TIMEOUT_SECONDS | 25 |
| LLM_MAX_ATTEMPTS | 2 |
| LLM_CONCURRENCY | 2 |
| LLM_MAX_INPUT_TOKENS | 16000 |
| LLM_MAX_OUTPUT_TOKENS | 2000 |
| LLM_RUN_TOKEN_BUDGET | 72000 |
| LLM_CACHE_SECONDS | 300 |
| LLM_MAX_RETRY_DELAY_SECONDS | 5 |

From repository root, using the existing Windows virtual environment:

```powershell
.tmp/local-venv/Scripts/python.exe backend/scripts/verify_llm.py
```

The diagnostic initializes the existing `LLMService`, uses the existing OpenAI Responses adapter and validates a tiny arithmetic JSON response with Pydantic. It reports model, result, attempts and token usage when available. It bypasses the response cache through an empty namespace. It neither prints model response bodies nor raw configuration errors, and does not read/write research history.

Exit codes: 0 = fresh validated response; 1 = request/response/diagnostic failure; 2 = disabled or invalid configuration. Configured retry and token limits apply. A successful mocked test is not live access verification.

The orchestrator initializes the same service in `run_async`, invokes `analyze_with_llm` after evidence extraction, and keeps deterministic results when disabled or when provider calls fail. No research agents were modified. Configuration is loaded at import time, so restart the backend after changing environment values. Invalid enabled configuration fails startup validation; the deterministic runtime fallback covers disabled LLM and provider-call failures, not malformed startup settings.

Observed diagnostic for this task: NOT_CONFIGURED, enabled=false, model=null, live_request_verified=false. No backend `.env`, API key or model was available in the inspected environment. Model access and real token usage therefore remain unverified.

Official protocol reference: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
