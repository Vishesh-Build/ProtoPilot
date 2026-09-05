import React, { useState, useEffect } from "react";
import {
  Radio, LayoutDashboard, Users, Cpu, GitBranch, Eye,
  Monitor, Tablet, Smartphone,
  RefreshCw, ExternalLink, ChevronRight,
  Layers, Clock, Sparkles, Copy, Check, Link2, AlertCircle, Download, Loader2,
} from "lucide-react";
import bgImage from "./assets/hero-bg.jpg";
import { meetingsApi } from "../lib/api.js";

/* ============================================================
   ProtoPilot — Prototype Viewer

   The backend's Prototype Builder agent produces ONE real,
   self-contained HTML file per meeting (not a set of named
   screens/routes) — so unlike the original mock, this shows that
   real file inside the device frame via a real iframe, and the
   right panel's "Export as code" downloads the actual ZIP from
   /meetings/{id}/export. Same visual shell as Dashboard / AI
   Workforce / Generation Pipeline.
   ============================================================ */

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');
  * { box-sizing: border-box; }
  html, body { height: 100%; width: 100%; margin: 0; padding: 0; }

  .pv-root {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
    position: fixed; inset: 0; width: 100%; height: 100%;
    display: flex; flex-direction: column;
    color: #14151B;
    background: #FBFBFE;
    overflow: hidden;
  }
  .pv-display { font-family: 'Space Grotesk', 'Inter', sans-serif; }

  .pv-bg-layer {
    position: fixed; inset: -60px; z-index: -1;
    background-image: url(${bgImage});
    background-size: cover; background-position: center;
    filter: blur(38px) saturate(1.05) brightness(1.02);
    transform: scale(1.08);
  }
  .pv-bg-tint {
    position: fixed; inset: 0; z-index: -1;
    background: linear-gradient(180deg, rgba(251,251,254,0.82) 0%, rgba(251,251,254,0.92) 100%);
  }

  .pv-nav {
    display: flex; align-items: center; gap: 22px;
    padding: 0 24px; height: 54px; flex-shrink: 0;
    background: rgba(255,255,255,0.7);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(236,238,245,0.8);
  }
  .pv-nav-mark {
    width: 24px; height: 24px; border-radius: 7px; margin-right: 6px;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }
  .pv-nav-mark img { width: 100%; height: 100%; object-fit: contain; }
  .pv-nav-tabs { display: flex; align-items: center; gap: 2px; flex: 1; overflow-x: auto; }
  .pv-nav-tab {
    display: flex; align-items: center; gap: 6px;
    font-size: 12.5px; font-weight: 600; color: #9599AA;
    padding: 7px 12px; border-radius: 8px; cursor: pointer; white-space: nowrap;
    transition: all 0.15s ease;
  }
  .pv-nav-tab:hover { color: #3A3C46; background: #F7F8FC; }
  .pv-nav-tab.active { color: #14151B; background: #EFF2FF; }
  .pv-nav-tab.active svg { color: #4A63E8; }
  .pv-nav-meta { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #767A8C; flex-shrink: 0; }

  .pv-body { flex: 1; display: flex; min-height: 0; }

  .pv-stage-wrap { flex: 1; min-width: 0; display: flex; flex-direction: column; padding: 20px 24px; overflow: hidden; }

  .pv-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-shrink: 0; }
  .pv-device-switch { display: flex; align-items: center; gap: 2px; background: rgba(255,255,255,0.75); border: 1px solid #E7E9F2; border-radius: 10px; padding: 3px; backdrop-filter: blur(10px); }
  .pv-device-btn {
    display: flex; align-items: center; justify-content: center;
    width: 30px; height: 26px; border-radius: 7px; cursor: pointer; color: #9599AA;
    transition: all 0.15s ease;
  }
  .pv-device-btn:hover { color: #3A3C46; }
  .pv-device-btn.active { background: #14151B; color: #fff; }

  .pv-url-bar {
    flex: 1; display: flex; align-items: center; gap: 8px;
    background: rgba(255,255,255,0.75); border: 1px solid #E7E9F2; border-radius: 999px;
    padding: 7px 14px; font-size: 12px; color: #767A8C; backdrop-filter: blur(10px);
    min-width: 0;
  }
  .pv-url-bar span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pv-url-dot { width: 6px; height: 6px; border-radius: 50%; background: #00C88A; flex-shrink: 0; }

  .pv-tool-btn {
    display: flex; align-items: center; gap: 6px;
    font-size: 12px; font-weight: 600; color: #3A3C46;
    background: rgba(255,255,255,0.75); border: 1px solid #E7E9F2; border-radius: 10px;
    padding: 7px 12px; cursor: pointer; transition: all 0.15s ease; flex-shrink: 0; backdrop-filter: blur(10px);
  }
  .pv-tool-btn:hover { background: #fff; border-color: #C9CCDA; }
  .pv-tool-btn.primary {
    color: #fff; background: linear-gradient(135deg, #4A63E8, #7C6BEA); border: none;
    box-shadow: 0 8px 18px rgba(74,99,232,0.28);
  }
  .pv-tool-btn.primary:hover { transform: translateY(-1px); }

  .pv-device-stage { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; overflow: auto; }

  .pv-device-frame {
    background: #fff; border-radius: 16px;
    box-shadow: 0 30px 70px rgba(35,40,80,0.14), 0 1px 0 rgba(255,255,255,0.6) inset;
    overflow: hidden; display: flex; flex-direction: column;
    transition: width 0.25s ease, height 0.25s ease;
  }
  .pv-device-frame.desktop { width: min(100%, 980px); height: min(100%, 620px); }
  .pv-device-frame.tablet { width: 520px; height: 660px; }
  .pv-device-frame.mobile { width: 320px; height: 640px; }

  .pv-device-chrome {
    flex-shrink: 0; height: 32px; display: flex; align-items: center; gap: 8px;
    padding: 0 12px; background: #F7F8FC; border-bottom: 1px solid #ECEEF5;
  }
  .pv-chrome-dot { width: 8px; height: 8px; border-radius: 50%; }
  .pv-device-screen { flex: 1; min-height: 0; }
  .pv-device-screen iframe { width: 100%; height: 100%; border: none; }

  .pv-empty-stage { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; color: #9599AA; font-size: 13px; text-align: center; padding: 40px; max-width: 380px; }

  .pv-side { width: 280px; flex-shrink: 0; overflow-y: auto; padding: 20px 20px 24px; }
  .pv-side::-webkit-scrollbar { width: 5px; }
  .pv-side::-webkit-scrollbar-thumb { background: #E4E7F0; border-radius: 8px; }

  .pv-panel {
    background: rgba(255,255,255,0.78);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(236,238,245,0.85); border-radius: 16px;
    padding: 18px 20px; margin-bottom: 16px;
  }
  .pv-panel-title {
    font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
    color: #9599AA; margin-bottom: 14px; display: flex; align-items: center; gap: 7px;
  }
  .pv-meta-row { display: flex; align-items: center; justify-content: space-between; font-size: 12.5px; padding: 6px 0; border-bottom: 1px solid #F3F4F8; }
  .pv-meta-row:last-child { border-bottom: none; }
  .pv-meta-label { color: #9599AA; }
  .pv-meta-value { color: #14151B; font-weight: 600; }

  .pv-export-btn {
    width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px;
    font-size: 12.5px; font-weight: 700; color: #fff;
    background: linear-gradient(135deg, #4A63E8, #7C6BEA); border: none; border-radius: 10px;
    padding: 11px; cursor: pointer; box-shadow: 0 8px 18px rgba(74,99,232,0.28); transition: transform 0.15s ease;
  }
  .pv-export-btn:hover { transform: translateY(-1px); }
  .pv-export-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

  .pv-agent-chip { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; color: #3A3C46; padding: 5px 0; }
  .pv-agent-dot { width: 7px; height: 7px; border-radius: 50%; background: #00C88A; flex-shrink: 0; }
`;

const DEVICES = [
  { id: "desktop", icon: Monitor, label: "Desktop" },
  { id: "tablet", icon: Tablet, label: "Tablet" },
  { id: "mobile", icon: Smartphone, label: "Mobile" },
];

const NAV_TABS = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Meeting Workspace", icon: Users },
  { label: "AI Workforce", icon: Cpu },
  { label: "Generation Pipeline", icon: GitBranch },
  { label: "Prototype Viewer", icon: Eye, active: true },
];

export default function PrototypeViewerPage({ meetingId, onOpenPipeline, onNavigate }) {
  const [device, setDevice] = useState("desktop");
  const [status, setStatus] = useState("loading"); // loading | no-meeting | not-ready | ready
  const [prototypeHtml, setPrototypeHtml] = useState(null);
  const [uiPlan, setUiPlan] = useState(null);
  const [exportReady, setExportReady] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!meetingId) { setStatus("no-meeting"); return; }
    let cancelled = false;

    meetingsApi.agentOutputs(meetingId)
      .then((data) => {
        if (cancelled) return;
        const outputs = data.agent_outputs || {};
        if (outputs.prototype) {
          setPrototypeHtml(outputs.prototype);
          setStatus("ready");
        } else if (outputs.ui) {
          setUiPlan(outputs.ui);
          setStatus("plan-only");
        } else {
          setStatus("not-ready");
        }
      })
      .catch(() => { if (!cancelled) setStatus("no-meeting"); });

    meetingsApi.exportStatus(meetingId)
      .then((data) => !cancelled && setExportReady(Boolean(data.ready_to_export)))
      .catch(() => {});

    return () => { cancelled = true; };
  }, [meetingId]);

  const openInNewTab = () => {
    const blob = new Blob([prototypeHtml], { type: "text/html" });
    window.open(URL.createObjectURL(blob), "_blank");
  };

  const handleExport = async () => {
    if (!meetingId) return;
    setDownloading(true);
    try {
      const res = await fetch(meetingsApi.exportUrl(meetingId), { credentials: "include" });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "protopilot-export.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.warn("Export failed:", err.message);
    } finally {
      setDownloading(false);
    }
  };

  const goTab = (label) => {
    if (label === "Dashboard") onNavigate?.("dashboard");
    if (label === "Meeting Workspace") onNavigate?.("live");
    if (label === "AI Workforce") onNavigate?.("workforce");
    if (label === "Generation Pipeline") (onOpenPipeline || onNavigate?.bind(null, "pipeline"))?.();
  };

  return (
    <div className="pv-root">
      <style>{styles}</style>
      <div className="pv-bg-layer" />
      <div className="pv-bg-tint" />

      <div className="pv-nav">
        <div className="pv-nav-mark"><img src="/logo.png" alt="ProtoPilot" /></div>
        <div className="pv-nav-tabs">
          {NAV_TABS.map((t) => (
            <div key={t.label} className={`pv-nav-tab ${t.active ? "active" : ""}`} onClick={() => goTab(t.label)}>
              <t.icon size={13} /> {t.label}
            </div>
          ))}
        </div>
        <div className="pv-nav-meta">
          <span>{meetingId ? meetingId.slice(0, 8) : "No meeting"}</span>
        </div>
      </div>

      <div className="pv-body">
        <div className="pv-stage-wrap">
          <div className="pv-toolbar">
            <div className="pv-device-switch">
              {DEVICES.map((d) => (
                <div key={d.id} className={`pv-device-btn ${device === d.id ? "active" : ""}`} onClick={() => setDevice(d.id)} title={d.label}>
                  <d.icon size={14} />
                </div>
              ))}
            </div>
            <div className="pv-url-bar">
              <span className="pv-url-dot" />
              <span>{status === "ready" ? "generated-prototype.html (local preview)" : "No prototype loaded"}</span>
            </div>
            {status === "ready" && (
              <>
                <div className="pv-tool-btn" title="Reload" onClick={() => window.location.reload()}><RefreshCw size={13} /></div>
                <div className="pv-tool-btn primary" onClick={openInNewTab}><ExternalLink size={13} /> Open full screen</div>
              </>
            )}
          </div>

          <div className="pv-device-stage">
            {status === "loading" && (
              <div className="pv-empty-stage"><Loader2 size={20} className="pv-spin" /> Loading…</div>
            )}
            {status === "no-meeting" && (
              <div className="pv-empty-stage">
                <AlertCircle size={22} color="#9599AA" />
                No active meeting — start one from the Dashboard first.
              </div>
            )}
            {status === "not-ready" && (
              <div className="pv-empty-stage">
                <Layers size={22} color="#9599AA" />
                <div style={{ fontWeight: 700, color: "#3A3C46", fontSize: 14 }}>No prototype generated yet</div>
                Run "Generate Prototype" from the Meeting Workspace — once the Prototype Builder agent finishes, the real clickable preview shows up here.
              </div>
            )}
            {status === "plan-only" && (
              <div className="pv-empty-stage" style={{ maxWidth: 520, textAlign: "left" }}>
                <div style={{ fontWeight: 700, color: "#B8860B", fontSize: 13 }}>Screen plan only — prototype builder hasn't finished</div>
                <div style={{ fontSize: 12.5, color: "#5B5F70", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{uiPlan}</div>
              </div>
            )}
            {status === "ready" && (
              <div className={`pv-device-frame ${device}`}>
                <div className="pv-device-chrome">
                  <span className="pv-chrome-dot" style={{ background: "#FF5F57" }} />
                  <span className="pv-chrome-dot" style={{ background: "#FEBC2E" }} />
                  <span className="pv-chrome-dot" style={{ background: "#28C840" }} />
                </div>
                <div className="pv-device-screen">
                  {/* This HTML is LLM-generated, i.e. untrusted, and we are inside
                      Electron. "allow-scripts allow-same-origin" together cancels
                      the sandbox out — the frame would share our origin and could
                      reach the parent DOM, our cookies and localStorage, or just
                      strip its own sandbox attribute. Scripts and forms are all a
                      clickable prototype needs; the origin stays opaque. */}
                  <iframe title="Generated prototype" srcDoc={prototypeHtml} sandbox="allow-scripts allow-forms" />
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="pv-side">
          <div className="pv-panel">
            <div className="pv-panel-title"><Sparkles size={12} /> Prototype info</div>
            <div className="pv-meta-row"><span className="pv-meta-label">Meeting</span><span className="pv-meta-value">{meetingId ? meetingId.slice(0, 8) : "—"}</span></div>
            <div className="pv-meta-row"><span className="pv-meta-label">Status</span><span className="pv-meta-value">{status === "ready" ? "Ready" : status === "plan-only" ? "Plan only" : status === "not-ready" ? "Not generated" : "—"}</span></div>
          </div>

          <div className="pv-panel">
            <div className="pv-panel-title"><Cpu size={12} /> Built by</div>
            <div className="pv-agent-chip"><span className="pv-agent-dot" /> UI — Interface Designer</div>
            <div className="pv-agent-chip"><span className="pv-agent-dot" /> API — API Layer</div>
            <div className="pv-agent-chip"><span className="pv-agent-dot" /> Proto — Prototype Builder</div>
            <div className="pv-tool-btn" style={{ width: "100%", justifyContent: "center", marginTop: 10 }} onClick={() => goTab("Generation Pipeline")}>
              <Link2 size={13} /> View build pipeline
            </div>
          </div>

          <div className="pv-panel">
            <div className="pv-panel-title">Export</div>
            <button className="pv-export-btn" onClick={handleExport} disabled={!exportReady || downloading}>
              {downloading ? <Loader2 size={14} className="pv-spin" /> : <Download size={14} />}
              {downloading ? "Preparing…" : "Export as code (ZIP)"}
            </button>
          </div>

          <div className="pv-panel" style={{ display: "flex", alignItems: "center", gap: 9, color: "#9599AA", fontSize: 11.5 }}>
            <Clock size={13} /> Reflects whatever the meeting has actually produced so far.
          </div>
        </div>
      </div>

      <style>{`.pv-spin { animation: pvSpin 1s linear infinite; } @keyframes pvSpin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}