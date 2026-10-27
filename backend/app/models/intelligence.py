from sqlalchemy import Column, ForeignKey, Integer, Text, DateTime
from app.db.database import Base
from app.models.user import utcnow

class ResearchIntelligence(Base):
    __tablename__ = 'research_intelligence'
    run_id = Column(Integer, ForeignKey('research_sessions.id'), primary_key=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class ModuleRecord:
    """Run-scoped module snapshot, committed with the compatible aggregate response."""
    run_id = Column(Integer, ForeignKey('research_sessions.id'), primary_key=True)
    payload = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

class GapIntelligence(ModuleRecord, Base):
    __tablename__ = "intelligence_research_gaps"

class DatasetIntelligence(ModuleRecord, Base):
    __tablename__ = "intelligence_datasets"

class SkillIntelligence(ModuleRecord, Base):
    __tablename__ = "intelligence_skills"

class CourseIntelligence(ModuleRecord, Base):
    __tablename__ = "intelligence_courses"

class ProjectIntelligence(ModuleRecord, Base):
    __tablename__ = "intelligence_projects"

class InternshipIntelligence(ModuleRecord, Base):
    __tablename__ = "intelligence_internships"

class CareerIntelligence(ModuleRecord, Base):
    __tablename__ = "intelligence_career_paths"

class NextStepIntelligence(ModuleRecord, Base):
    __tablename__ = "intelligence_next_steps"

MODULE_MODELS = {
    "research_gaps": GapIntelligence,
    "datasets": DatasetIntelligence,
    "skills": SkillIntelligence,
    "courses": CourseIntelligence,
    "projects": ProjectIntelligence,
    "internships": InternshipIntelligence,
    "career_paths": CareerIntelligence,
    "next_steps": NextStepIntelligence,
}

def persist_modules(db, run_id, modules):
    import json
    for name, model in MODULE_MODELS.items():
        if db.get(model, run_id) is not None:
            continue
        items = modules.get(name, [])
        db.add(model(run_id=run_id, payload=json.dumps(items),
                     status=modules.get('module_status', {}).get(name, 'available' if items else 'no_supported_results')))
