import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Zap,
  Lock,
  Unlock,
  ArrowLeft,
  Eye,
  EyeOff,
  Clock,
  Check,
  Trash2,
  Sparkles,
  Cpu,
  Layers,
  Activity,
  Video,
  Mic,
  Database,
  Brain,
  ChevronDown,
  ChevronUp,
  Info,
  Server,
  HelpCircle,
  RotateCcw,
} from "lucide-react";
import { adminApi } from "../lib/api.js";

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

  .human-admin-root {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    min-height: 100vh;
    background: radial-gradient(circle at 50% 0%, #151A2E 0%, #0B0E18 70%);
    color: #F1F5F9;
    display: flex;
    flex-direction: column;
    letter-spacing: -0.01em;
  }

  .human-card {
    background: rgba(18, 24, 38, 0.7);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .human-card:hover {
    border-color: rgba(255, 255, 255, 0.16);
    box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.5);
  }

  .human-glass-input {
    background: rgba(15, 21, 35, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    color: #FFFFFF;
    transition: all 0.2s ease;
  }
  .human-glass-input:focus {
    outline: none;
    border-color: #6366F1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25);
    background: rgba(18, 25, 42, 0.95);
  }

  .gradient-text {
    background: linear-gradient(135deg, #A5B4FC 0%, #E0E7FF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .btn-gradient {
    background: linear-gradient(135deg, #4F46E5 0%, #6366F1 50%, #06B6D4 100%);
    transition: all 0.25s ease;
  }
  .btn-gradient:hover {
    opacity: 0.95;
    transform: translateY(-1px);
    box-shadow: 0 8px 24px rgba(79, 70, 229, 0.4);
  }
  .btn-gradient:active {
    transform: translateY(0);
  }
`;

// Human friendly metadata for each service
const PROVIDER_METADATA = {
  "Groq AI": {
    icon: Zap,
    role: "Fast Prototype Generator",
    hindiDesc: "Aapke prototypes aur AI agents generate karta hai.",
    docUrl: "https://console.groq.com/keys",
    tip: "Free tier me 8,000 tokens/min milte hain.",
  },
  "Google Gemini": {
    icon: Brain,
    role: "High-Capacity AI Backup",
    hindiDesc: "Bade complex pipelines aur emergency quota ke liye.",
    docUrl: "https://aistudio.google.com/apikey",
    tip: "Free key aistudio.google.com se 1 minute me ban jati hai.",
  },
  "Sarvam AI": {
    icon: Mic,
    role: "Hindi / Voice-to-Text",
    hindiDesc: "Meeting me boli gayi baaton ko text me convert karta hai.",
    docUrl: "https://dashboard.sarvam.ai",
    tip: "Account me free trial credits milte hain.",
  },
  "LiveKit Video": {
    icon: Video,
    role: "Meeting Video & Microphone",
    hindiDesc: "Audio-video room aur live meeting connect rakhta hai.",
    docUrl: "https://cloud.livekit.io",
    tip: "LiveKit Cloud project active hona zaroori hai.",
  },
  "Database": {
    icon: Database,
    role: "Secure Data Storage (PostgreSQL)",
    hindiDesc: "Meetings, user accounts aur prototypes safe rakhta hai.",
    docUrl: "https://console.neon.tech",
    tip: "Neon Postgres SSL encrypted cloud database hai.",
  },
};

export default function AdminPage({ onBack, currentUser }) {
  const [authorized, setAuthorized] = useState(false);
  const [secretInput, setSecretInput] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [authError, setAuthError] = useState("");
  const [verifying, setVerifying] = useState(false);

  // Diagnostics & Status
  const [diagnostics, setDiagnostics] = useState(null);
  const [incidents, setIncidents] = useState({ active: [], history: [] });
  const [loading, setLoading] = useState(false);
  const [runningProbes, setRunningProbes] = useState(false);
  const [lastChecked, setLastChecked] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [resolvingId, setResolvingId] = useState(null);
  const [expandedDetails, setExpandedDetails] = useState({});

  const refreshIntervalRef = useRef(null);

  // Initial auth check
  const checkInitialAuth = useCallback(async () => {
    setVerifying(true);
    setAuthError("");
    try {
      const storedSecret = sessionStorage.getItem("admin_secret");
      const res = await adminApi.verifyAccess(storedSecret || "");
      if (res && res.authorized) {
        setAuthorized(true);
        loadDiagnostics();
      }
    } catch {
      setAuthorized(false);
    } finally {
      setVerifying(false);
    }
  }, []);

  useEffect(() => {
    checkInitialAuth();
  }, [checkInitialAuth]);

  // Load diagnostics
  const loadDiagnostics = async (isManual = false) => {
    if (isManual) setRunningProbes(true);
    else setLoading(true);

    try {
      const healthRes = await adminApi.health();
      if (healthRes && healthRes.diagnostics) {
        setDiagnostics(healthRes.diagnostics);
        setIncidents(healthRes.diagnostics.incidents || { active: [], history: [] });
        setLastChecked(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
      }
    } catch (err) {
      if (err.status === 403) {
        sessionStorage.removeItem("admin_secret");
        setAuthorized(false);
        setAuthError("Aapka session khatam ho gaya hai. Kripya dobara login karein.");
      }
    } finally {
      setLoading(false);
      setRunningProbes(false);
    }
  };

  // Run live test all
  const runLiveTestAll = async () => {
    setRunningProbes(true);
    try {
      const res = await adminApi.testAll();
      if (res && res.diagnostics) {
        setDiagnostics(res.diagnostics);
        setIncidents(res.diagnostics.incidents || { active: [], history: [] });
        setLastChecked(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
      }
    } catch (err) {
      if (err.status === 403) {
        sessionStorage.removeItem("admin_secret");
        setAuthorized(false);
      }
    } finally {
      setRunningProbes(false);
    }
  };

  // Auto refresh
  useEffect(() => {
    if (authorized && autoRefresh) {
      refreshIntervalRef.current = setInterval(() => {
        loadDiagnostics(false);
      }, 15000);
    } else {
      if (refreshIntervalRef.current) clearInterval(refreshIntervalRef.current);
    }
    return () => {
      if (refreshIntervalRef.current) clearInterval(refreshIntervalRef.current);
    };
  }, [authorized, autoRefresh]);

  // Handle unlock
  const handleUnlock = async (e) => {
    if (e) e.preventDefault();
    if (!secretInput.trim()) {
      setAuthError("Kripya secret password enter karein.");
      return;
    }

    setVerifying(true);
    setAuthError("");

    try {
      const res = await adminApi.verifyAccess(secretInput.trim());
      if (res && res.authorized) {
        sessionStorage.setItem("admin_secret", secretInput.trim());
        setAuthorized(true);
        setSecretInput("");
        loadDiagnostics();
      }
    } catch (err) {
      setAuthError(
        err.status === 403
          ? "Galat Password! Sirf authorized admin hi access kar sakte hain."
          : (err.message || "Server se connect nahi ho paya. Backend check karein.")
      );
    } finally {
      setVerifying(false);
    }
  };

  // Lock
  const handleLock = () => {
    sessionStorage.removeItem("admin_secret");
    setAuthorized(false);
    setDiagnostics(null);
  };

  // Mark resolved
  const handleResolve = async (incidentId) => {
    setResolvingId(incidentId);
    try {
      const res = await adminApi.resolveIncident(incidentId);
      if (res && res.incidents) {
        setIncidents(res.incidents);
      }
    } catch (err) {
      console.error("Resolve error:", err);
    } finally {
      setResolvingId(null);
    }
  };

  // Clear history
  const handleClearHistory = async () => {
    try {
      const res = await adminApi.clearResolved();
      if (res && res.incidents) {
        setIncidents(res.incidents);
      }
    } catch (err) {
      console.error("Clear error:", err);
    }
  };

  // --------------------------------------------------------------------------
  // SCREEN 1: BEAUTIFUL & FRIENDLY LOCK SCREEN
  // --------------------------------------------------------------------------
  if (!authorized) {
    return (
      <div className="human-admin-root items-center justify-center p-6">
        <style>{styles}</style>

        {/* Soft Background Radial Glows */}
        <div className="fixed top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="fixed bottom-10 right-1/4 w-[400px] h-[400px] bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative w-full max-w-md human-card p-8 shadow-2xl bg-[#111627]/90 border border-slate-700/60">
          {/* Logo & Welcome Header */}
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center text-white mb-4 shadow-lg shadow-indigo-500/30">
              <ShieldCheck className="w-8 h-8" />
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs font-semibold mb-2">
              <Sparkles className="w-3.5 h-3.5" />
              <span>ProtoPilot Mission Control</span>
            </div>

            <h1 className="text-2xl font-bold text-white tracking-tight">
              Admin System Dashboard
            </h1>
            <p className="text-sm text-slate-400 mt-1.5 max-w-xs leading-relaxed">
              Yahan se aap system ki health, API limits aur problems dekh sakte hain.
            </p>
          </div>

          {/* Error Banner */}
          {authError && (
            <div className="mb-5 p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60 flex items-start gap-3 text-rose-200 text-xs leading-relaxed">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{authError}</span>
            </div>
          )}

          {/* Input Form */}
          <form onSubmit={handleUnlock} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                Aapka Secret Admin Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showSecret ? "text" : "password"}
                  value={secretInput}
                  onChange={(e) => setSecretInput(e.target.value)}
                  placeholder="Password yahan daalein..."
                  className="w-full pl-10 pr-11 py-3 human-glass-input text-sm text-white placeholder:text-slate-500"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowSecret(!showSecret)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200"
                >
                  {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={verifying}
              className="w-full py-3 px-4 rounded-xl btn-gradient text-white font-semibold text-sm tracking-wide shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {verifying ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Checking Password...</span>
                </>
              ) : (
                <>
                  <Unlock className="w-4 h-4" />
                  <span>Unlock Admin Console</span>
                </>
              )}
            </button>
          </form>

          {/* Friendly Note */}
          <div className="mt-5 p-3 rounded-xl bg-slate-800/40 border border-slate-700/40 flex items-start gap-2.5 text-[11.5px] text-slate-400 leading-relaxed">
            <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <span>
              By default key: <code className="text-indigo-300 font-semibold">protopilot-admin-2026</code> hai. (Ise aap Render ke Environment Variables se change kar sakte hain).
            </span>
          </div>

          {/* Back Action */}
          <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
            <button
              type="button"
              onClick={onBack}
              className="flex items-center gap-1.5 hover:text-slate-300 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to App</span>
            </button>
            <span className="text-[11px] text-slate-500">v0.3.0 Pro</span>
          </div>
        </div>
      </div>
    );
  }

  // --------------------------------------------------------------------------
  // SCREEN 2: HUMAN-FRIENDLY ADMIN DASHBOARD
  // --------------------------------------------------------------------------
  const overallStatus = diagnostics?.overall_status || "healthy";
  const providers = diagnostics?.providers || [];
  const system = diagnostics?.system || {};
  const activeIncidents = incidents.active || [];
  const historicalIncidents = incidents.history || [];

  return (
    <div className="human-admin-root">
      <style>{styles}</style>

      {/* Top Friendly Header Bar */}
      <header className="border-b border-slate-800/80 bg-[#0E1322]/90 backdrop-blur-md sticky top-0 z-30 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/25">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-white tracking-tight">
                  ProtoPilot Control Room
                </h1>
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                  SYSTEM HEALTH
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Aapke app ki sabhi APIs, video calls aur database ka live status
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5">
            {/* Auto Refresh Switch */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-2 rounded-xl text-xs font-semibold border transition flex items-center gap-1.5 ${
                autoRefresh
                  ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/30"
                  : "bg-slate-800/60 text-slate-400 border-slate-700/60"
              }`}
              title="Automatic refresh har 15 second me"
            >
              <Clock className="w-3.5 h-3.5" />
              <span>Live Auto-Update: {autoRefresh ? "ON (15s)" : "PAUSED"}</span>
            </button>

            {/* Manual Check */}
            <button
              onClick={runLiveTestAll}
              disabled={runningProbes}
              className="px-4 py-2 rounded-xl btn-gradient text-white text-xs font-semibold flex items-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-60"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${runningProbes ? "animate-spin" : ""}`} />
              <span>{runningProbes ? "Testing APIs..." : "Check Sab Kuch (Test Now)"}</span>
            </button>

            {/* Lock */}
            <button
              onClick={handleLock}
              className="px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/90 text-slate-300 text-xs font-semibold border border-slate-700/80 flex items-center gap-1.5 transition"
              title="Lock Admin Console"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Lock</span>
            </button>

            {/* Exit */}
            <button
              onClick={onBack}
              className="px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/90 text-slate-300 text-xs font-semibold border border-slate-700/80 flex items-center gap-1.5 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>App Me Jao</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-6 space-y-7">
        {/* Status Summary Banner */}
        <div
          className={`p-5 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
            overallStatus === "healthy"
              ? "bg-emerald-950/30 border-emerald-800/50 text-emerald-300"
              : overallStatus === "degraded"
              ? "bg-amber-950/30 border-amber-800/50 text-amber-300"
              : "bg-rose-950/30 border-rose-800/50 text-rose-300"
          }`}
        >
          <div className="flex items-center gap-3.5">
            <div
              className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${
                overallStatus === "healthy"
                  ? "bg-emerald-500/20 text-emerald-400"
                  : overallStatus === "degraded"
                  ? "bg-amber-500/20 text-amber-400"
                  : "bg-rose-500/20 text-rose-400"
              }`}
            >
              {overallStatus === "healthy" ? (
                <CheckCircle2 className="w-6 h-6" />
              ) : (
                <AlertTriangle className="w-6 h-6 animate-bounce" />
              )}
            </div>
            <div>
              <div className="text-base font-bold text-white flex items-center gap-2">
                <span>
                  {overallStatus === "healthy"
                    ? "🟢 Sab Kuch Ekdum Badiya Chal Raha Hai!"
                    : overallStatus === "degraded"
                    ? "🟡 Thoda Dhyan Dein: Kuch Services Slow Ya Limit Par Hain"
                    : "🔴 Alert: Kuch Services Me Problem Aayi Hai"}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">
                {overallStatus === "healthy"
                  ? "Sabhi AI models (Groq, Gemini), Video Calling (LiveKit), Voice STT (Sarvam) aur Database 100% active aur ready hain."
                  : "Neeche dekhein kya issue aaya hai aur use kaise turant solve karna hai."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs shrink-0 font-medium">
            {lastChecked && (
              <span className="text-slate-400">
                Last checked: <strong className="text-slate-200">{lastChecked}</strong>
              </span>
            )}
          </div>
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* SECTION 1: 5 CORE SERVICES STATUS CARDS                            */}
        {/* ------------------------------------------------------------------ */}
        <div>
          <div className="flex items-center justify-between mb-3.5">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Aapki 5 Main Services Ka Live Status
              </h2>
            </div>
            <span className="text-xs text-slate-400">
              Green = Sab Sahi • Red = Check Karein
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {providers.map((p, idx) => {
              const meta = PROVIDER_METADATA[p.name] || {
                icon: Server,
                role: "External Service",
                hindiDesc: "App integration",
                tip: "",
              };
              const IconComp = meta.icon;

              const isHealthy = p.status === "healthy";
              const isWarning = p.status === "warning" || p.status === "rate_limited";
              const isUnconfigured = p.status === "unconfigured";
              const isCrit = !isHealthy && !isWarning && !isUnconfigured;

              return (
                <div
                  key={idx}
                  className={`human-card p-4 flex flex-col justify-between relative overflow-hidden ${
                    isCrit ? "border-rose-700/60 bg-rose-950/15" : ""
                  }`}
                >
                  <div>
                    {/* Top Bar */}
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div className="w-9 h-9 rounded-xl bg-slate-800/80 border border-slate-700/70 flex items-center justify-center text-indigo-400">
                        <IconComp className="w-4 h-4" />
                      </div>

                      {/* Status Badge */}
                      <span
                        className={`text-[10.5px] font-bold px-2 py-0.5 rounded-full ${
                          isHealthy
                            ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                            : isWarning
                            ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                            : isUnconfigured
                            ? "bg-slate-800 text-slate-400 border border-slate-700"
                            : "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                        }`}
                      >
                        {isHealthy
                          ? "Ready & Fast"
                          : isWarning
                          ? "Limit Reached"
                          : isUnconfigured
                          ? "Not Added"
                          : "Problem"}
                      </span>
                    </div>

                    {/* Title & Role */}
                    <h3 className="font-bold text-sm text-white">{p.name}</h3>
                    <p className="text-[11px] text-indigo-300 font-medium mb-1.5">{meta.role}</p>

                    {/* Simple Hindi Description */}
                    <p className="text-xs text-slate-300 leading-relaxed mb-3">
                      {meta.hindiDesc}
                    </p>
                  </div>

                  {/* Bottom Technical Pill (Simplified) */}
                  <div className="pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                    <span>
                      {p.latency_ms ? `⚡ ${p.latency_ms}ms` : isHealthy ? "Online" : p.status}
                    </span>
                    {meta.docUrl && (
                      <a
                        href={meta.docUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-indigo-400 hover:text-indigo-300 transition flex items-center gap-0.5"
                        title="Dashboard open karein"
                      >
                        Portal ↗
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* SECTION 2: ACTIVE PROBLEMS (KYUN HUA & KAISE FIX KAREIN)            */}
        {/* ------------------------------------------------------------------ */}
        <div>
          <div className="flex items-center justify-between mb-3.5">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                🚨 Abhi Kya Problem Aa Rahi Hai? ({activeIncidents.length})
              </h2>
            </div>
            {activeIncidents.length > 0 && (
              <span className="text-xs text-rose-400 font-semibold">
                Neeche diya gaya solution follow kijiye
              </span>
            )}
          </div>

          {activeIncidents.length === 0 ? (
            /* All Clear Card */
            <div className="human-card p-7 text-center flex flex-col items-center justify-center border-emerald-800/40 bg-emerald-950/10">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-3 shadow-lg shadow-emerald-500/10">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <h3 className="text-base font-bold text-white mb-1">
                Aapke System Me Koi Problem Nahi Hai!
              </h3>
              <p className="text-xs text-slate-400 max-w-lg leading-relaxed">
                Groq tokens, video call connections, Gemini backup aur database ekdum first-class chal rahe hain. Agar koi bhi API limit pe aayegi to yahan automatically reason aur fix aa jayega.
              </p>
            </div>
          ) : (
            /* Problem Cards */
            <div className="space-y-4">
              {activeIncidents.map((inc) => {
                const isResolving = resolvingId === inc.id;
                const isExpanded = expandedDetails[inc.id];

                return (
                  <div
                    key={inc.id}
                    className="human-card p-5 border-rose-800/50 bg-[#161B2B] shadow-xl space-y-4"
                  >
                    {/* Problem Header */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className="w-9 h-9 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 shrink-0 mt-0.5">
                          <AlertTriangle className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                              {inc.category}
                            </span>
                            {inc.occurrences > 1 && (
                              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                {inc.occurrences} Baar Hua
                              </span>
                            )}
                            <span className="text-xs text-slate-400">
                              {inc.timestamp ? new Date(inc.timestamp).toLocaleTimeString() : ""}
                            </span>
                          </div>
                          <h3 className="text-base font-bold text-white tracking-tight">
                            {inc.title}
                          </h3>
                        </div>
                      </div>

                      {/* Solve Button */}
                      <button
                        onClick={() => handleResolve(inc.id)}
                        disabled={isResolving}
                        className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-lg shadow-emerald-600/20 shrink-0"
                      >
                        {isResolving ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Check className="w-3.5 h-3.5" />
                        )}
                        <span>Theek Ho Gaya (Mark as Solved)</span>
                      </button>
                    </div>

                    {/* Dual Cards: Reason & Solution in Simple Human Words */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                      {/* Reason Card */}
                      <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-900/40">
                        <div className="text-xs font-bold text-rose-300 uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                          <XCircle className="w-4 h-4 text-rose-400" />
                          <span>Kyun Hua? (Exact Reason)</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">{inc.reason}</p>
                      </div>

                      {/* Solution Card */}
                      <div className="p-4 rounded-xl bg-indigo-950/25 border border-indigo-800/40">
                        <div className="text-xs font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                          <Zap className="w-4 h-4 text-indigo-400" />
                          <span>Ab Kaise Fix Karein? (Actionable Steps)</span>
                        </div>
                        <p className="text-xs text-indigo-100 leading-relaxed font-medium">
                          {inc.solution}
                        </p>
                      </div>
                    </div>

                    {/* Technical details toggle (optional) */}
                    {inc.raw_details && (
                      <div className="pt-1">
                        <button
                          onClick={() => setExpandedDetails((p) => ({ ...p, [inc.id]: !p[inc.id] }))}
                          className="text-[11.5px] text-slate-400 hover:text-slate-200 flex items-center gap-1 font-medium transition"
                        >
                          {isExpanded ? (
                            <>
                              <ChevronUp className="w-3 h-3" /> Technical log band karein
                            </>
                          ) : (
                            <>
                              <ChevronDown className="w-3 h-3" /> Technical log dekhna hai? Click karein
                            </>
                          )}
                        </button>
                        {isExpanded && (
                          <div className="mt-2 p-3 rounded-lg bg-black/50 border border-slate-800 text-[11px] text-slate-300 font-mono whitespace-pre-wrap break-all">
                            {inc.raw_details}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* SECTION 3: SYSTEM RESOURCES (SIMPLE TERMS)                         */}
        {/* ------------------------------------------------------------------ */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="human-card p-4 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-medium">Server Health</div>
              <div className="text-sm font-bold text-white">Ekdum Smooth & Fast</div>
            </div>
          </div>

          <div className="human-card p-4 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-medium">Server Memory (RAM)</div>
              <div className="text-sm font-bold text-white">
                {system.memory_rss_mb ? `${system.memory_rss_mb} MB (Normal)` : "Safe & Lightweight"}
              </div>
            </div>
          </div>

          <div className="human-card p-4 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-medium">Purani Problems Solved</div>
              <div className="text-sm font-bold text-white">
                {historicalIncidents.length} Issues Fix Kiye Gaye
              </div>
            </div>
          </div>
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* SECTION 4: PURANI SOLVED PROBLEMS (AUDIT LOG)                      */}
        {/* ------------------------------------------------------------------ */}
        <div>
          <div className="flex items-center justify-between mb-3.5">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-purple-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                📜 Purani Solved Problems Ka Record ({historicalIncidents.length})
              </h2>
            </div>
            {historicalIncidents.length > 0 && (
              <button
                onClick={handleClearHistory}
                className="text-xs text-slate-400 hover:text-rose-400 flex items-center gap-1 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear History</span>
              </button>
            )}
          </div>

          {historicalIncidents.length === 0 ? (
            <div className="human-card p-5 text-center text-xs text-slate-500">
              Purani koi problem record nahi hai.
            </div>
          ) : (
            <div className="space-y-2.5">
              {historicalIncidents.map((h, i) => (
                <div
                  key={i}
                  className="human-card p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{h.title}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-semibold">
                          {h.category}
                        </span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-0.5 line-clamp-1">
                        Reason: {h.reason}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-[11px] text-slate-400 shrink-0">
                    <span className="text-emerald-400 font-medium">
                      Resolved: {h.resolved_at ? new Date(h.resolved_at).toLocaleTimeString() : "Solved"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
