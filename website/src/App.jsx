import React, { useEffect, useState } from "react";
import {
  Download, Mic, FileText, Rocket, Sparkles, Users, GitBranch,
  Eye, ShieldCheck, ArrowRight, Check, Github, Monitor, Plus, Minus,
  CornerDownLeft,
} from "lucide-react";
import { useLatestRelease, RELEASES_PAGE } from "./lib/useLatestRelease.js";
import "./sections.css";

/* ============================================================
   ProtoPilot — marketing landing page (dark / aurora)

   Look inspired by Google Stitch: near-black canvas, a flowing
   purple→blue→cyan aurora, dotted grid, huge display type,
   glassy cards, an FAQ accordion.

   The download button stays "live": useLatestRelease() reads the
   newest GitHub release every load and points straight at the
   right installer for the visitor's OS. Ship a new app version
   and this page updates itself.
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
          <span className="nav-badge">BETA</span>
        </a>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#faq">FAQ</a>
        </div>
        <div className="nav-actions">
          <a className="nav-ghost" href={RELEASES_PAGE} target="_blank" rel="noreferrer">
            <Github size={16} /> GitHub
          </a>
          <DownloadButton className="btn btn-light btn-sm" showMeta={false} />
        </div>
      </div>
    </nav>
  );
}

const CHIPS = [
  "Turn today's standup into a prototype",
  "Draft requirements from our client call",
  "Build the dashboard we just discussed",
];

function Hero() {
  return (
    <header className="hero" id="top">
      <div className="hero-void" />
      <div className="aurora hero-aurora-1" />
      <div className="aurora hero-aurora-2" />
      <div className="aurora hero-aurora-3" />
      <div className="hero-dots" />

      <div className="container hero-inner">
        <div className="eyebrow reveal">
          <span className="live-dot" /> Now recording your ideas
        </div>
        <h1 className="hero-title display reveal">
          Prototypes at the
          <br />
          <span className="grad-text">speed of conversation</span>
        </h1>
        <p className="hero-sub reveal">
          ProtoPilot listens to your meeting, transcribes it live, and lets AI
          agents turn what your team actually said into requirements — and a
          working prototype, before the call even ends.
        </p>

        {/* glassy prompt mock — echoes the in-app meeting workspace */}
        <div className="prompt-box reveal">
          <div className="prompt-line" />
          <div className="prompt-placeholder">
            What shall we turn into a prototype today?
          </div>
          <div className="prompt-bar">
            <div className="prompt-tabs">
              <span className="prompt-tab active"><Mic size={13} /> Meeting</span>
              <span className="prompt-tab"><FileText size={13} /> Requirements</span>
            </div>
            <div className="prompt-actions">
              <span className="prompt-model"><Sparkles size={13} /> Agents</span>
              <span className="prompt-send"><CornerDownLeft size={15} /></span>
            </div>
          </div>
        </div>

        <div className="hero-chips reveal">
          {CHIPS.map((c) => (
            <span className="chip" key={c}>
              <Sparkles size={13} /> {c}
            </span>
          ))}
        </div>

        <div className="hero-cta reveal">
          <DownloadButton />
          <a className="btn btn-ghost" href="#how">
            See how it works <ArrowRight size={17} />
          </a>
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
    <section className="section features" id="features">
      <div className="aurora feat-aurora" />
      <div className="container">
        <div className="section-head reveal">
          <span className="eyebrow">Why ProtoPilot</span>
          <h2 className="section-title">
            Everything from the call.
            <br />
            <span className="grad-text">None of the busywork.</span>
          </h2>
          <p className="section-sub">
            You talk through an idea, and by the time you hang up there's
            something real to look at.
          </p>
        </div>
        <div className="feat-grid">
          {FEATURES.map((f, i) => {
            const Icon = f.icon;
            return (
              <div className="feat-card reveal" key={f.title} style={{ transitionDelay: `${i * 55}ms` }}>
                <div className="feat-dots" />
                <div className="feat-icon"><Icon size={20} /></div>
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
                <div className="step-icon"><Icon size={22} /></div>
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

const FAQS = [
  {
    q: "What is ProtoPilot?",
    a: "ProtoPilot is a desktop app that sits in on your meetings, transcribes the conversation live, and uses a team of AI agents to turn what was discussed into structured requirements and a working prototype — before the call even ends.",
  },
  {
    q: "Is ProtoPilot free?",
    a: "Yes. Download it and sign in with Google or email to get started. There's nothing to configure.",
  },
  {
    q: "Which platforms are supported?",
    a: "Right now there's a Windows 10/11 (64-bit) desktop build. The download button above always points at the latest installer.",
  },
  {
    q: "How do updates work?",
    a: "The app auto-updates itself. When a new version ships, ProtoPilot downloads it quietly in the background and offers a one-click restart — you never reinstall by hand.",
  },
  {
    q: "Does it really generate a working prototype?",
    a: "Yes. The generation pipeline runs through spec, design and build stages live, and produces a real prototype you can open, view and share from inside the app.",
  },
  {
    q: "What happens to my meetings?",
    a: "Your meetings and prototypes are tied to your account. You sign in, and your history stays yours.",
  },
];

function Faq() {
  const [open, setOpen] = useState(0);
  return (
    <section className="section faq" id="faq">
      <div className="container faq-inner">
        <h2 className="faq-title display reveal">Questions?</h2>
        <div className="faq-list">
          {FAQS.map((item, i) => {
            const isOpen = open === i;
            return (
              <div
                className={`faq-item reveal ${isOpen ? "open" : ""}`}
                key={item.q}
                onClick={() => setOpen(isOpen ? -1 : i)}
              >
                <div className="faq-q">
                  <span>{item.q}</span>
                  {isOpen ? <Minus size={18} /> : <Plus size={18} />}
                </div>
                {isOpen && <div className="faq-a">{item.a}</div>}
              </div>
            );
          })}
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
          <div className="aurora cta-aurora" />
          <div className="cta-dots" />
          <div className="cta-content">
            <span className="cta-mark">
              <img src="/logo.png" alt="ProtoPilot" />
            </span>
            <h2 className="cta-title display">Vibe your ideas into reality.</h2>
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
          <a href="#faq">FAQ</a>
          <a href={RELEASES_PAGE} target="_blank" rel="noreferrer">Releases</a>
        </div>
        <div className="footer-copy">
          © {new Date().getFullYear()} ProtoPilot · Meetings in. Prototypes out.
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
      <Faq />
      <DownloadCTA />
      <Footer />
    </>
  );
}
