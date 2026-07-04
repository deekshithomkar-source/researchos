import {
  Search,
  Brain,
  Database,
  FileText,
  Download,
  ShieldCheck,
  ArrowRight,
  CheckCircle2,
  Gauge,
  Layers3,
  LineChart,
  Sparkles,
} from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "AI Topic Understanding",
    desc: "The agent analyzes the user's research topic and identifies the main intent.",
    stat: "Intent map",
  },
  {
    icon: Search,
    title: "Smart Source Search",
    desc: "It searches reliable sources, articles, documents, and web data.",
    stat: "Source scan",
  },
  {
    icon: Database,
    title: "Data Collection",
    desc: "Important information is collected and filtered based on relevance.",
    stat: "Signal filter",
  },
  {
    icon: FileText,
    title: "Summary Generation",
    desc: "The system summarizes the collected information into clear points.",
    stat: "Brief builder",
  },
  {
    icon: Download,
    title: "Report Export",
    desc: "Users can download the final research report as PDF or document.",
    stat: "PDF / DOC",
  },
  {
    icon: ShieldCheck,
    title: "Secure Handling",
    desc: "User research history and data are stored safely.",
    stat: "Protected",
  },
];

const workflow = [
  {
    title: "User enters topic",
    detail: "The user defines the research subject, depth, and expected output.",
  },
  {
    title: "AI understands query",
    detail: "The agent extracts intent, entities, constraints, and related angles.",
  },
  {
    title: "Sources are searched",
    detail: "Reliable web pages, articles, documents, and datasets are discovered.",
  },
  {
    title: "Data is collected",
    detail: "Useful evidence is filtered, grouped, and ranked by relevance.",
  },
  {
    title: "Summary is created",
    detail: "Findings are transformed into clear, structured research points.",
  },
  {
    title: "Report is generated",
    detail: "The final output is prepared for download and future reference.",
  },
];

const metrics = [
  { label: "Workflow stages", value: "06", icon: Layers3 },
  { label: "Quality checks", value: "24", icon: CheckCircle2 },
  { label: "Report formats", value: "02", icon: Download },
];

export default function ResearchWorkflow() {
  return (
    <main className="workflow-page">
      <section className="workflow-hero">
        <div className="workflow-hero-content">
          <div className="workflow-try-now" aria-label="Try research agent">
            <a href="/auth">
              Try now
              <ArrowRight size={17} />
            </a>
          </div>

          <div className="workflow-kicker">
            <Sparkles size={16} />
            Research operations dashboard
          </div>
          <h1>Autonomous Research Agent Workflow</h1>
          <p>
            A professional overview of how the platform understands research
            intent, finds evidence, organizes data, and turns findings into
            export-ready reports.
          </p>

          <div className="workflow-actions">
            <a href="#workflow-steps" className="workflow-primary-action">
              View workflow
              <ArrowRight size={18} />
            </a>
            <span className="workflow-health">
              <span />
              System ready
            </span>
          </div>
        </div>

        <div className="workflow-command-panel" aria-label="Research status">
          <div className="command-panel-header">
            <span>Live run profile</span>
            <Gauge size={18} />
          </div>

          <div className="command-radar">
            <span />
            <span />
            <span />
            <Brain size={42} />
          </div>

          <div className="command-checks">
            <div>
              <CheckCircle2 size={17} />
              Intent analysis complete
            </div>
            <div>
              <CheckCircle2 size={17} />
              Source quality scoring enabled
            </div>
            <div>
              <CheckCircle2 size={17} />
              Export pipeline available
            </div>
          </div>
        </div>
      </section>

      <section className="workflow-metrics" aria-label="Workflow metrics">
        {metrics.map((metric, index) => {
          const Icon = metric.icon;

          return (
            <div
              className="workflow-metric"
              key={metric.label}
              style={{ "--delay": `${index * 90}ms` }}
            >
              <Icon size={20} />
              <strong>{metric.value}</strong>
              <span>{metric.label}</span>
            </div>
          );
        })}
      </section>

      <section className="workflow-section">
        <div className="workflow-section-heading">
          <span>Core capabilities</span>
          <h2>Built for structured research delivery</h2>
        </div>

        <div className="feature-grid">
          {features.map((feature, index) => {
            const Icon = feature.icon;

            return (
              <div
                key={feature.title}
                className="feature-tile"
                style={{ "--delay": `${index * 80}ms` }}
              >
                <div className="feature-topline">
                  <div className="feature-icon">
                    <Icon size={25} />
                  </div>
                  <span>{feature.stat}</span>
                </div>

                <h3>{feature.title}</h3>
                <p>{feature.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="workflow-section workflow-steps-section" id="workflow-steps">
        <div className="workflow-section-heading">
          <span>Execution model</span>
          <h2>How the agent moves from topic to report</h2>
        </div>

        <div className="workflow-timeline">
          {workflow.map((step, index) => (
            <article
              className="workflow-step"
              key={step.title}
              style={{ "--delay": `${index * 95}ms` }}
            >
              <div className="workflow-step-index">{index + 1}</div>
              <div>
                <h3>{step.title}</h3>
                <p>{step.detail}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="workflow-visual" aria-label="Research workflow path">
        <div>
          <span>Visual workflow</span>
          <h2>From question to validated document</h2>
        </div>

        <div className="workflow-chain">
          {workflow.map((item, index) => (
            <div
              className="workflow-chain-item"
              key={item.title}
              style={{ "--delay": `${index * 75}ms` }}
            >
              <div>
                <LineChart size={16} />
                {item.title}
              </div>

              {index !== workflow.length - 1 && <ArrowRight size={20} />}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
