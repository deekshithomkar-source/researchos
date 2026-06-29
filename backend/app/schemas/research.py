from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=255)
    academic_level: str = Field(default="MCA", min_length=2, max_length=100)
    objective: str | None = Field(default=None, max_length=1000)
    report_type: Literal[
        "academic_report",
        "literature_review",
        "project_proposal",
    ] = "academic_report"
    citation_style: Literal["apa", "ieee"] = "apa"
    source_limit: int = Field(default=10, ge=5, le=20)

    @field_validator("topic", "academic_level")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("objective")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        cleaned = value.strip() if value else None
        return cleaned or None


class ResearchResponse(BaseModel):
    id: int
    topic: str
    academic_level: str
    objective: str | None
    sub_questions: list[str]
    findings: list[dict]
    sources: list[dict]
    summary: str
    report: str
    provider_warning: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchHistoryItem(BaseModel):
    id: int
    topic: str
    academic_level: str
    created_at: datetime

    model_config = {"from_attributes": True}
