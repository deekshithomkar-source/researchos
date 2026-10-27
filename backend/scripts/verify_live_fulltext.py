"""Live licensed-body -> exact evidence -> SQLite verification, isolated from user data."""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.research_provider import CrossrefProvider
from app.services.full_text import FullTextService
from app.services.scholar_discovery import discover_scholars
from app.schemas.research import Source, ResearchResult
from app.agents.evidence_analysis import EvidenceExtractor, validate_traceability
from app.db.migrations import migrate
from app.models.research import ResearchRun
from app.models.analysis import ResearchPaper, ResearchEvidence
from app.services.research_artifacts import persist_artifacts

papers=[Source.model_validate(p) for p in CrossrefProvider().search('Europe PMC a full-text literature database for the life sciences and platform for innovation',1)]
diagnostics=FullTextService(enabled=True,max_papers=1).enrich(papers)
assert papers and papers[0].full_text, [d.model_dump() for d in diagnostics]
result=ResearchResult(sources=papers,scholars=discover_scholars(papers),full_text_diagnostics=diagnostics)
result.evidence=EvidenceExtractor().extract(papers)
validate_traceability(result)
assert result.evidence and all(e.locator=='full_text' for e in result.evidence)
with tempfile.TemporaryDirectory() as folder:
    engine=create_engine('sqlite:///'+str(Path(folder)/'fulltext.db'))
    migrate(engine,Path(folder)/'no-users.json')
    try:
        with sessionmaker(bind=engine)() as db:
            run=ResearchRun(topic='Europe PMC',academic_level='MCA',sub_questions='[]',findings='[]',summary='',report='',status='completed')
            db.add(run);db.flush()
            persist_artifacts(db,run,result);db.commit()
            stored=db.get(ResearchPaper,(run.id,papers[0].id))
            assert json.loads(stored.metadata_json)['full_text']['text']==papers[0].full_text.text
            assert db.query(ResearchEvidence).filter_by(run_id=run.id,locator='full_text').count()==len(result.evidence)
    finally: engine.dispose()
check={'status':'passed','doi':papers[0].doi,'full_text_url':papers[0].full_text.url,'license':papers[0].full_text.license_url,'evidence_passages':len(result.evidence),'characters':len(papers[0].full_text.text),'storage_verified':True}
print(json.dumps(check))
target=Path('../docs/scholarly-live-results.json');report=json.loads(target.read_text(encoding='utf-8'));report['full_text_flow']=check;target.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
