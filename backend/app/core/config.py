"""Server-only configuration; loaded before database/provider initialization."""
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")


class Settings(BaseModel):
    environment: str = "development"
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    session_hours: int = Field(default=12, ge=1, le=168)
    fulltext_enabled: bool = False
    provider_timeout: float = Field(default=10, ge=1, le=60)
    provider_attempts: int = Field(default=2, ge=1, le=3)
    search_budget_seconds: float = Field(default=90, ge=5, le=300)
    provider_concurrency: int = Field(default=3, ge=1, le=6)
    auth_attempts: int = Field(default=20, ge=1, le=100)
    auth_window_seconds: int = Field(default=300, ge=30)
    max_active_runs: int = Field(default=3, ge=1, le=20)

    @model_validator(mode="after")
    def validate_security(self):
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("SESSION_COOKIE_SAMESITE must be lax, strict, or none")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("SameSite=None requires secure cookies")
        if "*" in self.allowed_origins:
            raise ValueError("Credentialed origins must be explicit")
        if self.environment == "production" and (
            not self.cookie_secure or any(not value.startswith("https://") for value in self.allowed_origins)
        ):
            raise ValueError("Production requires secure cookies and HTTPS origins")
        return self


settings = Settings(
    fulltext_enabled=os.getenv("RESEARCH_FULLTEXT_ENABLED", "false").lower() == "true",
    environment=os.getenv("APP_ENV", "development"),
    allowed_origins=[x.strip().rstrip("/") for x in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if x.strip()],
    cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
    cookie_samesite=os.getenv("SESSION_COOKIE_SAMESITE", "lax"),
    session_hours=os.getenv("SESSION_HOURS", "12"),
    provider_timeout=os.getenv("PROVIDER_TIMEOUT_SECONDS", "10"),
    provider_attempts=os.getenv("PROVIDER_MAX_ATTEMPTS", "2"),
    search_budget_seconds=os.getenv("SEARCH_BUDGET_SECONDS", "90"),
    provider_concurrency=os.getenv("PROVIDER_CONCURRENCY", "3"),
    auth_attempts=os.getenv("AUTH_MAX_ATTEMPTS", "20"),
    auth_window_seconds=os.getenv("AUTH_WINDOW_SECONDS", "300"),
    max_active_runs=os.getenv("MAX_ACTIVE_RUNS_PER_USER", "3"),
)
