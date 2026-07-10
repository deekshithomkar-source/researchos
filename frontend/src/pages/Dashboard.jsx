import { useEffect, useRef, useState } from 'react';
import ResearchBrief from '../components/ResearchBrief.jsx';
import ResearchWorkspace from '../components/ResearchWorkspace.jsx';
import ResearchHistory from '../components/ResearchHistory.jsx';
import { apiRootUrl, checkApiHealth, getHistory, getResearchById, runResearch } from '../services/api.js';

export default function Dashboard() {
  const pageRef = useRef(null);
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

  useDashboardScrollMotion(pageRef);

  return (
    <main className="app-shell dashboard-shell" ref={pageRef}>
      <header className="topbar">
        <a className="dashboard-logo" href="/" aria-label="ResearchOS home">
          <img src="/assets/researchos-logo.svg" alt="ResearchOS" />
        </a>
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

function useDashboardScrollMotion(pageRef) {
  useEffect(() => {
    const page = pageRef.current;
    if (!page || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;

    let lastY = window.scrollY;
    let ticking = false;

    function updateMotion() {
      const motionItems = [...page.querySelectorAll('[data-dashboard-motion]')];
      if (!motionItems.length) return;

      const currentY = window.scrollY;
      const direction = currentY > lastY ? 'down' : 'up';
      page.dataset.scrollDirection = direction;
      lastY = currentY;

      const viewportCenter = window.innerHeight / 2;

      motionItems.forEach((item) => {
        const rect = item.getBoundingClientRect();
        const visible = rect.bottom > 0 && rect.top < window.innerHeight;
        const distance = Math.abs(rect.top + rect.height / 2 - viewportCenter);
        const strength = Math.max(0, 1 - distance / window.innerHeight);
        const lift = (direction === 'down' ? -10 : 10) * strength;

        item.classList.toggle('is-dashboard-visible', visible);
        item.style.setProperty('--dashboard-pop-y', `${lift.toFixed(2)}px`);
        item.style.setProperty('--dashboard-pop-scale', (1 + strength * 0.012).toFixed(4));
      });

      ticking = false;
    }

    function requestUpdate() {
      if (!ticking) {
        window.requestAnimationFrame(updateMotion);
        ticking = true;
      }
    }

    updateMotion();
    window.addEventListener('scroll', requestUpdate, { passive: true });
    window.addEventListener('resize', requestUpdate);

    return () => {
      window.removeEventListener('scroll', requestUpdate);
      window.removeEventListener('resize', requestUpdate);
    };
  }, [pageRef]);
}
