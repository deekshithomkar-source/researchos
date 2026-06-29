import { useMemo, useState } from 'react';

export default function ResearchWorkspace({ result, loading }) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const sources = useMemo(() => result?.sources || uniqueSources(result?.findings), [result]);

  if (loading && !result) {
    return (
      <section className="workspace loading-state">
        <div className="spinner" />
        <h2>Collecting scholarly evidence</h2>
        <p>Planning questions, retrieving sources, scoring metadata, and drafting the report.</p>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="workspace empty-state">
        <div className="empty-visual">
          <span />
          <span />
          <span />
        </div>
        <h2>Ready for a research run</h2>
        <p>Submit a brief to generate questions, source evidence, quality signals, and a downloadable report.</p>
      </section>
    );
  }

  const demoMode = sources.length > 0 && sources.every((source) => source.is_demo);
  const highQualityCount = sources.filter((source) => source.credibility_score >= 75).length;

  function downloadReport() {
    const blob = new Blob([result.report], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${slugify(result.topic)}-research-report.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function copyReport() {
    await navigator.clipboard.writeText(result.report);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <section className="workspace">
      <div className="workspace-header">
        <div>
          <span className="eyebrow">Session #{result.id}</span>
          <h2>{result.topic}</h2>
          <p className="muted">
            {result.academic_level} | {new Date(result.created_at).toLocaleString()}
          </p>
        </div>
        <div className="result-actions">
          <button className="secondary-button" onClick={copyReport}>
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button className="primary-button compact" onClick={downloadReport}>
            Download MD
          </button>
        </div>
      </div>

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

      <div className="tabs" role="tablist" aria-label="Research result sections">
        {[
          ['overview', 'Overview'],
          ['sources', 'Sources'],
          ['report', 'Report'],
        ].map(([id, label]) => (
          <button
            className={activeTab === id ? 'active' : ''}
            key={id}
            type="button"
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
            {result.sub_questions.map((question, index) => (
              <li key={index}>{question}</li>
            ))}
          </ol>

          <div className="section-heading summary-heading">
            <span className="eyebrow">Synthesis</span>
            <h3>Executive summary</h3>
          </div>
          <p className="summary">{result.summary}</p>
        </div>
      )}

      {activeTab === 'sources' && (
        <div className="workspace-section">
          <div className="source-list">
            {sources.map((source, index) => (
              <article className="source-card" key={source.id || `${source.title}-${index}`}>
                <div className="source-topline">
                  <span className={`quality quality-${qualityClass(source)}`}>
                    {source.credibility_label || 'Unscored'} | {source.credibility_score ?? 0}/100
                  </span>
                  <span>{source.year || 'Year unavailable'}</span>
                </div>
                <h4>{source.title}</h4>
                <p className="source-meta">
                  {(source.authors || []).slice(0, 3).join(', ') || 'Unknown author'}
                  {source.authors?.length > 3 ? ' et al.' : ''} | {source.venue || 'Venue unavailable'}
                </p>
                <p>{source.snippet}</p>
                <div className="source-footer">
                  <span>{source.citation_count || 0} citations</span>
                  {source.url && (
                    <a href={source.url} target="_blank" rel="noreferrer">
                      Open source
                    </a>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'report' && (
        <div className="workspace-section report-card">
          <pre>{result.report}</pre>
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
