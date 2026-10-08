import React, { useState, useEffect, useRef } from "react";
import { Mic, MicOff, Maximize2, PhoneOff, GripVertical, Radio } from "lucide-react";

/* ============================================================
   ProtoPilot — Floating Mini Meeting Window (Picture-in-Picture)
   
   Allows the user to minimize a live meeting while navigating
   anywhere in the application (Dashboard, Workforce, Pipeline, etc.)
   without dropping the LiveKit WebRTC connection or transcription.
   
   - Draggable anywhere inside the viewport.
   - Shows live meeting status, elapsed time, and audio indicator.
   - Click to restore to full meeting room immediately.
   - Quick mute / hang up controls.
   ============================================================ */

export default function FloatingMiniMeetingWindow({
  meetingId,
  meetingTitle = "Live Meeting",
  isHost = true,
  onRestore,
  onHangUp,
  micOn = true,
  onToggleMic,
}) {
  const [position, setPosition] = useState(() => {
    // Default position: bottom-right corner with 24px padding
    const width = 290;
    const height = 130;
    const initialX = typeof window !== "undefined" ? Math.max(20, window.innerWidth - width - 28) : 800;
    const initialY = typeof window !== "undefined" ? Math.max(20, window.innerHeight - height - 32) : 600;
    return { x: initialX, y: initialY };
  });

  const [isDragging, setIsDragging] = useState(false);
  const dragOffsetRef = useRef({ x: 0, y: 0 });
  const [elapsed, setElapsed] = useState("00:00:00");
  const startedAtRef = useRef(Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      const diff = Math.max(0, Math.floor((Date.now() - startedAtRef.current) / 1000));
      const h = String(Math.floor(diff / 3600)).padStart(2, "0");
      const m = String(Math.floor((diff % 3600) / 60)).padStart(2, "0");
      const s = String(diff % 60).padStart(2, "0");
      setElapsed(`${h}:${m}:${s}`);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleMouseDown = (e) => {
    // Only drag when clicking the drag handle or window frame, not buttons
    if (e.target.closest("button") || e.target.closest(".mini-btn")) return;
    setIsDragging(true);
    dragOffsetRef.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      const width = 290;
      const height = 130;
      const maxX = window.innerWidth - width - 10;
      const maxY = window.innerHeight - height - 10;

      const newX = Math.min(Math.max(10, e.clientX - dragOffsetRef.current.x), maxX);
      const newY = Math.min(Math.max(10, e.clientY - dragOffsetRef.current.y), maxY);

      setPosition({ x: newX, y: newY });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div
      onMouseDown={handleMouseDown}
      style={{
        position: "fixed",
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: 290,
        zIndex: 99999,
        background: "rgba(18, 20, 28, 0.94)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderRadius: 18,
        border: "1px solid rgba(255, 255, 255, 0.16)",
        boxShadow: "0 22px 60px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(0, 230, 168, 0.2)",
        cursor: isDragging ? "grabbing" : "grab",
        userSelect: "none",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        overflow: "hidden",
        animation: "miniFadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) both",
      }}
    >
      <style>{`
        @keyframes miniFadeIn {
          from { opacity: 0; transform: scale(0.9) translateY(10px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
        @keyframes miniPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.9); }
        }
        .mini-btn {
          width: 32px; height: 32px; border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          cursor: pointer; border: 1px solid rgba(255, 255, 255, 0.14);
          background: rgba(255, 255, 255, 0.08); color: #fff;
          transition: all 0.15s ease;
        }
        .mini-btn:hover {
          background: rgba(255, 255, 255, 0.18);
          transform: scale(1.06);
        }
        .mini-btn.hangup {
          background: #DC2626; border-color: #DC2626;
        }
        .mini-btn.hangup:hover {
          background: #EF4444; border-color: #EF4444;
        }
        .mini-btn.primary {
          background: #00C88A; border-color: #00C88A; color: #04251B;
        }
        .mini-btn.primary:hover {
          background: #00E6A8; border-color: #00E6A8;
        }
      `}</style>

      {/* Header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px 6px",
          borderBottom: "1px solid rgba(255, 255, 255, 0.07)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <div
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "#00E6A8",
              boxShadow: "0 0 8px rgba(0, 230, 168, 0.9)",
              animation: "miniPulse 1.4s infinite ease-in-out",
            }}
          />
          <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.06em", color: "#00E6A8", textTransform: "uppercase" }}>
            Live Call
          </span>
          <span style={{ fontSize: 10.5, color: "#8E93A6", fontFamily: "monospace", marginLeft: 4 }}>
            {elapsed}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#6A6E82" }}>
          <GripVertical size={13} style={{ cursor: "grab" }} />
        </div>
      </div>

      {/* Content body - Clickable to restore full meeting */}
      <div
        onClick={onRestore}
        title="Click to return to meeting room"
        style={{
          padding: "10px 14px 12px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 10,
        }}
      >
        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "#F4F5F8",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {meetingTitle}
          </div>
          <div style={{ fontSize: 10.5, color: "#9599AB", marginTop: 2, display: "flex", alignItems: "center", gap: 5 }}>
            <span>{isHost ? "Host Controls Active" : "Participant Audio Connected"}</span>
          </div>
        </div>

        {/* Quick Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: 7, flexShrink: 0 }} onClick={(e) => e.stopPropagation()}>
          {onToggleMic && (
            <button
              type="button"
              className="mini-btn"
              onClick={onToggleMic}
              title={micOn ? "Mute Microphone" : "Unmute Microphone"}
              style={{ background: micOn ? "rgba(255,255,255,0.08)" : "rgba(220, 38, 38, 0.85)" }}
            >
              {micOn ? <Mic size={14} /> : <MicOff size={14} color="#fff" />}
            </button>
          )}

          <button
            type="button"
            className="mini-btn primary"
            onClick={onRestore}
            title="Expand / Return to Meeting Room"
          >
            <Maximize2 size={13} />
          </button>

          <button
            type="button"
            className="mini-btn hangup"
            onClick={onHangUp}
            title="End / Leave Call"
          >
            <PhoneOff size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}
