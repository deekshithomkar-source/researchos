import { ToastNotification } from '../components/ResearchInteractions';
import { useEffect, useRef, useState } from 'react';
import WorkspaceNavigation from '../components/WorkspaceNavigation.jsx';
import ResearchBrief from '../components/ResearchBrief.jsx';
import ResearchWorkspace from '../components/ResearchWorkspace.jsx';
import ResearchHistory from '../components/ResearchHistory.jsx';
import { apiRootUrl, apiErrorMessage, checkApiHealth, getCurrentUser, getHistory, getResearchById, runResearch, signoutUser } from '../services/api.js';

const terminal = (run) => ['completed', 'failed'].includes(run.status);

export default function Dashboard() {
  const pageRef = useRef(null);
  const [view, setView] = useState('research');
  const [user, setUser] = useState(null);
  const submittedRun = useRef(null);
  const [notification, setNotification] = useState('');
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
      submittedRun.current = run.research_id;
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
        const session = await getCurrentUser(options);
        setUser(session.user || session);
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
          if (submittedRun.current === run.research_id) {
            setNotification(run.status === 'completed' ? 'Research saved. Your results are ready to review.' : 'Research could not finish. Review the error details and retry.');
            submittedRun.current = null;
          }
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

  function showView(nextView, target = 'workspace-main') {
    setView(nextView);
    window.setTimeout(() => {
      const element = document.getElementById(target);
      element?.scrollIntoView({ block: 'start' });
      element?.focus({ preventScroll: true });
    }, 0);
  }

  function focusResearch() {
    showView('research', 'topic');
    document.getElementById('topic')?.scrollIntoView({ block: 'center' });
    document.getElementById('topic')?.focus({ preventScroll: true });
  }

  return (
    <WorkspaceNavigation user={user} authenticated={authenticated} onSignout={handleSignout} onNewResearch={focusResearch} view={view} onNavigate={showView}>
    <main id="workspace-main" tabIndex={-1} className="app-shell dashboard-shell" ref={pageRef}>
      <header className="topbar">
        <span className="ros-breadcrumb">Workspace <span>/</span> {view === 'saved' ? 'Saved works' : 'Overview'}</span>
        <div className="topbar-actions">
          <span className={`status-pill ${apiOnline ? 'online' : 'offline'}`}><span aria-hidden="true" />{apiOnline ? 'API online' : 'API offline'}</span>
          <a className="docs-link" href={`${apiRootUrl}/docs`} target="_blank" rel="noreferrer">API docs</a>
          <button className="secondary-button" onClick={focusResearch}>New research</button>
        </div>
      </header>
      <section className="ros-welcome"><span className="eyebrow">Your research workspace</span><h1>{view === 'saved' ? 'Saved works' : user?.name ? `Welcome, ${user.name.split(' ')[0]}.` : 'Welcome to your workspace.'}</h1><p>{view === 'saved' ? 'Open a saved research run to review its papers, findings, and report here.' : 'A new question. A fresh perspective. Where will you begin?'}</p></section>
      <ToastNotification message={notification} onDismiss={() => setNotification('')}/>
      {error && <div className="error" role="alert">{error}</div>}
      <section aria-label={view === 'saved' ? 'Saved works' : 'Research workspace'}>
      {view === 'saved' && <div id="research-history" tabIndex={-1}><ResearchHistory history={history} loading={historyLoading} onSelect={handleSelectHistory} /></div>}
      <div className={view === 'saved' ? 'layout ros-saved-layout' : 'layout'}>
        <aside className="control-column" hidden={view === 'saved'}>
          <ResearchBrief onSubmit={handleRunResearch} loading={loading || !authenticated} />
        </aside>
<div id="research-results" tabIndex={-1} hidden={view === 'saved' && !result && !loading && !runState}><ResearchWorkspace result={result} loading={loading} runState={runState} /></div>
      </div>
      </section>
    </main>
    </WorkspaceNavigation>
  );
}
