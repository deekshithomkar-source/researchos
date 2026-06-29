export default function ResearchHistory({ history, loading, onSelect }) {
  return (
    <section className="panel history">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Saved work</span>
          <h2>Recent research</h2>
        </div>
        <span className="step-badge">{history.length}</span>
      </div>

      {loading && <p className="muted">Loading sessions...</p>}
      {!loading && history.length === 0 && <p className="muted">No research sessions yet.</p>}

      <div className="history-list">
        {history.map((item) => (
          <button className="history-item" key={item.id} onClick={() => onSelect(item.id)}>
            <span>
              <strong>{item.topic}</strong>
              <small>{item.academic_level}</small>
            </span>
            <time>{new Date(item.created_at).toLocaleDateString()}</time>
          </button>
        ))}
      </div>
    </section>
  );
}
