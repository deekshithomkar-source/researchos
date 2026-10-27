"""Opt-in live LLM check against an explicitly selected, locally saved research run."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.llm_config import llm_settings
from app.db.database import SessionLocal
from app.models.research import ResearchRun
from app.schemas.research import ResearchRequest, ResearchResult
from app.services.llm_service import LLMService
from app.agents.llm_agents import analyze_with_llm

async def main():
    parser=argparse.ArgumentParser(description='Sends only bounded saved evidence and its research brief to the configured LLM. Does not change saved research.')
    parser.add_argument('--research-id',required=True)
    args=parser.parse_args()
    if not llm_settings.enabled:
        raise SystemExit('LLM is disabled. Configure backend/.env: LLM_ENABLED, LLM_MODEL and OPENAI_API_KEY.')
    with SessionLocal() as db:
        run=db.query(ResearchRun).filter_by(research_id=args.research_id,status='completed').first()
        if not run or not run.result_json: raise SystemExit('Completed research snapshot not found.')
        result=ResearchResult.model_validate_json(run.result_json)
        request=ResearchRequest(topic=run.topic,objective=run.objective,academic_level=run.academic_level,
            report_type=run.report_type,citation_style=run.citation_style,source_target=run.source_target)
    analysis=await analyze_with_llm(request,result,LLMService(namespace=args.research_id))
    print(json.dumps({'status':analysis.status,'observations':len(analysis.observations),'sections':len(analysis.sections),
        'diagnostics':[d.model_dump() for d in analysis.diagnostics]},indent=2))
    if analysis.status!='completed': raise SystemExit(1)

if __name__=='__main__': asyncio.run(main())
