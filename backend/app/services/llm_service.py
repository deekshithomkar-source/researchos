"""Reusable async LLM service with strict validation and process-wide admission control."""
import asyncio
import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Protocol, TypeVar, Callable
import httpx
from pydantic import BaseModel, ValidationError
from app.core.config import settings
from app.core.llm_config import LLMSettings, llm_settings
from app.schemas.llm import LLMCallDiagnostic

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger('researchos.llm')

class LLMError(RuntimeError):
    def __init__(self, code, retryable=False, retry_after=0, input_tokens=0, output_tokens=0):
        super().__init__(code)  # Never include provider bodies, prompts or credentials.
        self.code, self.retryable, self.retry_after = code, retryable, retry_after
        self.input_tokens, self.output_tokens = input_tokens, output_tokens

@dataclass
class ProviderReply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0

class LLMProvider(Protocol):
    async def complete(self, *, instruction: str, data: str, schema: dict | None, model: str,
                       max_output_tokens: int) -> ProviderReply: ...

def strict_schema(schema):
    schema = json.loads(json.dumps(schema))
    def walk(node):
        if isinstance(node, dict):
            node.pop('default', None)
            if node.get('type') == 'object':
                node['additionalProperties'] = False
                node['required'] = list(node.get('properties', {}))
            for value in node.values(): walk(value)
        elif isinstance(node, list):
            for value in node: walk(value)
    walk(schema)
    return schema

class OpenAIResponsesProvider:
    def __init__(self, config: LLMSettings, transport=None):
        self.config, self.transport = config, transport

    async def complete(self, *, instruction, data, schema, model, max_output_tokens):
        body = dict(model=model, instructions=instruction,
            input=[{'role':'user', 'content':[{'type':'input_text','text':data}]}],
            max_output_tokens=max_output_tokens, store=False, tools=[], truncation='disabled')
        if schema is not None:
            body['text'] = {'format': {'type':'json_schema','name':'research_agent_result','strict':True,'schema':strict_schema(schema)}}
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds, transport=self.transport,
                    follow_redirects=False, trust_env=False) as client:
                async with client.stream('POST','https://api.openai.com/v1/responses',
                        headers={'Authorization':'Bearer '+self.config.api_key.get_secret_value()}, json=body) as response:
                    if response.status_code == 429:
                        header=response.headers.get('retry-after','1')
                        try: delay=max(0,float(header))
                        except ValueError:
                            try: delay=max(0,(parsedate_to_datetime(header)-datetime.now(timezone.utc)).total_seconds())
                            except (ValueError, TypeError): delay=1
                        raise LLMError('RATE_LIMITED',True,delay)
                    if response.status_code in (401,403): raise LLMError('AUTHENTICATION_ERROR')
                    if response.status_code >= 500: raise LLMError('PROVIDER_UNAVAILABLE',True)
                    if response.status_code == 408: raise LLMError('TIMEOUT',True)
                    if response.status_code >= 300: raise LLMError('MODEL_ERROR')
                    chunks=bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks)>2_000_000: raise LLMError('INVALID_PROVIDER_RESPONSE')
                    payload=json.loads(chunks)
            usage=payload.get('usage') or {}
            counts=[usage.get('input_tokens',0),usage.get('output_tokens',0)]
            if any(type(v) is not int or v < 0 for v in counts): raise LLMError('INVALID_PROVIDER_RESPONSE')
            if payload.get('status') == 'incomplete':
                reason=(payload.get('incomplete_details') or {}).get('reason')
                raise LLMError('TOKEN_LIMIT' if reason=='max_output_tokens' else 'MODEL_INCOMPLETE',input_tokens=counts[0],output_tokens=counts[1])
            if payload.get('status') != 'completed': raise LLMError('MODEL_ERROR')
            parts=[]
            for output in payload.get('output',[]):
                for content in output.get('content',[]):
                    if content.get('type')=='refusal': raise LLMError('REFUSAL')
                    if content.get('type')=='output_text': parts.append(content['text'])
            if not parts: raise LLMError('INVALID_PROVIDER_RESPONSE',True)
            usage=payload.get('usage') or {}
            counts=[usage.get('input_tokens',0),usage.get('output_tokens',0)]
            if any(type(v) is not int or v < 0 for v in counts): raise LLMError('INVALID_PROVIDER_RESPONSE')
            return ProviderReply(''.join(parts), *counts)
        except httpx.TimeoutException as error: raise LLMError('TIMEOUT',True) from None
        except httpx.TransportError: raise LLMError('PROVIDER_UNAVAILABLE',True) from None
        except (ValueError,KeyError,TypeError,AttributeError): raise LLMError('INVALID_PROVIDER_RESPONSE',True) from None

class Capacity:
    """Thread-safe because research workers use separate event loops."""
    def __init__(self, maximum):
        self.maximum, self.active, self.lock = maximum, 0, threading.Lock()
        self.cooldown_until = 0.0
    async def acquire(self):
        while True:
            with self.lock:
                remaining = self.cooldown_until - time.monotonic()
                if remaining > 0:
                    raise LLMError('RATE_LIMITED', True, remaining)
                if self.active < self.maximum:
                    self.active += 1
                    return
            await asyncio.sleep(.01)
    def defer(self, seconds):
        with self.lock: self.cooldown_until = max(self.cooldown_until, time.monotonic()+seconds)
    def release(self):
        with self.lock: self.active -= 1

_capacity=Capacity(llm_settings.concurrency)
_cache=OrderedDict()
_cache_lock=threading.Lock()

