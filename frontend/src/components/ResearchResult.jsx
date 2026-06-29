import { useState } from 'react';

export default function ResearchResult({ result }) {
  const [copied, setCopied] = useState(false);

  if (!result) {
    return (
      <div className="card empty-state">
        <span className="empty-icon">⌕</span>
        <h2>Your evidence workspace is ready</h2>
        <p>
          Enter a focused topic to generate research questions, inspect source quality,
          and create a referenced report.
        </p>
      </div>
    );
  }

  const sources = result.sources || uniqueSources(result.findings);
  const demoMode = sources.length > 0 && sources.every((source) => source.is_demo);

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
    <div className="result">
      <div className="card result-header">
        <div>
          <span className="eyebrow">Research session #{result.id}</span>
          <h2>{result.topic}</h2>
          <p className="muted">
            {result.academic_level} · {new Date(result.created_at).toLocaleString()}
          </p>
        </div>
        <div className="result-actions">
          <button className="secondary-button" onClick={copyReport}>
            {copied ? 'Copied' : 'Copy report'}
          </button>
          <button className="primary-button compact" onClick={downloadReport}>
            Download .md
          </button>
        </div>
      </div>

      {result.provider_warning && (
        <div className={`notice ${demoMode ? 'warning' : ''}`}>
          <strong>{demoMode ? 'Demo evidence only.' : 'Source notice.'}</strong>{' '}
          {result.provider_warning}
        </div>
      )}

      <div className="metrics">
        <div className="metric">
          <strong>{result.sub_questions.length}</strong>
          <span>Research questions</span>
        </div>
        <div className="metric">
          <strong>{sources.length}</strong>
          <span>Distinct sources</span>
        </div>
        <div className="metric">
          <strong>{sources.filter((source) => source.credibility_score >= 75).length}</strong>
          <span>High-quality signals</span>
        </div>
      </div>

      <div className="card">
        <div className="section-heading">
          <span className="eyebrow">Plan</span>
          <h3>Research questions</h3>
        </div>
        <ol className="question-list">
          {result.sub_questions.map((question, index) => (
            <li key={index}>{question}</li>
          ))}
        </ol>
      </div>

      <div className="card">
        <div className="section-heading">
          <span className="eyebrow">Synthesis</span>
          <h3>Executive summary</h3>
        </div>
        <p className="summary">{result.summary}</p>
      </div>

      <div className="card">
        <div className="section-heading source-heading">
          <div>
            <span className="eyebrow">Evidence</span>
            <h3>Source library</h3>
          </div>
          <span className="source-count">{sources.length} unique</span>
        </div>
        <div className="source-list">
          {sources.map((source, index) => (
            <article className="source-card" key={source.id || `${source.title}-${index}`}>
              <div className="source-topline">
                <span className={`quality quality-${qualityClass(source)}`}>
                  {source.credibility_label || 'Unscored'} · {source.credibility_score ?? 0}/100
                </span>
                <span>{source.year || 'Year unavailable'}</span>
              </div>
              <h4>{source.title}</h4>
              <p className="source-meta">
                {(source.authors || []).slice(0, 3).join(', ') || 'Unknown author'}
                {source.authors?.length > 3 ? ' et al.' : ''} · {source.venue}
              </p>
              <p>{source.snippet}</p>
              <div className="source-footer">
                <span>{source.citation_count || 0} citations</span>
                {source.url && (
                  <a href={source.url} target="_blank" rel="noreferrer">
                    Open source ↗
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="card report-card">
        <div className="section-heading">
          <span className="eyebrow">Deliverable</span>
          <h3>Generated report</h3>
        </div>
        <pre>{result.report}</pre>
      </div>
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
