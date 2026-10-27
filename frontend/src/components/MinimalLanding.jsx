import { EducationalIllustration, AccessibleModal, InteractiveWorkflow } from './ResearchInteractions';
import { useState } from 'react';
import { ArrowRight, BookOpen, Search, Layers, Lightbulb, Quote, GraduationCap, History, Menu, X } from 'lucide-react';

export function Brand() {
  return <a className="ros-brand" href="/" aria-label="ResearchOS home"><BookOpen size={25} strokeWidth={1.5} /><span>Research<span className="ros-brand-light">OS</span></span></a>;
}

const links = [['#features', 'Features'], ['#how-it-works', 'How It Works'], ['#research-tools', 'Research Tools'], ['#about', 'About']];
const capabilities = [
  [Search, 'Focused research', 'Discover scholarly papers through academic providers, with optional AI-assisted analysis when configured.'],
  [BookOpen, 'Paper analysis', 'Review available evidence alongside the papers it comes from.'],
  [Lightbulb, 'Research gaps', 'Explore supported limitations and opportunities, with traceable sources.'],
  [Quote, 'Sources & citations', 'Keep sources in context with APA and IEEE citations and report exports.'],
  [Layers, 'Compare approaches', 'Review methods and findings across the evidence available for your topic.'],
  [GraduationCap, 'Learning recommendations', 'Connect your research to skills, courses, and project ideas.'],
  [History, 'Research history', 'Return to your saved runs and pick up where your curiosity left off.'],
];

function ProductPreview() {
  const [tab, setTab] = useState('Analysis');
  const descriptions = {
    Analysis: 'Findings will appear here with links to the evidence that supports them.',
    'Research gaps': 'Supported gaps will connect to the limitations and evidence in your retrieved papers.',
    'Saved research': 'Your completed runs form a personal research library you can reopen from history.',
  };
  return <section className="ros-section" id="research-tools" aria-labelledby="preview-title">
    <div className="ros-section-heading"><span className="eyebrow">A little structure. A lot of possibility.</span><h2 id="preview-title">One space for your next big question.</h2><p>From your first question to a source-aware report, keep the whole investigation together.</p></div>
    <div className="ros-preview"><div className="ros-preview-bar"><Brand /><span className="ros-demo-label">Interactive workspace demo · no research data</span></div>
      <div className="ros-preview-grid"><aside><span className="eyebrow">Your workspace</span><strong>New research</strong><span>Recent research</span><p>Your saved work will live here.</p><a href="/auth">Create your workspace <ArrowRight size={16}/></a></aside>
        <div className="ros-preview-main"><span className="eyebrow">Start with curiosity</span><h3>What would you like to explore?</h3><div className="ros-demo-input"><Search size={18}/><span>Your research topic or academic question</span><ArrowRight size={18}/></div><div className="ros-preview-tabs" aria-label="Preview sections">{Object.keys(descriptions).map(name => <button key={name} aria-pressed={tab === name} onClick={() => setTab(name)}>{name}</button>)}</div><div className="ros-preview-empty" aria-live="polite"><BookOpen size={28} strokeWidth={1.3}/><h4>{tab}</h4><p>{descriptions[tab]}</p></div></div>
      </div>
    </div>
  </section>;
}

