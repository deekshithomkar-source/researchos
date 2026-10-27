"""Independent guidance processors; retrieved facts remain separate from recommendations."""
from app.schemas.modules import Course, Dataset, Internship
from pydantic import ValidationError
from app.services.depth_policy import depth_policy


def skills_module(run, papers, policy, text):
    skills = {
        'Foundational': ['Domain vocabulary: ' + run.topic, 'Statistics and probability', 'Critical reading'],
        'Technical': ['Python', 'Data cleaning', 'Visualization'] + (['Machine learning', 'Model evaluation'] if any(x in text for x in ['learning', 'ai ', 'artificial']) else []),
        'Research': ['Literature review', 'Research ethics', 'Experimental design', 'Reproducibility'],
        'Advanced': ['Uncertainty analysis', 'Bias assessment', 'Domain-specific validation'],
    }
    domain_skills = {
        'healthcare': ['Clinical data literacy', 'Patient privacy', 'Clinical validation'],
        'education': ['Learning assessment', 'Survey design', 'Educational data ethics'],
        'cybersecurity': ['Threat modeling', 'Network security', 'Security evaluation'],
        'blockchain': ['Distributed systems', 'Smart contract security'],
        'history': ['Archival research', 'Source criticism', 'Digital text analysis'],
        'solar': ['Energy systems', 'Time-series analysis', 'Performance measurement'],
    }
    for domain, additions in domain_skills.items():
        if domain in text:
            skills['Technical'].extend(additions)
    # Ground recommended reading and specialization in the completed result, not a new search.
    skills['Advanced'].extend('Evaluate methods used in: ' + p['title'] for p in papers[:2])
    skills['Research'] = list(dict.fromkeys([*policy.skills, *skills['Research']]))
    if policy.key == 'undergraduate':
        skills['Advanced'] = ['Optional later study: ' + skill for skill in skills['Advanced']]
    elif policy.key == 'mca':
        skills['Technical'] = list(dict.fromkeys(['Algorithm implementation', 'System architecture', 'Dataset validation', 'Evaluation metrics', *skills['Technical']]))
    else:
        skills['Advanced'] = list(dict.fromkeys([*policy.skills, *skills['Advanced']]))
    return skills


def projects_module(run, policy, skills, paper_ids, gap_ids, datasets, result):
    projects = [dict(id='evidence-map', title='Evidence map: ' + run.topic,
        problem_statement='Compare the retrieved studies, their methods, and evidence coverage against: ' + (run.objective or run.topic),
        technologies=['Python', 'SQLite', 'Reference manager'], difficulty='Beginner',
        expected_outcome='A reproducible literature matrix with citations and explicit unknowns.',
        paper_ids=paper_ids, gap_ids=gap_ids, dataset_ids=[], skills=skills['Research']),
        dict(id='dataset-audit', title='Dataset suitability and baseline study',
        problem_statement='Assess whether the discovered datasets can address the research objective before designing a baseline experiment.',
        technologies=['Python', 'pandas', 'Jupyter'], difficulty='Intermediate',
        expected_outcome='A documented data audit and evaluation protocol; results depend on lawful access and dataset suitability.',
        paper_ids=paper_ids, gap_ids=gap_ids, dataset_ids=datasets, skills=skills['Technical'],
        prerequisite='Select and validate a dataset first.' if not datasets else 'Review dataset license, consent, and representativeness.')]
    projects[1].update(title=policy.task + ': ' + run.topic, difficulty=policy.difficulty,
        problem_statement=policy.question + ' Objective: ' + (run.objective or run.topic),
        expected_outcome=policy.outcome, skills=list(policy.skills) + skills['Technical'])
    if getattr(run, 'report_type', '') == 'literature_review':
        projects[0]['expected_outcome'] = 'A documented search strategy, study-selection ledger and comparative evidence matrix.'
    elif getattr(run, 'report_type', '') == 'project_proposal':
        projects[0]['expected_outcome'] = 'An evidence-to-requirement map and a proposed evaluation plan; feasibility remains to be tested.'
    findings = [f['finding_id'] for f in result.get('key_findings', [])
                if f.get('finding_id') and set(f.get('paper_ids', [])) <= set(paper_ids)]
    projects[0]['difficulty'] = policy.difficulty
    projects[0]['expected_outcome'] += ' Review requirements: ' + '; '.join(policy.evidence_requirements)
    projects[1]['problem_statement'] += ' Method: ' + '; '.join(policy.methodology)
    projects[1]['prerequisite'] += ' Evidence requirements: ' + '; '.join(policy.evidence_requirements)
    for project in projects:
        project.update(topic=run.topic, finding_ids=findings)
    return projects


