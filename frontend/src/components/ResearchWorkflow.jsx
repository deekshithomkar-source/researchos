import { useEffect, useRef } from "react";
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  Clock3,
  FileText,
  Layers3,
  LockKeyhole,
  MessageSquareText,
  MoveRight,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

const benefits = [
  {
    icon: Search,
    title: "Focused discovery",
    desc: "Turn broad questions into targeted research paths with less manual sorting.",
  },
  {
    icon: ShieldCheck,
    title: "Evidence-first output",
    desc: "Keep findings grounded in sources so every brief feels easier to trust.",
  },
  {
    icon: Clock3,
    title: "Faster first drafts",
    desc: "Move from topic to structured summary without losing the thread.",
  },
  {
    icon: FileText,
    title: "Reusable reports",
    desc: "Save clean research briefs that are ready to revisit, refine, or share.",
  },
];

const workflow = [
  {
    title: "Frame the question",
    detail: "Add a topic, goal, and depth so the agent knows what useful means.",
  },
  {
    title: "Collect signal",
    detail: "Relevant sources are searched, filtered, and grouped into themes.",
  },
  {
    title: "Review the brief",
    detail: "Read a structured summary with source context and reusable notes.",
  },
];

const trustItems = ["Source-aware summaries", "Saved research history", "Clean export-ready notes"];

const previewSources = [
  "Academic notes",
  "Market reports",
  "Web evidence",
  "Strategic briefs",
];

function useScrollMotion(pageRef) {
  useEffect(() => {
    const page = pageRef.current;
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    if (!page || prefersReducedMotion.matches) {
      return undefined;
    }

    const motionItems = Array.from(page.querySelectorAll("[data-scroll-motion]"));
    let lastScrollY = window.scrollY;
    let frame = 0;

    const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

    const updateMotion = () => {
      const currentScrollY = window.scrollY;
      const direction = currentScrollY >= lastScrollY ? "down" : "up";
      const viewportHeight = window.innerHeight || 1;

      page.dataset.scrollDirection = direction;
      lastScrollY = currentScrollY;

      motionItems.forEach((item) => {
        const rect = item.getBoundingClientRect();
        const centerOffset = (rect.top + rect.height / 2 - viewportHeight / 2) / viewportHeight;
        const visibility = clamp(1 - Math.abs(centerOffset), 0, 1);
        const scrollLift = clamp(centerOffset * -32, -24, 24);
        const scrollTilt = clamp(centerOffset * 0.22, -0.35, 0.35);
        const scrollScale = 0.992 + visibility * 0.008;
        const isVisible = rect.top < viewportHeight * 0.92 && rect.bottom > viewportHeight * 0.08;

        item.style.setProperty("--scroll-y", `${scrollLift}px`);
        item.style.setProperty("--scroll-tilt", `${scrollTilt}deg`);
        item.style.setProperty("--scroll-scale", scrollScale.toFixed(3));
        item.style.setProperty("--scroll-progress", visibility.toFixed(3));
        item.classList.toggle("is-scroll-visible", isVisible);
      });

      frame = 0;
    };

    const scheduleMotion = () => {
      if (frame) {
        return;
      }

      frame = window.requestAnimationFrame(updateMotion);
    };

    scheduleMotion();
    window.addEventListener("scroll", scheduleMotion, { passive: true });
    window.addEventListener("resize", scheduleMotion);

    return () => {
      window.removeEventListener("scroll", scheduleMotion);
      window.removeEventListener("resize", scheduleMotion);

      if (frame) {
        window.cancelAnimationFrame(frame);
      }
    };
  }, [pageRef]);
}

