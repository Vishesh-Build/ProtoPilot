/* ============================================================
   ProtoPilot — API client

   Centralizes the backend base URL and the fetch boilerplate every
   auth call needs (credentials: "include" is required so the
   httpOnly session cookies actually get sent/received).

   Change API_BASE_URL once here (e.g. when you deploy the backend
   to a real domain) instead of hunting through every page.
   ============================================================ */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

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

  delete: (meetingId) => request(`/meetings/${meetingId}`, { method: "DELETE" }),

  agentOutputs: (meetingId) => request(`/meetings/${meetingId}/agent-outputs`),

  exportStatus: (meetingId) => request(`/meetings/${meetingId}/export/status`),

  exportUrl: (meetingId) => `${API_BASE_URL}/meetings/${meetingId}/export`,

  transcriptSocketUrl: (meetingId) =>
    `${API_BASE_URL.replace(/^http/, "ws")}/ws/meeting/${meetingId}`,

  generateSocketUrl: (meetingId) =>
    `${API_BASE_URL.replace(/^http/, "ws")}/ws/meeting/${meetingId}/generate`,
};

export { ApiError };