"""Backend-only LLM configuration. No credentials are serialized into research results."""
import os
from app.core.config import settings as _application_settings  # Load backend .env first.
from pydantic import BaseModel, Field, SecretStr, model_validator

class LLMSettings(BaseModel):
    enabled: bool = False
    provider: str = 'openai'
    model: str = ''
    api_key: SecretStr = SecretStr('')
    timeout_seconds: float = Field(default=25, ge=0.01, le=120)
    max_attempts: int = Field(default=2, ge=1, le=3)
    concurrency: int = Field(default=2, ge=1, le=8)
    max_input_tokens: int = Field(default=16000, ge=100, le=64000)
    max_output_tokens: int = Field(default=2000, ge=100, le=16000)
    run_token_budget: int = Field(default=72000, ge=100, le=512000)
    cache_seconds: int = Field(default=300, ge=0, le=3600)
    max_retry_delay: float = Field(default=5, ge=0, le=30)

    @model_validator(mode='after')
    def configured(self):
        if self.provider != 'openai':
            raise ValueError('LLM_PROVIDER must be openai; other adapters are not installed')
        if self.enabled and (not self.model.strip() or not self.api_key.get_secret_value().strip()):
            raise ValueError('LLM_ENABLED requires LLM_MODEL and OPENAI_API_KEY on the backend')
        return self

llm_settings = LLMSettings(**{key: os.getenv(env, default) for key,env,default in [
    ('enabled','LLM_ENABLED',False), ('provider','LLM_PROVIDER','openai'), ('model','LLM_MODEL',''),
    ('api_key','OPENAI_API_KEY',''), ('timeout_seconds','LLM_TIMEOUT_SECONDS',25),
    ('max_attempts','LLM_MAX_ATTEMPTS',2), ('concurrency','LLM_CONCURRENCY',2),
    ('max_input_tokens','LLM_MAX_INPUT_TOKENS',16000), ('max_output_tokens','LLM_MAX_OUTPUT_TOKENS',2000),
    ('run_token_budget','LLM_RUN_TOKEN_BUDGET',72000), ('cache_seconds','LLM_CACHE_SECONDS',300),
    ('max_retry_delay','LLM_MAX_RETRY_DELAY_SECONDS',5),
]})
