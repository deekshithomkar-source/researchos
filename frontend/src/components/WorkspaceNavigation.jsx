import { useEffect, useRef, useState } from 'react';
import { Menu, X, PanelLeftClose, PanelLeftOpen, Plus, History, LayoutDashboard, BookOpen, LogOut } from 'lucide-react';
import { Brand } from './MinimalLanding';

export default function WorkspaceNavigation({ children, user, authenticated, onSignout, onNewResearch, view, onNavigate }) {
  const [collapsed, setCollapsed] = useState(false);
  const [open, setOpen] = useState(false);
  const drawer = useRef(null);
  const trigger = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    const bodyOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    drawer.current.querySelector('button')?.focus();
    function keydown(event) {
      if (event.key === 'Escape') setOpen(false);
      if (event.key !== 'Tab') return;
      const items = [...drawer.current.querySelectorAll('a, button')].filter(node => node.getClientRects().length);
      const first = items[0], last = items.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    document.addEventListener('keydown', keydown);
    const media = window.matchMedia('(min-width: 901px)');
    const resize = () => { if (media.matches) setOpen(false); };
    media.addEventListener('change', resize);
    return () => { document.body.style.overflow = bodyOverflow; document.removeEventListener('keydown', keydown); media.removeEventListener('change', resize); (trigger.current || previous)?.focus(); };
  }, [open]);
  function navigate(id) {
    setOpen(false);
    onNavigate(id === 'research-history' ? 'saved' : 'research', id);
  }
  return <div className={`ros-app ${collapsed ? 'is-collapsed' : ''}`}>
    <a className="ros-skip" href="#workspace-main">Skip to workspace</a>
    <div className="ros-mobile-bar"><Brand/><button ref={trigger} aria-label="Open workspace navigation" aria-expanded={open} aria-controls="workspace-navigation" onClick={() => setOpen(true)}><Menu/></button></div>
    {open && <div className="ros-drawer-backdrop" onClick={() => setOpen(false)} aria-hidden="true"/>}
    <aside id="workspace-navigation" ref={drawer} className={`ros-sidebar ${open ? 'is-open' : ''}`} role={open ? 'dialog' : undefined} aria-modal={open || undefined} aria-label="Workspace navigation">
      <button className="ros-drawer-close" onClick={() => setOpen(false)} aria-label="Close workspace navigation"><X/></button>
      <Brand/><button className="ros-sidebar-collapse" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={() => setCollapsed(!collapsed)}>{collapsed ? <PanelLeftOpen size={20}/> : <PanelLeftClose size={20}/>}</button>
      <span className="ros-sidebar-label">Workspace</span><nav aria-label="Workspace sections">
        <button title="Overview" aria-current={view === 'research' ? 'page' : undefined} onClick={() => navigate('workspace-main')}><LayoutDashboard size={19}/><span>Overview</span></button>
        <button title="New research" onClick={() => { setOpen(false); onNewResearch(); }}><Plus size={19}/><span>New research</span></button>
        <button title="Saved works" aria-current={view === 'saved' ? 'page' : undefined} onClick={() => navigate('research-history')}><History size={19}/><span>Saved works</span></button>
        <button title="Research results" onClick={() => navigate('research-results')}><BookOpen size={19}/><span>Research results</span></button>
      </nav><div className="ros-sidebar-bottom"><p className="ros-sidebar-label">A space for deeper thinking.</p>{authenticated && <><span className="ros-profile" title={user?.name || 'Researcher'}><span aria-hidden="true">{(user?.name || 'R').slice(0, 1).toUpperCase()}</span><strong>{user?.name || 'Researcher'}</strong></span><button title="Sign out" onClick={onSignout}><LogOut size={18}/><span>Sign out</span></button></>}</div>
    </aside><div className="ros-app-content" inert={open ? true : undefined}>{children}</div>
  </div>;
}
