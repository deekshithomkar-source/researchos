import { LoadingSkeleton } from './ResearchInteractions';
export default function ResearchHistory({ history, loading, onSelect }) {
  return (
    <section className="panel history dashboard-pop" data-dashboard-motion>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Research history</span>
          <h2>Your saved research</h2>
        </div>
        <span className="step-badge">{history.length}</span>
      </div>

      {loading && <div role="status"><p className="muted">Loading sessions...</p><LoadingSkeleton/></div>}
      {!loading && history.length === 0 && <p className="muted">No research sessions yet.</p>}

      <div className="history-list">
        {history.map((item) => (
          <button className="history-item" key={item.id} onClick={() => onSelect(item.research_id || item.id)}>
            <span>
              <strong>{item.topic}</strong>
              <small>{item.academic_level} · {item.status || "completed"}{item.partial ? " · partial" : ""}</small>
            </span>
            <time>{new Date(item.created_at).toLocaleDateString()}</time>
          </button>
        ))}
      </div>
    </section>
  );
}
