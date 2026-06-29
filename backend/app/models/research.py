from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from app.db.database import Base


class ResearchSession(Base):
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
