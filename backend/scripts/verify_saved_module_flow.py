"""Replay real saved scholarly evidence across settings without issuing new provider queries."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db.database import SessionLocal
from app.models.research import ResearchRun
from app.schemas.research import ResearchRequest, ResearchResult
from app.services.result_modules import canonical_result

with SessionLocal() as db:
    run=db.query(ResearchRun).filter(ResearchRun.status=='completed', ResearchRun.result_json.isnot(None)).order_by(ResearchRun.id.desc()).first()
    if not run: raise SystemExit('A completed live research run is required')
    retained=ResearchResult.model_validate_json(run.result_json)
    rows=[]
    for level in ['Undergraduate','MCA',"Master's",'PhD']:
        for output in ['academic_report','literature_review','project_proposal']:
            for style in ['apa','ieee']:
                request=ResearchRequest(topic=run.topic,objective=run.objective,academic_level=level,report_type=output,citation_style=style,source_target=run.source_target)
                view=canonical_result(request,retained)
                assert [p.abstract for p in view.papers]==[p.abstract for p in retained.sources]
                rows.append(dict(level=level, output=output, citation_style=style, depth=view.overview.analysis_depth,
                    paper_count=len(view.papers), sections=[s.name for s in view.report.sections], citation_labels=[c.label for c in view.report.citations]))
    Path('../docs/module-flow-live-replay.json').write_text(json.dumps({'topic':run.topic,'basis':'Retained real provider evidence; settings replay, not 24 new retrievals','checks':rows},indent=2))
    print(f'PASS {len(rows)} real-evidence settings combinations; {len(retained.sources)} retained papers; exact abstracts preserved')
