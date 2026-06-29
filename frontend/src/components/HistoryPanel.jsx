export default function HistoryPanel({ history, onSelect }) {
  return (
    <div className="card history">
      <div className="card-heading">
        <div>
          <span className="eyebrow">Workspace</span>
          <h2>Recent research</h2>
        </div>
        <span className="history-count">{history.length}</span>
      </div>
      {history.length === 0 && <p className="muted">No research sessions yet.</p>}
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
  );
}
