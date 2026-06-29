import { useState } from 'react';

export default function ResearchForm({ onSubmit, loading }) {
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
    <form className="card form" onSubmit={handleSubmit}>
      <div className="card-heading">
        <div>
          <span className="eyebrow">New research</span>
          <h2>Define the outcome</h2>
        </div>
      </div>

      <label htmlFor="topic">Research topic</label>
      <input
        id="topic"
        value={topic}
        onChange={(event) => setTopic(event.target.value)}
        placeholder="e.g. AI adoption in Indian higher education"
        minLength={3}
        maxLength={255}
        required
      />

      <label htmlFor="objective">Research objective</label>
      <textarea
        id="objective"
        value={objective}
        onChange={(event) => setObjective(event.target.value)}
        placeholder="Optional: What decision, problem, or research gap should this report address?"
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
          <label htmlFor="report-type">Output type</label>
          <select
            id="report-type"
            value={reportType}
            onChange={(event) => setReportType(event.target.value)}
          >
            <option value="academic_report">Academic report</option>
            <option value="literature_review">Literature review</option>
            <option value="project_proposal">Project proposal</option>
          </select>
        </div>

        <div>
          <label htmlFor="citation-style">Citation style</label>
          <select
            id="citation-style"
            value={citationStyle}
            onChange={(event) => setCitationStyle(event.target.value)}
          >
            <option value="apa">APA</option>
            <option value="ieee">IEEE</option>
          </select>
        </div>

        <div>
          <label htmlFor="source-limit">Source target</label>
          <select
            id="source-limit"
            value={sourceLimit}
            onChange={(event) => setSourceLimit(Number(event.target.value))}
          >
            <option value={5}>5 sources</option>
            <option value={10}>10 sources</option>
            <option value={15}>15 sources</option>
          </select>
        </div>
      </div>

      <button className="primary-button" disabled={loading}>
        {loading ? 'Collecting and verifying sources…' : 'Start research'}
      </button>
      <p className="form-note">
        Reports use source metadata and abstracts. Important claims should still be checked against full papers.
      </p>
    </form>
  );
}
