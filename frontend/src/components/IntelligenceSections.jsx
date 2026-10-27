import { useEffect, useState } from 'react';
import { apiErrorMessage, generateIntelligence, getIntelligence } from '../services/api';
import { sectionData } from '../services/result-mapping';
import { resourceStatus, safeResourceUrl } from '../services/intelligence';

export default function IntelligenceSections({ result, section }) {
  const [state, setState] = useState(/** @type {{loading?: boolean, error?: string, data?: {modules: import('../services/result-contract').CanonicalResearchResult, basis: string, limitations: string[]}}} */ ({}));
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ loading: true });
    async function load() {
      try {
        let data = await getIntelligence(result.research_id, { signal: controller.signal });
        if (data.status === 'not_generated') data = await generateIntelligence(result.research_id, { signal: controller.signal });
        if (!controller.signal.aborted) setState({ data });
      } catch (error) {
        if (!controller.signal.aborted) setState({ error: apiErrorMessage(error, 'Resource discovery could not finish. Retry to check the saved result.') });
      }
    }
    if (result.status === 'completed') load();
    else setState({ error: 'Recommendations become available after research completes.' });
    return () => controller.abort();
  }, [result.research_id, result.status, attempt]);
  // Keep this mounted across tabs so discovery and its response are not repeatedly cancelled.
  if (!section) return null;
  if (state.loading) return <p role="status">Discovering resources and preparing saved guidance…</p>;
  if (state.error) return <div role="alert" className="notice warning">{state.error} <button onClick={() => setAttempt(attempt + 1)}>Retry</button></div>;
  const data = state.data;
  if (!data) return null;
  return <IntelligenceContent data={data} section={section} />;
}

export function IntelligenceContent({ data, section }) {
  const modules = data.modules;
  return <div className="workspace-section intelligence-section" data-result-section={section}>
    <p className="notice">{data.basis}</p>
    {sectionData(modules, section === "internships" ? "internships" : section).length === 0 && <p>No {section.replaceAll("_", " ")} recommendations are available for this run.</p>}
    {['datasets', 'courses'].includes(section) && <Resources value={{ status: modules.module_status[section], items: sectionData(modules, section) }} />}
    {section === 'skills' && <><h3>Suggested skills</h3>{['Foundational', 'Technical', 'Research', 'Advanced'].map(group => <Card key={group} title={group}><List values={sectionData(modules, 'skills').filter(skill => skill.category === group).map(skill => skill.name)} /></Card>)}<h3>Learning roadmap</h3>{sectionData(modules, 'roadmap').map(item => <Card key={item.stage} title={item.stage}><List values={item.skills} /><p>{item.milestone}</p></Card>)}</>}
    {section === 'projects' && sectionData(modules, 'projects').map(item => <Card key={item.id} title={item.title}><p>{item.problem_statement}</p><p>{item.difficulty} · {item.technologies.join(', ')}</p><p>Expected outcome: {item.expected_outcome}</p><p>{item.prerequisite}</p><List values={item.skills} /><p>Linked findings: {item.finding_ids.length}; papers: {item.paper_ids.length}; supported gaps: {item.gap_ids.length}; datasets: {item.dataset_ids.join(', ') || 'None verified yet'}</p></Card>)}
    {section === 'internships' && <><h3>Suggested internship roles — not vacancies</h3>{sectionData(modules, 'internships').filter(item => item.kind === 'suggested_role').map(item => <Card key={item.title} title={item.title}><List values={item.required_skills} /><p>Portfolio projects: {item.project_ids.join(', ')}</p></Card>)}<h3>Verified internship listings</h3><Resources value={{ status: modules.module_status.active_internships, items: sectionData(modules, 'internships').filter(item => item.kind === 'verified_listing') }} /></>}
    {section === 'career_paths' && sectionData(modules, 'career_paths').map(item => <Card key={item.title} title={item.title}><List values={item.required_skills} /><p>Topic: {item.topic}</p><p>Internship roles: {item.internship_roles.join(", ")}</p><p>{item.pathway.join(' -> ')}</p><p>Portfolio projects: {item.project_ids.join(', ')}</p></Card>)}
    {section === 'next_steps' && <ol>{sectionData(modules, 'next_steps').map((item, i) => <li key={i}>{item.action}<p>{item.reason}</p><small>Priority {item.priority} — {item.kind}: {item.target_id}</small></li>)}</ol>}
    <details><summary>Coverage and limitations</summary><List values={data.limitations} /></details>
  </div>;
}
function List({ values }) { return <ul>{values.map(value => <li key={value}>{value}</li>)}</ul>; }
function Card({ title, children }) { return <article className="source-card"><h4>{title}</h4>{children}</article>; }
function Resources({ value }) {
  return <><p role="status">{resourceStatus(value.status)}</p>{value.items.map(item => <Card key={item.id || item.url} title={item.title || item.name}>
    <p>{item.provider}{item.company ? ` · ${item.company}` : ''}</p><p>{item.description || item.availability_note}</p>
    {item.research_relevance && <p>{item.research_relevance}</p>}
    {item.license !== undefined && <p>License: {Array.isArray(item.license) ? item.license.join(', ') : (typeof item.license === 'string' ? item.license : 'Not reported; review the dataset card')}</p>}
    {item.difficulty && <p>Suggested difficulty: {item.difficulty} · Duration: {item.duration || 'Not reported'}</p>}
    {item.skills && <List values={item.skills} />}{item.classification_basis && <p>{item.classification_basis}</p>}
    {item.reason_for_recommendation && <p>{item.reason_for_recommendation}</p>}
    {item.location && <p>Location eligibility: {item.location}</p>}
    <p>Verified at {new Date(item.checked_at).toLocaleString()}</p>
    {safeResourceUrl(item.url) && <a href={safeResourceUrl(item.url)} target="_blank" rel="noreferrer">Open verified resource ({item.provider})</a>}
  </Card>)}</>;
}

