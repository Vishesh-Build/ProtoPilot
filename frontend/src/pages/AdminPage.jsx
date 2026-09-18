import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Shield,
  Lock,
  Unlock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Activity,
  Server,
  Database,
  Video,
  Cpu,
  Brain,
  ArrowLeft,
  Eye,
  EyeOff,
  Clock,
  Check,
  Trash2,
  Zap,
  Info,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { adminApi, ApiError } from "../lib/api.js";

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

  .admin-root {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    min-height: 100vh;
    background-color: #080B11;
    color: #F3F4F6;
    display: flex;
    flex-direction: column;
  }
  .admin-mono {
    font-family: 'JetBrains Mono', monospace;
  }

  @keyframes adminPulseSlow {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(1.05); }
  }
  .admin-pulse-slow {
    animation: adminPulseSlow 3s ease-in-out infinite;
  }

  @keyframes scanline {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(1000%); }
  }
  .admin-scanline {
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.4), transparent);
    animation: scanline 8s linear infinite;
    pointer-events: none;
  }

  .admin-card {
    background: #0F1420;
    border: 1px solid #1E293B;
    border-radius: 12px;
    transition: all 0.2s ease;
  }
  .admin-card:hover {
    border-color: #334155;
  }
`;

export default function AdminPage({ onBack, currentUser }) {
  const [authorized, setAuthorized] = useState(false);
  const [authType, setAuthType] = useState(null);
  const [secretInput, setSecretInput] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [authError, setAuthError] = useState("");
  const [verifying, setVerifying] = useState(false);

  // Diagnostics state
  const [loading, setLoading] = useState(false);
  const [runningProbes, setRunningProbes] = useState(false);
  const [diagnostics, setDiagnostics] = useState(null);
  const [incidents, setIncidents] = useState({ active: [], history: [] });
  const [lastChecked, setLastChecked] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [resolvingId, setResolvingId] = useState(null);
  const [expandedDetails, setExpandedDetails] = useState({});

  const refreshIntervalRef = useRef(null);

  // Check existing session authorization on mount
  const checkInitialAuth = useCallback(async () => {
    setVerifying(true);
    setAuthError("");
    try {
      const storedSecret = sessionStorage.getItem("admin_secret");
      const res = await adminApi.verifyAccess(storedSecret || "");
      if (res && res.authorized) {
        setAuthorized(true);
        setAuthType(res.auth_type);
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

  // Load diagnostics & incidents
  const loadDiagnostics = async (showProbeSpinner = false) => {
    if (showProbeSpinner) setRunningProbes(true);
    else setLoading(true);

    try {
      const healthRes = await adminApi.health();
      if (healthRes && healthRes.diagnostics) {
        setDiagnostics(healthRes.diagnostics);
        setIncidents(healthRes.diagnostics.incidents || { active: [], history: [] });
        setLastChecked(new Date().toLocaleTimeString());
      }
    } catch (err) {
      if (err.status === 403) {
        // Purge credentials and lock screen immediately
        sessionStorage.removeItem("admin_secret");
        setAuthorized(false);
        setAuthError("Session expired or permission revoked (403 Forbidden).");
      }
    } finally {
      setLoading(false);
      setRunningProbes(false);
    }
  };

  // Run forced live tests
  const runForcedTests = async () => {
    setRunningProbes(true);
    try {
      const res = await adminApi.testAll();
      if (res && res.diagnostics) {
        setDiagnostics(res.diagnostics);
        setIncidents(res.diagnostics.incidents || { active: [], history: [] });
        setLastChecked(new Date().toLocaleTimeString());
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

  // Auto-refresh timer (every 15s when active)
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

  // Manual unlock submission
  const handleUnlock = async (e) => {
    if (e) e.preventDefault();
    if (!secretInput.trim()) {
      setAuthError("Please enter your admin secret passphrase.");
      return;
    }

    setVerifying(true);
    setAuthError("");

    try {
      const res = await adminApi.verifyAccess(secretInput.trim());
      if (res && res.authorized) {
        sessionStorage.setItem("admin_secret", secretInput.trim());
        setAuthorized(true);
        setAuthType(res.auth_type);
        setSecretInput("");
        loadDiagnostics();
      }
    } catch (err) {
      setAuthError(
        err.status === 403
          ? "ACCESS DENIED: Invalid secret passphrase. Unauthorized access attempt recorded."
          : (err.message || "Failed to connect to verification gateway.")
      );
    } finally {
      setVerifying(false);
    }
  };

  // Lock and exit
  const handleLockConsole = () => {
    sessionStorage.removeItem("admin_secret");
    setAuthorized(false);
    setDiagnostics(null);
  };

  // Mark incident as resolved
  const handleResolve = async (incidentId) => {
    setResolvingId(incidentId);
    try {
      const res = await adminApi.resolveIncident(incidentId);
      if (res && res.incidents) {
        setIncidents(res.incidents);
      }
    } catch (err) {
      console.error("Failed to resolve incident:", err);
    } finally {
      setResolvingId(null);
    }
  };

  // Clear resolved history
  const handleClearResolved = async () => {
    try {
      const res = await adminApi.clearResolved();
      if (res && res.incidents) {
        setIncidents(res.incidents);
      }
    } catch (err) {
      console.error("Failed to clear resolved incidents:", err);
    }
  };

  const toggleDetails = (id) => {
    setExpandedDetails((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // -------------------------------------------------------------
  // VIEW 1: LOCKED SECURITY PERIMETER
  // -------------------------------------------------------------
  if (!authorized) {
    return (
      <div className="admin-root relative items-center justify-center p-4">
        <style>{styles}</style>
        <div className="admin-scanline" />

        {/* Ambient Glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

        <div className="relative w-full max-w-md admin-card p-8 shadow-2xl border-slate-800 bg-[#0c101a]/95 backdrop-blur-md">
          {/* Lock Header */}
          <div className="flex flex-col items-center text-center mb-7">
            <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center mb-4 text-indigo-400 shadow-[0_0_24px_rgba(99,102,241,0.25)]">
              <ShieldAlert className="w-8 h-8 text-indigo-400 admin-pulse-slow" />
            </div>
            <div className="text-[11px] font-bold uppercase tracking-widest text-indigo-400 admin-mono mb-1">
              ProtoPilot Security Perimeter
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Mission Control & Diagnostics
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-[280px]">
              Restricted console. Unauthorized access is strictly forbidden and monitored.
            </p>
          </div>

          {/* Error Message */}
          {authError && (
            <div className="mb-5 p-3 rounded-lg bg-red-950/40 border border-red-800/60 flex items-start gap-2.5 text-red-300 text-xs leading-relaxed animate-shake">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <span>{authError}</span>
            </div>
          )}

          {/* Key Input Form */}
          <form onSubmit={handleUnlock} className="space-y-4">
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 uppercase tracking-wider mb-1.5 admin-mono">
                Admin Master Passphrase
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showSecret ? "text" : "password"}
                  value={secretInput}
                  onChange={(e) => setSecretInput(e.target.value)}
                  placeholder="Enter secret key..."
                  className="w-full pl-9 pr-10 py-2.5 bg-slate-900/90 border border-slate-700/80 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 admin-mono transition"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowSecret(!showSecret)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300"
                >
                  {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {currentUser && (
              <div className="text-[11px] text-slate-500 flex items-center gap-1.5 px-1">
                <span>Account:</span>
                <span className="text-slate-300 font-medium admin-mono">{currentUser.email}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={verifying}
              className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-sm tracking-wide transition shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {verifying ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <Unlock className="w-4 h-4" />
                  <span>Authenticate & Unlock</span>
                </>
              )}
            </button>
          </form>

          {/* Back button */}
          <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
            <button
              type="button"
              onClick={onBack}
              className="flex items-center gap-1.5 hover:text-slate-300 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Application</span>
            </button>
            <span className="admin-mono text-[10px] text-slate-600">v0.3.0-SECURE</span>
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // VIEW 2: AUTHORIZED MISSION CONTROL CONSOLE
  // -------------------------------------------------------------
  const overallStatus = diagnostics?.overall_status || "healthy";
  const providers = diagnostics?.providers || [];
  const system = diagnostics?.system || {};
  const activeIncidents = incidents.active || [];
  const historicalIncidents = incidents.history || [];

  return (
    <div className="admin-root">
      <style>{styles}</style>

      {/* Top Mission Control Bar */}
      <header className="border-b border-slate-800 bg-[#0C101A] sticky top-0 z-30 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-bold text-white tracking-tight">
                ProtoPilot Mission Control
              </span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 admin-mono border border-indigo-500/30">
                ADMIN CONSOLE
              </span>
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-2">
              <span>Diagnostics & Problem Monitoring</span>
              {lastChecked && (
                <span className="text-slate-500 admin-mono text-[11px]">
                  • Updated {lastChecked}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5">
          {/* Status Badge */}
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold admin-mono border ${
              overallStatus === "healthy"
                ? "bg-emerald-950/40 text-emerald-400 border-emerald-800/60"
                : overallStatus === "degraded"
                ? "bg-amber-950/40 text-amber-400 border-amber-800/60"
                : "bg-red-950/40 text-red-400 border-red-800/60"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                overallStatus === "healthy"
                  ? "bg-emerald-500 animate-pulse"
                  : overallStatus === "degraded"
                  ? "bg-amber-500 animate-pulse"
                  : "bg-red-500 animate-ping"
              }`}
            />
            <span className="uppercase tracking-wider">
              {overallStatus === "healthy"
                ? "All Systems Operational"
                : overallStatus === "degraded"
                ? "Degraded Performance"
                : "Active Incidents Detected"}
            </span>
          </div>

          {/* Auto Refresh Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition flex items-center gap-1.5 ${
              autoRefresh
                ? "bg-slate-800/80 text-indigo-300 border-indigo-500/40"
                : "bg-slate-900 text-slate-400 border-slate-800"
            }`}
            title={autoRefresh ? "Auto-refresh is ON (every 15s)" : "Auto-refresh is paused"}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Auto (15s): {autoRefresh ? "ON" : "OFF"}</span>
          </button>

          {/* Probe Trigger */}
          <button
            onClick={runForcedTests}
            disabled={runningProbes}
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 shadow-md shadow-indigo-600/20"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${runningProbes ? "animate-spin" : ""}`} />
            <span>{runningProbes ? "Testing APIs..." : "Run Live Probes"}</span>
          </button>

          {/* Lock Console */}
          <button
            onClick={handleLockConsole}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition"
            title="Lock admin console and purge session credentials"
          >
            <Lock className="w-3.5 h-3.5" />
            <span>Lock</span>
          </button>

          {/* Exit to Main App */}
          <button
            onClick={onBack}
            className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Exit Admin</span>
          </button>
        </div>
      </header>

      {/* Main Dashboard Content */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        {/* KPI Metrics Strip */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="admin-card p-4 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                System Status
              </div>
              <div className="text-lg font-bold text-white capitalize">{overallStatus}</div>
            </div>
          </div>

          <div className="admin-card p-4 flex items-center gap-3.5">
            <div
              className={`w-10 h-10 rounded-xl border flex items-center justify-center ${
                activeIncidents.length > 0
                  ? "bg-red-500/10 border-red-500/30 text-red-400"
                  : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              }`}
            >
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Active Problems
              </div>
              <div
                className={`text-lg font-bold ${
                  activeIncidents.length > 0 ? "text-red-400" : "text-emerald-400"
                }`}
              >
                {activeIncidents.length}{" "}
                <span className="text-xs font-normal text-slate-400">issues</span>
              </div>
            </div>
          </div>

          <div className="admin-card p-4 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Host Memory & CPU
              </div>
              <div className="text-sm font-bold text-white admin-mono">
                {system.memory_rss_mb ? `${system.memory_rss_mb} MB` : "N/A"}
                <span className="text-xs font-normal text-slate-400 ml-1.5">
                  ({system.cpu_percent != null ? `${system.cpu_percent}% CPU` : ""})
                </span>
              </div>
            </div>
          </div>

          <div className="admin-card p-4 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Incident History
              </div>
              <div className="text-lg font-bold text-white">
                {historicalIncidents.length}{" "}
                <span className="text-xs font-normal text-slate-400">resolved</span>
              </div>
            </div>
          </div>
        </div>

        {/* ------------------------------------------------------------- */}
        {/* SECTION 1: LIVE DEPENDENCY HEALTH PROBES                      */}
        {/* ------------------------------------------------------------- */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-bold text-white tracking-wide uppercase">
                Provider Health & Quota Probes
              </h2>
            </div>
            <span className="text-xs text-slate-400">
              Real-time connectivity and quota verification
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3.5">
            {providers.map((p, idx) => {
              const isHealthy = p.status === "healthy";
              const isWarning = p.status === "warning" || p.status === "rate_limited";
              const isCrit = !isHealthy && !isWarning;

              return (
                <div key={idx} className="admin-card p-4 flex flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span className="font-bold text-sm text-white tracking-tight">
                        {p.name}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase admin-mono border ${
                          isHealthy
                            ? "bg-emerald-950/50 text-emerald-400 border-emerald-800/60"
                            : isWarning
                            ? "bg-amber-950/50 text-amber-400 border-amber-800/60"
                            : "bg-red-950/50 text-red-400 border-red-800/60"
                        }`}
                      >
                        {p.status}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed mb-3">
                      {p.message || "Operational"}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 admin-mono">
                    <span>
                      {p.latency_ms != null ? `${p.latency_ms}ms` : p.quota || "online"}
                    </span>
                    {p.model && <span className="text-slate-400 truncate max-w-[90px]">{p.model}</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ------------------------------------------------------------- */}
        {/* SECTION 2: ACTIVE PROBLEMS (REASON & SOLUTION)                */}
        {/* ------------------------------------------------------------- */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-bold text-white tracking-wide uppercase">
                Active Problems & Solutions ({activeIncidents.length})
              </h2>
            </div>
            {activeIncidents.length > 0 && (
              <span className="text-xs text-amber-400 font-medium">
                Action required to restore optimal operation
              </span>
            )}
          </div>

          {activeIncidents.length === 0 ? (
            <div className="admin-card p-8 text-center flex flex-col items-center justify-center border-emerald-900/30 bg-emerald-950/10">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-3">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white mb-1">
                Zero Active Incidents
              </h3>
              <p className="text-xs text-slate-400 max-w-md leading-relaxed">
                All LLM providers (Groq, Gemini), Video Calling (LiveKit), Speech-to-Text
                (Sarvam), and PostgreSQL database are running normally with no active quota
                exhaustion or disconnections.
              </p>
            </div>
          ) : (
            <div className="space-y-3.5">
              {activeIncidents.map((inc) => {
                const isExpanded = expandedDetails[inc.id];
                const isResolving = resolvingId === inc.id;

                return (
                  <div
                    key={inc.id}
                    className="admin-card p-5 border-amber-900/40 bg-[#121624] space-y-3 relative overflow-hidden"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0 mt-0.5">
                          <AlertTriangle className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-200 admin-mono border border-slate-700">
                              {inc.category}
                            </span>
                            <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-950/60 text-amber-400 admin-mono border border-amber-800/60">
                              {inc.severity}
                            </span>
                            {inc.occurrences > 1 && (
                              <span className="text-xs font-bold px-2 py-0.5 rounded bg-red-950/60 text-red-300 admin-mono border border-red-800/60">
                                {inc.occurrences}x occurrences
                              </span>
                            )}
                            <span className="text-[11px] text-slate-500 admin-mono">
                              {inc.timestamp ? new Date(inc.timestamp).toLocaleTimeString() : ""}
                            </span>
                          </div>
                          <h3 className="text-base font-bold text-white tracking-tight">
                            {inc.title}
                          </h3>
                        </div>
                      </div>

                      {/* Resolve Action */}
                      <button
                        onClick={() => handleResolve(inc.id)}
                        disabled={isResolving}
                        className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 active:bg-emerald-800 text-white text-xs font-semibold flex items-center gap-1.5 transition shrink-0 shadow-md shadow-emerald-700/20"
                        title="Mark this issue as solved"
                      >
                        {isResolving ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Check className="w-3.5 h-3.5" />
                        )}
                        <span>Mark Resolved</span>
                      </button>
                    </div>

                    {/* Reason & Solution Dual Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                      {/* Exact Reason */}
                      <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                        <div className="text-[11px] font-bold text-red-400 uppercase tracking-wider flex items-center gap-1.5 mb-1 admin-mono">
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Exact Reason / Kyun Hua</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">{inc.reason}</p>
                      </div>

                      {/* Actionable Solution */}
                      <div className="p-3.5 rounded-lg bg-indigo-950/30 border border-indigo-800/40">
                        <div className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5 mb-1 admin-mono">
                          <Zap className="w-3.5 h-3.5" />
                          <span>Actionable Solution / Kaise Fix Karein</span>
                        </div>
                        <p className="text-xs text-indigo-200 leading-relaxed">{inc.solution}</p>
                      </div>
                    </div>

                    {/* Raw Details Accordion */}
                    {inc.raw_details && (
                      <div>
                        <button
                          onClick={() => toggleDetails(inc.id)}
                          className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center gap-1 admin-mono"
                        >
                          {isExpanded ? (
                            <>
                              <ChevronUp className="w-3 h-3" /> Hide Technical Log
                            </>
                          ) : (
                            <>
                              <ChevronDown className="w-3 h-3" /> View Technical Log Snippet
                            </>
                          )}
                        </button>
                        {isExpanded && (
                          <div className="mt-2 p-2.5 rounded bg-black/60 border border-slate-800 text-[11px] text-slate-300 admin-mono break-all whitespace-pre-wrap">
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

        {/* ------------------------------------------------------------- */}
        {/* SECTION 3: INCIDENT HISTORY & AUDIT LOG                       */}
        {/* ------------------------------------------------------------- */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-purple-400" />
              <h2 className="text-sm font-bold text-white tracking-wide uppercase">
                Incident History & Audit Log ({historicalIncidents.length})
              </h2>
            </div>
            {historicalIncidents.length > 0 && (
              <button
                onClick={handleClearResolved}
                className="text-xs text-slate-400 hover:text-red-400 flex items-center gap-1 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Resolved History</span>
              </button>
            )}
          </div>

          {historicalIncidents.length === 0 ? (
            <div className="admin-card p-6 text-center text-xs text-slate-500">
              No historical incidents recorded.
            </div>
          ) : (
            <div className="space-y-2">
              {historicalIncidents.map((h, i) => (
                <div
                  key={i}
                  className="admin-card p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-slate-600 shrink-0" />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{h.title}</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 admin-mono">
                          {h.category}
                        </span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-0.5 line-clamp-1">
                        Reason: {h.reason}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-[11px] text-slate-500 admin-mono shrink-0">
                    <div>Logged: {h.timestamp ? new Date(h.timestamp).toLocaleDateString() : ""}</div>
                    {h.resolved_at && (
                      <div className="text-emerald-400">
                        Resolved: {new Date(h.resolved_at).toLocaleTimeString()}
                      </div>
                    )}
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