def roadmap_module(skills, policy):
    roadmap = [dict(stage=stage, skills=skills[group], milestone=milestone) for stage, group, milestone in [
        ('Beginner', 'Foundational', 'Annotate three retrieved papers and define key terms.'),
        ('Intermediate', 'Technical', 'Complete a course and reproduce a small data analysis.'),
        ('Advanced', 'Advanced', 'Document uncertainty, bias, and evaluation limitations.'),
        ('Research specialization', 'Research', 'Design an evidence-linked study with a supervisor.')]]
    roadmap[1]['milestone'] = '; '.join(policy.learning_recommendations)
    roadmap[-1]['milestone'] = policy.outcome
    roadmap[-1]['skills'] = list(policy.skills)
    return roadmap


def internships_module(skills, text):
    title = next((role for domain, role in (
        ('cybersecurity', 'Security research intern'), ('healthcare', 'Clinical data research intern'),
        ('education', 'Learning analytics intern'), ('history', 'Digital humanities intern')) if domain in text), 'Data analysis intern')
    return [dict(title='Research assistant intern', required_skills=skills['Research'], project_ids=['evidence-map']),
            dict(title=title, required_skills=skills['Technical'], project_ids=['dataset-audit'])]


def career_module(run, skills, roles):
    policy = depth_policy(getattr(run, 'academic_level', 'MCA'))
    return [dict(title=run.topic + ' research analyst', topic=run.topic,
                 required_skills=skills['Research'], project_ids=['evidence-map'],
                 internship_roles=[roles[0]['title']], pathway=[policy.career_preparation[0], roles[0]['title'], 'Research analyst', 'Research specialization']),
            dict(title=run.topic + ' applied specialist', topic=run.topic,
                 required_skills=skills['Technical'], project_ids=['dataset-audit'],
                 internship_roles=[roles[1]['title']], pathway=[policy.career_preparation[1], roles[1]['title'], 'Junior domain analyst', 'Domain specialist'])]


def next_steps_module(papers, skills, resources, projects, gap_ids, roles):
    steps = [dict(action='Read: ' + p['title'], kind='paper', target_id=p['id']) for p in papers[:3]]
    steps += [dict(action='Learn: ' + s, kind='skill', target_id=s) for s in skills['Technical'][:2]]
    steps += [dict(action='Complete: ' + c['title'], kind='course', target_id=c['id']) for c in resources['courses']['items']]
    steps += [dict(action='Build: ' + p['title'], kind='project', target_id=p['id']) for p in projects]
    steps += [dict(action='Investigate the supported gap', kind='gap', target_id=g) for g in gap_ids]
    steps += [dict(action='Explore role: ' + r['title'], kind='suggested_role', target_id=r['title']) for r in roles]
    for priority, step in enumerate(steps, 1):
        step.update(priority=priority, reason={
            'paper': 'Establish the evidence base before implementation.',
            'skill': 'Build prerequisites for the proposed projects.',
            'course': 'Study verified learning material supporting the skill plan.',
            'project': 'Apply skills to the research objective.',
            'gap': 'Investigate an explicitly supported limitation.',
            'suggested_role': 'Use the portfolio to explore a role category; this is not a vacancy.'}[step['kind']])
    return steps


def datasets_module(items):
    return _validated(items, Dataset, lambda d: dict(id=d['id'], name=d['title'], provider=d['provider'],
        description=d['description'], url=d['url'], license=d.get('license'),
        research_relevance=d['relevance'], checked_at=d['checked_at']))


def courses_module(items, run):
    policy = depth_policy(getattr(run, 'academic_level', 'MCA'))
    return _validated(items, Course, lambda c: dict(c, level=c['difficulty'],
        reason_for_recommendation='Develop ' + ', '.join(c['skills']) + ' for ' + run.topic +
        '. Suggested study depth: ' + getattr(run, 'academic_level', 'MCA') + '. ' + '; '.join(policy.learning_recommendations)))


def listings_module(items):
    return _validated(items, Internship, lambda item: dict(kind='verified_listing', **item))


def _validated(items, schema, transform):
    accepted = []
    for item in items:
        try:
            normalized = transform(item)
            schema.model_validate(normalized)
            accepted.append({**item, **normalized})
        except (ValidationError, KeyError, TypeError, ValueError):
            continue
    return accepted
