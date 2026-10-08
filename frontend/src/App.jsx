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
import AdminPage from "./pages/AdminPage.jsx";
import UpdateNotification from "./components/UpdateNotification.jsx";
import CosmicOrbLoader from "./components/CosmicOrbLoader.jsx";
import FloatingMiniMeetingWindow from "./components/FloatingMiniMeetingWindow.jsx";
import { authApi, meetingsApi, API_BASE_URL, setStoredToken } from "./lib/api.js";

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
  const rawOAuthToken = params.get("oauth_token") || params.get("token") || params.get("access_token");
  const oauthToken = rawOAuthToken ? rawOAuthToken.trim().replace(/^["']|["']$/g, "") : null;
  const cameFromOAuth = params.get("oauth") === "success" || Boolean(oauthToken);
  if (oauthToken) {
    setStoredToken(oauthToken);
    try {
      window.history.replaceState({}, document.title, window.location.pathname);
    } catch {}
    if (typeof window !== "undefined" && !window.protopilotDesktop) {
      try {
        window.location.href = `protopilot://auth-callback?oauth=success&oauth_token=${encodeURIComponent(oauthToken)}`;
      } catch (e) {}
    }
  }
  const tokenParam = params.get("token");
  // Only treat tokenParam as password reset token if not coming from OAuth
  const initialResetToken = !cameFromOAuth && tokenParam ? tokenParam : null;
  const wantsAdmin = params.get("page") === "admin" || params.get("admin") === "1";

  const [page, setPage] = useState(
    initialResetToken ? "reset" : cameFromOAuth ? "dashboard" : wantsAdmin ? "admin" : "home"
  );
  const [resetToken, setResetToken] = useState(initialResetToken);
  const [currentUser, setCurrentUser] = useState(null);
  const [sessionCheckDone, setSessionCheckDone] = useState(Boolean(initialResetToken));
  const [showSplash, setShowSplash] = useState(!initialResetToken);

  const [activeMeetingId, setActiveMeetingId] = useState(null);
  const [isMeetingHost, setIsMeetingHost] = useState(true);

  // Global secret shortcut (Ctrl + Shift + A) to open/toggle Admin Console
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "A" || e.key === "a")) {
        e.preventDefault();
        setPage((prev) => (prev === "admin" ? (currentUser ? "dashboard" : "home") : "admin"));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentUser]);

  // Global OAuth token handler from deep-links or external browser redirect
  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      window.protopilotDesktop &&
      typeof window.protopilotDesktop.onOAuthTokenReceived === "function"
    ) {
      const unsub = window.protopilotDesktop.onOAuthTokenReceived(async ({ token }) => {
        if (token) {
          const clean = token.trim().replace(/^["']|["']$/g, "");
          setStoredToken(clean);
          try {
            const user = await authApi.me(clean);
            setCurrentUser(user);
            setPage("dashboard");
          } catch (e) {
            console.error("[App] Failed to load user profile with OAuth token:", e);
          }
        }
      });
      return unsub;
    }
  }, []);


  // True while a live call should stay connected in the background. The app
  // renders one page at a time, so without this, navigating from the meeting
  // to the Workforce/Pipeline/Prototype pages unmounts LiveMeetingCall and
  // drops the LiveKit room (and restarts the transcription bot) — the "call
  // drops when I open the pipeline" bug. We keep it mounted (just hidden)
  // while a meeting is live, and only tear it down on an explicit Back / Hang
  // up or when navigating out to a non-meeting page.
  const [meetingLive, setMeetingLive] = useState(false);

  // Why the pipeline was opened: "run" (host pressed Generate/Regenerate —
  // actually build) vs "view" (just navigated in to look — replay the built
  // one, never start a paid run). Defaults to "view" so no navigation can
  // accidentally kick off generation; only the explicit button sets "run".
  const [pipelineIntent, setPipelineIntent] = useState("view");

  const [liveAgents, setLiveAgents] = useState({});
  const [liveOutputs, setLiveOutputs] = useState({});
  const [liveLogs, setLiveLogs] = useState({});

  useEffect(() => {
    if (initialResetToken) return;
    let cancelled = false;

    // Strict safety timer: never block app startup for more than 2500ms
    const safetyTimer = setTimeout(() => {
      if (!cancelled) {
        setSessionCheckDone(true);
      }
    }, 2500);

    authApi
      .me()
      .then((user) => {
        if (cancelled) return;
        setCurrentUser(user);
        setPage((p) => {
          if (p === "admin") return "admin";
          return p === "home" || cameFromOAuth ? "dashboard" : p;
        });
      })
      .catch(() => {
        if (cancelled) return;
        if (cameFromOAuth) {
          setPage("login");
        }
      })
      .finally(() => {
        clearTimeout(safetyTimer);
        if (!cancelled) setSessionCheckDone(true);
        if (!cancelled && cameFromOAuth) {
          try {
            window.history.replaceState({}, "", window.location.pathname);
          } catch {}
        }
      });

    return () => {
      cancelled = true;
      clearTimeout(safetyTimer);
    };
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
    setMeetingLive(false);
    setPage("home");
  };

  const handleGenerationUpdate = useCallback((agents, outputs, logs) => {
    setLiveAgents(agents || {});
    if (outputs) setLiveOutputs(outputs);
    if (logs) setLiveLogs(logs);
  }, []);

  const startNewMeeting = () => {
    setActiveMeetingId(generateMeetingId());
    setIsMeetingHost(true);
    setLiveAgents({});
    setLiveOutputs({});
    setLiveLogs({});
    setMeetingLive(true);
    setPage("live");
  };

  const resumeMeeting = async (meetingId) => {
    setActiveMeetingId(meetingId);
    try {
      const data = await meetingsApi.get(meetingId);
      const isHost = Boolean(
        !data.host_user_id || (currentUser && data.host_user_id === currentUser.id)
      );
      setIsMeetingHost(isHost);
    } catch (err) {
      console.warn("[App] Error checking host on resume:", err);
      // Resumed from user's own dashboard — default to host true so controls are never blocked
      setIsMeetingHost(true);
    }
    setMeetingLive(true);
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
    setLiveLogs({});
    setMeetingLive(true);
    setPage("live");
  };

  // Minimize meeting back to dashboard (or previous page) without ending call
  const minimizeMeeting = () => {
    setPage("dashboard");
  };

  // Restore mini meeting window back to full meeting view
  const restoreMeeting = () => {
    setPage("live");
  };

  // Explicit Hang Up / End Meeting — cleanly tears down LiveKit room
  const endLiveMeeting = () => {
    setMeetingLive(false);
    setActiveMeetingId(null);
    setPage("dashboard");
  };

  // Navigate between app pages while keeping live call active via floating mini window!
  const navigate = (target) => {
    if (target === "pipeline") setPipelineIntent("view");
    // Only disconnect call if navigating out to authentication pages
    if (["home", "login", "register", "forgot", "reset"].includes(target)) {
      setMeetingLive(false);
      setActiveMeetingId(null);
    }
    setPage(target);
  };

  const liveCallProps = {
    meetingId: activeMeetingId,
    currentUser,
    isHost: isMeetingHost,
    onBack: minimizeMeeting,
    onMinimize: minimizeMeeting,
    onHangUp: endLiveMeeting,
    onGeneratePrototype: () => { setPipelineIntent("run"); setPage("pipeline"); },
    onViewPrototype: () => setPage("viewer"),
    onOpenWorkforce: () => navigate("workforce"),
    onOpenPipeline: () => navigate("pipeline"),
  };

  // The persistent live call. Rendered once and kept mounted across every
  // meeting sub-page so the LiveKit room, the mic, and the caption feed
  // survive navigation. Shown only on the "live" page (display:contents keeps
  // its own full-screen layout intact); hidden — but still connected — while
  // the host is on Dashboard/Workforce/Pipeline/Prototype with floating window.
  const persistentLiveCall =
    meetingLive && activeMeetingId ? (
      <div style={{ display: page === "live" ? "contents" : "none" }}>
        <LiveMeetingCall {...liveCallProps} />
      </div>
    ) : null;

  const currentPage = (() => {
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
        // Normally rendered by persistentLiveCall above. This fallback only
        // fires if "live" is somehow shown without an active meeting, so we
        // never mount two LiveMeetingCall instances at once.
        return persistentLiveCall ? null : <LiveMeetingCall {...liveCallProps} />;

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
            onOpenAdmin={() => setPage("admin")}
          />
        );

      case "workforce":
        return <AIWorkforcePage liveAgents={liveAgents} liveOutputs={liveOutputs} liveLogs={liveLogs} onNavigate={navigate} />;

      case "pipeline":
        return <GenerationPipelinePage meetingId={activeMeetingId} intent={pipelineIntent} onNavigate={navigate} onGenerationUpdate={handleGenerationUpdate} />;

      case "viewer":
        return <PrototypeViewerPage meetingId={activeMeetingId} onNavigate={navigate} onOpenPipeline={() => navigate("pipeline")} />;

      case "admin":
        return (
          <AdminPage
            currentUser={currentUser}
            onBack={() => {
              if (wantsAdmin && !currentUser) {
                setPage("home");
              } else {
                setPage(currentUser ? "dashboard" : "home");
              }
            }}
          />
        );

      case "home":
      default:
        return (
          <HomePage
            onLogin={() => setPage("login")}
            onRegister={() => setPage("register")}
            onGetStarted={() => setPage("register")}
            onOpenAdmin={() => setPage("admin")}
          />
        );
    }
  })();

  return (
    <>
      {persistentLiveCall}
      {meetingLive && activeMeetingId && page !== "live" && (
        <FloatingMiniMeetingWindow
          meetingId={activeMeetingId}
          meetingTitle="Live Meeting"
          isHost={isMeetingHost}
          onRestore={restoreMeeting}
          onHangUp={endLiveMeeting}
        />
      )}
      {currentPage}
      <UpdateNotification />
      {showSplash && (
        <CosmicOrbLoader
          isReady={sessionCheckDone}
          onFinish={() => setShowSplash(false)}
        />
      )}
    </>
  );
}
