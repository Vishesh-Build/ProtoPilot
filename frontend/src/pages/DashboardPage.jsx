import React, { useState, useEffect } from "react";
import {
  Radio, Plus, Mic, Play, Clock, ArrowRight, ChevronRight,
  LayoutDashboard, Users, Cpu, GitBranch, Eye,
  Settings, Bell, Command, CheckCircle2, Loader2, FileClock,
  Sparkles, Zap, Layers, TrendingUp, AlertCircle, LogIn, X, Trash2, Pencil,
} from "lucide-react";
import bgImage from "./assets/hero-bg.jpg";
import { meetingsApi } from "../lib/api.js";

/* ============================================================
   ProtoPilot — Dashboard

   Same shell/tokens as AI Workforce (fixed inset:0 fill, light
   brand palette, Space Grotesk + Inter). Stats, meeting history,
   and recent prototypes are now all real — pulled from GET
   /meetings on the real backend. An empty account correctly
   shows zeros, not fake demo numbers.
   ============================================================ */

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');
  * { box-sizing: border-box; }
  html, body { height: 100%; width: 100%; margin: 0; padding: 0; }

  .db-root {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
    position: fixed; inset: 0; width: 100%; height: 100%;
    display: flex; flex-direction: column;
    color: #14151B;
    background: #FBFBFE;
    overflow: hidden;
  }
  .db-display { font-family: 'Space Grotesk', 'Inter', sans-serif; }

  .db-bg-layer {
    position: fixed; inset: -60px; z-index: -1;
    background-image: url(${bgImage});
    background-size: cover; background-position: center;
    filter: blur(38px) saturate(1.05) brightness(1.02);
    transform: scale(1.08);
  }
  .db-bg-tint {
    position: fixed; inset: 0; z-index: -1;
    background: linear-gradient(180deg, rgba(251,251,254,0.82) 0%, rgba(251,251,254,0.92) 100%);
  }

  .db-nav {
    display: flex; align-items: center; gap: 22px;
    padding: 0 24px; height: 54px; flex-shrink: 0;
    background: rgba(255,255,255,0.7);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(236,238,245,0.8);
  }
  .db-nav-mark {
    width: 24px; height: 24px; border-radius: 7px; margin-right: 6px;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }
  .db-nav-mark img { width: 100%; height: 100%; object-fit: contain; }
  .db-nav-tabs { display: flex; align-items: center; gap: 2px; flex: 1; overflow-x: auto; }
  .db-nav-tab {
    display: flex; align-items: center; gap: 6px;
    font-size: 12.5px; font-weight: 600; color: #9599AA;
    padding: 7px 12px; border-radius: 8px; cursor: pointer; white-space: nowrap;
    transition: all 0.15s ease;
  }
  .db-nav-tab:hover { color: #3A3C46; background: #F7F8FC; }
  .db-nav-tab.active { color: #14151B; background: #EFF2FF; }
  .db-nav-tab.active svg { color: #4A63E8; }
  .db-nav-meta { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #767A8C; flex-shrink: 0; }
  .db-avatar-pill {
    width: 26px; height: 26px; border-radius: 8px; background: linear-gradient(135deg, #7C6BEA, #4A63E8);
    display: flex; align-items: center; justify-content: center; color: #fff; font-size: 10.5px; font-weight: 700;
    cursor: pointer;
  }

  .db-body { flex: 1; overflow-y: auto; padding: 30px 36px 48px; }
  .db-header-row { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 22px; }
  .db-greeting { font-size: 24px; font-weight: 700; letter-spacing: -0.02em; }
  .db-greeting-sub { font-size: 13px; color: #767A8C; margin-top: 4px; }

  .db-stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
  .db-stat-card { background: rgba(255,255,255,0.75); backdrop-filter: blur(14px); border: 1px solid rgba(236,238,245,0.9); border-radius: 16px; padding: 16px; }
  .db-stat-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .db-stat-icon { width: 32px; height: 32px; border-radius: 9px; display: flex; align-items: center; justify-content: center; }
  .db-stat-trend { font-size: 10.5px; color: #17A56A; font-weight: 600; display: flex; align-items: center; gap: 3px; }
  .db-stat-num { font-size: 24px; font-weight: 700; }
  .db-stat-label { font-size: 11.5px; color: #767A8C; margin-top: 3px; }

  .db-grid { display: grid; grid-template-columns: 1fr 320px; gap: 20px; }

  .db-cta-card {
    position: relative; overflow: hidden; border-radius: 18px; padding: 26px;
    background: linear-gradient(135deg, #EFF2FF 0%, #F5F0FF 100%);
    border: 1px solid rgba(74,99,232,0.12);
    display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;
  }
  .db-cta-blob-1 { position: absolute; top: -30%; right: -8%; width: 220px; height: 220px; border-radius: 50%; background: radial-gradient(circle, rgba(0,230,168,0.18), transparent 70%); }
  .db-cta-blob-2 { position: absolute; bottom: -40%; left: 10%; width: 180px; height: 180px; border-radius: 50%; background: radial-gradient(circle, rgba(124,107,234,0.14), transparent 70%); }
  .db-cta-left { position: relative; z-index: 1; max-width: 420px; }
  .db-cta-eyebrow { display: inline-flex; align-items: center; gap: 6px; font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #4A63E8; margin-bottom: 10px; }
  .db-cta-title { font-size: 21px; font-weight: 700; letter-spacing: -0.01em; margin: 0 0 8px; }
  .db-cta-sub { font-size: 12.5px; color: #5B5F70; line-height: 1.55; margin: 0; }
  .db-cta-btn {
    position: relative; z-index: 1; display: flex; align-items: center; gap: 7px;
    background: #14151B; color: #fff; border: none; border-radius: 999px;
    padding: 12px 20px; font-size: 12.5px; font-weight: 700; cursor: pointer;
    box-shadow: 0 10px 24px rgba(20,21,27,0.22); transition: transform 0.15s ease;
  }
  .db-cta-btn:hover { transform: translateY(-1px); }
  .db-cta-illustration { position: relative; z-index: 1; flex-shrink: 0; margin-left: 18px; }

  .db-section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .db-section-title { display: flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 700; }
  .db-section-link { display: flex; align-items: center; gap: 3px; font-size: 12px; color: #4A63E8; font-weight: 600; cursor: pointer; }

  .db-meeting-list { display: flex; flex-direction: column; gap: 8px; }
  .db-meeting-row { display: flex; align-items: center; gap: 12px; background: rgba(255,255,255,0.72); border: 1px solid rgba(236,238,245,0.9); border-radius: 14px; padding: 10px 12px; }
  .db-meeting-thumb { width: 44px; height: 44px; border-radius: 11px; overflow: hidden; flex-shrink: 0; background: #F7F8FC; }
  .db-meeting-info { flex: 1; min-width: 0; }
  .db-meeting-title { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .db-meeting-meta { font-size: 11px; color: #9599AA; display: flex; align-items: center; gap: 6px; margin-top: 3px; }
  .db-status-badge { display: inline-flex; align-items: center; gap: 3px; font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 999px; }
  .db-status-badge.completed { color: #17A56A; background: #E4F8EF; }
  .db-status-badge.processing { color: #B8860B; background: #FFF6E0; }
  .db-status-badge.draft { color: #767A8C; background: #F2F3F6; }
  .db-resume-btn { display: flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 700; color: #4A63E8; background: #EFF2FF; border: none; border-radius: 999px; padding: 7px 12px; cursor: pointer; flex-shrink: 0; }
  .db-delete-btn { display: flex; align-items: center; justify-content: center; width: 30px; height: 30px; color: #9599AA; background: transparent; border: 1px solid rgba(236,238,245,0.9); border-radius: 999px; cursor: pointer; flex-shrink: 0; transition: all 0.15s ease; }
  .db-delete-btn:hover { color: #C0392B; background: #FDECEA; border-color: #F5C6CB; }
  .db-rename-btn { display: flex; align-items: center; justify-content: center; width: 30px; height: 30px; color: #9599AA; background: transparent; border: 1px solid rgba(236,238,245,0.9); border-radius: 999px; cursor: pointer; flex-shrink: 0; transition: all 0.15s ease; }
  .db-rename-btn:hover { color: #4A63E8; background: #EFF2FF; border-color: #C7D0F5; }

  .db-side-card { background: rgba(255,255,255,0.75); backdrop-filter: blur(14px); border: 1px solid rgba(236,238,245,0.9); border-radius: 16px; padding: 16px; margin-bottom: 16px; }
  .db-side-title { display: flex; align-items: center; gap: 7px; font-size: 12.5px; font-weight: 700; margin-bottom: 12px; }
  .db-side-link-btn { display: flex; align-items: center; gap: 5px; justify-content: center; width: 100%; font-size: 11.5px; font-weight: 700; color: #4A63E8; background: transparent; border: 1px dashed rgba(74,99,232,0.3); border-radius: 10px; padding: 9px; cursor: pointer; margin-top: 6px; }

  .db-proto-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid rgba(236,238,245,0.7); }
  .db-proto-item:last-of-type { border-bottom: none; }
  .db-proto-thumb { width: 38px; height: 38px; border-radius: 9px; overflow: hidden; flex-shrink: 0; background: #F7F8FC; }
  .db-proto-info { flex: 1; min-width: 0; }
  .db-proto-title { font-size: 12px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .db-proto-meta { font-size: 10.5px; color: #9599AA; margin-top: 2px; }
  .db-proto-open-btn { color: #9599AA; cursor: pointer; flex-shrink: 0; transition: color 0.15s ease; }
  .db-proto-open-btn:hover { color: #4A63E8; }

  .db-empty-note { font-size: 12px; color: #9599AA; padding: 10px 2px; }

  .db-cta-btn-row { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; position: relative; z-index: 1; }
  .db-join-btn {
    display: flex; align-items: center; gap: 7px;
    background: transparent; color: #4A63E8; border: 1px solid rgba(74,99,232,0.3);
    border-radius: 999px; padding: 10px 18px; font-size: 12px; font-weight: 700; cursor: pointer;
    transition: all 0.15s ease;
  }
  .db-join-btn:hover { background: rgba(74,99,232,0.08); }

  .db-modal-overlay {
    position: fixed; inset: 0; z-index: 100;
    background: rgba(15,16,22,0.45); backdrop-filter: blur(4px);
    display: flex; align-items: center; justify-content: center;
  }
  .db-modal-card {
    width: 380px; background: #fff; border-radius: 18px; padding: 22px;
    box-shadow: 0 24px 60px rgba(20,21,27,0.28);
  }
  .db-modal-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .db-modal-title { font-size: 15.5px; font-weight: 700; }
  .db-modal-close { cursor: pointer; color: #9599AA; }
  .db-modal-sub { font-size: 12px; color: #767A8C; margin: 4px 0 16px; line-height: 1.5; }
  .db-modal-input {
    width: 100%; border: 1px solid #E4E6EF; border-radius: 10px; padding: 11px 13px;
    font-size: 13px; outline: none; font-family: inherit;
  }
  .db-modal-input:focus { border-color: #4A63E8; }
  .db-modal-error { font-size: 11.5px; color: #C0392B; margin-top: 8px; }
  .db-modal-submit {
    width: 100%; margin-top: 16px; display: flex; align-items: center; justify-content: center; gap: 7px;
    background: #14151B; color: #fff; border: none; border-radius: 10px; padding: 11px; font-size: 13px;
    font-weight: 700; cursor: pointer;
  }
  .db-modal-submit:disabled { opacity: 0.6; cursor: default; }
  .db-modal-danger { background: #C0392B; }
  .db-modal-danger:hover:not(:disabled) { background: #A93226; }
`;

const NAV_TABS = [
  { label: "Dashboard", icon: LayoutDashboard, active: true },
  { label: "Meeting Workspace", icon: Users },
  { label: "AI Workforce", icon: Cpu },
  { label: "Generation Pipeline", icon: GitBranch },
  { label: "Prototype Viewer", icon: Eye },
];

function formatWhen(isoString) {
  const d = new Date(isoString);
  const diffMs = Date.now() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return `Today, ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return d.toLocaleDateString();
}

function formatDuration(createdAt, endedAt) {
  const end = endedAt ? new Date(endedAt) : new Date();
  const mins = Math.round((end - new Date(createdAt)) / 60000);
  return mins < 1 ? "<1 min" : `${mins} min`;
}

export default function DashboardPage({ onNewMeeting, onResumeMeeting, onOpenWorkforce, onOpenPrototype, onJoinMeeting, currentUser, onLogout }) {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [joinOpen, setJoinOpen] = useState(false);
  const [joinId, setJoinId] = useState("");
  const [joinBusy, setJoinBusy] = useState(false);
  const [joinError, setJoinError] = useState(null);

  // Delete-a-meeting confirm flow. Deletion is permanent (the backend wipes the
  // transcript, requirements and generated prototype), so it always goes through
  // this confirm modal — never a one-click removal.
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  // Rename-a-meeting flow. The default name is a timestamp ("Meeting on …"),
  // so letting the host give it a real title is what makes the history list
  // actually readable later.
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameValue, setRenameValue] = useState("");
  const [renameBusy, setRenameBusy] = useState(false);
  const [renameError, setRenameError] = useState(null);

  const handleJoinSubmit = async () => {
    const id = joinId.trim();
    if (!id) return;
    setJoinBusy(true);
    setJoinError(null);
    try {
      await onJoinMeeting?.(id);
      setJoinOpen(false);
      setJoinId("");
    } catch (err) {
      setJoinError(
        err?.status === 404
          ? "No meeting found with that ID — ask the host to start the meeting first, then try again."
          : (err?.message || "Couldn't join that meeting.")
      );
    } finally {
      setJoinBusy(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await meetingsApi.delete(deleteTarget.meeting_id);
      // Drop it from local state — recentMeetings and recentPrototypes both
      // derive from `meetings`, so both lists update at once.
      setMeetings((prev) => prev.filter((m) => m.meeting_id !== deleteTarget.meeting_id));
      setDeleteTarget(null);
    } catch (err) {
      setDeleteError(err?.message || "Couldn't delete that meeting.");
    } finally {
      setDeleteBusy(false);
    }
  };

  const handleRenameConfirm = async () => {
    if (!renameTarget) return;
    const name = renameValue.trim();
    if (!name) return;
    setRenameBusy(true);
    setRenameError(null);
    try {
      const updated = await meetingsApi.rename(renameTarget.meeting_id, name);
      // Patch the one row in place — keep every other field the backend
      // returned so the meta line (readiness, prototype badge) stays correct.
      setMeetings((prev) =>
        prev.map((m) => (m.meeting_id === renameTarget.meeting_id ? { ...m, ...updated } : m))
      );
      setRenameTarget(null);
    } catch (err) {
      setRenameError(err?.message || "Couldn't rename that meeting.");
    } finally {
      setRenameBusy(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    meetingsApi
      .list()
      .then((data) => {
        if (cancelled) return;
        setMeetings(data.meetings || []);
        setLoadError(null);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err.message);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []);

  const greeting = (() => {
    const h = new Date().getHours();
    return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  })();

  const prototypesShipped = meetings.filter((m) => m.has_prototype).length;
  const avgReadiness = meetings.length
    ? Math.round(meetings.reduce((sum, m) => sum + (m.readiness_percent || 0), 0) / meetings.length)
    : 0;
  const totalTranscriptLines = meetings.reduce((sum, m) => sum + (m.transcript_lines || 0), 0);

  const STATS = [
    { label: "Meetings recorded", value: String(meetings.length), icon: Mic, color: "#4A63E8", bg: "#EFF2FF" },
    { label: "Prototypes shipped", value: String(prototypesShipped), icon: Layers, color: "#7C6BEA", bg: "#F2EFFF" },
    { label: "Avg. readiness score", value: `${avgReadiness}%`, icon: Cpu, color: "#00A87C", bg: "#E4F8EF" },
    { label: "Transcript lines", value: String(totalTranscriptLines), icon: Zap, color: "#B8860B", bg: "#FFF6E0" },
  ];

  const recentMeetings = [...meetings]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 4);

  const recentPrototypes = meetings.filter((m) => m.has_prototype).slice(0, 3);

  return (
    <div className="db-root">
      <style>{styles}</style>
      <div className="db-bg-layer" />
      <div className="db-bg-tint" />

      <div className="db-nav">
        <div className="db-nav-mark"><img src="/logo.png" alt="ProtoPilot" /></div>
        <div className="db-nav-tabs">
          {NAV_TABS.map((t) => (
            <div
              key={t.label}
              className={`db-nav-tab ${t.active ? "active" : ""}`}
              onClick={() => {
                if (t.label === "Meeting Workspace") onNewMeeting?.();
                if (t.label === "AI Workforce") onOpenWorkforce?.();
                if (t.label === "Prototype Viewer") onOpenPrototype?.();
              }}
            >
              <t.icon size={13} /> {t.label}
            </div>
          ))}
        </div>
        <div className="db-nav-meta">
          <div className="db-avatar-pill" title={currentUser ? `${currentUser.name} — click to sign out` : ""} onClick={onLogout}>
            {(currentUser?.name || "?")[0]?.toUpperCase()}
          </div>
        </div>
      </div>

      <div className="db-body">
        <div className="db-header-row">
          <div>
            <div className="db-greeting db-display">{greeting}{currentUser?.name ? `, ${currentUser.name}` : ""}</div>
            <div className="db-greeting-sub">
              {loading ? "Loading your meetings…" : `${meetings.length} meeting${meetings.length === 1 ? "" : "s"} recorded`}
            </div>
          </div>
        </div>

        {loadError && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#B8860B", fontSize: 12.5, marginBottom: 16 }}>
            <AlertCircle size={14} /> {loadError}
          </div>
        )}

        <div className="db-stats-row">
          {STATS.map((s) => (
            <div className="db-stat-card" key={s.label}>
              <div className="db-stat-top">
                <div className="db-stat-icon" style={{ background: s.bg }}>
                  <s.icon size={15} color={s.color} />
                </div>
              </div>
              <div className="db-stat-num db-display">{s.value}</div>
              <div className="db-stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        <div className="db-grid">
          <div>
            <div className="db-cta-card">
              <div className="db-cta-blob-1" />
              <div className="db-cta-blob-2" />
              <div className="db-cta-left">
                <div className="db-cta-eyebrow"><Sparkles size={11} /> Start something new</div>
                <h3 className="db-cta-title db-display">Turn your next meeting into a prototype</h3>
                <p className="db-cta-sub">Start a live video call — everyone's voice gets transcribed separately, translated to English, and turned into requirements you can accept or reject.</p>
              </div>
              <div className="db-cta-btn-row">
                <button className="db-cta-btn" onClick={onNewMeeting}>
                  <Plus size={16} /> New meeting
                </button>
                <button className="db-join-btn" onClick={() => { setJoinError(null); setJoinOpen(true); }}>
                  <LogIn size={13} /> Join meeting
                </button>
              </div>
              <div className="db-cta-illustration">
                <svg width="64" height="64" viewBox="0 0 64 64">
                  <circle cx="32" cy="32" r="30" fill="#fff" opacity="0.6" />
                  <circle cx="32" cy="32" r="22" fill="url(#mic-grad)" opacity="0.9" />
                  <defs>
                    <linearGradient id="mic-grad" x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stopColor="#4A63E8" />
                      <stop offset="100%" stopColor="#00C88A" />
                    </linearGradient>
                  </defs>
                  <g transform="translate(32,32)">
                    <rect x="-5" y="-13" width="10" height="18" rx="5" fill="#fff" />
                    <path d="M -10 -1 A 10 10 0 0 0 10 -1" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" />
                    <line x1="0" y1="9" x2="0" y2="14" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
                  </g>
                </svg>
              </div>
            </div>

            <div className="db-section">
              <div className="db-section-head">
                <span className="db-section-title"><FileClock size={14} color="#4A63E8" /> Meeting history</span>
              </div>
              <div className="db-meeting-list">
                {!loading && recentMeetings.length === 0 && (
                  <div className="db-empty-note">No meetings yet — click "New Meeting" to start your first one.</div>
                )}
                {recentMeetings.map((m) => (
                  <div className="db-meeting-row" key={m.meeting_id}>
                    <div className="db-meeting-thumb" />
                    <div className="db-meeting-info">
                      <div className="db-meeting-title">{m.name}</div>
                      <div className="db-meeting-meta">
                        <span>{formatWhen(m.created_at)}</span> · <span>{formatDuration(m.created_at, m.ended_at)}</span>
                        <span className={`db-status-badge ${m.status === "ended" ? "completed" : "processing"}`}>
                          {m.status === "ended" ? <CheckCircle2 size={10} /> : <Loader2 size={10} className="wf-spin" />}
                          {m.status === "ended" ? "Ended" : "In progress"}
                        </span>
                      </div>
                    </div>
                    <button className="db-resume-btn" onClick={() => onResumeMeeting?.(m.meeting_id)}>
                      <Play size={12} /> Resume
                    </button>
                    <button
                      className="db-rename-btn"
                      title="Rename this meeting"
                      onClick={() => { setRenameError(null); setRenameValue(m.name); setRenameTarget(m); }}
                    >
                      <Pencil size={13} />
                    </button>
                    <button
                      className="db-delete-btn"
                      title="Delete this meeting permanently"
                      onClick={() => { setDeleteError(null); setDeleteTarget(m); }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div>
            <div className="db-side-card">
              <div className="db-side-title"><Cpu size={14} color="#4A63E8" /> AI Workforce</div>
              <p style={{ fontSize: 11.5, color: "#767A8C", lineHeight: 1.5, margin: "0 0 10px" }}>
                Open a meeting and generate a prototype to watch the 9 agents work in real time.
              </p>
              <button className="db-side-link-btn" onClick={onOpenWorkforce}>
                View full workforce <ArrowRight size={13} />
              </button>
            </div>

            <div className="db-side-card">
              <div className="db-side-title"><Layers size={14} color="#7C6BEA" /> Recent prototypes</div>
              {recentPrototypes.length === 0 && (
                <div className="db-empty-note">None generated yet.</div>
              )}
              {recentPrototypes.map((p) => (
                <div className="db-proto-item" key={p.meeting_id}>
                  <div className="db-proto-thumb" />
                  <div className="db-proto-info">
                    <div className="db-proto-title">{p.name}</div>
                    <div className="db-proto-meta">{formatWhen(p.created_at)}</div>
                  </div>
                  <div className="db-proto-open-btn" onClick={() => onOpenPrototype?.(p.meeting_id)}>
                    <ChevronRight size={15} />
                  </div>
                </div>
              ))}
              <button className="db-side-link-btn" onClick={() => onOpenPrototype?.()}>
                Open in Prototype Viewer <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {joinOpen && (
        <div className="db-modal-overlay" onClick={() => !joinBusy && setJoinOpen(false)}>
          <div className="db-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="db-modal-head">
              <div className="db-modal-title">Join a meeting</div>
              <X size={16} className="db-modal-close" onClick={() => !joinBusy && setJoinOpen(false)} />
            </div>
            <p className="db-modal-sub">
              Paste the meeting ID the host shared with you (it's shown at the top of
              their live meeting screen — tap it to copy).
            </p>
            <input
              className="db-modal-input"
              placeholder="e.g. 3f9a2c10-8b41-4e2a-9c77-..."
              value={joinId}
              autoFocus
              onChange={(e) => setJoinId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleJoinSubmit()}
            />
            {joinError && <div className="db-modal-error">{joinError}</div>}
            <button className="db-modal-submit" disabled={joinBusy || !joinId.trim()} onClick={handleJoinSubmit}>
              {joinBusy ? <Loader2 size={14} className="wf-spin" /> : <LogIn size={14} />}
              {joinBusy ? "Joining…" : "Join meeting"}
            </button>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="db-modal-overlay" onClick={() => !deleteBusy && setDeleteTarget(null)}>
          <div className="db-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="db-modal-head">
              <div className="db-modal-title">Delete this meeting?</div>
              <X size={16} className="db-modal-close" onClick={() => !deleteBusy && setDeleteTarget(null)} />
            </div>
            <p className="db-modal-sub">
              <b>{deleteTarget.name}</b> and everything in it — the transcript, every
              captured requirement, and the generated prototype — will be permanently
              deleted. This can't be undone.
            </p>
            {deleteError && <div className="db-modal-error">{deleteError}</div>}
            <button className="db-modal-submit db-modal-danger" disabled={deleteBusy} onClick={handleDeleteConfirm}>
              {deleteBusy ? <Loader2 size={14} className="wf-spin" /> : <Trash2 size={14} />}
              {deleteBusy ? "Deleting…" : "Delete permanently"}
            </button>
          </div>
        </div>
      )}

      {renameTarget && (
        <div className="db-modal-overlay" onClick={() => !renameBusy && setRenameTarget(null)}>
          <div className="db-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="db-modal-head">
              <div className="db-modal-title">Rename meeting</div>
              <X size={16} className="db-modal-close" onClick={() => !renameBusy && setRenameTarget(null)} />
            </div>
            <p className="db-modal-sub">
              Give this meeting a name you'll recognise later in your history.
            </p>
            <input
              className="db-modal-input"
              placeholder="e.g. Restaurant app kickoff"
              value={renameValue}
              autoFocus
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRenameConfirm()}
            />
            {renameError && <div className="db-modal-error">{renameError}</div>}
            <button
              className="db-modal-submit"
              disabled={renameBusy || !renameValue.trim() || renameValue.trim() === renameTarget.name}
              onClick={handleRenameConfirm}
            >
              {renameBusy ? <Loader2 size={14} className="wf-spin" /> : <Pencil size={14} />}
              {renameBusy ? "Saving…" : "Save name"}
            </button>
          </div>
        </div>
      )}

      <style>{`.wf-spin { animation: wfSpin 1s linear infinite; } @keyframes wfSpin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