class LLMService:
    def __init__(self, provider=None, config=None, capacity=None, namespace=''):
        self.config=config or llm_settings
        self.provider=provider if provider is not None else (OpenAIResponsesProvider(self.config) if self.config.enabled else None)
        self.capacity=capacity or _capacity
        # A service belongs to one research run. No cross-user response cache sharing.
        self.namespace=namespace
        self.reserved_tokens=0
        self.diagnostics=[]
        self.budget_lock=threading.Lock()

    @property
    def enabled(self): return self.provider is not None

    async def generate_structured(self, *, instruction: str, data: BaseModel, output_schema: type[T],
                                  agent: str, validate: Callable[[T], None] | None = None) -> T:
        return await self._generate(instruction,data,output_schema,agent,validate)

    async def generate_text(self, *, instruction: str, data: BaseModel, agent: str='text') -> str:
        # Reusable interface only; research findings always use validated structured output.
        return await self._generate(instruction,data,None,agent,None)

    async def _generate(self,instruction,data,output_schema,agent,validate):
        if not self.enabled: raise LLMError('NOT_CONFIGURED')
        schema=output_schema.model_json_schema() if output_schema else None
        serialized=data.model_dump_json()
        # Conservative byte upper bound, including schema and message overhead. Not a model tokenizer.
        estimated=len((instruction+serialized+json.dumps(schema)).encode('utf-8'))+512
        if estimated>self.config.max_input_tokens: raise LLMError('INPUT_TOKEN_LIMIT')
        key=hashlib.sha256(json.dumps([self.namespace,self.config.model,instruction,serialized,schema],sort_keys=True).encode()).hexdigest()
        diagnostic=LLMCallDiagnostic(agent=agent,status='pending',model=self.config.model)
        start=time.monotonic()
        try:
            if self.namespace and self.config.cache_seconds:
                with _cache_lock:
                    item=_cache.get(key)
                    if item and item[0] <= time.monotonic():
                        del _cache[key]; item=None
                if item:
                    parsed=output_schema.model_validate_json(item[1]) if output_schema else item[1]
                    if validate: validate(parsed)
                    diagnostic.cached=True; diagnostic.status='completed'
                    return parsed
            for attempt in range(self.config.max_attempts):
                diagnostic.attempts=attempt+1
                acquired=False
                try:
                    await asyncio.wait_for(self.capacity.acquire(),timeout=self.config.timeout_seconds)
                    acquired=True
                    reserve=estimated+self.config.max_output_tokens
                    with self.budget_lock:
                        if self.reserved_tokens+reserve>self.config.run_token_budget: raise LLMError('RUN_TOKEN_BUDGET')
                        self.reserved_tokens+=reserve
                    diagnostic.reserved_tokens+=reserve
                    reply=await asyncio.wait_for(self.provider.complete(instruction=instruction,data=serialized,schema=schema,
                        model=self.config.model,max_output_tokens=self.config.max_output_tokens),timeout=self.config.timeout_seconds)
                    diagnostic.input_tokens+=reply.input_tokens; diagnostic.output_tokens+=reply.output_tokens
                    if reply.output_tokens>self.config.max_output_tokens: raise LLMError('TOKEN_LIMIT')
                    if not reply.text.strip(): raise LLMError('INVALID_PROVIDER_RESPONSE',True)
                    if len(reply.text.encode('utf-8'))>self.config.max_output_tokens*16: raise LLMError('TOKEN_LIMIT')
                    try: parsed=output_schema.model_validate_json(reply.text) if output_schema else reply.text
                    except ValidationError: raise LLMError('INVALID_STRUCTURED_OUTPUT',True) from None
                    if validate: validate(parsed)
                    if self.namespace and self.config.cache_seconds:
                        with _cache_lock:
                            _cache[key]=(time.monotonic()+self.config.cache_seconds,reply.text)
                            _cache.move_to_end(key)
                            while len(_cache)>128: _cache.popitem(last=False)
                    diagnostic.status='completed'
                    return parsed
                except (asyncio.TimeoutError, LLMError) as error:
                    failure=LLMError('TIMEOUT',True) if isinstance(error,asyncio.TimeoutError) else error
                    diagnostic.status=failure.code
                    diagnostic.input_tokens+=failure.input_tokens
                    diagnostic.output_tokens+=failure.output_tokens
                    if failure.code == 'RATE_LIMITED': self.capacity.defer(failure.retry_after)
                except asyncio.CancelledError:
                    diagnostic.status='CANCELLED'
                    raise
                except Exception:
                    failure=LLMError('MODEL_ERROR')
                    diagnostic.status=failure.code
                finally:
                    if acquired: self.capacity.release()
                # Never shorten a provider's Retry-After. Surface long cooldowns without retrying.
                if not failure.retryable or attempt+1>=self.config.max_attempts or failure.retry_after>self.config.max_retry_delay:
                    raise failure
                await asyncio.sleep(max(failure.retry_after,min(.25*2**attempt,self.config.max_retry_delay)))
        finally:
            diagnostic.duration_ms=round((time.monotonic()-start)*1000)
            self.diagnostics.append(diagnostic)
            logger.info('llm_call',extra={**diagnostic.model_dump(),'error_code':None if diagnostic.status=='completed' else diagnostic.status})

    async def generate(self, *, instruction, evidence):
        """Compatibility for the previously injected legacy provider interface."""
        if self.provider is None: raise NotImplementedError('No LLM provider configured')
        if hasattr(self.provider,'generate'):
            for attempt in range(settings.provider_attempts):
                try:
                    return await asyncio.wait_for(self.provider.generate(instruction=instruction,evidence=evidence),settings.provider_timeout)
                except (TimeoutError,OSError):
                    if attempt+1==settings.provider_attempts: raise
                    await asyncio.sleep(.25*(attempt+1))
        raise LLMError('USE_TYPED_GENERATION')
