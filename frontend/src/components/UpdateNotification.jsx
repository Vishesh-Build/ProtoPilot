import React, { useEffect, useState } from "react";

/* ============================================================
   ProtoPilot — Auto-update notification

   A tiny floating pill in the bottom-right corner, shown ONLY in
   the packaged desktop app and ONLY when the main process reports
   an update is downloading or ready. In a browser (no
   window.protopilotDesktop) or when there's nothing to update, it
   renders nothing.

   Flow (state comes from electron main via preload):
     - "downloading" → subtle "Downloading update…" text
     - "ready"       → "Update ready" + a Restart button the user
                        clicks when convenient (never forced)

   Just like VS Code / Claude: no popup, no interruption — a quiet
   button that appears only when there's genuinely a new version.
   ============================================================ */

export default function UpdateNotification() {
  const desktop = typeof window !== "undefined" ? window.protopilotDesktop : null;
  const [state, setState] = useState(null);

  useEffect(() => {
    if (!desktop || !desktop.onUpdateState) return;

    // Get whatever the main process already knows (in case an update
    // finished downloading before this component mounted).
    desktop.getUpdateState?.().then(setState).catch(() => {});

    // Subscribe to live updates; unsubscribe on unmount.
    const unsubscribe = desktop.onUpdateState(setState);
    return unsubscribe;
  }, [desktop]);

  if (!desktop || !state) return null;

  const { status, version, percent } = state;
  if (status !== "downloading" && status !== "ready") return null;

  const wrap = {
    position: "fixed",
    bottom: 20,
    right: 20,
    zIndex: 9999,
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "10px 14px",
    borderRadius: 12,
    background: "rgba(17, 24, 39, 0.96)",
    color: "#fff",
    boxShadow: "0 8px 30px rgba(0,0,0,0.35)",
    fontSize: 13,
    fontFamily: "system-ui, sans-serif",
    maxWidth: 340,
  };

  if (status === "downloading") {
    return (
      <div style={wrap}>
        <span>
          Downloading update{typeof percent === "number" ? ` ${percent}%` : "…"}
        </span>
      </div>
    );
  }

  // status === "ready"
  return (
    <div style={wrap}>
      <span>
        Update {version ? `${version} ` : ""}ready to install
      </span>
      <button
        onClick={() => desktop.installUpdate?.()}
        style={{
          border: "none",
          borderRadius: 8,
          padding: "6px 12px",
          background: "#6366f1",
          color: "#fff",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        Restart to update
      </button>
    </div>
  );
}
