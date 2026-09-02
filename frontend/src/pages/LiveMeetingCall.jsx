import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  ChevronLeft, ChevronRight, Mic, MicOff, Video, VideoOff, Monitor, MonitorOff,
  Copy, PhoneOff, X, Check, Zap, Settings, Smile, Send, Sparkles, Loader2, AlertCircle,
  Pencil,
} from "lucide-react";
import { Room, RoomEvent, Track } from "livekit-client";
import { meetingsApi, ApiError } from "../lib/api.js";

/* ============================================================
   ProtoPilot — Live Meeting Call

   Real LiveKit video/audio + real per-participant transcription
   (via the backend's /ws/meeting/{id} broadcast socket) + real
   requirement accept/reject synced to the backend + real chat
   over LiveKit's data channel.

   Removed from the original mock: the "X wants to join" banner —
   it wasn't backed by any real waiting-room mechanism, and per
   the "nothing fake" rule it's gone rather than left as a decal.
   A real waiting-room/admit flow is a genuine follow-up feature,
   not something to fake in the meantime.

   Required props now: meetingId, currentUser, isHost — the parent
   (App.jsx) generates/holds meetingId and passes it down; without
   real backend context this component doesn't have a meeting to
   attach to.
   ============================================================ */

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  html, body { height: 100%; margin: 0; }

  .lmc-root {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
    background: radial-gradient(1200px 700px at 15% -10%, #F4F5FC 0%, #EFF1F5 45%, #E4E7EE 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100vw;
    height: 100vh;
    box-sizing: border-box;
    padding: 20px;
    overflow: hidden;
  }

  .lmc-frame {
    width: 100%;
    height: 100%;
    max-width: 1280px;
    border-radius: 22px;
    padding: 1.5px;
    background: linear-gradient(135deg, #C9CEFB, #EAD9F5, #C9CEFB);
    box-shadow: 0 30px 70px rgba(30,32,60,0.18);
    box-sizing: border-box;
  }

  .lmc-card {
    background: #FFFFFF;
    border-radius: 20.5px;
    padding: 18px 20px 20px;
    box-sizing: border-box;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .lmc-fade-up { animation: lmcFadeUp 0.5s cubic-bezier(0.16,1,0.3,1) both; }
  @keyframes lmcFadeUp { from { opacity:0; transform: translateY(10px);} to {opacity:1; transform:translateY(0);} }

  .lmc-back-btn {
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: #F2F3F6; border: 1px solid #E7E8EE;
    cursor: pointer; color: #6B6F80; transition: all 0.15s ease;
    flex-shrink: 0;
  }
  .lmc-back-btn:hover { background: #E7E8EE; color: #1A1B23; }

  .lmc-pill {
    display: flex; align-items: center; gap: 10px;
    background: #F2F3F6; border: 1px solid #E7E8EE;
    border-radius: 999px; padding: 6px 8px 6px 14px;
    font-size: 12px; color: #3A3C46; font-weight: 500;
  }
  .lmc-pill-btn {
    width: 26px; height: 26px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; border: none; transition: transform 0.15s ease, filter 0.15s ease;
  }
  .lmc-pill-btn:hover { transform: scale(1.06); filter: brightness(1.08); }

  .lmc-topbar { padding-bottom: 14px; border-bottom: 1px solid #F1F2F7; }

  .lmc-body {
    display: grid;
    grid-template-columns: 1fr 272px;
    gap: 16px;
    flex: 1;
    min-height: 0;
    margin-top: 14px;
  }

  .lmc-left-col { display: flex; flex-direction: column; min-height: 0; height: 100%; }

  .lmc-video-stage {
    position: relative;
    border-radius: 18px;
    overflow: hidden;
    flex: 1;
    min-height: 0;
    background:
      radial-gradient(600px 300px at 30% 15%, rgba(0,230,168,0.35), transparent 60%),
      radial-gradient(500px 260px at 75% 30%, rgba(80,140,255,0.30), transparent 60%),
      linear-gradient(160deg, #10151F 0%, #060810 70%);
  }
  .lmc-video-noise {
    position: absolute; inset: 0;
    background-image: radial-gradient(rgba(255,255,255,0.05) 1px, transparent 1px);
    background-size: 3px 3px;
    opacity: 0.5;
    mix-blend-mode: overlay;
    pointer-events: none;
  }
  .lmc-speaker-silhouette {
    position: absolute; left: 50%; bottom: 0; transform: translateX(-50%);
    width: 200px; height: 240px;
    background: linear-gradient(180deg, #2A2F3D 0%, #12141C 100%);
    border-radius: 100px 100px 0 0;
    opacity: 0.9;
  }
  .lmc-speaker-head {
    position: absolute; left: 50%; bottom: 218px; transform: translateX(-50%);
    width: 86px; height: 86px; border-radius: 50%;
    background: linear-gradient(160deg, #38404F, #191B24);
  }

  .lmc-main-video {
    position: absolute; inset: 0; width: 100%; height: 100%;
    object-fit: cover; background: #000;
  }

  .lmc-connecting {
    position: absolute; inset: 0; z-index: 3;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px;
    color: #F4F4F6; font-size: 13px; font-weight: 600;
    background: rgba(6,8,16,0.55);
  }
  .lmc-spin { animation: lmcSpin 0.9s linear infinite; }
  @keyframes lmcSpin { to { transform: rotate(360deg); } }
  .lmc-connect-error { color: #FF9B9B; text-align: center; max-width: 320px; font-size: 12px; font-weight: 500; line-height: 1.5; }

  .lmc-you-badge {
    position: absolute; top: 14px; left: 14px; z-index: 2;
    display: flex; align-items: center; gap: 7px;
    background: rgba(10,12,20,0.55); backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 999px; padding: 5px 12px 5px 5px;
    color: #F4F4F6; font-size: 11.5px; font-weight: 600;
  }
  .lmc-you-avatar {
    width: 20px; height: 20px; border-radius: 50%;
    background: linear-gradient(135deg,#00E6A8,#00A9C9);
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 800; color: #04140F;
  }

  .lmc-rec-badge {
    position: absolute; top: 14px; right: 14px; z-index: 2;
    display: flex; align-items: center; gap: 8px;
    background: rgba(10,12,20,0.55); backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 999px; padding: 6px 14px;
    color: #F4F4F6; font-size: 11.5px; font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .lmc-rec-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #FF5A5A;
    box-shadow: 0 0 6px rgba(255,90,90,0.9);
    animation: lmcRecPulse 1.4s ease-in-out infinite;
  }
  @keyframes lmcRecPulse { 0%,100% { opacity:1; } 50% { opacity:0.35; } }

  .lmc-call-controls {
    position: absolute; bottom: 60px; left: 50%; transform: translateX(-50%); z-index: 2;
    display: flex; align-items: center; gap: 10px;
    background: rgba(15,16,22,0.55); backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 999px; padding: 8px;
  }
  .lmc-ctrl-btn {
    width: 38px; height: 38px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.14);
    color: #F4F4F6; cursor: pointer; transition: all 0.15s ease;
  }
  .lmc-ctrl-btn:hover { background: rgba(255,255,255,0.16); transform: translateY(-1px); }
  .lmc-ctrl-btn.active { background: rgba(0,230,168,0.85); border-color: rgba(0,230,168,1); color: #04140F; }
  .lmc-ctrl-btn.off { background: rgba(225,75,75,0.85); border-color: rgba(225,75,75,1); }
  .lmc-ctrl-btn.hangup { background: #FF4D4D; border-color: #FF4D4D; }
  .lmc-ctrl-btn.hangup:hover { background: #FF6B6B; }

  .lmc-caption-bar {
    position: absolute; left: 12px; right: 12px; bottom: 12px; z-index: 2;
    display: flex; align-items: center; gap: 10px;
    background: rgba(8,9,14,0.62); backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px; padding: 8px 12px;
  }
  .lmc-caption-audio-bar { width: 2.5px; border-radius: 2px; background: #00E6A8; animation: lmcAudioLevel 0.9s ease-in-out infinite; }
  @keyframes lmcAudioLevel { 0%,100% { transform: scaleY(0.3); opacity:0.5; } 50% { transform: scaleY(1); opacity:1; } }
  .lmc-caption-text-wrap { flex: 1; min-width: 0; }
  .lmc-caption-label { font-size: 10px; font-weight: 700; color: #8A8FA3; letter-spacing: 0.03em; margin-bottom: 2px; }
  .lmc-caption-text { font-size: 12.5px; color: #F4F4F6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .lmc-caption-gear { color: #9A9EB0; cursor: pointer; flex-shrink: 0; transition: color 0.15s ease; }
  .lmc-caption-gear:hover { color: #F4F4F6; }

  .lmc-thumb-strip { display: flex; align-items: center; gap: 10px; margin-top: 12px; flex-shrink: 0; overflow-x: auto; }
  .lmc-thumb {
    position: relative; width: 122px; height: 70px; border-radius: 12px; overflow: hidden;
    flex-shrink: 0; cursor: pointer; transition: transform 0.15s ease, box-shadow 0.15s ease;
    background: linear-gradient(160deg,#3A4050,#181A22);
  }
  .lmc-thumb:hover { transform: translateY(-2px); }
  .lmc-thumb.speaking { box-shadow: 0 0 0 2px #00E6A8; }
  .lmc-thumb-video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .lmc-thumb-name {
    position: absolute; left: 8px; bottom: 6px; z-index: 1;
    font-size: 10.5px; font-weight: 600; color: #fff;
    text-shadow: 0 1px 3px rgba(0,0,0,0.6);
  }
  .lmc-thumb-mic {
    position: absolute; right: 7px; top: 7px; z-index: 1;
    width: 16px; height: 16px; border-radius: 50%;
    background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center;
  }
  .lmc-thumb-more {
    width: 34px; height: 70px; border-radius: 12px; flex-shrink: 0;
    background: #1A1B22; display: flex; align-items: center; justify-content: center;
    color: #fff; cursor: pointer; transition: background 0.15s ease;
  }
  .lmc-thumb-more:hover { background: #2A2B34; }

  .lmc-scroll::-webkit-scrollbar { width: 5px; }
  .lmc-scroll::-webkit-scrollbar-thumb { background: #D8DAE2; border-radius: 8px; }
  .lmc-scroll::-webkit-scrollbar-track { background: transparent; }

  .lmc-right-col {
    display: flex; flex-direction: column; min-height: 0; height: 100%;
    border-left: 1px solid #EEEFF4; padding-left: 16px;
  }

  .lmc-tab { padding: 7px 13px; border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.18s ease; }
  .lmc-tab.active { background: #14151B; color: #fff; box-shadow: 0 4px 10px rgba(20,21,27,0.22); }
  .lmc-tab.inactive { color: #9599AA; }
  .lmc-tab.inactive:hover { color: #34353E; background: #F5F6FA; }

  .lmc-points-header { display:flex; align-items:center; justify-content:space-between; margin-bottom: 10px; flex-shrink:0; }
  .lmc-points-badge { font-size: 9.5px; font-weight: 800; letter-spacing: 0.04em; color: #4A63E8; background: #DFE4FF; padding: 3px 8px; border-radius: 999px; }

  .lmc-point-row {
    position: relative;
    display: flex; align-items: flex-start; gap: 9px;
    background: #F7F8FC; border: 1px solid #ECEEF7;
    border-radius: 13px; padding: 10px 10px 10px 12px;
    transition: all 0.18s ease;
  }
  .lmc-point-row:hover { border-color: #DEE1F0; box-shadow: 0 4px 12px rgba(40,44,80,0.06); transform: translateY(-1px); }
  .lmc-point-row.approved { background: #EEFBF3; border-color: #CDEEDA; }
  .lmc-point-row.rejected { background: #FDF3F3; border-color: #F5D9D9; }
  .lmc-point-dot { width: 5px; height: 5px; border-radius: 50%; background: #B7BCD6; margin-top: 6px; flex-shrink: 0; }
  .lmc-point-row.approved .lmc-point-dot { background: #17A56A; }
  .lmc-point-row.rejected .lmc-point-dot { background: #E14B4B; }
  .lmc-point-text { flex: 1; font-size: 12px; color: #363A48; line-height: 1.5; }
  .lmc-point-row.rejected .lmc-point-text { color: #A9A2A2; text-decoration: line-through; text-decoration-color: #E5B9B9; }
  .lmc-point-actions { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
  .lmc-point-btn {
    width: 22px; height: 22px; border-radius: 50%; border: 1px solid transparent;
    display: flex; align-items: center; justify-content: center; cursor: pointer;
    background: #fff; color: #B7BCD6; transition: all 0.15s ease; flex-shrink: 0;
  }
  .lmc-point-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .lmc-point-btn:hover { transform: scale(1.08); }
  .lmc-point-btn.reject:hover, .lmc-point-btn.reject.on { background: #E14B4B; color: #fff; border-color: #E14B4B; }
  .lmc-point-btn.accept:hover, .lmc-point-btn.accept.on { background: #17A56A; color: #fff; border-color: #17A56A; }
  .lmc-point-btn.edit:hover { background: #4A55C9; color: #fff; border-color: #4A55C9; }
  .lmc-point-edit-input {
    flex: 1; font-size: 12px; line-height: 1.5; color: #363A48; font-family: inherit;
    background: #fff; border: 1px solid #C9CEFB; border-radius: 6px; padding: 3px 6px;
    outline: none;
  }
  .lmc-point-edit-input:focus { border-color: #4A55C9; box-shadow: 0 0 0 2px rgba(74,85,201,0.15); }

  .lmc-msg-in { background: #F2F3F6; border-radius: 4px 14px 14px 14px; padding: 10px 13px; font-size: 12.5px; color: #24252C; line-height: 1.5; }
  .lmc-msg-out { background: #DFF5E9; border-radius: 14px 4px 14px 14px; padding: 10px 13px; font-size: 12.5px; color: #16311F; line-height: 1.5; }

  .lmc-input-row {
    display: flex; align-items: center; gap: 8px;
    background: #F2F3F6; border: 1px solid #E7E8EE; border-radius: 999px;
    padding: 6px 8px 6px 16px;
  }
  .lmc-send-btn {
    width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
    background: #14151B; color: #fff; border: none; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all 0.15s ease;
  }
  .lmc-send-btn:hover { background: #2A2B34; transform: scale(1.05); }
  .lmc-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .lmc-generate-btn {
    display: flex; align-items: center; justify-content: center; gap: 7px;
    background: linear-gradient(135deg, #4A63E8, #8A6FE8);
    color: #fff; border: none; border-radius: 999px;
    padding: 11px 16px; font-size: 12.5px; font-weight: 700;
    letter-spacing: -0.01em;
    cursor: pointer; transition: all 0.18s ease;
    box-shadow: 0 8px 20px rgba(74,99,232,0.32);
    width: 100%;
  }
  .lmc-generate-btn:hover { transform: translateY(-1px); box-shadow: 0 10px 24px rgba(74,99,232,0.42); filter: brightness(1.04); }
  .lmc-generate-btn:disabled { opacity: 0.45; cursor: not-allowed; transform: none; box-shadow: none; }

  .lmc-points-footer { flex-shrink: 0; margin-top: 12px; display: flex; flex-direction: column; gap: 6px; }
  .lmc-points-count { font-size: 10.5px; color: #9A9EB0; text-align: right; }

  .lmc-host-only-note { font-size: 10.5px; color: #9A9EB0; text-align: center; margin-top: 6px; }
`;

/* ---------------- small helper components ---------------- */

/** Attaches a LiveKit track to a <video>/<audio> element for as long as it's mounted. */
function TrackMedia({ track, muted = false, className }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!track || !el) return undefined;
    track.attach(el);
    return () => {
      track.detach(el);
    };
  }, [track]);

  if (!track) return null;

  return track.kind === "audio" ? (
    <audio ref={ref} autoPlay muted={muted} />
  ) : (
    <video ref={ref} autoPlay playsInline muted={muted} className={className} />
  );
}

function formatElapsed(startedAt) {
  if (!startedAt) return "00:00:00";
  const totalSeconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
  const h = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
  const m = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const s = String(totalSeconds % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

/* ---------------- component ---------------- */

export default function LiveMeetingCall({
  meetingId,
  meetingTitle = "Live Meeting",
  roomName,
  currentUser,
  isHost = false,
  onHangUp,
  onBack,
  onGeneratePrototype,
}) {
  const [tab, setTab] = useState("points");
  const [message, setMessage] = useState("");
  const [points, setPoints] = useState([]);
  const [editingPointId, setEditingPointId] = useState(null);
  const [editDraft, setEditDraft] = useState("");
  const [generating, setGenerating] = useState(false);

  const [connectionState, setConnectionState] = useState("connecting"); // connecting | connected | error
  const [connectionError, setConnectionError] = useState("");
  const [participants, setParticipants] = useState({}); // identity -> { identity, name, isLocal, videoTrack, audioTrack, screenTrack, micOn, speaking }
  const [pinnedIdentity, setPinnedIdentity] = useState(null);

  const [micOn, setMicOn] = useState(true);
  const [cameraOn, setCameraOn] = useState(false);
  const [screenShareOn, setScreenShareOn] = useState(false);

  const [captionText, setCaptionText] = useState("Waiting for someone to speak…");
  const [chatMessages, setChatMessages] = useState([]);
  const [elapsedText, setElapsedText] = useState("00:00:00");
  const [idCopied, setIdCopied] = useState(false);

  const roomRef = useRef(null);
  const socketRef = useRef(null);
  const startedAtRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [tab, chatMessages, points]);

  const bars = Array.from({ length: 12 });

  /* ---------- LiveKit connection ---------- */

  const upsertParticipant = useCallback((identity, patch) => {
    setParticipants((prev) => ({
      ...prev,
      [identity]: { ...(prev[identity] || { identity }), ...patch },
    }));
  }, []);

  const removeParticipant = useCallback((identity) => {
    setParticipants((prev) => {
      const next = { ...prev };
      delete next[identity];
      return next;
    });
  }, []);

  useEffect(() => {
    if (!meetingId) {
      setConnectionState("error");
      setConnectionError("No meeting to join — meetingId is missing.");
      return undefined;
    }

    let cancelled = false;
    const room = new Room({ adaptiveStream: true, dynacast: true });
    roomRef.current = room;

    room.on(RoomEvent.ParticipantConnected, (p) => {
      upsertParticipant(p.identity, { identity: p.identity, name: p.name || p.identity, isLocal: false, micOn: false, speaking: false });
    });

    room.on(RoomEvent.ParticipantDisconnected, (p) => removeParticipant(p.identity));

    room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      const key = track.kind === Track.Kind.Video && publication.source === Track.Source.ScreenShare ? "screenTrack" : track.kind === Track.Kind.Video ? "videoTrack" : "audioTrack";
      upsertParticipant(participant.identity, { name: participant.name || participant.identity, isLocal: false, [key]: track });
      if (publication.source === Track.Source.ScreenShare) {
        setPinnedIdentity(participant.identity); // auto-focus whoever starts sharing their screen
      }
    });

    room.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
      const key = track.kind === Track.Kind.Video && publication.source === Track.Source.ScreenShare ? "screenTrack" : track.kind === Track.Kind.Video ? "videoTrack" : "audioTrack";
      upsertParticipant(participant.identity, { [key]: null });
    });

    room.on(RoomEvent.LocalTrackPublished, (publication) => {
      const track = publication.track;
      const key = publication.source === Track.Source.ScreenShare ? "screenTrack" : track.kind === Track.Kind.Video ? "videoTrack" : "audioTrack";
      upsertParticipant(room.localParticipant.identity, { [key]: track });
    });

    room.on(RoomEvent.LocalTrackUnpublished, (publication) => {
      const key = publication.source === Track.Source.ScreenShare ? "screenTrack" : publication.kind === "video" ? "videoTrack" : "audioTrack";
      upsertParticipant(room.localParticipant.identity, { [key]: null });
    });

    room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      const speakingIds = new Set(speakers.map((s) => s.identity));
      setParticipants((prev) => {
        const next = { ...prev };
        for (const id of Object.keys(next)) {
          next[id] = { ...next[id], speaking: speakingIds.has(id) };
        }
        return next;
      });
    });

    room.on(RoomEvent.DataReceived, (payload, participant) => {
      try {
        const msg = JSON.parse(new TextDecoder().decode(payload));
        if (msg.type === "chat") {
          setChatMessages((prev) => [...prev, {
            from: participant?.identity === room.localParticipant.identity ? "out" : "in",
            name: msg.name || participant?.name || "Someone",
            text: msg.text,
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          }]);
        }
      } catch {
        // ignore malformed data messages from anything else on the room
      }
    });

    room.on(RoomEvent.Disconnected, () => {
      if (!cancelled) setConnectionState("error");
      if (!cancelled) setConnectionError("Disconnected from the call.");
    });

    async function connect() {
      try {
        if (isHost) {
          // Idempotent — safe even if this meeting already exists.
          await meetingsApi.create(meetingId, meetingTitle).catch(() => {});
        }
        const { livekit_url, token } = await meetingsApi.getLiveKitToken(meetingId);
        if (cancelled) return;

        await room.connect(livekit_url, token);
        if (cancelled) return;

        upsertParticipant(room.localParticipant.identity, {
          identity: room.localParticipant.identity,
          name: currentUser?.name || room.localParticipant.name || "You",
          isLocal: true,
          micOn: false,
        });

        await room.localParticipant.setMicrophoneEnabled(true);
        setMicOn(true);

        if (isHost) {
          await meetingsApi.startCall(meetingId).catch((err) => {
            console.warn("Couldn't start the transcription bot:", err.message);
          });
        }

        startedAtRef.current = Date.now();
        setConnectionState("connected");
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof ApiError
            ? err.message
            : "Couldn't connect to the call — check your camera/mic permissions and connection.";
        setConnectionError(message);
        setConnectionState("error");
      }
    }

    connect();

    return () => {
      cancelled = true;
      room.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingId]);

  // Elapsed-time ticker
  useEffect(() => {
    const interval = setInterval(() => {
      if (startedAtRef.current) setElapsedText(formatElapsed(startedAtRef.current));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  /* ---------- Transcript / requirements socket ---------- */

  useEffect(() => {
    if (!meetingId || connectionState !== "connected") return undefined;

    const socket = new WebSocket(meetingsApi.transcriptSocketUrl(meetingId));
    socketRef.current = socket;

    socket.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      if (data.type === "transcript") {
        setCaptionText(`${data.speaker}: ${data.english_text}`);
      } else if (data.type === "requirements" && Array.isArray(data.new)) {
        setPoints((prev) => [
          ...prev,
          ...data.new.map((r) => ({ id: r.id, text: r.title, status: r.status })),
        ]);
      }
    };

    return () => socket.close();
  }, [meetingId, connectionState]);

  // Initial requirements load (in case some were already captured before this client connected).
  useEffect(() => {
    if (!meetingId || connectionState !== "connected") return;
    meetingsApi
      .listRequirements(meetingId)
      .then((data) => {
        setPoints((data.requirements || []).map((r) => ({ id: r.id, text: r.title, status: r.status })));
      })
      .catch(() => {});
  }, [meetingId, connectionState]);

  /* ---------- Controls ---------- */

  const toggleMic = async () => {
    const room = roomRef.current;
    if (!room) return;
    const next = !micOn;
    await room.localParticipant.setMicrophoneEnabled(next);
    setMicOn(next);
    upsertParticipant(room.localParticipant.identity, { micOn: next });
  };

  const toggleCamera = async () => {
    const room = roomRef.current;
    if (!room) return;
    const next = !cameraOn;
    await room.localParticipant.setCameraEnabled(next);
    setCameraOn(next);
  };

  const toggleScreenShare = async () => {
    const room = roomRef.current;
    if (!room) return;
    try {
      const next = !screenShareOn;
      await room.localParticipant.setScreenShareEnabled(next);
      setScreenShareOn(next);
      if (next) setPinnedIdentity(room.localParticipant.identity);
    } catch {
      // user cancelled the OS screen-share picker — not an error to surface
    }
  };

  const handleHangUp = async () => {
    const room = roomRef.current;
    if (isHost && meetingId) {
      await meetingsApi.end(meetingId).catch(() => {});
    }
    await room?.disconnect();
    onHangUp?.();
  };

  const sendChatMessage = () => {
    const room = roomRef.current;
    const text = message.trim();
    if (!room || !text) return;
    const payload = new TextEncoder().encode(
      JSON.stringify({ type: "chat", name: currentUser?.name || "You", text })
    );
    room.localParticipant.publishData(payload, { reliable: true });
    setChatMessages((prev) => [...prev, { from: "out", name: "You", text, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }]);
    setMessage("");
  };

  const setPointStatus = async (id, status) => {
    if (!isHost) return; // backend enforces this too — this just avoids a pointless round trip
    const current = points.find((p) => p.id === id);
    const nextStatus = current?.status === status ? "pending" : status;
    setPoints((prev) => prev.map((p) => (p.id === id ? { ...p, status: nextStatus } : p)));
    try {
      await meetingsApi.updateRequirementStatus(meetingId, id, nextStatus);
    } catch (err) {
      // roll back on failure — don't leave the UI claiming a change that didn't stick
      setPoints((prev) => prev.map((p) => (p.id === id ? { ...p, status: current?.status || "pending" } : p)));
      console.warn("Couldn't update requirement status:", err.message);
    }
  };

  const startEditingPoint = (pt) => {
    if (!isHost) return;
    setEditingPointId(pt.id);
    setEditDraft(pt.text);
  };

  const cancelEditingPoint = () => {
    setEditingPointId(null);
    setEditDraft("");
  };

  const saveEditedPoint = async (id) => {
    const text = editDraft.trim();
    const current = points.find((p) => p.id === id);
    if (!text || text === current?.text) {
      cancelEditingPoint();
      return;
    }
    setPoints((prev) => prev.map((p) => (p.id === id ? { ...p, text } : p)));
    setEditingPointId(null);
    setEditDraft("");
    try {
      await meetingsApi.updateRequirementTitle(meetingId, id, text);
    } catch (err) {
      // roll back on failure — same pattern as setPointStatus
      setPoints((prev) => prev.map((p) => (p.id === id ? { ...p, text: current?.text || p.text } : p)));
      console.warn("Couldn't update requirement title:", err.message);
    }
  };

  const acceptedCount = points.filter((p) => p.status === "approved").length;
  const canGenerate = acceptedCount > 0 && !generating;

  const handleGenerate = () => {
    if (!canGenerate) return;
    setGenerating(true);
    onGeneratePrototype?.(points.filter((p) => p.status === "approved"));
    setTimeout(() => setGenerating(false), 1600);
  };

  const participantList = Object.values(participants);
  const localIdentity = roomRef.current?.localParticipant?.identity;
  const pinned = (pinnedIdentity && participants[pinnedIdentity]) ||
    participantList.find((p) => p.identity !== localIdentity && p.speaking) ||
    participantList.find((p) => p.identity !== localIdentity) ||
    participants[localIdentity];

  const pinnedMainTrack = pinned?.screenTrack || pinned?.videoTrack || null;

  return (
    <div className="lmc-root">
      <style>{styles}</style>

      <div className="lmc-frame lmc-fade-up">
        <div className="lmc-card">

          {/* ---------- Top bar ---------- */}
          <div className="lmc-topbar" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexShrink: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div className="lmc-back-btn" onClick={onBack}>
                <ChevronLeft size={16} />
              </div>
              <div>
                <div style={{ fontSize: 16.5, fontWeight: 800, color: "#14151B" }}>{meetingTitle}</div>
                <div style={{ fontSize: 11.5, color: "#9599AA", marginTop: 2, fontWeight: 500 }}>{roomName || meetingId}</div>
              </div>
            </div>

            <div
              className="lmc-pill"
              style={{ cursor: "pointer" }}
              onClick={() => {
                if (!meetingId) return;
                navigator.clipboard?.writeText(meetingId);
                setIdCopied(true);
                setTimeout(() => setIdCopied(false), 1500);
              }}
              title="Copy meeting ID to share with others"
            >
              <span>{idCopied ? "Copied — share this to let others join" : meetingId}</span>
              <div className="lmc-pill-btn" style={{ background: "#14151B", color: "#fff" }}>
                <Copy size={12} />
              </div>
            </div>
          </div>

          {/* ---------- Body: video + side panel ---------- */}
          <div className="lmc-body">

            {/* ---- Left: video stage ---- */}
            <div className="lmc-left-col">
              <div className="lmc-video-stage">
                {connectionState === "connecting" && (
                  <div className="lmc-connecting">
                    <Loader2 size={22} className="lmc-spin" />
                    Connecting to the call…
                  </div>
                )}

                {connectionState === "error" && (
                  <div className="lmc-connecting">
                    <AlertCircle size={22} />
                    <div className="lmc-connect-error">{connectionError}</div>
                  </div>
                )}

                <div className="lmc-video-noise" />

                {pinnedMainTrack ? (
                  <TrackMedia track={pinnedMainTrack} muted={pinned?.isLocal} className="lmc-main-video" />
                ) : (
                  <>
                    <div className="lmc-speaker-silhouette" />
                    <div className="lmc-speaker-head" />
                  </>
                )}

                {/* Remote audio — always attached even when a different participant is pinned visually */}
                {participantList
                  .filter((p) => p.identity !== localIdentity && p.audioTrack)
                  .map((p) => <TrackMedia key={`audio-${p.identity}`} track={p.audioTrack} />)}

                <div className="lmc-you-badge">
                  <span className="lmc-you-avatar">{(currentUser?.name || "Y")[0].toUpperCase()}</span>
                  {pinned?.isLocal ? "You" : pinned?.name || "…"}
                </div>

                <div className="lmc-rec-badge">
                  <span className="lmc-rec-dot" /> Transcribing live… <span style={{ opacity: 0.5 }}>|</span> {elapsedText}
                </div>

                <div className="lmc-call-controls">
                  <div className={`lmc-ctrl-btn ${micOn ? "active" : "off"}`} onClick={toggleMic} title={micOn ? "Mute" : "Unmute"}>
                    {micOn ? <Mic size={15} /> : <MicOff size={15} />}
                  </div>
                  <div className={`lmc-ctrl-btn ${cameraOn ? "active" : ""}`} onClick={toggleCamera} title="Toggle camera">
                    {cameraOn ? <Video size={15} /> : <VideoOff size={15} />}
                  </div>
                  <div className={`lmc-ctrl-btn ${screenShareOn ? "active" : ""}`} onClick={toggleScreenShare} title="Share screen">
                    {screenShareOn ? <MonitorOff size={15} /> : <Monitor size={15} />}
                  </div>
                  <div className="lmc-ctrl-btn hangup" onClick={handleHangUp} title="Leave meeting">
                    <PhoneOff size={15} />
                  </div>
                </div>

                <div className="lmc-caption-bar">
                  <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 14, flexShrink: 0 }}>
                    {bars.map((_, i) => (
                      <div key={i} className="lmc-caption-audio-bar" style={{ height: 5 + (i % 4) * 3, animationDelay: `${i * 70}ms` }} />
                    ))}
                  </div>
                  <div className="lmc-caption-text-wrap">
                    <div className="lmc-caption-label">LIVE TRANSCRIPT</div>
                    <div className="lmc-caption-text">{captionText}</div>
                  </div>
                  <Settings size={15} className="lmc-caption-gear" />
                </div>
              </div>

              {/* ---- Participant thumbnail strip ---- */}
              <div className="lmc-thumb-strip">
                {participantList.map((p) => (
                  <div
                    key={p.identity}
                    className={`lmc-thumb ${p.speaking ? "speaking" : ""}`}
                    onClick={() => setPinnedIdentity(p.identity)}
                  >
                    {p.videoTrack && <TrackMedia track={p.videoTrack} muted={p.isLocal} className="lmc-thumb-video" />}
                    <div className="lmc-thumb-mic">
                      {p.micOn ? <Mic size={9} color="#fff" /> : <MicOff size={9} color="#fff" />}
                    </div>
                    <div className="lmc-thumb-name">{p.isLocal ? "You" : p.name}</div>
                  </div>
                ))}
                {participantList.length === 0 && connectionState === "connected" && (
                  <div style={{ fontSize: 11.5, color: "#9599AA" }}>Waiting for others to join…</div>
                )}
              </div>
            </div>

            {/* ---- Right: chat / participants / points panel ---- */}
            <div className="lmc-right-col">
              <div style={{ display: "flex", gap: 4, marginBottom: 12, flexShrink: 0 }}>
                <div className={`lmc-tab ${tab === "chat" ? "active" : "inactive"}`} onClick={() => setTab("chat")}>Room Chat</div>
                <div className={`lmc-tab ${tab === "participants" ? "active" : "inactive"}`} onClick={() => setTab("participants")}>Participants</div>
                <div className={`lmc-tab ${tab === "points" ? "active" : "inactive"}`} onClick={() => setTab("points")}>Points</div>
              </div>

              {tab === "points" ? (
                <>
                  <div className="lmc-points-header">
                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5, fontWeight: 700, color: "#2A3596" }}>
                      <Zap size={13} /> Important Points
                    </div>
                    <span className="lmc-points-badge">AUTO</span>
                  </div>

                  <div ref={scrollRef} className="lmc-scroll" style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, paddingRight: 2, minHeight: 0 }}>
                    {points.length === 0 && (
                      <div style={{ fontSize: 12, color: "#9A9EB0", padding: "8px 2px" }}>
                        Nothing captured yet — points appear here automatically as the conversation happens.
                      </div>
                    )}
                    {points.map((pt, i) => (
                      <div key={pt.id} className={`lmc-point-row ${pt.status} lmc-fade-up`} style={{ animationDelay: `${i * 40}ms` }}>
                        <span className="lmc-point-dot" />
                        {editingPointId === pt.id ? (
                          <input
                            className="lmc-point-edit-input"
                            value={editDraft}
                            autoFocus
                            onChange={(e) => setEditDraft(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") saveEditedPoint(pt.id);
                              if (e.key === "Escape") cancelEditingPoint();
                            }}
                            onBlur={() => saveEditedPoint(pt.id)}
                          />
                        ) : (
                          <span className="lmc-point-text">{pt.text}</span>
                        )}
                        <div className="lmc-point-actions">
                          {editingPointId === pt.id ? (
                            <>
                              <button className="lmc-point-btn accept on" title="Save edit" onClick={() => saveEditedPoint(pt.id)}>
                                <Check size={12} strokeWidth={2.5} />
                              </button>
                              <button className="lmc-point-btn reject" title="Cancel edit" onClick={cancelEditingPoint}>
                                <X size={12} strokeWidth={2.5} />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                className="lmc-point-btn edit"
                                title={isHost ? "Edit point — fix a mistranscribed or wrong point" : "Only the host can manage points"}
                                disabled={!isHost}
                                onClick={() => startEditingPoint(pt)}
                              >
                                <Pencil size={11} strokeWidth={2.5} />
                              </button>
                              <button
                                className={`lmc-point-btn reject ${pt.status === "rejected" ? "on" : ""}`}
                                title={isHost ? "Reject point" : "Only the host can manage points"}
                                disabled={!isHost}
                                onClick={() => setPointStatus(pt.id, "rejected")}
                              >
                                <X size={12} strokeWidth={2.5} />
                              </button>
                              <button
                                className={`lmc-point-btn accept ${pt.status === "approved" ? "on" : ""}`}
                                title={isHost ? "Accept point" : "Only the host can manage points"}
                                disabled={!isHost}
                                onClick={() => setPointStatus(pt.id, "approved")}
                              >
                                <Check size={12} strokeWidth={2.5} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="lmc-points-footer">
                    <div className="lmc-points-count">{acceptedCount} of {points.length} accepted</div>
                    {isHost ? (
                      <button className="lmc-generate-btn" disabled={!canGenerate} onClick={handleGenerate}>
                        <Sparkles size={14} />
                        {generating ? "Generating…" : "Generate Prototype"}
                      </button>
                    ) : (
                      <div className="lmc-host-only-note">Only the host can generate the prototype</div>
                    )}
                  </div>
                </>
              ) : (
                <div ref={scrollRef} className="lmc-scroll" style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14, paddingRight: 2, minHeight: 0 }}>
                  {tab === "chat" && chatMessages.length === 0 && (
                    <div style={{ fontSize: 12, color: "#9A9EB0" }}>No messages yet — say hi.</div>
                  )}
                  {tab === "chat" && chatMessages.map((m, i) => (
                    <div key={i} className="lmc-fade-up" style={{ animationDelay: `${i * 50}ms` }}>
                      <div style={{
                        display: "flex", justifyContent: "space-between",
                        fontSize: 11, color: "#9A9EB0", marginBottom: 4,
                        flexDirection: m.from === "out" ? "row-reverse" : "row",
                      }}>
                        <span>{m.name}</span>
                        {m.time && <span>{m.time}</span>}
                      </div>
                      <div style={{ display: "flex", justifyContent: m.from === "out" ? "flex-end" : "flex-start" }}>
                        <div className={m.from === "out" ? "lmc-msg-out" : "lmc-msg-in"} style={{ maxWidth: "88%" }}>{m.text}</div>
                      </div>
                    </div>
                  ))}

                  {tab === "participants" && participantList.map((p) => (
                    <div key={p.identity} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 30, height: 30, borderRadius: "50%", background: "linear-gradient(160deg,#8FA8C9,#3E5470)", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 12, fontWeight: 700 }}>
                        {(p.isLocal ? currentUser?.name : p.name || "?")[0]?.toUpperCase()}
                      </div>
                      <span style={{ fontSize: 12.5, color: "#24252C", fontWeight: 500 }}>{p.isLocal ? "You" : p.name}</span>
                      {p.micOn ? <Mic size={12} color="#9A9EB0" style={{ marginLeft: "auto" }} /> : <MicOff size={12} color="#E14B4B" style={{ marginLeft: "auto" }} />}
                    </div>
                  ))}
                </div>
              )}

              {tab === "chat" && (
                <div className="lmc-input-row" style={{ marginTop: 12, flexShrink: 0 }}>
                  <input
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendChatMessage()}
                    placeholder="Type message here..."
                    style={{ flex: 1, border: "none", outline: "none", background: "transparent", fontSize: 12.5, color: "#24252C" }}
                  />
                  <Smile size={16} color="#9A9EB0" style={{ cursor: "pointer", flexShrink: 0 }} />
                  <button className="lmc-send-btn" onClick={sendChatMessage} disabled={!message.trim()}>
                    <Send size={13} />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}