import { useEffect, useRef, useState } from 'react';
import ResearchBrief from '../components/ResearchBrief.jsx';
import ResearchWorkspace from '../components/ResearchWorkspace.jsx';
import ResearchHistory from '../components/ResearchHistory.jsx';
import { apiRootUrl, apiErrorMessage, checkApiHealth, getCurrentUser, getHistory, getResearchById, runResearch, signoutUser } from '../services/api.js';

const terminal = (run) => ['completed', 'failed'].includes(run.status);

export default function Dashboard() {
  const pageRef = useRef(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [apiOnline, setApiOnline] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [error, setError] = useState('');
  const [activeId, setActiveId] = useState(null);
  const [runState, setRunState] = useState(null);

  function handleError(error, fallback) {
    if (error.response?.status === 401) {
      window.location.replace('/auth');
      return;
    }
    setError(apiErrorMessage(error, fallback));
  }

  async function loadHistory(options = {}) {
    setHistoryLoading(true);
    try {
      const data = await getHistory(options);
      setHistory(data);
      return data;
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleRunResearch(payload) {
    setLoading(true);
    setError('');
    setResult(null);
    setRunState(null);
    setActiveId(null);
    try {
      const run = await runResearch(payload);
      setRunState(run);
      setActiveId(run.research_id);
      setApiOnline(true);
      loadHistory().catch((error) => handleError(error, 'Research started, but history could not be refreshed.'));
    } catch (error) {
      handleError(error, 'Unable to submit research. Please try again.');
      setLoading(false);
    }
  }

  function handleSelectHistory(id) {
    setError('');
    setResult(null);
    setRunState(null);
    setLoading(true);
    setActiveId(id);
  }

  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal };
    async function boot() {
      try {
        await getCurrentUser(options);
        if (controller.signal.aborted) return;
        setAuthenticated(true);
        const [, records] = await Promise.all([checkApiHealth(options), getHistory(options)]);
        setApiOnline(true);
        if (controller.signal.aborted) return;
        setHistory(records);
        const unfinished = records.find((run) => !terminal(run));
        if (unfinished) {
          setLoading(true);
          setActiveId(unfinished.research_id);
        }
      } catch (error) {
        if (!controller.signal.aborted) handleError(error, 'Backend is not reachable. Please try again.');
      } finally {
        if (!controller.signal.aborted) setHistoryLoading(false);
      }
    }
    boot();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!activeId) return undefined;
    const controller = new AbortController();
    let timer;
    let failures = 0;
    async function poll() {
      try {
        const run = await getResearchById(activeId, { signal: controller.signal });
        if (controller.signal.aborted) return;
        failures = 0;
        setRunState(run);
        setApiOnline(true);
        if (terminal(run)) {
          setLoading(false);
          setResult(run.status === 'completed' || run.sources.length ? run : null);
          if (run.status === 'failed') setError(run.error_message || 'Research failed.');
          setActiveId(null);
          loadHistory().catch((error) => handleError(error, 'Unable to refresh history.'));
          return;
        }
        setLoading(true);
        timer = window.setTimeout(poll, 1000);
      } catch (error) {
        if (controller.signal.aborted) return;
        failures += 1;
        if (error.response?.status === 401 || failures >= 3) {
          setLoading(false);
          setActiveId(null);
          handleError(error, 'Progress connection interrupted. Select this run in history to reconnect.');
        } else {
          timer = window.setTimeout(poll, 1500);
        }
      }
    }
    poll();
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [activeId]);

  async function handleSignout() {
    try {
      await signoutUser();
      window.location.assign('/auth');
    } catch (error) {
      handleError(error, 'Unable to sign out. Please try again.');
    }
  }

  useDashboardScrollMotion(pageRef);

  return (
    <main className="app-shell dashboard-shell" ref={pageRef}>
      <header className="topbar">
        <a className="dashboard-logo" href="/" aria-label="ResearchOS home">
          <img src="/assets/researchos-logo.svg" alt="ResearchOS" />
        </a>
        <div className="topbar-actions">
          <span className={`status-pill ${apiOnline ? 'online' : 'offline'}`}>
            <span aria-hidden="true" />{apiOnline ? 'API online' : 'API offline'}
          </span>
          <a className="docs-link" href={`${apiRootUrl}/docs`} target="_blank" rel="noreferrer">API docs</a>
          {authenticated && <button className="secondary-button" onClick={handleSignout}>Sign out</button>}
        </div>
      </header>
      {error && <div className="error" role="alert">{error}</div>}
      <section className="layout">
        <aside className="control-column">
          <ResearchBrief onSubmit={handleRunResearch} loading={loading || !authenticated} />
          <ResearchHistory history={history} loading={historyLoading} onSelect={handleSelectHistory} />
        </aside>
        <ResearchWorkspace result={result} loading={loading} runState={runState} />
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
