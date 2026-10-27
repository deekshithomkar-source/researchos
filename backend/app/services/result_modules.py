"""Pure projection from retained evidence and saved enrichment; no network or DB writes."""
from app.schemas.modules import CanonicalResearchResult
from app.services.report_validation import audit_claims
from app.services.depth_policy import depth_policy
from app.agents.evidence_analysis import IntentAnalyzer, ResearchQuestionGenerator, stable_id
from app.agents.evidence_synthesis import synthesize_sections, render_report

def canonical_result(request, result, enrichment=None, completed=True):
    # Refresh presentation only. Historical snapshots, identities and evidence are untouched.
    result = result.model_copy(deep=True)
    report_claims = audit_claims(result)
    unsupported = {claim.claim_id for claim in report_claims if claim.support == 'unsupported'}
    result.key_findings = [item for item in result.key_findings if item.finding_id not in unsupported]
    result.gaps = [item for item in result.gaps if item.gap_id not in unsupported]
    if completed and result.sources:
        result.intent = IntentAnalyzer().analyze(request)
        result.sub_questions = ResearchQuestionGenerator().generate(result.intent)
        synthesize_sections(request, result)
        result.report = render_report(request.topic, request.report_type, result)
    citations = {c.paper_id: c for c in result.citations}
    papers, sources = [], []
    for p in result.sources:
        papers.append(dict(paper_id=p.id, title=p.title, authors=p.authors, year=p.year, doi=p.doi,
            url=p.url, abstract=p.abstract, author_identifiers=p.author_identifiers,journal=p.venue,provider=p.provider,citation_count=p.citation_count,retrieved_at=p.retrieved_at, evidence_scope="full_text" if p.full_text else "abstract_only" if p.abstract else "metadata_only", relevance_score=p.ranking.total if p.ranking else None, citation=citations.get(p.id)))
        for origin in getattr(p, 'origins', None) or [dict(provider=p.provider, provider_paper_id=p.id, url=p.url)]:
            sources.append(dict(source_id=stable_id(p.id, origin['provider'], origin['provider_paper_id']), paper_id=p.id,
                **origin, metadata_available=[k for k in ('authors','year','doi','abstract') if getattr(p,k,None)]))
    data = dict(evidence_analysis=result.evidence_analysis, overview=dict(summary=result.summary, objective=request.objective, academic_level=request.academic_level,
        analysis_depth=depth_policy(request.academic_level).focus, output_type=request.report_type,
        citation_style=request.citation_style, source_target=request.source_limit, paper_count=len(papers), coverage_notes=result.coverage_notes),
        research_questions=result.sub_questions, papers=papers, sources=sources, scholars=result.scholars,
        research_gaps=[dict(gap_id=g.gap_id, description=g.statement, gap_type=g.category, supporting_paper_ids=g.paper_ids, evidence_ids=g.evidence_ids) for g in result.gaps],
        report=dict(title=request.topic, academic_level=request.academic_level, claims=report_claims, validation_warnings=[c.warning for c in report_claims if c.warning] + ['Incomplete section: ' + name for name in result.missing_sections] + ['Missing citation metadata for ' + c.paper_id + ': ' + ', '.join(c.metadata_missing) for c in result.citations if c.metadata_missing], output_type=request.report_type, citation_style=request.citation_style, sections=result.report_sections, citations=result.citations, markdown=result.report))
    if enrichment:
        resources=enrichment['resources']
        data.update(datasets=[dict(id=d['id'],name=d['title'],provider=d['provider'],description=d['description'],url=d['url'],license=d.get('license'),research_relevance=d['relevance'],checked_at=d['checked_at']) for d in resources['datasets']['items']],
            courses=resources['courses']['items'], skills=[dict(category=k,name=s) for k,skills in enrichment['skills'].items() for s in skills],
            projects=enrichment['projects'], roadmap=enrichment['roadmap'], career_paths=enrichment['career_paths'], next_steps=enrichment['next_steps'],
            internships=[dict(kind='suggested_role',**r) for r in enrichment['suggested_internship_roles']] + [dict(kind='verified_listing',**r) for r in resources['active_internships']['items']],
            module_status={k:v['status'] for k,v in resources.items()})
    else:
        data['module_status']={k:'not_generated' for k in ('datasets','courses','active_internships','skills','projects','career_paths','next_steps')}
    for name in ('research_gaps', 'skills', 'projects', 'internships', 'career_paths', 'next_steps'):
        data['module_status'].setdefault(name, 'available' if data.get(name) else 'no_supported_results' if enrichment or name == 'research_gaps' else 'not_generated')
    return CanonicalResearchResult.model_validate(data)
