/* ============================================================
   ProtoPilot — API client

   Centralizes the backend base URL and the fetch boilerplate every
   auth call needs (credentials: "include" is required so the
   httpOnly session cookies actually get sent/received).

   Change API_BASE_URL once here (e.g. when you deploy the backend
   to a real domain) instead of hunting through every page.
   ============================================================ */

export const API_BASE_URL =
  (typeof window !== "undefined" &&
    window.protopilotDesktop &&
    window.protopilotDesktop.apiBaseUrl) || // Electron: runtime-configurable (main.cjs)
  import.meta.env.VITE_API_BASE_URL || // plain browser/Vite build
  "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

/* ------------------------------------------------------------
   Silent session renewal.

   The access_token cookie expires (default a few hours) long before the
   refresh_token cookie (30 days). The backend exposes POST /auth/refresh
   which rotates both cookies, but until now the frontend never called
   it — a 30-minute meeting always ended in a forced logout.

   On a 401, we try ONE refresh and replay the original request. Auth
   endpoints themselves never trigger a refresh (their 401 is a real
   "wrong credentials" / "expired reset link", and retrying them would
   loop). Concurrent 401s share a single refresh call — without that, a
   burst of parallel requests would stampede the refresh endpoint and
   the second one would invalidate the first's freshly rotated cookie.
   ------------------------------------------------------------ */
let _refreshInFlight = null;

async function refreshSession() {
  if (!_refreshInFlight) {
    _refreshInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) return false;
        return true;
      } catch {
        return false;
      } finally {
        // Keep the promise cached only while it is pending; the next 401
        // (e.g. after the new access token also expires) must be able to
        // refresh again.
        setTimeout(() => { _refreshInFlight = null; }, 0);
      }
    })();
  }
  return _refreshInFlight;
}

const _NO_REFRESH = new Set([
  "/auth/login",
  "/auth/register",
  "/auth/refresh",
  "/auth/logout",
  "/auth/forgot-password",
  "/auth/reset-password",
]);

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(
      "Can't reach the server — check your connection and that the backend is running.",
      0
    );
  }

  // Access token expired mid-session: silently renew once and replay.
  if (res.status === 401 && !_NO_REFRESH.has(path)) {
    const renewed = await refreshSession();
    if (renewed) {
      try {
        res = await fetch(`${API_BASE_URL}${path}`, {
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          ...options,
        });
      } catch {
        throw new ApiError(
          "Can't reach the server — check your connection and that the backend is running.",
          0
        );
      }
    }
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    // No JSON body (e.g. 204) — fine for some endpoints.
  }

  if (!res.ok) {
    const message =
      (data && (data.detail || data.message)) ||
      `Request failed (${res.status})`;
    throw new ApiError(message, res.status);
  }

  return data;
}

export const authApi = {
  register: (name, email, password) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    }),

  login: (email, password) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () => request("/auth/logout", { method: "POST" }),

  me: () => request("/auth/me"),

  forgotPassword: (email) =>
    request("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  resetPassword: (token, newPassword) =>
    request("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    }),
};

export const meetingsApi = {
  create: (meetingId, name) =>
    request("/meetings", {
      method: "POST",
      body: JSON.stringify({ meeting_id: meetingId, name }),
    }),

  get: (meetingId) => request(`/meetings/${meetingId}`),

  end: (meetingId) => request(`/meetings/${meetingId}/end`, { method: "POST" }),

  getLiveKitToken: (meetingId) =>
    request(`/meetings/${meetingId}/livekit-token`, { method: "POST" }),

  startCall: (meetingId) =>
    request(`/meetings/${meetingId}/start-call`, { method: "POST" }),

  stopCall: (meetingId) =>
    request(`/meetings/${meetingId}/stop-call`, { method: "POST" }),

  listRequirements: (meetingId) => request(`/meetings/${meetingId}/requirements`),

  addRequirement: (meetingId, title) =>
    request(`/meetings/${meetingId}/requirements`, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),

  updateRequirementStatus: (meetingId, requirementId, status) =>
    request(`/meetings/${meetingId}/requirements/${requirementId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  updateRequirementTitle: (meetingId, requirementId, title) =>
    request(`/meetings/${meetingId}/requirements/${requirementId}/title`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),

  list: () => request("/meetings"),

  rename: (meetingId, name) =>
    request(`/meetings/${meetingId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),

  delete: (meetingId) => request(`/meetings/${meetingId}`, { method: "DELETE" }),

  agentOutputs: (meetingId) => request(`/meetings/${meetingId}/agent-outputs`),

  exportStatus: (meetingId) => request(`/meetings/${meetingId}/export/status`),

  exportUrl: (meetingId) => `${API_BASE_URL}/meetings/${meetingId}/export`,

  transcriptSocketUrl: (meetingId) =>
    `${API_BASE_URL.replace(/^http/, "ws")}/ws/meeting/${meetingId}`,

  // force=true skips the backend's replay-of-existing-outputs guard, so the
  // host pressing "Regenerate" re-runs over the currently-approved
  // requirements (picking up anything approved since the last build) instead
  // of getting the stale prototype back. Opening it without force is a plain
  // (free) replay of what's already there.
  generateSocketUrl: (meetingId, { force = false } = {}) =>
    `${API_BASE_URL.replace(/^http/, "ws")}/ws/meeting/${meetingId}/generate${force ? "?force=1" : ""}`,
};

export { ApiError };