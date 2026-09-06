import React, { useEffect, useRef } from "react";
import {
  Download, Mic, FileText, Rocket, Sparkles, Users, GitBranch,
  Eye, ShieldCheck, Zap, ArrowRight, Check, Github, Monitor,
} from "lucide-react";
import { useLatestRelease, RELEASES_PAGE } from "./lib/useLatestRelease.js";
import "./sections.css";

/* ============================================================
   ProtoPilot — marketing landing page

   One scrolling page:
     Nav → Hero (+ smart download) → Logos/trust → Features
     → How it works (3 steps) → Product preview → Download CTA
     → Footer

   The download button is "live": useLatestRelease() reads the
   newest GitHub release every load and points straight at the
   right installer for the visitor's OS. Ship a new app version
   and this page updates itself — no edits here.
   ============================================================ */

function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.14 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

function DownloadButton({ className = "btn btn-primary", showMeta = true }) {
  const rel = useLatestRelease();
  const label = rel.loading
    ? "Download for desktop"
    : `Download for ${rel.osLabel}`;
  return (
    <div className="dl-wrap">
      <a
        href={rel.downloadUrl}
        className={className}
        target={rel.hasDirectAsset ? "_self" : "_blank"}
        rel="noreferrer"
      >
        <Download size={18} />
        {label}
      </a>
      {showMeta && (
        <div className="dl-meta">
          {rel.version ? (
            <>
              <span className="dl-dot" /> Latest {rel.version}
              {!rel.hasDirectAsset && rel.os !== "windows" && (
                <> · Windows build available</>
              )}
            </>
          ) : (
            <>Free · Windows 10/11</>
          )}
        </div>
      )}
    </div>
  );
}

function Nav() {
  return (
    <nav className="nav">
      <div className="container nav-inner">
        <a className="nav-brand" href="#top">
          <span className="nav-mark">
            <img src="/logo.png" alt="ProtoPilot" />
          </span>
          <span>ProtoPilot</span>
        </a>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#preview">Preview</a>
        </div>
        <div className="nav-actions">
          <a
            className="nav-ghost"
            href={RELEASES_PAGE}
            target="_blank"
            rel="noreferrer"
          >
            <Github size={16} /> GitHub
          </a>
          <DownloadButton className="btn btn-dark btn-sm" showMeta={false} />
        </div>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <header className="hero" id="top">
      <div className="hero-glow" />
      <div className="hero-mint" />
      <div className="hero-grid" />
      <div className="container hero-inner">
        <div className="eyebrow reveal">
          <span className="live-dot" /> Now recording your ideas
        </div>
        <h1 className="hero-title display reveal">
          Meetings in.
          <br />
          <span className="grad-text">Prototypes out.</span>
        </h1>
        <p className="hero-sub reveal">
          ProtoPilot listens to your meetings, transcribes the conversation,
          and lets AI agents turn what your team actually said into
          requirements — and a working prototype, before the call even ends.
        </p>
        <div className="hero-cta reveal">
          <DownloadButton />
          <a className="btn btn-ghost" href="#how">
            See how it works <ArrowRight size={17} />
          </a>
        </div>
        <div className="hero-trust reveal">
          <span><Check size={14} /> Free to use</span>
          <span><Check size={14} /> Auto-updates</span>
          <span><Check size={14} /> No setup</span>
        </div>
      </div>
    </header>
  );
}

const FEATURES = [
  {
    icon: Mic,
    title: "Live transcription",
    desc: "Joins your call and captures every word in real time — no note-taker, no missed decisions.",
  },
  {
    icon: Users,
    title: "AI workforce",
    desc: "A team of specialised agents reads the conversation and splits the work like a real product team.",
  },
  {
    icon: FileText,
    title: "Requirements, extracted",
    desc: "Turns loose discussion into structured requirements you can actually build against.",
  },
  {
    icon: GitBranch,
    title: "Generation pipeline",
    desc: "Watch each stage run live — from spec to design to a working prototype, step by step.",
  },
  {
    icon: Eye,
    title: "Instant prototype",
    desc: "A real, viewable prototype at the end of the call. Share it, open it, iterate on it.",
  },
  {
    icon: ShieldCheck,
    title: "Yours, secured",
    desc: "Sign in with Google or email. Your meetings and prototypes stay tied to your account.",
  },
];

