import { useEffect, useState } from 'react';
import ResearchBrief from '../components/ResearchBrief.jsx';
import ResearchWorkspace from '../components/ResearchWorkspace.jsx';
import ResearchHistory from '../components/ResearchHistory.jsx';
import { apiRootUrl, checkApiHealth, getHistory, getResearchById, runResearch } from '../services/api.js';

export default function Dashboard() {
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [apiOnline, setApiOnline] = useState(false);
  const [error, setError] = useState('');

  async function loadHistory() {
    setHistoryLoading(true);
    const data = await getHistory();
    setHistory(data);
    setHistoryLoading(false);
  }

  async function handleRunResearch(payload) {
    setLoading(true);
    setError('');
    try {
      const data = await runResearch(payload);
      setResult(data);
      await loadHistory();
      setApiOnline(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Unable to run research. Check the backend connection and try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectHistory(id) {
    setError('');
    try {
      const data = await getResearchById(id);
      setResult(data);
    } catch {
      setError('Unable to load selected research session.');
    }
  }

  useEffect(() => {
    async function boot() {
      try {
        await checkApiHealth();
        setApiOnline(true);
        await loadHistory();
      } catch {
        setApiOnline(false);
        setHistoryLoading(false);
        setError('Backend is not reachable. Start the API server or set VITE_API_URL for deployment.');
      }
    }

    boot();
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <span className="brand-mark">R</span>
          <div>
            <p className="eyebrow">ResearchOS</p>
            <h1>Autonomous Research Agent</h1>
          </div>
        </div>
        <div className="topbar-actions">
          <span className={`status-pill ${apiOnline ? 'online' : 'offline'}`}>
            <span aria-hidden="true" />
            {apiOnline ? 'API online' : 'API offline'}
          </span>
          <a className="docs-link" href={`${apiRootUrl}/docs`} target="_blank" rel="noreferrer">
            API docs
          </a>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="layout">
        <aside className="control-column">
          <ResearchBrief onSubmit={handleRunResearch} loading={loading} />
          <ResearchHistory history={history} loading={historyLoading} onSelect={handleSelectHistory} />
        </aside>
        <ResearchWorkspace result={result} loading={loading} />
      </section>
    </main>
  );
}
