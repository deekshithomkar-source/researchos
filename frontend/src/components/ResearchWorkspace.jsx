import { exportResearchReport } from '../services/api';
import IntelligenceSections from './IntelligenceSections';
import { sectionData } from '../services/result-mapping';
import { intelligenceTabs } from '../services/intelligence';
import { useMemo, useState } from 'react';

export default function ResearchWorkspace({ result, loading, runState }) {
  const [exportError, setExportError] = useState('');
  const [exporting, setExporting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const sources = useMemo(() => result?.sources || uniqueSources(result?.findings), [result]);

  if (loading && !result) {
    return (
      <section className="workspace loading-state dashboard-pop" data-dashboard-motion>
        <div className="spinner" />
        <h2>{runState?.status_message || 'Starting research'}</h2>
        <div role="status" aria-live="polite">
          <p>{runState?.current_stage?.replaceAll('_', ' ') || 'Submitting your brief'} · {runState?.progress || 0}%</p>
          <progress aria-label="Research progress" max={100} value={runState?.progress || 0} />
        </div>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="workspace empty-state dashboard-pop" data-dashboard-motion>
        <div className="empty-visual">
          <span />
          <span />
          <span />
        </div>
        <h2>{runState?.status === 'failed' ? 'Research could not be completed' : 'Ready for a research run'}</h2>
        <p>{runState?.status === 'failed' ? runState.status_message : 'Submit a brief to generate questions, source evidence, quality signals, and a downloadable report.'}</p>
      </section>
    );
  }

  const modules = result.modules;
  const report = modules?.report.markdown || '';
  const demoMode = sources.length > 0 && sources.every((source) => source.is_demo);
  const highQualityCount = sources.filter((source) => source.credibility_score >= 75).length;

  function downloadReport() {
    const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${slugify(result.topic)}-research-report.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function downloadDocument(format) {
    setExporting(true);
    setExportError('');
    try {
      const blob = await exportResearchReport(result.research_id, format);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${slugify(result.topic)}-research-report.${format}`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setExportError('The report could not be exported. Check your session and retry.');
    } finally { setExporting(false); }
  }

  async function copyReport() {
    await navigator.clipboard.writeText(report);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <section className="workspace dashboard-pop" data-dashboard-motion>
      <div className="workspace-header">
        <div>
          <span className="eyebrow">Session #{result.id}</span>
          <h2>{result.topic}</h2>
          <p className="muted">
            {result.academic_level} | {new Date(result.created_at).toLocaleString()}
          </p>
        </div>
        <div className="result-actions">
          <button className="secondary-button" onClick={copyReport} disabled={!report}>
            {copied ? 'Copied' : 'Copy'}
          </button>
          {['pdf', 'docx'].map(format => <button key={format} className="secondary-button" onClick={() => downloadDocument(format)} disabled={!report || exporting}>Download {format.toUpperCase()}</button>)}
          <button className="primary-button compact" onClick={downloadReport} disabled={!report}>
            Download MD
          </button>
        </div>
      </div>

      {exportError && <p role="alert">{exportError}</p>}
      {result.partial && <div className="notice warning">Partial evidence: some sources or processing stages were unavailable. Review the coverage notes.</div>}
      {result.provider_warning && (
        <div className={`notice ${demoMode ? 'warning' : ''}`}>
          <strong>{demoMode ? 'Demo evidence only.' : 'Source notice.'}</strong> {result.provider_warning}
        </div>
      )}

      <div className="metrics">
        <Metric value={result.sub_questions.length} label="Questions" />
        <Metric value={sources.length} label="Sources" />
        <Metric value={highQualityCount} label="Strong signals" />
      </div>

      <div className="tabs landscape-tabs" role="tablist" aria-label="Research result sections">
        {[
          ['overview', 'Overview'],
          ['papers', 'Research Papers'],
          ['sources', 'Sources'],
          ['gaps', 'Research Gaps'],
          ...intelligenceTabs,
          ['report', 'Report'],
        ].map(([id, label]) => (
          <button
            className={activeTab === id ? 'active' : ''}
            key={id}
            type="button"
            role="tab"
            aria-selected={activeTab === id}
            onClick={() => setActiveTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="workspace-section">
          <div className="section-heading">
            <span className="eyebrow">Plan</span>
            <h3>Research questions</h3>
          </div>
          <ol className="question-list">
            {(modules?.research_questions || []).map((question, index) => (
              <li key={index}>{question}</li>
            ))}
          </ol>

          <div className="section-heading summary-heading">
            <span className="eyebrow">Synthesis</span>
            <h3>Executive summary</h3>
          </div>
          <p>{modules?.overview.academic_level}: {modules?.overview.analysis_depth}</p>
          <p className="summary">{modules?.overview.summary || "No overview is available."}</p>
          {result.coverage_notes?.length > 0 && <ul>{result.coverage_notes.map((note) => <li key={note}>{note}</li>)}</ul>}
        </div>
      )}

      {activeTab === 'papers' && <div className="workspace-section" data-result-section="papers">
        <h3>Research papers</h3>
        {sectionData(modules, 'papers').length === 0 && <p>No scholarly paper records are available.</p>}
        {sectionData(modules, 'papers').map(paper => <article className="source-card" key={paper.paper_id}>
          <h4>{paper.title}</h4><p>{paper.authors.join(', ') || 'Authors unavailable'} | {paper.year || 'Year unavailable'}</p>
          <p>{paper.abstract || 'Abstract unavailable; no findings inferred from metadata.'}</p>
          <p>Topic/objective relevance: {paper.relevance_score == null ? 'Not scored' : `${Math.round(paper.relevance_score * 100)}%`}</p>
          {paper.doi && <p>DOI: {paper.doi}</p>}
          {paper.citation && <p className="paper-citation">{paper.citation.style.toUpperCase()}: {paper.citation.reference}</p>}
          {paper.url && <a href={paper.url} target="_blank" rel="noreferrer">Read paper</a>}
        </article>)}
      </div>}
      {activeTab === 'sources' && <div className="workspace-section" data-result-section="sources">
        <h3>Retrieval sources and provenance</h3>
        {sectionData(modules, 'sources').length === 0 && <p>No retrieval provenance was retained.</p>}
        {sectionData(modules, 'sources').map(source => <article className="source-card" key={source.source_id}>
          <h4>{source.provider}</h4><p>Provider record: {source.provider_paper_id}</p><p>Linked paper: {source.paper_id}</p>
          <p>Available metadata: {source.metadata_available.join(', ') || 'Title only'}</p>
          <p>Provenance: retrieved provider metadata</p>
          {source.url && <a href={source.url} target="_blank" rel="noreferrer">Open source record</a>}
        </article>)}
      </div>}

      <IntelligenceSections key={result.research_id} result={result} section={intelligenceTabs.some(([id]) => id === activeTab) ? activeTab : null} />
      {activeTab === 'gaps' && <div className="workspace-section" data-result-section="research_gaps"><h3>Evidence-supported research gaps</h3>{sectionData(modules, 'research_gaps').length ? sectionData(modules, 'research_gaps').map(gap => <article className="source-card" key={gap.gap_id}><h4>{gap.gap_type.replaceAll('_', ' ')}</h4><p>{gap.description}</p><p>Supporting papers: {gap.supporting_paper_ids.join(', ')}</p><p>Confidence basis: author-reported excerpt; not a field-wide novelty assessment.</p><p>Evidence: {gap.evidence_ids.join(', ')}</p></article>) : <p>No explicit supported gaps were identified in the retrieved evidence.</p>}</div>}
      {activeTab === 'report' && (
        <div className="workspace-section report-card">
          <pre>{report || "No report is available for this run."}</pre>
        </div>
      )}
    </section>
  );
}

function Metric({ value, label }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function uniqueSources(findings = []) {
  const sources = new Map();
  findings.forEach((finding) => {
    finding.sources?.forEach((source) => {
      const key = source.id || source.url || source.title;
      if (!sources.has(key)) sources.set(key, source);
    });
  });
  return [...sources.values()];
}

function qualityClass(source) {
  if (source.is_demo) return 'demo';
  if (source.credibility_score >= 75) return 'high';
  if (source.credibility_score >= 55) return 'moderate';
  return 'basic';
}

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

