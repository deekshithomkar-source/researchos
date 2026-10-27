"""Atomic snapshot + normalized artifact persistence in the worker transaction."""
import json
from sqlalchemy import delete
from app.models.analysis import (ResearchPaper, ResearchSource, ResearchEvidence,
    ResearchFinding, ResearchGap, ResearchReport, finding_evidence, gap_evidence)
from app.models.scholarly import ResearchAuthor, paper_authors
from app.models.analysis import ResearchAnalysisRevision
from app.services.scholar_discovery import discover_scholars
from app.agents.evidence_analysis import stable_id, validate_traceability


def persist_artifacts(db, run, result):
    validate_traceability(result)
    analysis = result.evidence_analysis
    if analysis and analysis.revision and db.get(ResearchAnalysisRevision, (run.id, analysis.revision)) is None:
        db.add(ResearchAnalysisRevision(run_id=run.id, revision=analysis.revision,
            schema_version=analysis.schema_version, payload=json.dumps(dict(analysis=analysis.model_dump(),
                sources=[p.model_dump(mode="json") for p in result.sources], evidence=[e.model_dump(mode="json") for e in result.evidence]))))
    # Replace only this run's analysis rows, in FK order, within the caller's
    # transaction. Repeated stage checkpoints are idempotent and never commit here.
    for table in (paper_authors, finding_evidence, gap_evidence):
        db.execute(delete(table).where(table.c.run_id == run.id))
    for model in (ResearchAuthor, ResearchReport, ResearchFinding, ResearchGap, ResearchEvidence, ResearchSource, ResearchPaper):
        db.execute(delete(model).where(model.run_id == run.id))
    for paper in result.sources:
        db.add(ResearchPaper(run_id=run.id, paper_id=paper.id, title=paper.title, doi=paper.doi,
                            metadata_json=paper.model_dump_json()))
    db.flush()
    for author in discover_scholars(result.sources):
        db.add(ResearchAuthor(run_id=run.id,author_id=author.author_id,name=author.name,metadata_json=author.model_dump_json()))
    db.flush()
    for author in discover_scholars(result.sources):
        for paper_id in author.related_paper_ids:
            db.execute(paper_authors.insert().values(run_id=run.id,author_id=author.author_id,paper_id=paper_id))
    for paper in result.sources:
        origins = getattr(paper, 'origins', None) or [{'provider': paper.provider, 'provider_paper_id': paper.id, 'url': paper.url}]
        seen = set()
        for origin in origins:
            source_id = stable_id(paper.id, origin['provider'], origin['provider_paper_id'])
            if source_id in seen:
                continue
            seen.add(source_id)
            db.add(ResearchSource(run_id=run.id, source_id=source_id, paper_id=paper.id, **origin))
    for item in result.evidence:
        db.add(ResearchEvidence(run_id=run.id, **item.model_dump()))
    for finding in result.key_findings:
        db.add(ResearchFinding(run_id=run.id, finding_id=finding.finding_id, statement=finding.statement, basis=finding.basis))
    for gap in result.gaps:
        db.add(ResearchGap(run_id=run.id, gap_id=gap.gap_id, statement=gap.statement, category=gap.category, scope=gap.scope))
    db.flush()
    for finding in result.key_findings:
        for eid in finding.evidence_ids:
            db.execute(finding_evidence.insert().values(run_id=run.id, finding_id=finding.finding_id, evidence_id=eid))
    for gap in result.gaps:
        for eid in gap.evidence_ids:
            db.execute(gap_evidence.insert().values(run_id=run.id, gap_id=gap.gap_id, evidence_id=eid))
    if result.report:
        db.add(ResearchReport(run_id=run.id, content=result.report,
                             sections_json=json.dumps([s.model_dump() for s in result.report_sections]),
                             citations_json=json.dumps([c.model_dump() for c in result.citations])))
