import React, { useState, useEffect, useRef } from "react";
import {
  Radio, Check, Loader2, Circle, ChevronRight, Terminal, Link2,
  LayoutDashboard, Users, Cpu, GitBranch, Eye,
  Settings, Bell, Command, FileCode2, Boxes, Rocket, Clock, Package, AlertCircle,
} from "lucide-react";
import bgImage from "./assets/hero-bg.jpg";
import { meetingsApi } from "../lib/api.js";

/* ============================================================
   ProtoPilot — Generation Pipeline

   Real 9-agent pipeline (matches app/agents/definitions.py exactly:
   PM -> Architect -> Database -> API -> {UI, Backend} -> QA -> DevOps
   -> Prototype), driven by the actual backend WebSocket at
   /ws/meeting/{id}/generate. Opening this page IS what starts a
   real generation run — connecting the socket is what triggers the
   backend pipeline (see app/ws/generate.py).
   ============================================================ */

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  * { box-sizing: border-box; }
  html, body { height: 100%; width: 100%; margin: 0; padding: 0; }

  .gp-root {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
    position: fixed; inset: 0; width: 100%; height: 100%;
    display: flex; flex-direction: column;
    color: #14151B;
    background: #FBFBFE;
    overflow: hidden;
  }
  .gp-display { font-family: 'Space Grotesk', 'Inter', sans-serif; }

  .gp-bg-layer {
    position: fixed; inset: -60px; z-index: -1;
    background-image: url(${bgImage});
    background-size: cover; background-position: center;
    filter: blur(38px) saturate(1.05) brightness(1.02);
    transform: scale(1.08);
  }
  .gp-bg-tint {
    position: fixed; inset: 0; z-index: -1;
    background: linear-gradient(180deg, rgba(251,251,254,0.82) 0%, rgba(251,251,254,0.92) 100%);
  }
  .gp-mono { font-family: 'JetBrains Mono', monospace; }

  .gp-nav {
    display: flex; align-items: center; gap: 22px;
    padding: 0 24px; height: 54px; flex-shrink: 0;
    background: rgba(255,255,255,0.7);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(236,238,245,0.8);
  }
  .gp-nav-brand { display: flex; align-items: center; gap: 8px; margin-right: 6px; }
  .gp-nav-mark {
    width: 24px; height: 24px; border-radius: 7px;
    background: linear-gradient(135deg, #00E6A8, #4A63E8);
    display: flex; align-items: center; justify-content: center;
  }
  .gp-nav-tabs { display: flex; align-items: center; gap: 2px; flex: 1; overflow-x: auto; }
  .gp-nav-tab {
    display: flex; align-items: center; gap: 6px;
    font-size: 12.5px; font-weight: 600; color: #9599AA;
    padding: 7px 12px; border-radius: 8px; cursor: pointer; white-space: nowrap;
    transition: all 0.15s ease;
  }
  .gp-nav-tab:hover { color: #3A3C46; background: #F7F8FC; }
  .gp-nav-tab.active { color: #14151B; background: #EFF2FF; }
  .gp-nav-tab.active svg { color: #4A63E8; }
  .gp-nav-meta { display: flex; align-items: center; gap: 14px; font-size: 12px; color: #767A8C; flex-shrink: 0; }
  .gp-nav-pill { display: flex; align-items: center; gap: 6px; font-weight: 600; }
  .gp-dot { width: 6px; height: 6px; border-radius: 50%; background: #00C88A; box-shadow: 0 0 0 3px rgba(0,200,138,0.18); }

  .gp-body { flex: 1; display: flex; min-height: 0; }

  .gp-rail {
    width: 300px; flex-shrink: 0; overflow-y: auto;
    background: rgba(255,255,255,0.68);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid rgba(236,238,245,0.8);
    padding: 20px 16px 24px;
  }
  .gp-rail::-webkit-scrollbar { width: 5px; }
  .gp-rail::-webkit-scrollbar-thumb { background: #E4E7F0; border-radius: 8px; }

  .gp-rail-head { display: flex; align-items: center; gap: 8px; margin: 4px 6px 18px; }
  .gp-rail-title { font-size: 15px; font-weight: 700; }
  .gp-rail-icon {
    width: 26px; height: 26px; border-radius: 8px;
    background: linear-gradient(135deg, #4A63E8, #7C6BEA);
    display: flex; align-items: center; justify-content: center; color: #fff;
  }

  .gp-track { position: relative; padding-left: 4px; }
  .gp-thread { position: absolute; left: 23px; top: 22px; bottom: 22px; width: 2px; background: #E7E9F2; }

  .gp-node { position: relative; display: flex; gap: 12px; padding: 10px 8px; border-radius: 12px; cursor: pointer; margin-bottom: 2px; transition: background 0.15s ease; }
  .gp-node:hover { background: #F7F8FC; }
  .gp-node.selected { background: #F0F3FF; }

  .gp-node-avatar {
    position: relative; z-index: 1; flex-shrink: 0;
    width: 34px; height: 34px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700;
    background: #F0F1F6; color: #9599AA; border: 2px solid #fff;
    box-shadow: 0 0 0 1px #E7E9F2;
  }
  .gp-node-avatar.completed { background: #E4F8EF; color: #17A56A; box-shadow: 0 0 0 1px #B8ECD4; }
  .gp-node-avatar.working, .gp-node-avatar.thinking { background: #FFF6E0; color: #B8860B; box-shadow: 0 0 0 1px #F5DFA0; }
  .gp-node-avatar.idle { background: #F0F1F6; color: #ABAFC0; box-shadow: 0 0 0 1px #E7E9F2; }
  .gp-node-avatar.failed { background: #FDF3F3; color: #E14B4B; box-shadow: 0 0 0 1px #F5D9D9; }

  .gp-node-body { flex: 1; min-width: 0; padding-top: 1px; }
  .gp-node-name { font-size: 13px; font-weight: 700; color: #14151B; }
  .gp-node-role { font-size: 11px; color: #9599AA; margin-top: 1px; }

  .gp-node-status-row { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
  .gp-node-status { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; }
  .gp-node-status.completed { color: #17A56A; }
  .gp-node-status.working, .gp-node-status.thinking { color: #B8860B; }
  .gp-node-status.idle { color: #ABAFC0; }
  .gp-node-status.failed { color: #E14B4B; }
  .gp-node-pct { font-size: 10.5px; color: #ABAFC0; font-weight: 600; }

  .gp-node-bar { height: 4px; border-radius: 3px; background: #EFF1F7; margin-top: 6px; overflow: hidden; }
  .gp-node-bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
  .gp-node-bar-fill.completed { background: linear-gradient(90deg, #00C88A, #17D89A); }
  .gp-node-bar-fill.working, .gp-node-bar-fill.thinking { background: linear-gradient(90deg, #F0B429, #F7CA5E); }
  .gp-node-bar-fill.idle { background: #E4E7F0; }
  .gp-node-bar-fill.failed { background: #E14B4B; }

  .gp-node-deps { display: flex; align-items: center; gap: 4px; font-size: 10.5px; color: #ABAFC0; margin-top: 7px; }

  .gp-detail { flex: 1; min-width: 0; overflow-y: auto; padding: 28px 36px 40px; }
  .gp-detail::-webkit-scrollbar { width: 6px; }
  .gp-detail::-webkit-scrollbar-thumb { background: #E4E7F0; border-radius: 8px; }

  .gp-detail-head { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 26px; }
  .gp-detail-who { display: flex; align-items: center; gap: 14px; }
  .gp-detail-avatar {
    width: 46px; height: 46px; border-radius: 13px;
    display: flex; align-items: center; justify-content: center; color: #fff;
  }
  .gp-detail-name { font-size: 19px; font-weight: 700; }
  .gp-detail-role { font-size: 12.5px; color: #767A8C; margin-top: 2px; }
  .gp-status-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 11.5px; font-weight: 700; padding: 5px 11px; border-radius: 999px;
  }
  .gp-status-badge.completed { color: #17A56A; background: #E4F8EF; }
  .gp-status-badge.working, .gp-status-badge.thinking { color: #B8860B; background: #FFF6E0; }
  .gp-status-badge.idle { color: #9599AA; background: #F0F1F6; }
  .gp-status-badge.failed { color: #E14B4B; background: #FDF3F3; }

  .gp-progress-num { font-size: 22px; font-weight: 700; font-family: 'Space Grotesk', sans-serif; }
  .gp-progress-label { font-size: 10.5px; color: #9599AA; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }

  .gp-panel {
    background: rgba(255,255,255,0.76);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(236,238,245,0.85); border-radius: 16px;
    padding: 20px 22px; margin-bottom: 16px;
  }
  .gp-panel-title {
    font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
    color: #9599AA; margin-bottom: 14px; display: flex; align-items: center; gap: 7px;
  }

  .gp-current-callout {
    display: flex; align-items: center; gap: 10px;
    background: #FFF9EC; border: 1px solid #F5E3B3; border-radius: 12px;
    padding: 11px 14px; font-size: 12.5px; color: #8A6300; font-weight: 600; margin-bottom: 16px;
  }

  .gp-log-box { background: #14151B; border-radius: 14px; padding: 16px 18px; max-height: 320px; overflow-y: auto; }
  .gp-log-box::-webkit-scrollbar { width: 5px; }
  .gp-log-box::-webkit-scrollbar-thumb { background: #34364A; border-radius: 8px; }
  .gp-log-line { font-size: 12px; line-height: 1.7; color: #A9AEC4; white-space: pre-wrap; }

  .gp-empty-note { font-size: 12.5px; color: #ABAFC0; font-style: italic; }

  .gp-deps-row { display: flex; flex-wrap: wrap; gap: 8px; }
  .gp-dep-chip {
    display: flex; align-items: center; gap: 6px;
    font-size: 12px; font-weight: 600; color: #3A3C46;
    background: #F7F8FC; border: 1px solid #E7E9F2; border-radius: 999px; padding: 6px 12px 6px 8px;
  }
  .gp-dep-chip-avatar {
    width: 18px; height: 18px; border-radius: 6px; font-size: 8.5px; font-weight: 700;
    display: flex; align-items: center; justify-content: center; color: #fff;
  }

  .gp-spin { animation: gpSpin 1s linear infinite; }
  @keyframes gpSpin { to { transform: rotate(360deg); } }
`;

const STAGE_COLORS = {
  PM: "#4A63E8", AR: "#7C6BEA", DB: "#4A63E8", AP: "#00A87C",
  UI: "#E0509C", BA: "#4A63E8", QA: "#B8860B", DE: "#767A8C", PR: "#767A8C",
};

// Matches app/agents/definitions.py's actual dependency chain exactly.
const AGENT_TEMPLATE = [
  { id: "pm", initials: "PM", name: "PM", role: "Product Manager", deps: [], output: "PRD" },
  { id: "architect", initials: "AR", name: "Architect", role: "System Architect", deps: ["PM"], output: "Architecture doc" },
  { id: "database", initials: "DB", name: "Database", role: "Database Designer", deps: ["Architect"], output: "Database schema" },
  { id: "api", initials: "AP", name: "API", role: "API Layer", deps: ["Database"], output: "API endpoint list" },
  { id: "ui", initials: "UI", name: "UI", role: "Interface Designer", deps: ["API"], output: "Frontend screen plan" },
  { id: "backend", initials: "BA", name: "Backend", role: "Backend Logic", deps: ["API"], output: "Backend logic plan" },
  { id: "qa", initials: "QA", name: "QA", role: "Quality Assurance", deps: ["UI", "Backend"], output: "QA checklist" },
  { id: "devops", initials: "DE", name: "DevOps", role: "Deployment", deps: ["QA"], output: "Deployment guide" },
  { id: "prototype", initials: "PR", name: "Prototype", role: "Prototype Builder", deps: ["UI", "API", "Database"], output: "Clickable HTML prototype" },
];

const NAV_TABS = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Meeting Workspace", icon: Users },
  { label: "AI Workforce", icon: Cpu },
  { label: "Generation Pipeline", icon: GitBranch, active: true },
  { label: "Prototype Viewer", icon: Eye },
];

export default function GenerationPipelinePage({ meetingId, intent = "view", onNavigate, onGenerationUpdate }) {
  const [selectedId, setSelectedId] = useState("prototype");
  const [agents, setAgents] = useState({});
  const [outputs, setOutputs] = useState({});
  const [logs, setLogs] = useState({});
  const [pipelineError, setPipelineError] = useState(null);
  const [finished, setFinished] = useState(false);
  // View mode only: the meeting has no generated outputs yet, so there's
  // nothing to replay. Distinct from an in-progress run.
  const [viewEmpty, setViewEmpty] = useState(false);
  const socketRef = useRef(null);
  // Mirrors `finished` so the socket close/error handlers can read it without
  // re-binding — the handlers are created once per mount, and a stale closure
  // would otherwise claim "lost connection" after a clean finish.
  const finishedRef = useRef(false);

  // What opening this page does depends on WHY it was opened:
  //   • "view" — replay the already-built outputs over plain HTTP. The
  //     generate socket is never opened (opening it is a server-side trigger),
  //     so merely navigating in can never start or re-run a paid pipeline.
  //   • "run"  — the host pressed Generate/Regenerate. Connecting this socket
  //     with force=1 IS what starts the real backend pipeline
  //     (app/ws/generate.py), re-running over the currently-approved
  //     requirements (so a requirement approved after the last build is
  //     picked up).
  // Runs once per mount, not per render.
  useEffect(() => {
    if (!meetingId) return undefined;

    if (intent !== "run") {
      let cancelled = false;
      meetingsApi.agentOutputs(meetingId)
        .then((data) => {
          if (cancelled) return;
          const outs = data.agent_outputs || {};
          if (Object.keys(outs).length === 0) {
            setViewEmpty(true);
            return;
          }
          setOutputs(outs);
          setAgents(
            Object.fromEntries(
              Object.keys(outs).map((id) => [id, { status: "completed", progress: 100 }]),
            ),
          );
          finishedRef.current = true;
          setFinished(true);
        })
        .catch(() => { if (!cancelled) setViewEmpty(true); });
      return () => { cancelled = true; };
    }

    const socket = new WebSocket(meetingsApi.generateSocketUrl(meetingId, { force: true }));
    socketRef.current = socket;

    socket.onmessage = (event) => {
      let data;
      try { data = JSON.parse(event.data); } catch { return; }

      if (data.type === "agent_update") {
        setAgents((prev) => ({ ...prev, [data.agent]: { status: data.status, progress: data.progress } }));
      } else if (data.type === "agent_output") {
        setOutputs((prev) => ({ ...prev, [data.agent]: data.output }));
      } else if (data.type === "agent_log") {
        const stamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
        setLogs((prev) => {
          const existing = prev[data.agent] || [];
          return { ...prev, [data.agent]: [...existing, `[${stamp}] ${data.message}`] };
        });
      } else if (data.type === "pipeline_complete") {
        finishedRef.current = true;
        setFinished(true);
      } else if (data.type === "pipeline_failed") {
        // The run is OVER — an agent failed, and the backend says which. This
        // must not produce "Prototype ready" below; the banner carries the
        // truth instead.
        finishedRef.current = true;
        setFinished(true);
        setPipelineError(data.message || "Generation finished with failures.");
      } else if (data.type === "error") {
        setPipelineError(data.message);
      }
    };
    // onerror fires (followed by onclose) in a couple of innocent cases — for
    // example React dev's StrictMode double-mount closes the first socket
    // while it is still CONNECTING, which the spec counts as a failure. Once
    // the verdict (pipeline_complete / pipeline_failed) is in, the connection
    // dying means nothing, so both handlers stay silent.
    socket.onerror = () => {
      if (!finishedRef.current) setPipelineError((e) => e || "Lost connection to the generation pipeline.");
    };
    socket.onclose = () => {
      // The server closes the socket when a run ends. If no verdict arrived,
      // that is a genuine disconnection — never leave a "Build running"
      // spinner forever.
      if (!finishedRef.current) setPipelineError((e) => e || "Lost connection to the generation pipeline.");
    };

    return () => {
      // Detach BEFORE closing. React dev's StrictMode double-mount closes this
      // socket while CONNECTING, and per spec a close during CONNECTING fires
      // error then close — a dying mount's socket must not be allowed to paint
      // "Lost connection" over the live socket that replaced it.
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      socket.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingId, intent]);

  // Lift the live state up to App.jsx so AI Workforce can show it too.
  useEffect(() => {
    onGenerationUpdate?.(agents, outputs, logs);
  }, [agents, outputs, logs, onGenerationUpdate]);

  const merged = AGENT_TEMPLATE.map((t) => ({
    ...t,
    status: agents[t.id]?.status || "idle",
    progress: agents[t.id]?.progress ?? 0,
    realOutput: outputs[t.id],
    realLogs: logs[t.id] || [],
  }));
  const agentLookup = Object.fromEntries(merged.map((a) => [a.id, a]));
  const stage = agentLookup[selectedId] || merged[0];

  const completedCount = merged.filter((s) => s.status === "completed").length;
  const failedCount = merged.filter((s) => s.status === "failed").length;
  const overallPct = Math.round(merged.reduce((sum, s) => sum + s.progress, 0) / merged.length);

  if (!meetingId) {
    return (
      <div className="gp-root" style={{ alignItems: "center", justifyContent: "center" }}>
        <style>{styles}</style>
        <div style={{ textAlign: "center", color: "#767A8C", fontSize: 13 }}>
          No active meeting — start one from the Dashboard first.
        </div>
      </div>
    );
  }

  // Viewed (not run) for a meeting that hasn't generated anything yet — there
  // is nothing to replay, so guide the host back rather than show 9 idle nodes.
  if (viewEmpty) {
    return (
      <div className="gp-root" style={{ alignItems: "center", justifyContent: "center" }}>
        <style>{styles}</style>
        <div className="gp-bg-layer" />
        <div className="gp-bg-tint" />
        <div style={{ textAlign: "center", color: "#767A8C", fontSize: 13, display: "flex", flexDirection: "column", alignItems: "center", gap: 14, maxWidth: 380, padding: 20 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#3A3C46" }} className="gp-display">Nothing generated yet</div>
          <div style={{ lineHeight: 1.6 }}>Head back to the meeting and press <b>Generate Prototype</b> once a few requirements are approved.</div>
          <button
            onClick={() => onNavigate?.("live")}
            style={{ marginTop: 4, background: "linear-gradient(135deg,#4A63E8,#7C6BEA)", color: "#fff", border: "none", borderRadius: 999, padding: "9px 18px", fontSize: 12.5, fontWeight: 700, cursor: "pointer" }}
          >
            Back to meeting
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="gp-root">
      <style>{styles}</style>
      <div className="gp-bg-layer" />
      <div className="gp-bg-tint" />

      <div className="gp-nav">
        <div className="gp-nav-brand">
          <div className="gp-nav-mark"><Radio size={12} color="#fff" /></div>
        </div>
        <div className="gp-nav-tabs">
          {NAV_TABS.map((t) => (
            <div
              key={t.label}
              className={`gp-nav-tab ${t.active ? "active" : ""}`}
              onClick={() => {
                if (t.label === "Dashboard") onNavigate?.("dashboard");
                if (t.label === "Meeting Workspace") onNavigate?.("live");
                if (t.label === "AI Workforce") onNavigate?.("workforce");
                if (t.label === "Prototype Viewer") onNavigate?.("viewer");
              }}
            >
              <t.icon size={13} /> {t.label}
            </div>
          ))}
        </div>
        <div className="gp-nav-meta">
          <span>
            {completedCount}/{merged.length} stages complete
            {failedCount > 0 && <span style={{ color: "#E14B4B" }}> · {failedCount} failed</span>}
          </span>
          {!finished && !pipelineError && <span className="gp-nav-pill"><span className="gp-dot" />Build running</span>}
          {finished && failedCount > 0 && <span className="gp-nav-pill" style={{ color: "#E14B4B" }}>Build failed</span>}
        </div>
      </div>

      {pipelineError && (
        <div style={{ padding: "8px 20px", background: "#FDF3F3", borderBottom: "1px solid #F5D9D9", fontSize: 12, color: "#E14B4B", display: "flex", alignItems: "center", gap: 8 }}>
          <AlertCircle size={13} /> {pipelineError}
        </div>
      )}

      <div className="gp-body">
        <div className="gp-rail">
          <div className="gp-rail-head">
            <div className="gp-rail-icon"><Boxes size={13} /></div>
            <span className="gp-rail-title gp-display">Generation Pipeline</span>
          </div>

          <div className="gp-track">
            <div className="gp-thread" style={{ "--gp-thread-pct": `${overallPct}%` }} />
            {merged.map((s) => (
              <div
                key={s.id}
                className={`gp-node ${selectedId === s.id ? "selected" : ""}`}
                onClick={() => setSelectedId(s.id)}
              >
                <div className={`gp-node-avatar ${s.status}`}>
                  {s.status === "completed" ? <Check size={14} /> : s.status === "working" || s.status === "thinking" ? <Loader2 size={14} className="gp-spin" /> : s.initials}
                </div>
                <div className="gp-node-body">
                  <div className="gp-node-name">{s.name}</div>
                  <div className="gp-node-role">{s.role}</div>
                  <div className="gp-node-status-row">
                    <span className={`gp-node-status ${s.status}`}>
                      {s.status === "completed" ? "Completed" : s.status === "failed" ? "Failed" : s.status !== "idle" ? "Working" : "Idle"}
                    </span>
                    <span className="gp-node-pct">{s.progress}%</span>
                  </div>
                  <div className="gp-node-bar"><div className={`gp-node-bar-fill ${s.status}`} style={{ width: `${s.progress}%` }} /></div>
                  {s.deps.length > 0 && (
                    <div className="gp-node-deps"><Link2 size={10} /> depends on {s.deps.join(", ")}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="gp-detail">
          <div className="gp-detail-head">
            <div className="gp-detail-who">
              <div className="gp-detail-avatar" style={{ background: STAGE_COLORS[stage.initials] }}>
                <FileCode2 size={19} />
              </div>
              <div>
                <div className="gp-detail-name gp-display">{stage.name}</div>
                <div className="gp-detail-role">{stage.role}</div>
              </div>
              <span className={`gp-status-badge ${stage.status}`}>
                {stage.status === "completed" ? <Check size={12} /> : stage.status !== "idle" ? <Loader2 size={12} className="gp-spin" /> : <Circle size={12} />}
                {stage.status === "completed" ? "Completed" : stage.status === "failed" ? "Failed" : stage.status !== "idle" ? "Working" : "Idle"}
              </span>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="gp-progress-num gp-display">{stage.progress}%</div>
              <div className="gp-progress-label">Progress</div>
            </div>
          </div>

          <div className="gp-panel">
            <div className="gp-panel-title"><Package size={12} /> Expected output</div>
            <div style={{ fontSize: 13, color: "#3A3C46" }}>{stage.output}</div>
          </div>

          <div className="gp-panel">
            <div className="gp-panel-title"><Terminal size={12} /> Live output</div>
            <div className="gp-log-box gp-mono">
              {stage.realLogs.length > 0 ? (
                stage.realLogs.map((line, i) => (
                  <div key={i} className="gp-log-line">{line}</div>
                ))
              ) : (
                <>
                  {stage.status === "idle" && (
                    <div className="gp-log-line" style={{ color: "#5B5F70" }}>Waiting on dependencies...</div>
                  )}
                  {(stage.status === "working" || stage.status === "thinking") && (
                    <div className="gp-log-line" style={{ color: "#6FE6C4" }}>{stage.status === "thinking" ? "Reading input from dependencies..." : "Generating..."}</div>
                  )}
                  {stage.status === "completed" && stage.id !== "prototype" && (
                    <div className="gp-log-line">{stage.realOutput || "Completed."}</div>
                  )}
                  {stage.status === "completed" && stage.id === "prototype" && (
                    <div className="gp-log-line" style={{ color: "#6FE6C4" }}>Prototype generated — open Prototype Viewer to see it.</div>
                  )}
                  {stage.status === "failed" && (
                    <div className="gp-log-line" style={{ color: "#FF6B6B" }}>Failed — check the backend server logs.</div>
                  )}
                </>
              )}
            </div>
          </div>

          {stage.deps.length > 0 && (
            <div className="gp-panel">
              <div className="gp-panel-title"><Link2 size={12} /> Dependencies</div>
              <div className="gp-deps-row">
                {stage.deps.map((depName) => {
                  const depStage = merged.find((s) => s.name === depName);
                  return (
                    <div className="gp-dep-chip" key={depName}>
                      <span className="gp-dep-chip-avatar" style={{ background: depStage ? STAGE_COLORS[depStage.initials] : "#9599AA" }}>
                        {depStage && depStage.status === "completed" ? <Check size={10} color="#fff" /> : depStage?.initials}
                      </span>
                      {depName}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {finished && failedCount === 0 && (
            <div className="gp-panel" style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }} onClick={() => onNavigate?.("viewer")}>
              <Rocket size={14} color="#4A63E8" />
              <span style={{ fontSize: 12.5, fontWeight: 600 }}>Prototype ready — open it in Prototype Viewer.</span>
              <ChevronRight size={14} style={{ marginLeft: "auto" }} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