export default function MinimalLanding() {
  const [menu, setMenu] = useState(false);
  const [feature, setFeature] = useState(null);
  return <div className="ros-landing">
    <a href="#main-content" className="ros-skip">Skip to content</a>
    <header className="ros-nav"><Brand/><button className="ros-menu-button" aria-expanded={menu} aria-controls="landing-navigation" aria-label={menu ? 'Close navigation' : 'Open navigation'} onClick={() => setMenu(!menu)}>{menu ? <X/> : <Menu/>}</button><nav id="landing-navigation" className={menu ? 'is-open' : ''} aria-label="Main navigation" onKeyDown={event => { if (event.key === 'Escape') { setMenu(false); document.querySelector('.ros-menu-button')?.focus(); } }}>{links.map(([href, label]) => <a href={href} key={href} onClick={() => setMenu(false)}>{label}</a>)}<a href="/auth?mode=signin">Sign In</a><a className="ros-button" href="/auth">Get Started <ArrowRight size={16}/></a></nav></header>
    <main id="main-content" className="ros-main">
      <section className="ros-hero"><div className="ros-floating ros-floating-book" aria-hidden="true"><BookOpen size={32} strokeWidth={1.2}/></div><div className="ros-floating ros-floating-idea" aria-hidden="true"><Lightbulb size={30} strokeWidth={1.2}/></div><span className="eyebrow">Your intelligent research workspace</span><h1>Great research starts<br/>with <span>curiosity.</span></h1><p>Explore ideas, analyze academic knowledge, discover research gaps, and turn curiosity into meaningful insights — all in one intelligent workspace.</p><div className="ros-cta-row"><a className="ros-button" href="/auth">Start Researching <ArrowRight size={18}/></a><a className="ros-text-link" href="#how-it-works">Explore How It Works <ArrowRight size={16}/></a></div><span className="ros-hero-note">Built for questions worth exploring.</span></section>
      <section className="ros-pillars" aria-label="Research pillars">{[['Discover', 'Explore topics, academic literature, and credible research resources.'], ['Analyze', 'Understand papers, compare approaches, and evaluate academic findings.'], ['Innovate', 'Identify research gaps, develop new ideas, and plan your next investigation.']].map(([title, text], index) => <article key={title}><EducationalIllustration kind={index}/><h2>{title}<span>0{index + 1}</span></h2><p>{text}</p></article>)}</section>
      <ProductPreview/>
      <section className="ros-section" id="features"><div className="ros-section-heading"><span className="eyebrow">Less scattered. More connected.</span><h2>Thoughtful tools for deeper work.</h2></div><div className="ros-capabilities">{capabilities.map(([Icon, title, text]) => <article key={title}><Icon size={23} strokeWidth={1.5}/><h3>{title}</h3><p>{text}</p>{['Focused research', 'Compare approaches', 'Research history'].includes(title) ? <details className="ros-feature-inline"><summary>How it works</summary><p>{title === 'Research history' ? 'Open Research history in your workspace and select a saved run to reopen its results.' : title === 'Compare approaches' ? 'Review retrieved methods and findings side by side in the report. Comparisons depend on available evidence.' : 'Set a topic, objective, level, and source target. Provider coverage and unavailable evidence are shown in the results.'}</p></details> : <button className="ros-feature-trigger" onClick={() => setFeature([title, text])}>Explore feature <ArrowRight size={15}/></button>}</article>)}</div></section>
      <InteractiveWorkflow/>
      <section className="ros-education ros-section" id="about"><div className="ros-education-art"><EducationalIllustration kind={0}/><EducationalIllustration kind={1}/></div><div><span className="eyebrow">Learning has no finish line</span><h2>Made for curious minds.</h2><p>Whether you're a student, academic researcher, or lifelong learner, ResearchOS gives you the tools to explore deeper.</p><p className="ros-education-note">Follow a question. Connect ideas. Make space for what comes next.</p></div></section>
      <section className="ros-final"><span className="eyebrow">Make room for discovery</span><h2>Your next discovery begins here.</h2><p>A simpler, smarter way to explore research.</p><a href="/auth" className="ros-button">Start Researching <ArrowRight size={18}/></a></section>
    </main><footer className="ros-footer"><Brand/><nav aria-label="Footer navigation">{links.map(([href, label]) => <a key={href} href={href}>{label}</a>)}</nav><small>© {new Date().getFullYear()} ResearchOS</small></footer>
    {feature && <AccessibleModal title={feature[0]} onClose={() => setFeature(null)}><p>{feature[1]}</p><EducationalIllustration kind={feature[0] === 'Research gaps' ? 2 : 1}/><ol><li>Start with a topic and your research objective.</li><li>Review the available papers and their supporting evidence.</li><li>{feature[0] === 'Sources & citations' ? 'Choose APA author-date or IEEE numbered citations, then export your report as PDF, DOCX, or Markdown.' : feature[0] === 'Learning recommendations' ? 'Open Skills, Courses, or Projects. Verified resource links are separate from generated recommendations.' : feature[0] === 'Research history' ? 'Select a saved run in Research history to reopen its results.' : feature[0] === 'Research gaps' ? 'Open Research Gaps to inspect evidence-supported limitations. Missing evidence is shown honestly.' : 'Open the relevant result section to inspect its evidence and coverage notes.'}</li></ol><p className="ros-preview-disclaimer">Feature walkthrough, not generated research. Available results depend on retrieved evidence and provider availability.</p><a className="ros-button" href="/auth">Start your research <ArrowRight size={16}/></a></AccessibleModal>}
  </div>;
}
