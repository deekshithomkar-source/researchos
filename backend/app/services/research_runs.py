"""Research persistence and ownership; no HTTP or provider dependencies."""
import json
from sqlalchemy import text
from app.models.research import ResearchRun
from app.schemas.research import ResearchRequest, ResearchResponse

ACTIVE_STATUSES = ('queued', 'planning', 'searching', 'evaluating', 'validating', 'extracting', 'analyzing', 'synthesizing')


class TooManyRunsError(RuntimeError):
    pass


def create_run(db, user_id: str, request: ResearchRequest, max_active: int) -> ResearchRun:
    # Serialize count + insert across SQLite connections to enforce the admission limit.
    if db.bind.dialect.name == 'sqlite':
        db.execute(text('BEGIN IMMEDIATE'))
    count = db.query(ResearchRun).filter(ResearchRun.user_id == user_id, ResearchRun.status.in_(ACTIVE_STATUSES)).count()
    if count >= max_active:
        db.rollback()
        raise TooManyRunsError('Too many active research runs. Wait for a run to finish.')
    run = ResearchRun(user_id=user_id, topic=request.topic, objective=request.objective,
                      academic_level=request.academic_level, report_type=request.report_type,
                      citation_style=request.citation_style, source_target=request.source_limit,
                      sub_questions='[]', findings='[]', summary='', report='', status='queued',
                      progress=0, current_stage='queued', status_message='Waiting to start')
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def owned_run(db, identifier: str, user_id: str):
    query = db.query(ResearchRun).filter(ResearchRun.user_id == user_id)
    # Retain numeric links from the existing frontend, always scoped to the owner.
    if identifier.isdecimal():
        # SQLite INTEGER keys are signed 64-bit. Bound input before conversion
        # to avoid overflow (and Python's limit on very long integer strings).
        normalized = identifier.lstrip('0') or '0'
        if len(normalized) > 19 or int(normalized) > 9223372036854775807:
            return None
        return query.filter(ResearchRun.id == int(normalized)).first()
    return query.filter(ResearchRun.research_id == identifier).first()


def serialize_run(run: ResearchRun) -> ResearchResponse:
    if run.result_json:
        result = json.loads(run.result_json)
    else:
        # Additive migrations retain the original result columns. Read those
        # columns for pre-snapshot runs without changing their ownership.
        findings = json.loads(run.findings or '[]')
        sources = {}
        for finding in findings:
            for source in finding.get('sources', []):
                sources.setdefault(source['id'], source)
        result = {
            'sub_questions': json.loads(run.sub_questions or '[]'),
            'findings': findings,
            'sources': list(sources.values()),
            'summary': run.summary,
            'report': run.report,
        }
    metadata = {field: getattr(run, field) for field in (
        'id', 'research_id', 'topic', 'academic_level', 'objective', 'report_type', 'citation_style',
        'source_target', 'status', 'progress', 'current_stage', 'status_message', 'created_at',
        'updated_at', 'completed_at', 'error_message', 'partial'
    )}
    response = ResearchResponse(**{**result, **metadata})
    from app.services.result_modules import canonical_result
    request = ResearchRequest(topic=run.topic, academic_level=run.academic_level, objective=run.objective,
        report_type=run.report_type, citation_style=run.citation_style, source_target=run.source_target)
    response.modules = canonical_result(request, response, completed=run.status == 'completed')
    return response
