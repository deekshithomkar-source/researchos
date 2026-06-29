from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.agents.research_orchestrator import ResearchOrchestrator
from app.core.serializer import from_json_text, to_json_text
from app.db.database import get_db
from app.models.research import ResearchSession
from app.schemas.research import ResearchHistoryItem, ResearchRequest, ResearchResponse

router = APIRouter()


@router.post("/run", response_model=ResearchResponse)
def run_research(payload: ResearchRequest, db: Session = Depends(get_db)):
    orchestrator = ResearchOrchestrator()
    result = orchestrator.run(
        topic=payload.topic,
        academic_level=payload.academic_level,
        objective=payload.objective,
        report_type=payload.report_type,
        citation_style=payload.citation_style,
        source_limit=payload.source_limit,
    )

    session = ResearchSession(
        topic=payload.topic,
        academic_level=payload.academic_level,
        objective=payload.objective,
        sub_questions=to_json_text(result["sub_questions"]),
        findings=to_json_text(result["findings"]),
        summary=result["summary"],
        report=result["report"],
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return ResearchResponse(
        id=session.id,
        topic=session.topic,
        academic_level=session.academic_level,
        objective=session.objective,
        sub_questions=from_json_text(session.sub_questions),
        findings=from_json_text(session.findings),
        sources=result["sources"],
        summary=session.summary,
        report=session.report,
        provider_warning=result["provider_warning"],
        created_at=session.created_at,
    )


@router.get("/history", response_model=list[ResearchHistoryItem])
def get_history(db: Session = Depends(get_db)):
    return db.query(ResearchSession).order_by(ResearchSession.created_at.desc()).all()


@router.get("/{session_id}", response_model=ResearchResponse)
def get_research_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")

    return ResearchResponse(
        id=session.id,
        topic=session.topic,
        academic_level=session.academic_level,
        objective=session.objective,
        sub_questions=from_json_text(session.sub_questions),
        findings=from_json_text(session.findings),
        sources=_unique_sources(from_json_text(session.findings)),
        summary=session.summary,
        report=session.report,
        provider_warning=_stored_warning(from_json_text(session.findings)),
        created_at=session.created_at,
    )


def _unique_sources(findings: list[dict]) -> list[dict]:
    unique = {}
    for finding in findings:
        for source in finding.get("sources", []):
            key = source.get("id") or source.get("url") or source.get("title")
            if key and key not in unique:
                unique[key] = source
    return list(unique.values())


def _stored_warning(findings: list[dict]) -> str | None:
    sources = _unique_sources(findings)
    if sources and all(source.get("is_demo") for source in sources):
        return "This saved session contains demo evidence, not citable scholarly sources."
    return None
