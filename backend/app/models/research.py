import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.user import utcnow


class ResearchRun(Base):
    __tablename__ = "research_sessions"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(255), nullable=False)
    academic_level = Column(String(100), nullable=False)
    objective = Column(Text, nullable=True)
    sub_questions = Column(Text, nullable=False)
    findings = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    report = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    research_id = Column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    report_type = Column(String(32), nullable=False, default="academic_report")
    citation_style = Column(String(10), nullable=False, default="apa")
    source_target = Column(Integer, nullable=False, default=10)
    status = Column(String(24), nullable=False, default="queued")
    progress = Column(Integer, nullable=False, default=0)
    current_stage = Column(String(64), nullable=False, default="queued")
    status_message = Column(Text, nullable=False, default="Waiting to start")
    updated_at = Column(DateTime, default=utcnow, server_default=func.now(), onupdate=utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    partial = Column(Boolean, nullable=False, default=False)


# Preserve existing imports and the existing table/primary keys.
ResearchSession = ResearchRun
