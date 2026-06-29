import { useEffect, useState } from 'react';
import ResearchForm from '../components/ResearchForm.jsx';
import ResearchResult from '../components/ResearchResult.jsx';
import HistoryPanel from '../components/HistoryPanel.jsx';
import { checkApiHealth, getHistory, getResearchById, runResearch } from '../services/api.js';

export default function App() {
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
    <main>
      <header className="hero">
        <div>
          <span className="hero-badge">ResearchOS · MCA project</span>
          <h1>Research that shows its work.</h1>
          <p>
            Plan a topic, retrieve scholarly evidence, inspect source quality,
            and turn it into a structured academic deliverable.
          </p>
        </div>
        <div className="pipeline" aria-label="Research pipeline">
          <span>Plan</span><i>→</i><span>Search</span><i>→</i>
          <span>Verify</span><i>→</i><span>Report</span>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="layout">
        <div>
          <ResearchForm onSubmit={handleRunResearch} loading={loading} />
          <HistoryPanel history={history} onSelect={handleSelectHistory} />
        </div>
        <ResearchResult result={result} />
      </section>
    </main>
  );
}