function Features() {
  return (
    <section className="section" id="features">
      <div className="container">
        <div className="section-head reveal">
          <span className="eyebrow">Why ProtoPilot</span>
          <h2 className="section-title">
            Everything from the call.
            <br />
            <span className="grad-text">None of the busywork.</span>
          </h2>
          <p className="section-sub">
            The whole point: you talk through an idea, and by the time you hang
            up there's something real to look at.
          </p>
        </div>
        <div className="feat-grid">
          {FEATURES.map((f, i) => {
            const Icon = f.icon;
            return (
              <div className="feat-card reveal" key={f.title} style={{ transitionDelay: `${i * 60}ms` }}>
                <div className="feat-icon">
                  <Icon size={20} />
                </div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

const STEPS = [
  {
    icon: Mic,
    step: "01",
    title: "Start a meeting",
    desc: "Open ProtoPilot and start (or join) a call. It begins transcribing the moment the conversation does.",
  },
  {
    icon: Sparkles,
    step: "02",
    title: "Let the agents work",
    desc: "AI agents read the transcript live, pull out requirements, and kick off the generation pipeline.",
  },
  {
    icon: Rocket,
    step: "03",
    title: "Open your prototype",
    desc: "Before the call ends, a working prototype is ready to view and share. No handoff, no waiting.",
  },
];

function HowItWorks() {
  return (
    <section className="section how" id="how">
      <div className="container">
        <div className="section-head center reveal">
          <span className="eyebrow">How it works</span>
          <h2 className="section-title">Three steps, one call.</h2>
        </div>
        <div className="steps">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <div className="step reveal" key={s.step} style={{ transitionDelay: `${i * 90}ms` }}>
                <div className="step-num display">{s.step}</div>
                <div className="step-icon">
                  <Icon size={22} />
                </div>
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
                {i < STEPS.length - 1 && <div className="step-connector" />}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Preview() {
  return (
    <section className="section preview" id="preview">
      <div className="container">
        <div className="section-head center reveal">
          <span className="eyebrow">Inside the app</span>
          <h2 className="section-title">
            Built to feel <span className="grad-text">effortless.</span>
          </h2>
          <p className="section-sub" style={{ margin: "16px auto 0" }}>
            A clean desktop app that stays out of the way — until the ideas
            start flowing.
          </p>
        </div>
        <div className="preview-frame reveal">
          <div className="preview-bar">
            <span className="pv-dot" style={{ background: "#FF5F57" }} />
            <span className="pv-dot" style={{ background: "#FEBC2E" }} />
            <span className="pv-dot" style={{ background: "#28C840" }} />
            <span className="pv-url">ProtoPilot</span>
          </div>
          <div className="preview-body">
            <div className="pv-mock-nav">
              <span className="pv-mock-mark">
                <img src="/logo.png" alt="" />
              </span>
              <span className="pv-mock-title">Meeting Workspace</span>
              <span className="pv-live"><span className="live-dot" /> Live</span>
            </div>
            <div className="pv-mock-grid">
              <div className="pv-mock-panel">
                <div className="pv-mock-label"><Mic size={13} /> Transcript</div>
                <div className="pv-line" style={{ width: "92%" }} />
                <div className="pv-line" style={{ width: "78%" }} />
                <div className="pv-line" style={{ width: "85%" }} />
                <div className="pv-line dim" style={{ width: "64%" }} />
                <div className="pv-line dim" style={{ width: "70%" }} />
              </div>
              <div className="pv-mock-panel">
                <div className="pv-mock-label"><FileText size={13} /> Requirements</div>
                <div className="pv-req"><Check size={13} /> User can start a meeting</div>
                <div className="pv-req"><Check size={13} /> Live transcription</div>
                <div className="pv-req"><Check size={13} /> Extract requirements</div>
                <div className="pv-req pending"><span className="pv-spin" /> Generating prototype…</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function DownloadCTA() {
  return (
    <section className="section cta-section">
      <div className="container">
        <div className="cta-card reveal">
          <div className="cta-glow" />
          <span className="cta-mark">
            <img src="/logo.png" alt="ProtoPilot" />
          </span>
          <h2 className="section-title" style={{ color: "#fff" }}>
            Ready to turn talk into a prototype?
          </h2>
          <p className="cta-sub">
            Download ProtoPilot for desktop. It's free, it auto-updates, and
            there's nothing to configure.
          </p>
          <div className="cta-actions">
            <DownloadButton className="btn btn-primary" />
          </div>
          <div className="cta-os">
            <Monitor size={14} /> Windows 10 &amp; 11 · 64-bit
          </div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div className="footer-brand">
          <span className="nav-mark">
            <img src="/logo.png" alt="ProtoPilot" />
          </span>
          <span>ProtoPilot</span>
        </div>
        <div className="footer-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#preview">Preview</a>
          <a href={RELEASES_PAGE} target="_blank" rel="noreferrer">
            Releases
          </a>
        </div>
        <div className="footer-copy">
          © {new Date().getFullYear()} ProtoPilot. Meetings in. Prototypes out.
        </div>
      </div>
    </footer>
  );
}

export default function App() {
  useReveal();
  return (
    <>
      <Nav />
      <Hero />
      <Features />
      <HowItWorks />
      <Preview />
      <DownloadCTA />
      <Footer />
    </>
  );
}
