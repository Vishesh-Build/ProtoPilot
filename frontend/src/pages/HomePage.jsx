import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Mic, Sparkles, Layers, Check, ArrowRight, ChevronDown,
  LogIn, UserPlus, Radio, FileText, Rocket,
} from "lucide-react";

/* ============================================================
   ProtoPilot — Home (Desktop App)

   Hero: full-bleed abstract "white futuristic architecture" scene
   built in pure CSS/SVG (curved light bands + soft glow + marble
   floor), matching the brand's teal + indigo accent already used
   in the Live Meeting screen.

   Scroll section: a living, looping demo — reimagines the classic
   "code editor + AI assistant" pattern for THIS product: a light
   glass panel where a meeting transcript types itself out, and
   requirement points get extracted and ticked off on the right,
   ending in a pulse on "Generate Prototype". Triggers the first
   time it scrolls into view, then loops.
   ============================================================ */

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }

  .pp-root {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
    width: 100vw;
    height: 100vh;
    overflow-y: auto;
    overflow-x: hidden;
    scroll-behavior: smooth;
    background: #FAFBFD;
    color: #14151B;
  }
  .pp-root::-webkit-scrollbar { width: 6px; }
  .pp-root::-webkit-scrollbar-thumb { background: #DEE1EC; border-radius: 8px; }

  .pp-display { font-family: 'Space Grotesk', 'Inter', sans-serif; }

  /* ---------------- NAV ---------------- */
  .pp-nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 30;
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 40px;
  }
  .pp-logo { display: flex; align-items: center; gap: 9px; font-weight: 700; font-size: 15px; color: #14151B; }
  .pp-logo-mark {
    width: 26px; height: 26px; border-radius: 8px;
    background: linear-gradient(135deg, #00E6A8, #4A63E8);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 12px rgba(74,99,232,0.35);
  }
  .pp-nav-actions { display: flex; align-items: center; gap: 10px; }
  .pp-btn-ghost {
    display: flex; align-items: center; gap: 7px;
    padding: 9px 16px; border-radius: 999px; font-size: 12.5px; font-weight: 600;
    color: #14151B; background: rgba(255,255,255,0.55); backdrop-filter: blur(10px);
    border: 1px solid rgba(20,21,27,0.08); cursor: pointer; transition: all 0.18s ease;
  }
  .pp-btn-ghost:hover { background: rgba(255,255,255,0.85); transform: translateY(-1px); }
  .pp-btn-solid {
    display: flex; align-items: center; gap: 7px;
    padding: 9px 18px; border-radius: 999px; font-size: 12.5px; font-weight: 700;
    color: #fff; background: linear-gradient(135deg, #14151B, #2A2C3A);
    border: none; cursor: pointer; transition: all 0.18s ease;
    box-shadow: 0 8px 20px rgba(20,21,27,0.22);
  }
  .pp-btn-solid:hover { transform: translateY(-1px); box-shadow: 0 10px 24px rgba(20,21,27,0.3); }

  /* ---------------- HERO (abstract white architecture) ---------------- */
  .pp-hero {
    position: relative;
    height: 100vh;
    width: 100%;
    overflow: hidden;
    display: flex; align-items: center; justify-content: center;
    background:
      radial-gradient(1100px 620px at 18% 8%, #ffffff 0%, #F3F5FA 42%, #EAEDF5 100%);
  }
  .pp-hero-glow {
    position: absolute; top: -10%; left: -5%; width: 62%; height: 75%;
    background: radial-gradient(circle at 35% 30%, rgba(255,255,255,0.95), rgba(210,225,255,0.35) 55%, transparent 75%);
    filter: blur(6px);
  }
  .pp-hero-mint {
    position: absolute; bottom: 8%; right: -8%; width: 55%; height: 40%;
    background: radial-gradient(circle at 60% 50%, rgba(0,230,168,0.16), transparent 70%);
    filter: blur(20px);
  }
  .pp-hero-arcs { position: absolute; inset: 0; }
  .pp-hero-floor {
    position: absolute; left: 0; right: 0; bottom: 0; height: 40%;
    background: linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.6) 55%, #ffffff 100%);
  }

  .pp-hero-content {
    position: relative; z-index: 2;
    display: flex; flex-direction: column; align-items: center;
    text-align: center; max-width: 780px; padding: 0 24px;
  }
  .pp-eyebrow {
    display: flex; align-items: center; gap: 7px;
    font-size: 11.5px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    color: #4A63E8; background: rgba(74,99,232,0.08);
    border: 1px solid rgba(74,99,232,0.16);
    padding: 6px 14px; border-radius: 999px; margin-bottom: 22px;
  }
  .pp-eyebrow-dot { width: 6px; height: 6px; border-radius: 50%; background: #00C88A; box-shadow: 0 0 8px rgba(0,200,138,0.7); animation: ppPulse 1.6s ease-in-out infinite; }
  @keyframes ppPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }

  .pp-hero-title {
    font-size: 64px; font-weight: 700; line-height: 1.02; letter-spacing: -0.03em;
    color: #0F1016; margin: 0;
  }
  .pp-hero-title .pp-grad {
    background: linear-gradient(120deg, #14151B 30%, #4A63E8 65%, #00C88A 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .pp-hero-sub {
    margin-top: 20px; font-size: 16px; line-height: 1.6; color: #5B5F70;
    max-width: 560px; font-weight: 450;
  }
  .pp-hero-cta { display: flex; align-items: center; gap: 12px; margin-top: 34px; }
  .pp-btn-primary {
    display: flex; align-items: center; gap: 8px;
    padding: 13px 24px; border-radius: 999px; font-size: 13.5px; font-weight: 700;
    color: #fff; background: linear-gradient(135deg, #4A63E8, #7C6BEA);
    border: none; cursor: pointer; transition: all 0.18s ease;
    box-shadow: 0 12px 26px rgba(74,99,232,0.34);
  }
  .pp-btn-primary:hover { transform: translateY(-2px); box-shadow: 0 16px 32px rgba(74,99,232,0.42); }
  .pp-btn-secondary {
    display: flex; align-items: center; gap: 8px;
    padding: 13px 22px; border-radius: 999px; font-size: 13.5px; font-weight: 600;
    color: #14151B; background: rgba(255,255,255,0.6); backdrop-filter: blur(8px);
    border: 1px solid rgba(20,21,27,0.1); cursor: pointer; transition: all 0.18s ease;
  }
  .pp-btn-secondary:hover { background: #fff; transform: translateY(-2px); }

  .pp-scroll-cue {
    position: absolute; bottom: 34px; left: 50%; transform: translateX(-50%); z-index: 2;
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    color: #9599AA; font-size: 10.5px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;
  }
  .pp-scroll-cue-icon { animation: ppBounce 1.8s ease-in-out infinite; }
  @keyframes ppBounce { 0%,100% { transform: translateY(0); opacity: 0.5; } 50% { transform: translateY(6px); opacity: 1; } }

  /* ---------------- SECTION: live capture demo ---------------- */
  .pp-section {
    position: relative;
    min-height: 100vh;
    padding: 110px 40px 90px;
    display: flex; flex-direction: column; align-items: center;
    background: #FAFBFD;
  }
  .pp-section-head { text-align: center; max-width: 620px; margin-bottom: 46px; }
  .pp-section-eyebrow { font-size: 11.5px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #00A97B; margin-bottom: 10px; }
  .pp-section-title { font-size: 32px; font-weight: 700; letter-spacing: -0.02em; color: #0F1016; margin: 0; }
  .pp-section-sub { font-size: 14.5px; color: #6B6F80; margin-top: 10px; line-height: 1.6; }

  .pp-demo-frame {
    width: 100%; max-width: 980px;
    border-radius: 24px; padding: 1.5px;
    background: linear-gradient(135deg, #DCE1FA, #E9DEF5, #D3F3E7);
    box-shadow: 0 30px 70px rgba(35,40,80,0.10);
  }
  .pp-demo-card {
    background: rgba(255,255,255,0.86); backdrop-filter: blur(16px);
    border-radius: 22.5px; padding: 26px;
    display: grid; grid-template-columns: 1fr 1fr; gap: 22px;
  }
  .pp-demo-col-label {
    display: flex; align-items: center; gap: 7px;
    font-size: 11px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
    color: #8A8FA3; margin-bottom: 12px;
  }

  .pp-transcript-panel {
    background: #101219; border-radius: 16px; padding: 18px;
    min-height: 250px; display: flex; flex-direction: column; gap: 12px;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.05);
  }
  .pp-rec-row { display: flex; align-items: center; gap: 7px; margin-bottom: 4px; }
  .pp-rec-dot { width: 6px; height: 6px; border-radius: 50%; background: #FF5A5A; box-shadow: 0 0 6px rgba(255,90,90,0.9); animation: ppRecPulse 1.4s ease-in-out infinite; }
  @keyframes ppRecPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
  .pp-rec-label { font-size: 10.5px; font-weight: 700; letter-spacing: 0.04em; color: #C7CAD6; text-transform: uppercase; }

  .pp-transcript-line { font-size: 12.5px; line-height: 1.6; color: #DCE0EC; }
  .pp-transcript-line .who { color: #6FE6C4; font-weight: 700; }
  .pp-caret { display: inline-block; width: 6px; height: 13px; background: #6FE6C4; margin-left: 2px; vertical-align: -2px; animation: ppBlink 0.9s steps(1) infinite; }
  @keyframes ppBlink { 0%,49% { opacity: 1; } 50%,100% { opacity: 0; } }

  .pp-points-panel { display: flex; flex-direction: column; gap: 9px; min-height: 250px; }
  .pp-point-item {
    display: flex; align-items: flex-start; gap: 9px;
    background: #F7F8FC; border: 1px solid #ECEEF7; border-radius: 12px;
    padding: 10px 12px; font-size: 12.5px; color: #363A48; line-height: 1.5;
    opacity: 0; transform: translateY(6px);
    animation: ppPointIn 0.45s cubic-bezier(0.16,1,0.3,1) forwards;
  }
  @keyframes ppPointIn { to { opacity: 1; transform: translateY(0); } }
  .pp-point-check {
    width: 18px; height: 18px; border-radius: 50%; flex-shrink: 0; margin-top: 1px;
    background: #17A56A; color: #fff; display: flex; align-items: center; justify-content: center;
  }

  .pp-gen-btn {
    margin-top: auto; display: flex; align-items: center; justify-content: center; gap: 8px;
    padding: 12px 16px; border-radius: 999px; font-size: 12.5px; font-weight: 700;
    color: #fff; background: linear-gradient(135deg, #4A63E8, #7C6BEA); border: none;
    box-shadow: 0 8px 20px rgba(74,99,232,0.3);
    opacity: 0.35; transition: opacity 0.3s ease;
  }
  .pp-gen-btn.ready { opacity: 1; animation: ppGenPulse 1.6s ease-in-out infinite; }
  @keyframes ppGenPulse { 0%,100% { box-shadow: 0 8px 20px rgba(74,99,232,0.3); } 50% { box-shadow: 0 10px 28px rgba(74,99,232,0.55); } }

  /* ---------------- FEATURE STRIP ---------------- */
  .pp-features {
    width: 100%; max-width: 980px; margin-top: 64px;
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px;
  }
  .pp-feature-card {
    background: #fff; border: 1px solid #EFF0F6; border-radius: 18px; padding: 22px;
    transition: all 0.2s ease;
  }
  .pp-feature-card:hover { transform: translateY(-3px); box-shadow: 0 14px 30px rgba(30,34,70,0.08); border-color: #E4E7F5; }
  .pp-feature-icon {
    width: 38px; height: 38px; border-radius: 11px; margin-bottom: 14px;
    display: flex; align-items: center; justify-content: center; color: #fff;
  }
  .pp-feature-title { font-size: 14.5px; font-weight: 700; color: #14151B; margin-bottom: 6px; }
  .pp-feature-text { font-size: 12.5px; color: #767A8C; line-height: 1.55; }

  .pp-footer {
    width: 100%; max-width: 980px; margin-top: 80px;
    padding-top: 24px; border-top: 1px solid #EEF0F6;
    display: flex; align-items: center; justify-content: space-between;
    font-size: 11.5px; color: #9599AA;
  }
`;

/* ---------------- scripted demo content ---------------- */

const TRANSCRIPT_LINES = [
  { who: "Alicia", text: "We need CSV export on the reports page." },
  { who: "Sri", text: "Also a dark mode toggle in settings, please." },
  { who: "Corbyn", text: "And let's lock the daily standup at 1 PM." },
];

const REQUIREMENT_POINTS = [
  "Export reports to CSV",
  "Dark mode toggle in settings",
  "Daily standup reminder — 1:00 PM",
];

/* ---------------- component ---------------- */

export default function HomePage({ onLogin, onRegister, onGetStarted }) {
  const sectionRef = useRef(null);
  const timeouts = useRef([]);
  const hasStarted = useRef(false);
  const [scrolled, setScrolled] = useState(false);

  const [lineIdx, setLineIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [pointsShown, setPointsShown] = useState(0);
  const [genReady, setGenReady] = useState(false);

  const clearTimers = () => {
    timeouts.current.forEach(clearTimeout);
    timeouts.current = [];
  };
  const after = (fn, ms) => {
    const id = setTimeout(fn, ms);
    timeouts.current.push(id);
  };

  const runDemo = useCallback(() => {
    clearTimers();
    setLineIdx(0);
    setCharIdx(0);
    setPointsShown(0);
    setGenReady(false);

    const typeLine = (li) => {
      if (li >= TRANSCRIPT_LINES.length) {
        after(() => revealPoint(0), 500);
        return;
      }
      setLineIdx(li);
      const text = TRANSCRIPT_LINES[li].text;
      let ci = 0;
      const step = () => {
        ci += 1;
        setCharIdx(ci);
        if (ci < text.length) {
          after(step, 18 + Math.random() * 14);
        } else {
          after(() => typeLine(li + 1), 420);
        }
      };
      after(step, 120);
    };

    const revealPoint = (pi) => {
      if (pi >= REQUIREMENT_POINTS.length) {
        after(() => setGenReady(true), 250);
        after(() => runDemo(), 4200); // loop
        return;
      }
      setPointsShown(pi + 1);
      after(() => revealPoint(pi + 1), 550);
    };

    typeLine(0);
  }, []);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasStarted.current) {
            hasStarted.current = true;
            runDemo();
          }
        });
      },
      { threshold: 0.35 }
    );
    io.observe(el);
    return () => { io.disconnect(); clearTimers(); };
  }, [runDemo]);

  const handleScroll = (e) => setScrolled(e.target.scrollTop > 40);

  const scrollToDemo = () => {
    sectionRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="pp-root" onScroll={handleScroll}>
      <style>{styles}</style>

      {/* ---------- NAV ---------- */}
      <div className="pp-nav" style={{
        background: scrolled ? "rgba(250,251,253,0.75)" : "transparent",
        backdropFilter: scrolled ? "blur(14px)" : "none",
        borderBottom: scrolled ? "1px solid #EEF0F6" : "1px solid transparent",
        transition: "all 0.25s ease",
      }}>
        <div className="pp-logo">
          <div className="pp-logo-mark"><Radio size={13} color="#fff" /></div>
          <span className="pp-display">ProtoPilot</span>
        </div>
        <div className="pp-nav-actions">
          <button className="pp-btn-ghost" onClick={onLogin}>
            <LogIn size={13} /> Log in
          </button>
          <button className="pp-btn-solid" onClick={onRegister}>
            <UserPlus size={13} /> Register
          </button>
        </div>
      </div>

      {/* ---------- HERO ---------- */}
      <section className="pp-hero">
        <div className="pp-hero-glow" />
        <div className="pp-hero-mint" />
        <HeroArcs />
        <div className="pp-hero-floor" />

        <div className="pp-hero-content">
          <div className="pp-eyebrow"><span className="pp-eyebrow-dot" /> Now recording your next meeting</div>
          <h1 className="pp-hero-title pp-display">
            Meetings in. <span className="pp-grad">Prototypes out.</span>
          </h1>
          <p className="pp-hero-sub">
            ProtoPilot listens to your meetings, transcribes the conversation, and lets AI
            agents turn what your team actually said into requirements — and a working
            prototype, before the call even ends.
          </p>
          <div className="pp-hero-cta">
            <button className="pp-btn-primary" onClick={onGetStarted}>
              Get started <ArrowRight size={15} />
            </button>
            <button className="pp-btn-secondary" onClick={scrollToDemo}>
              See how it works
            </button>
          </div>
        </div>

        <div className="pp-scroll-cue" onClick={scrollToDemo} style={{ cursor: "pointer" }}>
          Scroll
          <ChevronDown size={16} className="pp-scroll-cue-icon" />
        </div>
      </section>

      {/* ---------- LIVE CAPTURE DEMO ---------- */}
      <section className="pp-section" ref={sectionRef}>
        <div className="pp-section-head">
          <div className="pp-section-eyebrow">From talk to spec</div>
          <h2 className="pp-section-title pp-display">Watch it capture, live</h2>
          <p className="pp-section-sub">
            While your team talks, ProtoPilot transcribes in real time on the left —
            and quietly extracts requirements on the right, ready to accept and build.
          </p>
        </div>

        <div className="pp-demo-frame">
          <div className="pp-demo-card">
            {/* Transcript column */}
            <div>
              <div className="pp-demo-col-label"><Mic size={12} /> Live transcript</div>
              <div className="pp-transcript-panel">
                <div className="pp-rec-row">
                  <span className="pp-rec-dot" />
                  <span className="pp-rec-label">Recording</span>
                </div>
                {TRANSCRIPT_LINES.slice(0, lineIdx).map((l, i) => (
                  <div key={i} className="pp-transcript-line">
                    <span className="who">{l.who}:</span> {l.text}
                  </div>
                ))}
                {lineIdx < TRANSCRIPT_LINES.length && (
                  <div className="pp-transcript-line">
                    <span className="who">{TRANSCRIPT_LINES[lineIdx].who}:</span>{" "}
                    {TRANSCRIPT_LINES[lineIdx].text.slice(0, charIdx)}
                    <span className="pp-caret" />
                  </div>
                )}
              </div>
            </div>

            {/* Requirements column */}
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div className="pp-demo-col-label"><Sparkles size={12} /> Requirements captured</div>
              <div className="pp-points-panel">
                {REQUIREMENT_POINTS.slice(0, pointsShown).map((pt, i) => (
                  <div key={i} className="pp-point-item">
                    <span className="pp-point-check"><Check size={11} strokeWidth={2.5} /></span>
                    {pt}
                  </div>
                ))}
                <button className={`pp-gen-btn ${genReady ? "ready" : ""}`}>
                  <Rocket size={14} /> Generate Prototype
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ---------- FEATURES ---------- */}
        <div className="pp-features">
          <div className="pp-feature-card">
            <div className="pp-feature-icon" style={{ background: "linear-gradient(135deg,#14151B,#3A3D4C)" }}>
              <Mic size={17} />
            </div>
            <div className="pp-feature-title">Record &amp; transcribe</div>
            <div className="pp-feature-text">Every call is captured and transcribed automatically, no note-taking required.</div>
          </div>
          <div className="pp-feature-card">
            <div className="pp-feature-icon" style={{ background: "linear-gradient(135deg,#4A63E8,#7C6BEA)" }}>
              <FileText size={17} />
            </div>
            <div className="pp-feature-title">Extract requirements</div>
            <div className="pp-feature-text">AI agents pull out real requirements as they're said — you just accept or reject.</div>
          </div>
          <div className="pp-feature-card">
            <div className="pp-feature-icon" style={{ background: "linear-gradient(135deg,#00C88A,#00A9C9)" }}>
              <Layers size={17} />
            </div>
            <div className="pp-feature-title">Generate a prototype</div>
            <div className="pp-feature-text">Accepted points become a working prototype and docs, ready before the call ends.</div>
          </div>
        </div>

        <div className="pp-footer">
          <span>© 2026 ProtoPilot</span>
          <span>Built for teams who'd rather ship than write minutes.</span>
        </div>
      </section>
    </div>
  );
}

/* Soft sweeping arcs standing in for the tunnel-light architecture reference,
   built from pure SVG so nothing external is loaded. */
function HeroArcs() {
  return (
    <svg
      viewBox="0 0 1600 900"
      preserveAspectRatio="xMidYMid slice"
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.9 }}
    >
      <defs>
        <linearGradient id="ppArc1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="50%" stopColor="#ffffff" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#CBD5F5" stopOpacity="0.2" />
        </linearGradient>
        <linearGradient id="ppArc2" x1="0" y1="0" x2="1" y2="0.3">
          <stop offset="0%" stopColor="#D9E4FF" stopOpacity="0" />
          <stop offset="50%" stopColor="#B9C6F2" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#9FE9CE" stopOpacity="0.25" />
        </linearGradient>
        <filter id="ppBlurSoft"><feGaussianBlur stdDeviation="6" /></filter>
      </defs>
      <path d="M -100 120 C 350 -80, 700 -60, 1000 140 C 1250 300, 1500 260, 1750 60"
        fill="none" stroke="url(#ppArc1)" strokeWidth="26" filter="url(#ppBlurSoft)" />
      <path d="M -100 260 C 300 40, 760 30, 1050 260 C 1280 440, 1520 420, 1780 220"
        fill="none" stroke="url(#ppArc2)" strokeWidth="16" filter="url(#ppBlurSoft)" />
      <path d="M -100 40 C 320 -140, 640 -150, 900 30"
        fill="none" stroke="#ffffff" strokeOpacity="0.7" strokeWidth="3" filter="url(#ppBlurSoft)" />
      <path d="M 700 900 C 900 680, 1200 660, 1700 780"
        fill="none" stroke="url(#ppArc2)" strokeWidth="30" filter="url(#ppBlurSoft)" opacity="0.5" />
    </svg>
  );
}
