import { useState } from 'react';

const reportTypes = [
  { value: 'academic_report', label: 'Academic report' },
  { value: 'literature_review', label: 'Literature review' },
  { value: 'project_proposal', label: 'Project proposal' },
];

const sourceTargets = [5, 10, 15, 20];

export default function ResearchBrief({ onSubmit, loading }) {
  const [topic, setTopic] = useState('');
  const [academicLevel, setAcademicLevel] = useState('MCA');
  const [objective, setObjective] = useState('');
  const [reportType, setReportType] = useState('academic_report');
  const [citationStyle, setCitationStyle] = useState('apa');
  const [sourceLimit, setSourceLimit] = useState(10);

  function handleSubmit(event) {
    event.preventDefault();
    if (!topic.trim()) return;

    onSubmit({
      topic: topic.trim(),
      academic_level: academicLevel,
      objective: objective.trim() || null,
      report_type: reportType,
      citation_style: citationStyle,
      source_limit: sourceLimit,
    });
  }

  return (
    <form className="panel form" onSubmit={handleSubmit}>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">New run</span>
          <h2>Research brief</h2>
        </div>
        <span className="step-badge">01</span>
      </div>

      <label htmlFor="topic">Research topic</label>
      <input
        id="topic"
        value={topic}
        onChange={(event) => setTopic(event.target.value)}
        placeholder="AI adoption in Indian higher education"
        minLength={3}
        maxLength={255}
        required
      />

      <label htmlFor="objective">Objective</label>
      <textarea
        id="objective"
        value={objective}
        onChange={(event) => setObjective(event.target.value)}
        placeholder="Optional research gap, decision, or problem statement"
        maxLength={1000}
      />

      <div className="form-grid">
        <div>
          <label htmlFor="academic-level">Academic level</label>
          <select
            id="academic-level"
            value={academicLevel}
            onChange={(event) => setAcademicLevel(event.target.value)}
          >
            <option value="MCA">MCA</option>
            <option value="BCA">BCA</option>
            <option value="Engineering">Engineering</option>
            <option value="Research Scholar">Research Scholar</option>
          </select>
        </div>

        <div>
          <label htmlFor="report-type">Output</label>
          <select
            id="report-type"
            value={reportType}
            onChange={(event) => setReportType(event.target.value)}
          >
            {reportTypes.map((type) => (
              <option value={type.value} key={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="segmented" aria-label="Citation style">
        {['apa', 'ieee'].map((style) => (
          <button
            className={citationStyle === style ? 'active' : ''}
            key={style}
            type="button"
            onClick={() => setCitationStyle(style)}
          >
            {style.toUpperCase()}
          </button>
        ))}
      </div>

      <label htmlFor="source-limit">Source target</label>
      <div className="source-options" id="source-limit">
        {sourceTargets.map((target) => (
          <button
            className={sourceLimit === target ? 'active' : ''}
            key={target}
            type="button"
            onClick={() => setSourceLimit(target)}
          >
            {target}
          </button>
        ))}
      </div>

      <button className="primary-button" disabled={loading}>
        {loading ? 'Running research...' : 'Run research'}
      </button>
    </form>
  );
}
