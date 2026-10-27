"""Mock diagnostic requests; never require credentials or network access."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from scripts.verify_llm import probe
from app.core.llm_config import LLMSettings
from app.services.llm_service import LLMService, ProviderReply, LLMError, Capacity


class Provider:
    def __init__(self, reply): self.reply = reply; self.calls = 0
    async def complete(self, **kwargs):
        self.calls += 1
        if isinstance(self.reply, Exception): raise self.reply
        return ProviderReply(self.reply, 15, 8)


class LLMDiagnosticTests(unittest.TestCase):
    def run_probe(self, reply):
        provider = Provider(reply)
        config = LLMSettings(model='fixture-model', max_attempts=1, cache_seconds=0)
        service = LLMService(provider=provider, config=config, capacity=Capacity(1))
        return asyncio.run(probe(service)), provider

    def test_structured_success_reports_usage(self):
        (report, code), provider = self.run_probe('{"status":"ok","value":4}')
        self.assertEqual(code, 0)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(report['model'], 'fixture-model')
        self.assertEqual(report['usage']['input_tokens'], 15)
        self.assertEqual(report['usage']['output_tokens'], 8)

    def test_invalid_output_and_provider_failure_are_not_success(self):
        for response, status in [('not json', 'INVALID_STRUCTURED_OUTPUT'),
                                 ('{"status":"ok","value":5}', 'INVALID_STRUCTURED_OUTPUT'),
                                 (LLMError('RATE_LIMITED'), 'RATE_LIMITED'),
                                 (LLMError('AUTHENTICATION_ERROR'), 'AUTHENTICATION_ERROR'),
                                 (LLMError('TIMEOUT'), 'TIMEOUT')]:
            (report, code), _ = self.run_probe(response)
            self.assertEqual(code, 1)
            self.assertEqual(report['status'], status)
            self.assertFalse(report['live_request_verified'])

    def test_disabled_makes_no_request(self):
        report, code = asyncio.run(probe(LLMService(config=LLMSettings())))
        self.assertEqual(code, 2)
        self.assertEqual(report['status'], 'NOT_CONFIGURED')

    def test_invalid_config_does_not_print_secret(self):
        env = dict(os.environ, LLM_ENABLED='true', OPENAI_API_KEY='secret-fixture-do-not-print',
                   LLM_MODEL='fixture-model', LLM_TIMEOUT_SECONDS='invalid')
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'verify_llm.py'
        result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('INVALID_CONFIGURATION', result.stdout)
        self.assertNotIn('secret-fixture-do-not-print', result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
