"""Worker entry point usable from FastAPI, a CLI, or a future queue worker."""
import asyncio
import json
import logging
from typing import Protocol

from app.agents.research_orchestrator import NoEvidenceError, ResearchOrchestrator
from app.db.database import SessionLocal
from app.models.research import ResearchRun
from app.models.user import utcnow
from app.schemas.research import ResearchRequest
from app.services.research_runs import ACTIVE_STATUSES
from app.services.research_artifacts import persist_artifacts

logger = logging.getLogger('researchos.worker')


class ResearchExecutor(Protocol):
    def enqueue(self, research_id: str) -> None: ...


def execute_research(research_id: str, session_factory=None, orchestrator_factory=None):
    session_factory = session_factory or SessionLocal
    orchestrator_factory = orchestrator_factory or ResearchOrchestrator
    with session_factory() as db:
        claimed = db.query(ResearchRun).filter(ResearchRun.research_id == research_id, ResearchRun.status == 'queued').update(
            {'status': 'planning', 'current_stage': 'starting', 'status_message': 'Starting research', 'updated_at': utcnow()}, synchronize_session=False)
        db.commit()
        if not claimed:
            return
        run = db.query(ResearchRun).filter_by(research_id=research_id).one()
        request = ResearchRequest(topic=run.topic, objective=run.objective, academic_level=run.academic_level,
                                  report_type=run.report_type, citation_style=run.citation_style, source_target=run.source_target)

    def checkpoint(stage, result):
        with session_factory() as db:
            run = db.query(ResearchRun).filter_by(research_id=research_id).one()
            run.status, run.progress = stage.status, stage.progress
            run.current_stage, run.status_message = stage.name, stage.message
            persist_artifacts(db, run, result)
            run.result_json = result.model_dump_json()
            run.partial = result.partial
            run.updated_at = utcnow()
            db.commit()
        logger.info('research_stage', extra={'research_id': research_id, 'stage': stage.name, 'progress': stage.progress})

    try:
        result = asyncio.run(orchestrator_factory().run_async(request, research_id, checkpoint))
        with session_factory() as db:
            run = db.query(ResearchRun).filter_by(research_id=research_id).one()
            persist_artifacts(db, run, result)
            run.result_json = result.model_dump_json()
            run.sub_questions = json.dumps(result.sub_questions)
            run.findings = json.dumps([finding.model_dump() for finding in result.findings])
            run.summary, run.report = result.summary, result.report
            run.partial = result.partial
            run.status, run.progress, run.current_stage = 'completed', 100, 'completed'
            run.status_message = 'Completed with limited evidence' if result.partial else 'Research completed'
            run.completed_at = run.updated_at = utcnow()
            db.commit()
        logger.info('research_completed', extra={'research_id': research_id, 'partial': result.partial})
    except Exception as error:
        # Do not expose provider URLs, request payloads, credentials, or stack details to clients.
        message = str(error) if isinstance(error, NoEvidenceError) else 'Research could not be completed. Any retrieved evidence has been preserved.'
        with session_factory() as db:
            run = db.query(ResearchRun).filter_by(research_id=research_id).one()
            run.status, run.current_stage = 'failed', 'failed'
            run.status_message = run.error_message = message
            run.completed_at = run.updated_at = utcnow()
            snapshot = json.loads(run.result_json or '{}')
            run.partial = bool(snapshot.get('sources'))
            db.commit()
        logger.error('research_failed', extra={'research_id': research_id, 'error_type': type(error).__name__})


def recover_interrupted_runs(session_factory=SessionLocal):
    """Single-process development recovery: interrupted jobs fail visibly, never hang."""
    with session_factory() as db:
        runs = db.query(ResearchRun).filter(ResearchRun.status.in_(ACTIVE_STATUSES)).all()
        for run in runs:
            run.status = run.current_stage = 'failed'
            run.status_message = run.error_message = 'The development worker restarted. Please submit this research again.'
            run.completed_at = run.updated_at = utcnow()
            run.partial = bool(json.loads(run.result_json or '{}').get('sources'))
            logger.warning('research_interrupted', extra={'research_id': run.research_id})
        db.commit()
