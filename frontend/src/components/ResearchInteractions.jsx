import { useEffect, useRef, useState } from 'react';
import { X, Info } from 'lucide-react';

export function EducationalIllustration({ kind = 0 }) {
  const artwork = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { threshold: 0.25 });
    if (artwork.current) observer.observe(artwork.current);
    return () => observer.disconnect();
  }, []);
  return <svg ref={artwork} data-visible={visible} className={`ros-illustration ros-art-${kind}`} viewBox="0 0 280 180" fill="none" stroke="#020D19" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <ellipse cx="140" cy="158" rx="105" ry="10" fill="#e5e4de" stroke="none"/>
    <g className="ros-art-scene">{kind === 0 ? <><rect x="151" y="28" width="72" height="93" rx="6" fill="#fff"/><path d="M164 45h42M164 56h32M164 68h36M164 80h20"/><circle cx="90" cy="54" r="18" fill="#F0EDE4"/><path d="M72 53q-3-28 22-24 18 3 15 24M79 78q-28 9-27 55h75q-1-43-25-55" fill="#536F8B"/><path d="m74 95 16 30 34-14M109 92l18 17"/><path d="m92 113 31-8 30 9v32l-30-9-31 8zM123 105v32" fill="#fff"/><path d="M42 148h141M48 140h30M51 133h27"/><g className="ros-art-search"><circle cx="214" cy="112" r="22" fill="#F0EDE4"/><path d="m230 129 18 20M205 112h18M214 103v18"/></g></> : kind === 1 ? <><rect x="42" y="44" width="79" height="103" rx="6" fill="#fff" transform="rotate(-8 42 44)"/><path d="m57 62 44-6M59 73l31-4M61 86l25-3"/><rect x="109" y="26" width="95" height="123" rx="7" fill="#fff"/><path d="M126 45h60M126 56h38M128 126V95M147 126V105M166 126V83M185 126V70M122 127h69"/><path className="ros-art-chart" pathLength="1" d="M128 95v31M166 84v42" stroke="#536F8B" strokeWidth="7"/><circle cx="222" cy="47" r="17" fill="#F0EDE4"/><circle cx="239" cy="98" r="10" fill="#536F8B"/><path d="m228 64 8 24M208 57l-15 11M229 105l-25 12M215 47l5 5 10-12"/></> : <><path d="M107 113c0-25-25-34-25-59a41 41 0 0 1 82 0c0 25-25 34-25 59z" fill="#fff"/><path d="M107 123h32M112 134h22M118 113V76l-12-13M128 113V76l12-13"/><path className="ros-art-rays" d="M123 5V0M71 29l-16-9M174 29l16-9M64 65H44M181 65h20"/><circle cx="62" cy="118" r="12" fill="#536F8B"/><circle cx="203" cy="122" r="17" fill="#F0EDE4"/><circle cx="171" cy="151" r="7" fill="#536F8B"/><path d="m75 118 31 7M140 124l46-2M192 135l-15 12M203 114v16M195 122h16"/></>}
    </g>
  </svg>;
}

export function AccessibleModal({ title, onClose, children }) {
  const ref = useRef(null);
  const [closing, setClosing] = useState(false);
  useEffect(() => {
    const trigger = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    const dialog = ref.current;
    dialog.showModal();
    document.body.style.overflow = 'hidden';
    return () => { dialog.close(); document.body.style.overflow = previousOverflow; if (trigger instanceof HTMLElement) trigger.focus(); };
  }, []);
  useEffect(() => {
    if (!closing) return;
    const timer = setTimeout(onClose, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 160);
    return () => clearTimeout(timer);
  }, [closing, onClose]);
  return <dialog ref={ref} className={`ros-modal ${closing ? 'is-closing' : ''}`} aria-labelledby="feature-dialog-title" onKeyDown={event => {
    if (event.key === 'Escape') { event.preventDefault(); setClosing(true); return; }
    if (event.key !== 'Tab') return;
    const controls = [...ref.current.querySelectorAll('button, a[href], input, select, textarea, [tabindex="0"]')];
    const first = controls[0], last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }} onCancel={event => { event.preventDefault(); setClosing(true); }} onClick={event => { if (event.target === event.currentTarget) setClosing(true); }}>
    <div className="ros-modal-content"><button className="ros-modal-close" aria-label="Close feature preview" onClick={() => setClosing(true)}><X size={20}/></button><span className="eyebrow">Inside your workspace</span><h2 id="feature-dialog-title">{title}</h2>{children}</div>
  </dialog>;
}

const stages = [
  ['Ask', 'Give your curiosity a direction.', 'Enter your topic, objective, and academic level. Choose a report format, citation style, and source target.'],
  ['Analyze', 'Bring the evidence into focus.', 'Review retrieved papers and available passages. Findings stay linked to evidence, and incomplete coverage stays visible.'],
  ['Discover', 'Turn understanding into a next step.', 'Explore supported gaps, learning recommendations, and project ideas. Reopen saved research or export your report.'],
];
export function InteractiveWorkflow() {
  const [active, setActive] = useState(0);
  return <section className="ros-section" id="how-it-works"><div className="ros-section-heading"><span className="eyebrow">From a question to a direction</span><h2>Follow your curiosity. Find your next step.</h2></div><div className="ros-workflow-controls" aria-label="Research workflow stages">{stages.map(([title], i) => <button key={title} aria-pressed={active === i} onClick={() => setActive(i)}><span>0{i + 1}</span>{title}<span aria-hidden="true">{i < 2 ? '→' : '✓'}</span></button>)}</div><div className="ros-workflow-detail" aria-live="polite"><EducationalIllustration kind={active}/><div key={active} className="ros-stage-copy"><h3>{stages[active][1]}</h3><p>{stages[active][2]}</p></div></div></section>;
}

export function ToastNotification({ message, onDismiss }) {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(onDismiss, 6500);
    return () => clearTimeout(timer);
  }, [message, onDismiss]);
  return <div className="ros-toast-region" role="status" aria-live="polite" aria-atomic="true">{message && <div className="ros-toast"><Info size={18} aria-hidden="true"/><span>{message}</span><button onClick={onDismiss} aria-label="Dismiss notification"><X size={16}/></button></div>}</div>;
}

export function LoadingSkeleton() {
  return <div className="ros-skeleton" aria-hidden="true"><span/><span/><span/></div>;
}