export default function ResearchWorkflow() {
  const pageRef = useRef(null);

  useScrollMotion(pageRef);

  return (
    <main className="workflow-page" ref={pageRef}>
      <div className="workflow-noise" aria-hidden="true" />
      <nav className="workflow-nav" aria-label="Primary navigation">
        <a className="workflow-brand" href="/" aria-label="ResearchOS home">
          <img src="/assets/researchos-logo.svg" alt="ResearchOS" />
        </a>
        <div className="workflow-nav-actions">
          <a className="workflow-nav-button" href="/auth">
            Try now
            <ArrowRight size={22} />
          </a>
        </div>
      </nav>

      <section className="workflow-hero">
        <div className="workflow-hero-content">
          <div className="workflow-kicker">
            <Sparkles size={15} />
            AI research assistant
          </div>
          <h1>Autonomous Research Agent</h1>
          <p>
            A calm workspace for turning open-ended questions into clear,
            source-aware research briefs you can trust and revisit.
          </p>

          <div className="workflow-actions">
            <a href="/auth" className="workflow-primary-action">
              Start researching
              <ArrowRight size={18} />
            </a>
            <a href="#workflow-how" className="workflow-secondary-action">
              See how it works
            </a>
          </div>

          <div className="workflow-trust-strip" aria-label="Product strengths">
            {trustItems.map((item) => (
              <span key={item}>
                <CheckCircle2 size={16} />
                {item}
              </span>
            ))}
          </div>
        </div>

        <div className="workflow-command-panel" aria-label="Research workspace preview">
          <div className="workflow-float workflow-float-one" />
          <div className="workflow-float workflow-float-two" />
          <div className="workflow-orbit" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>

          <div className="research-window">
            <div className="research-window-bar">
              <span />
              <span />
              <span />
              <strong>Research run</strong>
            </div>

            <div className="research-window-body">
              <div className="research-query-card">
                <div>
                  <span>Active topic</span>
                  <h2>Market map for AI productivity tools</h2>
                </div>
                <BookOpenCheck size={22} />
              </div>

              <div className="research-source-grid">
                {previewSources.map((source, index) => (
                  <span key={source} style={{ "--delay": `${index * 180}ms` }}>
                    {source}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="insight-card insight-card-one">
            <MessageSquareText size={18} />
            <div>
              <span>Brief status</span>
              <strong>Summary ready</strong>
            </div>
          </div>

          <div className="insight-card insight-card-two">
            <ShieldCheck size={18} />
            <div>
              <span>Evidence</span>
              <strong>Sources filtered</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="workflow-section workflow-intro workflow-scroll-motion" data-scroll-motion>
        <span>What it does</span>
        <p>
          Designed for people who need reliable first drafts, organized notes,
          and useful source context without managing scattered tabs.
        </p>
      </section>

      <section className="workflow-section workflow-scroll-motion" id="benefits" data-scroll-motion>
        <div className="workflow-section-heading">
          <span>Why use it</span>
          <h2>Built for focused research work</h2>
        </div>

        <div className="benefit-grid">
          {benefits.map((benefit, index) => {
            const Icon = benefit.icon;

            return (
              <div
                key={benefit.title}
                className="benefit-card"
                style={{ "--delay": `${index * 80}ms` }}
              >
                <div className="benefit-icon">
                  <Icon size={22} />
                </div>
                <h3>{benefit.title}</h3>
                <p>{benefit.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section
        className="workflow-showcase workflow-scroll-motion"
        aria-label="Research output preview"
        data-scroll-motion
      >
        <div className="workflow-section-heading">
          <span>Output quality</span>
          <h2>Briefs that are easy to review and build on.</h2>
        </div>

        <div className="showcase-grid">
          <div className="showcase-report">
            <div className="showcase-report-header">
              <div>
                <FileText size={19} />
                <span>Generated brief</span>
              </div>
              <strong>Ready</strong>
            </div>
            <h3>AI productivity tools: adoption signals</h3>
            <p>
              Summarized themes, source-backed observations, and practical next
              questions for deeper analysis.
            </p>
          </div>

          <div className="showcase-points">
            <div>
              <LockKeyhole size={18} />
              <strong>Private workspace</strong>
            </div>
            <div>
              <Layers3 size={18} />
              <strong>Organized themes</strong>
            </div>
            <div>
              <Clock3 size={18} />
              <strong>Reusable history</strong>
            </div>
          </div>
        </div>
      </section>

      <section
        className="workflow-section workflow-steps-section workflow-scroll-motion"
        id="workflow-how"
        data-scroll-motion
      >
        <div className="workflow-section-heading">
          <span>Workflow</span>
          <h2>From question to structured brief</h2>
        </div>

        <div className="workflow-timeline">
          {workflow.map((step, index) => (
            <article
              className="workflow-step"
              key={step.title}
              style={{ "--delay": `${index * 95}ms` }}
            >
              <div className="workflow-step-index">{index + 1}</div>
              {index !== workflow.length - 1 && <MoveRight size={20} />}
              <div>
                <h3>{step.title}</h3>
                <p>{step.detail}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="workflow-cta workflow-scroll-motion" data-scroll-motion>
        <div>
          <span>Ready when you are</span>
          <h2>Start with a cleaner research workflow.</h2>
        </div>
        <a href="/auth" className="workflow-primary-action">
          Open the platform
          <ArrowRight size={18} />
        </a>
      </section>
    </main>
  );
}
