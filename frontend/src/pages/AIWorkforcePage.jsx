import React, { useState } from "react";
import {
  Radio, Check, Loader2, Circle, ChevronRight, Terminal,
  LayoutDashboard, Users, Cpu, GitBranch, Eye,
  Settings, Bell, Command, Link2,
} from "lucide-react";
import bgImage from "./assets/hero-bg.jpg";

/* ============================================================
   ProtoPilot — AI Workforce

   Structure (rail + detail panel) is unchanged. What's real now:
   status/progress/output text come from `liveAgents`/`liveOutputs`
   (lifted up from GenerationPipelinePage's real WebSocket to
   /ws/meeting/{id}/generate — see App.jsx). No generation has run
   yet = every agent shown idle, matching an honest empty state.
   ============================================================ */

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  * { box-sizing: border-box; }
  html, body { height: 100%; width: 100%; margin: 0; padding: 0; }

  .wf-root {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
    position: fixed; inset: 0; width: 100%; height: 100%;
    display: flex; flex-direction: column;
    color: #14151B;
    background: #FBFBFE;
    overflow: hidden;
  }
  .wf-display { font-family: 'Space Grotesk', 'Inter', sans-serif; }

  .wf-bg-layer {
    position: fixed; inset: -60px; z-index: -1;
    background-image: url(${bgImage});
    background-size: cover; background-position: center;
    filter: blur(38px) saturate(1.05) brightness(1.02);
    transform: scale(1.08);
  }
  .wf-bg-tint {
    position: fixed; inset: 0; z-index: -1;
    background: linear-gradient(180deg, rgba(251,251,254,0.82) 0%, rgba(251,251,254,0.92) 100%);
  }
  .wf-mono { font-family: 'JetBrains Mono', monospace; }

  .wf-nav {
    display: flex; align-items: center; gap: 22px;
    padding: 0 24px; height: 54px; flex-shrink: 0;
    background: rgba(255,255,255,0.7);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(236,238,245,0.8);
  }
  .wf-nav-brand { display: flex; align-items: center; gap: 8px; margin-right: 6px; }
  .wf-nav-mark {
    width: 24px; height: 24px; border-radius: 7px;
    background: linear-gradient(135deg, #00E6A8, #4A63E8);
    display: flex; align-items: center; justify-content: center;
  }
  .wf-nav-tabs { display: flex; align-items: center; gap: 2px; flex: 1; overflow-x: auto; }
  .wf-nav-tab {
    display: flex; align-items: center; gap: 6px;
    font-size: 12.5px; font-weight: 600; color: #9599AA;
    padding: 7px 12px; border-radius: 8px; cursor: pointer; white-space: nowrap;
    transition: all 0.15s ease;
  }
  .wf-nav-tab:hover { color: #3A3C46; background: #F7F8FC; }
  .wf-nav-tab.active { color: #14151B; background: #EFF2FF; }
  .wf-nav-tab.active svg { color: #4A63E8; }
  .wf-nav-meta { display: flex; align-items: center; gap: 14px; font-size: 12px; color: #767A8C; flex-shrink: 0; }
  .wf-nav-pill { display: flex; align-items: center; gap: 6px; font-weight: 600; }
  .wf-dot { width: 6px; height: 6px; border-radius: 50%; background: #00C88A; box-shadow: 0 0 0 3px rgba(0,200,138,0.18); }

  .wf-body { flex: 1; display: flex; min-height: 0; }

  .wf-rail {
    width: 300px; flex-shrink: 0; overflow-y: auto;
    background: rgba(255,255,255,0.68);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid rgba(236,238,245,0.8);
    padding: 20px 16px 24px;
  }
  .wf-rail::-webkit-scrollbar { width: 5px; }
  .wf-rail::-webkit-scrollbar-thumb { background: #E4E7F0; border-radius: 8px; }

  .wf-rail-head { display: flex; align-items: center; gap: 8px; margin: 4px 6px 18px; }
  .wf-rail-title { font-size: 15px; font-weight: 700; }
  .wf-rail-icon {
    width: 26px; height: 26px; border-radius: 8px;
    background: linear-gradient(135deg, #4A63E8, #7C6BEA);
    display: flex; align-items: center; justify-content: center; color: #fff;
  }

  .wf-track { position: relative; padding-left: 4px; }
  .wf-thread {
    position: absolute; left: 23px; top: 22px; bottom: 22px; width: 2px;
    background: #E7E9F2;
  }

  .wf-node { position: relative; display: flex; gap: 12px; padding: 10px 8px; border-radius: 12px; cursor: pointer; margin-bottom: 2px; transition: background 0.15s ease; }
  .wf-node:hover { background: #F7F8FC; }
  .wf-node.selected { background: #F0F3FF; }

  .wf-node-avatar {
    position: relative; z-index: 1; flex-shrink: 0;
    width: 34px; height: 34px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700;
    background: #F0F1F6; color: #9599AA; border: 2px solid #fff;
    box-shadow: 0 0 0 1px #E7E9F2;
  }
  .wf-node-avatar.completed { background: #E4F8EF; color: #17A56A; box-shadow: 0 0 0 1px #B8ECD4; }
  .wf-node-avatar.working, .wf-node-avatar.thinking { background: #FFF6E0; color: #B8860B; box-shadow: 0 0 0 1px #F5DFA0; }
  .wf-node-avatar.idle { background: #F0F1F6; color: #ABAFC0; box-shadow: 0 0 0 1px #E7E9F2; }
  .wf-node-avatar.failed { background: #FDF3F3; color: #E14B4B; box-shadow: 0 0 0 1px #F5D9D9; }

  .wf-node-body { flex: 1; min-width: 0; padding-top: 1px; }
  .wf-node-top { display: flex; align-items: center; justify-content: between; gap: 6px; }
  .wf-node-name { font-size: 13px; font-weight: 700; color: #14151B; }
  .wf-node-role { font-size: 11px; color: #9599AA; margin-top: 1px; }

  .wf-node-status-row { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
  .wf-node-status { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; }
  .wf-node-status.completed { color: #17A56A; }
  .wf-node-status.working, .wf-node-status.thinking { color: #B8860B; }
  .wf-node-status.idle { color: #ABAFC0; }
  .wf-node-status.failed { color: #E14B4B; }
  .wf-node-pct { font-size: 10.5px; color: #ABAFC0; font-weight: 600; }

  .wf-node-bar { height: 4px; border-radius: 3px; background: #EFF1F7; margin-top: 6px; overflow: hidden; }
  .wf-node-bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
  .wf-node-bar-fill.completed { background: linear-gradient(90deg, #00C88A, #17D89A); }
  .wf-node-bar-fill.working, .wf-node-bar-fill.thinking { background: linear-gradient(90deg, #F0B429, #F7CA5E); }
  .wf-node-bar-fill.idle { background: #E4E7F0; }
  .wf-node-bar-fill.failed { background: #E14B4B; }

  .wf-node-deps { display: flex; align-items: center; gap: 4px; font-size: 10.5px; color: #ABAFC0; margin-top: 7px; }

  .wf-detail { flex: 1; min-width: 0; overflow-y: auto; padding: 28px 36px 40px; }
  .wf-detail::-webkit-scrollbar { width: 6px; }
  .wf-detail::-webkit-scrollbar-thumb { background: #E4E7F0; border-radius: 8px; }

  .wf-detail-head { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 26px; }
  .wf-detail-who { display: flex; align-items: center; gap: 14px; }
  .wf-detail-avatar {
    width: 46px; height: 46px; border-radius: 13px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 700; color: #fff;
  }
  .wf-detail-name { font-size: 19px; font-weight: 700; }
  .wf-detail-role { font-size: 12.5px; color: #767A8C; margin-top: 2px; }
  .wf-status-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 11.5px; font-weight: 700; padding: 5px 11px; border-radius: 999px;
  }
  .wf-status-badge.completed { color: #17A56A; background: #E4F8EF; }
  .wf-status-badge.working, .wf-status-badge.thinking { color: #B8860B; background: #FFF6E0; }
  .wf-status-badge.idle { color: #9599AA; background: #F0F1F6; }
  .wf-status-badge.failed { color: #E14B4B; background: #FDF3F3; }

  .wf-progress-ring-wrap { display: flex; align-items: center; gap: 10px; }
  .wf-progress-num { font-size: 22px; font-weight: 700; font-family: 'Space Grotesk', sans-serif; }
  .wf-progress-label { font-size: 10.5px; color: #9599AA; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }

  .wf-panel {
    background: rgba(255,255,255,0.76);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(236,238,245,0.85); border-radius: 16px;
    padding: 20px 22px; margin-bottom: 16px;
  }
  .wf-panel-title {
    font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
    color: #9599AA; margin-bottom: 14px; display: flex; align-items: center; gap: 7px;
  }

  .wf-current-callout {
    display: flex; align-items: center; gap: 10px;
    background: #FFF9EC; border: 1px solid #F5E3B3; border-radius: 12px;
    padding: 11px 14px; font-size: 12.5px; color: #8A6300; font-weight: 600; margin-bottom: 16px;
  }

  .wf-log-box {
    background: #14151B; border-radius: 14px; padding: 16px 18px;
    max-height: 320px; overflow-y: auto;
  }
  .wf-log-box::-webkit-scrollbar { width: 5px; }
  .wf-log-box::-webkit-scrollbar-thumb { background: #34364A; border-radius: 8px; }
  .wf-log-line { font-size: 12px; line-height: 1.7; color: #A9AEC4; white-space: pre-wrap; }

  .wf-empty-note { font-size: 12.5px; color: #ABAFC0; font-style: italic; }

  .wf-deps-row { display: flex; flex-wrap: wrap; gap: 8px; }
  .wf-dep-chip {
    display: flex; align-items: center; gap: 6px;
    font-size: 12px; font-weight: 600; color: #3A3C46;
    background: #F7F8FC; border: 1px solid #E7E9F2; border-radius: 999px; padding: 6px 12px 6px 8px;
  }
  .wf-dep-chip-avatar {
    width: 18px; height: 18px; border-radius: 6px; font-size: 8.5px; font-weight: 700;
    display: flex; align-items: center; justify-content: center; color: #fff;
  }

  .wf-spin { animation: wfSpin 1s linear infinite; }
  @keyframes wfSpin { to { transform: rotate(360deg); } }
`;

const AGENT_COLORS = {
  PM: "#4A63E8", AR: "#7C6BEA", DB: "#4A63E8", AP: "#00A87C",
  UI: "#E0509C", BA: "#4A63E8", QA: "#B8860B", DE: "#767A8C", PR: "#767A8C",
};

// Backend agent ids (app/agents/definitions.py) mapped to this UI's display info.
const AGENT_TEMPLATE = [
  { id: "pm", initials: "PM", name: "PM", role: "Product Manager", deps: [] },
  { id: "architect", initials: "AR", name: "Architect", role: "System Architect", deps: ["PM"] },
  { id: "database", initials: "DB", name: "DB", role: "Database Designer", deps: ["Architect"] },
  { id: "api", initials: "AP", name: "API", role: "API Layer", deps: ["DB"] },
  { id: "ui", initials: "UI", name: "UI", role: "Interface Designer", deps: ["API"] },
  { id: "backend", initials: "BA", name: "Backend", role: "Backend Logic", deps: ["API"] },
  { id: "qa", initials: "QA", name: "QA", role: "Quality Assurance", deps: ["UI", "Backend"] },
  { id: "devops", initials: "DE", name: "DevOps", role: "Deployment", deps: ["QA"] },
  { id: "prototype", initials: "PR", name: "Proto", role: "Prototype Builder", deps: ["UI", "API", "DB"] },
];

const NAV_TABS = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Meeting Workspace", icon: Users },
  { label: "AI Workforce", icon: Cpu, active: true },
  { label: "Generation Pipeline", icon: GitBranch },
  { label: "Prototype Viewer", icon: Eye },
];

export default function AIWorkforcePage({ liveAgents = {}, liveOutputs = {}, onNavigate }) {
  const [selectedId, setSelectedId] = useState("architect");

  const merged = AGENT_TEMPLATE.map((t) => ({
    ...t,
    status: liveAgents[t.id]?.status || "idle",
    progress: liveAgents[t.id]?.progress ?? 0,
    output: liveOutputs[t.id],
  }));
  const agentLookup = Object.fromEntries(merged.map((a) => [a.id, a]));
  const agent = agentLookup[selectedId] || merged[0];

  const completedCount = merged.filter((a) => a.status === "completed").length;
  const activeCount = merged.filter((a) => a.status !== "idle").length;

  return (
    <div className="wf-root">
      <style>{styles}</style>
      <div className="wf-bg-layer" />
      <div className="wf-bg-tint" />

      <div className="wf-nav">
        <div className="wf-nav-brand">
          <div className="wf-nav-mark"><Radio size={12} color="#fff" /></div>
        </div>
        <div className="wf-nav-tabs">
          {NAV_TABS.map((t) => (
            <div
              key={t.label}
              className={`wf-nav-tab ${t.active ? "active" : ""}`}
              onClick={() => {
                if (t.label === "Dashboard") onNavigate?.("dashboard");
                if (t.label === "Meeting Workspace") onNavigate?.("live");
                if (t.label === "Generation Pipeline") onNavigate?.("pipeline");
                if (t.label === "Prototype Viewer") onNavigate?.("viewer");
              }}
            >
              <t.icon size={13} /> {t.label}
            </div>
          ))}
        </div>
        <div className="wf-nav-meta">
          <span>{completedCount}/{merged.length} completed</span>
          {activeCount > 0 && <span className="wf-nav-pill"><span className="wf-dot" />{activeCount} active</span>}
        </div>
      </div>

      <div className="wf-body">
        <div className="wf-rail">
          <div className="wf-rail-head">
            <div className="wf-rail-icon"><Cpu size={13} /></div>
            <span className="wf-rail-title wf-display">AI Workforce</span>
          </div>

          <div className="wf-track">
            <div className="wf-thread" />
            {merged.map((a) => (
              <div
                key={a.id}
                className={`wf-node ${selectedId === a.id ? "selected" : ""}`}
                onClick={() => setSelectedId(a.id)}
              >
                <div className={`wf-node-avatar ${a.status}`}>
                  {a.status === "completed" ? <Check size={14} /> : a.status === "working" || a.status === "thinking" ? <Loader2 size={14} className="wf-spin" /> : a.initials}
                </div>
                <div className="wf-node-body">
                  <div className="wf-node-top">
                    <span className="wf-node-name">{a.name}</span>
                  </div>
                  <div className="wf-node-role">{a.role}</div>
                  <div className="wf-node-status-row">
                    <span className={`wf-node-status ${a.status}`}>
                      {a.status === "completed" ? "Completed" : a.status === "failed" ? "Failed" : a.status !== "idle" ? "Working" : "Idle"}
                    </span>
                    <span className="wf-node-pct">{a.progress}%</span>
                  </div>
                  <div className="wf-node-bar"><div className={`wf-node-bar-fill ${a.status}`} style={{ width: `${a.progress}%` }} /></div>
                  {a.deps.length > 0 && (
                    <div className="wf-node-deps"><Link2 size={10} /> depends on {a.deps.join(", ")}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="wf-detail">
          <div className="wf-detail-head">
            <div className="wf-detail-who">
              <div className="wf-detail-avatar" style={{ background: AGENT_COLORS[agent.initials] }}>{agent.initials}</div>
              <div>
                <div className="wf-detail-name wf-display">{agent.name}</div>
                <div className="wf-detail-role">{agent.role}</div>
              </div>
              <span className={`wf-status-badge ${agent.status}`}>
                {agent.status === "completed" ? <Check size={12} /> : agent.status !== "idle" ? <Loader2 size={12} className="wf-spin" /> : <Circle size={12} />}
                {agent.status === "completed" ? "Completed" : agent.status === "failed" ? "Failed" : agent.status !== "idle" ? "Working" : "Idle"}
              </span>
            </div>
            <div className="wf-progress-ring-wrap">
              <div style={{ textAlign: "right" }}>
                <div className="wf-progress-num wf-display">{agent.progress}%</div>
                <div className="wf-progress-label">Progress</div>
              </div>
            </div>
          </div>

          {agent.status !== "idle" && agent.status !== "completed" && (
            <div className="wf-current-callout">
              <Loader2 size={14} className="wf-spin" /> Right now: {agent.status === "thinking" ? "reading input from dependencies" : "generating output"}
            </div>
          )}

          <div className="wf-panel">
            <div className="wf-panel-title"><Terminal size={12} /> Output</div>
            <div className="wf-log-box wf-mono">
              {agent.status === "idle" && (
                <div className="wf-log-line" style={{ color: "#5B5F70" }}>Waiting for dependencies to complete before starting…</div>
              )}
              {(agent.status === "working" || agent.status === "thinking") && (
                <div className="wf-log-line" style={{ color: "#6FE6C4" }}>{agent.status === "thinking" ? "Reading input from dependencies…" : "Generating output…"}</div>
              )}
              {agent.status === "failed" && (
                <div className="wf-log-line" style={{ color: "#FF6B6B" }}>Failed — check the backend server logs for details.</div>
              )}
              {agent.status === "completed" && agent.id === "prototype" && (
                <div className="wf-log-line" style={{ color: "#6FE6C4" }}>Generated a real HTML prototype — open Prototype Viewer to see it.</div>
              )}
              {agent.status === "completed" && agent.id !== "prototype" && (
                <div className="wf-log-line">{agent.output || "Completed — no output text recorded."}</div>
              )}
            </div>
          </div>

          {agent.deps.length > 0 && (
            <div className="wf-panel">
              <div className="wf-panel-title"><Link2 size={12} /> Dependencies</div>
              <div className="wf-deps-row">
                {agent.deps.map((depName) => {
                  const depAgent = merged.find((a) => a.name === depName);
                  return (
                    <div className="wf-dep-chip" key={depName}>
                      <span className="wf-dep-chip-avatar" style={{ background: depAgent ? AGENT_COLORS[depAgent.initials] : "#9599AA" }}>
                        {depAgent ? depAgent.initials : "?"}
                      </span>
                      {depName}
                      {depAgent && depAgent.status === "completed" && <Check size={11} color="#17A56A" />}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
