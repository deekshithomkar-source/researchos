from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.background import get_executor
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.research import ResearchRun
from app.models.user import User, utcnow
from app.schemas.research import ResearchHistoryItem, ResearchRequest, ResearchResponse
from app.services.execution import ResearchExecutor
from app.services.research_runs import TooManyRunsError, create_run, owned_run, serialize_run

router = APIRouter()


@router.post('', response_model=ResearchResponse, status_code=202)
@router.post('/run', response_model=ResearchResponse, status_code=202, include_in_schema=False)
def submit_research(payload: ResearchRequest, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db), executor: ResearchExecutor = Depends(get_executor)):
    try:
        run = create_run(db, user.id, payload, settings.max_active_runs)
    except TooManyRunsError as error:
        raise HTTPException(429, str(error)) from error
    response = serialize_run(run)
    try:
        executor.enqueue(run.research_id)
    except Exception as error:
        run.status = run.current_stage = 'failed'
        run.error_message = run.status_message = 'Unable to schedule research. Please try again.'
        run.completed_at = run.updated_at = utcnow()
        db.commit()
        raise HTTPException(503, run.error_message) from error
    return response


@router.get('/history', response_model=list[ResearchHistoryItem])
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db),
            limit: int = Query(default=100, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    return db.query(ResearchRun).filter(ResearchRun.user_id == user.id).order_by(
        ResearchRun.created_at.desc(), ResearchRun.id.desc()).offset(offset).limit(limit).all()


@router.get('/{research_id}', response_model=ResearchResponse)
def get_research(research_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = owned_run(db, research_id, user.id)
    if run is None:
        raise HTTPException(404, 'Research not found.')
    response = serialize_run(run)
    saved = db.get(ResearchIntelligence, run.id)
    if saved and run.status == 'completed':
        response.modules = CanonicalResearchResult.model_validate(intelligence_view(run, json.loads(saved.payload))['modules'])
    return response

# Enrichment is independent of the research engine and cached per owned run.
import json
import threading
from sqlalchemy.exc import IntegrityError
from app.models.intelligence import ResearchIntelligence, persist_modules
from app.services.intelligence import build_intelligence
from app.schemas.modules import CanonicalResearchResult
from pydantic import BaseModel, ConfigDict
from app.services.result_modules import canonical_result

class IntelligenceResponse(BaseModel):
    model_config = ConfigDict(extra='allow')
    version: int
    modules: CanonicalResearchResult

class PendingIntelligence(BaseModel):
    status: str = 'not_generated'

def intelligence_view(run, payload):
    result = serialize_run(run)
    if payload.get('version', 1) < 2 or payload.get('module_revision', 0) < 2:
        payload = build_intelligence(run, result.model_dump(mode='json'), discover=lambda terms: payload['resources'])
    request = ResearchRequest(topic=run.topic, objective=run.objective, academic_level=run.academic_level,
        report_type=run.report_type, citation_style=run.citation_style, source_target=run.source_target)
    return {**payload, 'modules': canonical_result(request, result, payload).model_dump(mode='json')}


_intelligence_slots = threading.BoundedSemaphore(2)

@router.get('/{research_id}/intelligence', response_model=IntelligenceResponse | PendingIntelligence)
def get_intelligence(research_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = owned_run(db, research_id, user.id)
    if run is None:
        raise HTTPException(404, 'Research not found.')
    saved = db.get(ResearchIntelligence, run.id)
    return intelligence_view(run, json.loads(saved.payload)) if saved else {'status': 'not_generated'}

@router.post('/{research_id}/intelligence', response_model=IntelligenceResponse)
def generate_intelligence(research_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = owned_run(db, research_id, user.id)
    if run is None:
        raise HTTPException(404, 'Research not found.')
    saved = db.get(ResearchIntelligence, run.id)
    if saved:
        view = intelligence_view(run, json.loads(saved.payload))
        persist_modules(db, run.id, view['modules'])
        db.commit()
        return view
    if run.status != 'completed':
        raise HTTPException(409, 'Complete the research run first.')
    result = serialize_run(run).model_dump(mode='json')
    if not result.get('sources'):
        raise HTTPException(409, 'Scholarly sources are required for recommendations.')
    if not _intelligence_slots.acquire(blocking=False):
        raise HTTPException(429, 'Resource discovery is busy. Please retry shortly.')
    try:
        payload = intelligence_view(run, build_intelligence(run, result))
        db.add(ResearchIntelligence(run_id=run.id, payload=json.dumps(payload)))
        persist_modules(db, run.id, payload["modules"])
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return intelligence_view(run, json.loads(db.get(ResearchIntelligence, run.id).payload))
        return payload
    finally:
        _intelligence_slots.release()

@router.get('/{research_id}/report/export/{file_format}')
def export_report(research_id: str, file_format: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from fastapi.responses import Response
    from app.services.report_docx import DocxReportRenderer
    from app.services.report_pdf import PdfReportRenderer
    run = owned_run(db, research_id, user.id)
    if run is None:
        raise HTTPException(404, 'Research not found.')
    if file_format not in ('pdf', 'docx'):
        raise HTTPException(422, 'Supported formats are pdf and docx.')
    if run.status != 'completed':
        raise HTTPException(409, 'Complete the research run before exporting.')
    response = serialize_run(run)
    if not response.sources:
        raise HTTPException(409, 'No verified scholarly sources are available for export.')
    report = response.modules.report
    renderer = PdfReportRenderer() if file_format == 'pdf' else DocxReportRenderer()
    return Response(content=renderer.render(report), media_type=renderer.media_type,
        headers={'Content-Disposition': f'attachment; filename="research-report.{file_format}"', 'Cache-Control': 'private, no-store'})
