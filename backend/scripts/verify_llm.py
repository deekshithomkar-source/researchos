"""Backend-only live model diagnostic. Run from any working directory.

Exit codes: 0 validated live reply, 1 provider/response failure, 2 disabled/invalid config.
Never prints credentials, prompts, provider bodies or raw validation exceptions.
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ProbeInput(BaseModel):
    task: str = 'Return status ok and value 4 for the arithmetic check 2 + 2.'


class ProbeOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['ok']
    value: Literal[4]


async def probe(service):
    from app.services.llm_service import LLMError
    result = {'provider': service.config.provider, 'model': service.config.model or None,
              'enabled': service.enabled, 'success': False, 'live_request_verified': False}
    if not service.enabled:
        return {**result, 'status': 'NOT_CONFIGURED',
                'message': 'LLM disabled. Set OPENAI_API_KEY, LLM_MODEL and LLM_ENABLED=true in backend/.env or the backend process environment. Deterministic research remains available.'}, 2
    try:
        await service.generate_structured(instruction='Perform the supplied arithmetic check. Return only the requested JSON object.',
            data=ProbeInput(), output_schema=ProbeOutput, agent='configuration_probe')
        result.update(status='SUCCESS', success=True, live_request_verified=True)
        code = 0
    except LLMError as error:
        result.update(status=error.code, message='LLM request failed. Research agents retain their deterministic evidence fallback. Check model access, credentials, network, quota and configured budgets.')
        code = 1
    # Only allowlisted numeric diagnostics; no response body or arbitrary provider text.
    result['usage'] = {
        'input_tokens': sum(d.input_tokens for d in service.diagnostics),
        'output_tokens': sum(d.output_tokens for d in service.diagnostics),
        'attempts': sum(d.attempts for d in service.diagnostics),
        'duration_ms': sum(d.duration_ms for d in service.diagnostics),
    }
    return result, code


def main():
    try:
        # Lazy imports catch configuration validation before it can print secret inputs.
        from app.core.llm_config import llm_settings
        from app.services.llm_service import LLMService
        # Empty namespace disables response cache, so success requires a fresh request.
        report, code = asyncio.run(probe(LLMService(config=llm_settings, namespace='')))
    except ValidationError:
        report, code = {'status': 'INVALID_CONFIGURATION', 'success': False,
            'live_request_verified': False,
            'message': 'Check backend environment values and numeric bounds. Enabling LLM requires OPENAI_API_KEY and LLM_MODEL. No configuration values are printed.'}, 2
    except Exception:
        report, code = {'status': 'DIAGNOSTIC_ERROR', 'success': False,
            'live_request_verified': False, 'message': 'Diagnostic could not finish; no live success established. Check backend dependencies and configuration.'}, 1
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
