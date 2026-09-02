import React, { useEffect, useState, useCallback } from "react";

import HomePage from "./pages/HomePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.jsx";
import ResetPasswordPage from "./pages/ResetPasswordPage.jsx";
import LiveMeetingCall from "./pages/LiveMeetingCall.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import AIWorkforcePage from "./pages/AIWorkforcePage.jsx";
import GenerationPipelinePage from "./pages/GenerationPipelinePage.jsx";
import PrototypeViewerPage from "./pages/PrototypeViewerPage.jsx";
import { authApi, meetingsApi, API_BASE_URL } from "./lib/api.js";

/* ============================================================
   ProtoPilot — App shell

   Pages: home → login → register → forgot → reset → dashboard
   → live → workforce → pipeline → viewer

   Meeting identity: `activeMeetingId` is generated here (once)
   when starting a NEW meeting, and passed down to every screen
   so they all agree on the same real backend meeting. Resuming an
   existing meeting from Dashboard's history passes its real id
   in instead of generating one, and looks up whether the current
   user is actually its host before handing over host controls.

   Generation state (agents/outputs) is lifted from
   GenerationPipelinePage here via onGenerationUpdate, so AI
   Workforce still shows the same live/final data if the user
   navigates there afterward — GenerationPipelinePage owns the
   actual WebSocket connection (opening it is what starts the
   real backend pipeline), this component just remembers the
   latest state.
   ============================================================ */

function getSearchParams() {
  if (typeof window === "undefined") return new URLSearchParams();
  return new URLSearchParams(window.location.search);
}

function generateMeetingId() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `meeting-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function App() {
  const params = getSearchParams();
  const initialToken = params.get("token");
  const cameFromOAuth = params.get("oauth") === "success";

  const [page, setPage] = useState(initialToken ? "reset" : "home");
  const [resetToken, setResetToken] = useState(initialToken);
  const [currentUser, setCurrentUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(!initialToken);

  const [activeMeetingId, setActiveMeetingId] = useState(null);
  const [isMeetingHost, setIsMeetingHost] = useState(true);

  const [liveAgents, setLiveAgents] = useState({});
  const [liveOutputs, setLiveOutputs] = useState({});

  useEffect(() => {
    if (initialToken) return;
    let cancelled = false;
    authApi
      .me()
      .then((user) => {
        if (cancelled) return;
        setCurrentUser(user);
        setPage((p) => (p === "home" || cameFromOAuth ? "dashboard" : p));
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setCheckingSession(false);
        if (!cancelled && cameFromOAuth) window.history.replaceState({}, "", window.location.pathname);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const goToLogin = () => {
    setResetToken(null);
    setPage("login");
  };

  const handleLoggedIn = (user) => {
    setCurrentUser(user);
    setPage("dashboard");
  };

  const handleLogout = async () => {
    await authApi.logout().catch(() => {});
    setCurrentUser(null);
    setActiveMeetingId(null);
    setPage("home");
  };

  const handleGenerationUpdate = useCallback((agents, outputs) => {
    setLiveAgents(agents || {});
    if (outputs) setLiveOutputs(outputs);
  }, []);

  const startNewMeeting = () => {
    setActiveMeetingId(generateMeetingId());
    setIsMeetingHost(true);
    setLiveAgents({});
    setLiveOutputs({});
    setPage("live");
  };

  const resumeMeeting = async (meetingId) => {
    setActiveMeetingId(meetingId);
    try {
      const res = await fetch(`${API_BASE_URL}/meetings/${meetingId}`, { credentials: "include" });
      const data = await res.json();
      setIsMeetingHost(Boolean(currentUser && data.host_user_id === currentUser.id));
    } catch {
      setIsMeetingHost(false);
    }
    setPage("live");
  };

  // Someone else's meeting: they paste the meeting ID the host shared
  // (copied from the live meeting header). We just confirm the meeting
  // actually exists on the backend (host must have started it already —
  // meetingsApi.create() runs as part of the host's own connect flow)
  // and never make the joiner the host, regardless of who created it.
  const joinMeeting = async (meetingId) => {
    const session = await meetingsApi.get(meetingId); // throws ApiError (404) if not found — caller shows it
    setActiveMeetingId(meetingId);
    setIsMeetingHost(Boolean(currentUser && session.host_user_id === currentUser.id));
    setLiveAgents({});
    setLiveOutputs({});
    setPage("live");
  };

  const navigate = (target) => setPage(target);

  if (checkingSession) return null;

  switch (page) {
    case "login":
      return (
        <LoginPage
          onLogin={handleLoggedIn}
          onGoRegister={() => setPage("register")}
          onForgotPassword={() => setPage("forgot")}
        />
      );

    case "register":
      return <RegisterPage onRegister={handleLoggedIn} onGoLogin={() => setPage("login")} />;

    case "forgot":
      return <ForgotPasswordPage onBackToLogin={() => setPage("login")} />;

    case "reset":
      return <ResetPasswordPage token={resetToken} onBackToLogin={goToLogin} onResetComplete={goToLogin} />;

    case "live":
      return (
        <LiveMeetingCall
          meetingId={activeMeetingId}
          currentUser={currentUser}
          isHost={isMeetingHost}
          onBack={() => setPage("dashboard")}
          onHangUp={() => setPage("dashboard")}
          onGeneratePrototype={() => setPage("pipeline")}
        />
      );

    case "dashboard":
      return (
        <DashboardPage
          currentUser={currentUser}
          onLogout={handleLogout}
          onNewMeeting={startNewMeeting}
          onResumeMeeting={resumeMeeting}
          onJoinMeeting={joinMeeting}
          onOpenWorkforce={() => setPage("workforce")}
          onOpenPrototype={(meetingId) => {
            if (meetingId) setActiveMeetingId(meetingId);
            setPage("viewer");
          }}
        />
      );

    case "workforce":
      return <AIWorkforcePage liveAgents={liveAgents} liveOutputs={liveOutputs} onNavigate={navigate} />;

    case "pipeline":
      return <GenerationPipelinePage meetingId={activeMeetingId} onNavigate={navigate} onGenerationUpdate={handleGenerationUpdate} />;

    case "viewer":
      return <PrototypeViewerPage meetingId={activeMeetingId} onNavigate={navigate} onOpenPipeline={() => setPage("pipeline")} />;

    case "home":
    default:
      return (
        <HomePage
          onLogin={() => setPage("login")}
          onRegister={() => setPage("register")}
          onGetStarted={() => setPage("register")}
        />
      );
  }
}
