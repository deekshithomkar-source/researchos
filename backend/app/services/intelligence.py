"""Evidence-linked guidance, deliberately distinct from retrieved factual listings."""
import re
from app.services.resource_discovery import discover_resources
from app.services.depth_policy import depth_policy
from app.services.intelligence_modules import (skills_module, projects_module, roadmap_module, internships_module, career_module, next_steps_module, datasets_module, courses_module, listings_module)

def build_intelligence(run, result, discover=discover_resources):
    papers = result.get('sources', [])
    if not papers:
        raise ValueError('Completed scholarly sources are required')
    policy = depth_policy(getattr(run, 'academic_level', 'MCA'))
    text = (run.topic + ' ' + (run.objective or '')).lower()
    domains = [word for word in ('healthcare', 'education', 'cybersecurity', 'blockchain', 'machine learning', 'artificial intelligence') if word in text]
    terms = domains or [w for w in re.findall(r'[a-z]{4,}', text) if w not in {'research', 'study', 'using', 'impact'}][:2]
    try:
        discovered = discover(terms or [run.topic])
        if not isinstance(discovered, dict):
            discovered = {}
    except Exception:
        discovered = {}
    resources = {}
    for name, processor in (('datasets', datasets_module), ('courses', lambda items: courses_module(items, run)), ('active_internships', listings_module)):
        resource = discovered.get(name, {'status': 'provider_unavailable', 'items': []})
        try:
            items = processor(resource.get('items', []))
            resources[name] = {**resource, 'items': items}
            if len(items) != len(resource.get('items', [])):
                resources[name]['status'] = 'partial' if items else 'invalid_response'
        except Exception:
            resources[name] = {'status': 'invalid_response', 'items': []}
    for item in resources['active_internships']['items']:
        item.pop('kind', None)
    skills = skills_module(run, papers, policy, text)
    paper_ids = [p.get('id') for p in papers if p.get('id')]
    gap_ids = [g['gap_id'] for g in result.get('gaps', [])]
    datasets = [d['id'] for d in resources['datasets']['items']]
    projects = projects_module(run, policy, skills, paper_ids, gap_ids, datasets, result)
    roles = internships_module(skills, text)
    roadmap = roadmap_module(skills, policy)
    steps = next_steps_module(papers, skills, resources, projects, gap_ids, roles)
    return dict(version=2, module_revision=2, academic_level=getattr(run, 'academic_level', 'MCA'), analysis_depth=policy.focus, basis='Rule-generated guidance based on this completed research run; not established findings or employment promises.',
        research_id=run.research_id, paper_ids=paper_ids, gap_ids=gap_ids, resources=resources,
        skills=skills, roadmap=roadmap, projects=projects, suggested_internship_roles=roles,
        career_paths=career_module(run, skills, roles),
        next_steps=steps, limitations=['Course catalog currently covers programming and machine learning foundations.',
        'Dataset relevance is a search match, not a guarantee of suitability.', 'Internship coverage is limited to the Remotive remote-job feed.',
        'Verification reflects the saved check time. Availability can change.'])

