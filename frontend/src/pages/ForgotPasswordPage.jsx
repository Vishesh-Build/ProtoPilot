import React, { useState } from "react";
import {
  Mail, ArrowRight, ArrowLeft, Radio, ShieldCheck,
  Check, Sparkles, Lock as LockIcon, MailCheck, AlertCircle,
} from "lucide-react";
import { authApi } from "../lib/api.js";

/* ============================================================
   ProtoPilot — Forgot password (desktop split layout)
   Same shell/tokens as Login/Register. Two states: request form,
   then a "check your inbox" confirmation state.
   ============================================================ */

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');
  * { box-sizing: border-box; }
  html, body { height: 100%; width: 100%; margin: 0; padding: 0; }

  .auth-root {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
    position: fixed;
    inset: 0;
    width: 100%;
    height: 100%;
    display: flex;
    color: #14151B;
    overflow: hidden;
  }
  .auth-display { font-family: 'Space Grotesk', 'Inter', sans-serif; }

  .auth-left {
    position: relative;
    flex: 1.15;
    min-width: 0;
    overflow: hidden;
    background: radial-gradient(1100px 700px at 15% 0%, #ffffff 0%, #F3F5FA 42%, #E7EAF4 100%);
    display: flex; flex-direction: column; justify-content: space-between;
    padding: 44px 56px;
  }
  .auth-left-glow { position: absolute; top: -15%; left: -10%; width: 65%; height: 70%;
    background: radial-gradient(circle at 35% 30%, rgba(255,255,255,0.95), rgba(210,225,255,0.35) 55%, transparent 75%);
    filter: blur(6px); }
  .auth-left-mint { position: absolute; bottom: -10%; right: -12%; width: 55%; height: 50%;
    background: radial-gradient(circle at 60% 50%, rgba(0,230,168,0.18), transparent 70%);
    filter: blur(24px); }

  .liquid-blob { position: absolute; filter: blur(46px); opacity: 0.55; z-index: 1; pointer-events: none; }
  .lb-1 { width: 340px; height: 340px; top: 6%; left: 12%;
    background: radial-gradient(circle at 30% 30%, #E3B6FF, #B98CF0 60%, transparent 75%);
    animation: liquidMove1 15s ease-in-out infinite; }
  .lb-2 { width: 300px; height: 300px; bottom: 8%; left: 30%;
    background: radial-gradient(circle at 60% 40%, #7C9CFF, #4A63E8 55%, transparent 75%);
    animation: liquidMove2 18s ease-in-out infinite; }
  .lb-3 { width: 220px; height: 220px; top: 40%; right: 6%;
    background: radial-gradient(circle at 50% 50%, #6FE6C4, #00C88A 55%, transparent 75%);
    animation: liquidMove3 20s ease-in-out infinite; }
  @keyframes liquidMove1 {
    0%,100% { transform: translate(0,0) scale(1); border-radius: 42% 58% 65% 35% / 45% 40% 60% 55%; }
    33% { transform: translate(30px,22px) scale(1.08); border-radius: 60% 40% 45% 55% / 55% 60% 40% 45%; }
    66% { transform: translate(-14px,30px) scale(0.96); border-radius: 50% 50% 38% 62% / 40% 55% 45% 60%; }
  }
  @keyframes liquidMove2 {
    0%,100% { transform: translate(0,0) scale(1); border-radius: 55% 45% 40% 60% / 50% 45% 55% 50%; }
    50% { transform: translate(-26px,-18px) scale(1.1); border-radius: 40% 60% 55% 45% / 60% 40% 55% 45%; }
  }
  @keyframes liquidMove3 {
    0%,100% { transform: translate(0,0) scale(1); }
    50% { transform: translate(20px,-24px) scale(1.12); }
  }

  .auth-logo { position: relative; z-index: 2; display: flex; align-items: center; gap: 9px; }
  .auth-logo-mark {
    width: 30px; height: 30px; border-radius: 9px;
    background: linear-gradient(135deg, #00E6A8, #4A63E8);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 12px rgba(74,99,232,0.35);
  }
  .auth-logo-text { font-weight: 700; font-size: 16px; }

  .auth-left-mid { position: relative; z-index: 2; max-width: 460px; }
  .auth-left-eyebrow {
    display: inline-flex; align-items: center; gap: 7px;
    font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    color: #7C6BEA; background: rgba(124,107,234,0.1); border: 1px solid rgba(124,107,234,0.2);
    padding: 6px 13px; border-radius: 999px; margin-bottom: 20px;
  }
  .auth-left-title { font-size: 40px; font-weight: 700; line-height: 1.08; letter-spacing: -0.02em; margin: 0 0 16px; }
  .auth-left-title .grad {
    background: linear-gradient(120deg, #14151B 30%, #7C6BEA 65%, #4A63E8 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .auth-left-sub { font-size: 14.5px; color: #5B5F70; line-height: 1.65; max-width: 380px; }

  .auth-trust-list { position: relative; z-index: 2; display: flex; flex-direction: column; gap: 12px; }
  .auth-trust-item { display: flex; align-items: center; gap: 10px; font-size: 13px; color: #3A3C46; font-weight: 500; }
  .auth-trust-icon {
    width: 24px; height: 24px; border-radius: 7px; flex-shrink: 0;
    background: rgba(255,255,255,0.75); backdrop-filter: blur(6px);
    border: 1px solid rgba(255,255,255,0.8);
    display: flex; align-items: center; justify-content: center; color: #17A56A;
  }

  .auth-right {
    flex: 1;
    min-width: 380px;
    max-width: 640px;
    background: #FFFFFF;
    box-shadow: -1px 0 0 rgba(20,21,27,0.05);
    display: flex; align-items: center; justify-content: center;
    overflow-y: auto;
    padding: 40px;
  }
  .auth-right::-webkit-scrollbar { width: 6px; }
  .auth-right::-webkit-scrollbar-thumb { background: #E4E7F0; border-radius: 8px; }

  .auth-form-wrap { width: 100%; max-width: 380px; }

  .auth-back-link {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 12.5px; font-weight: 600; color: #767A8C; cursor: pointer;
    margin-bottom: 22px; transition: color 0.15s ease;
  }
  .auth-back-link:hover { color: #4A63E8; }

  .auth-form-head { margin-bottom: 26px; }
  .auth-title { font-size: 26px; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 8px; }
  .auth-subtitle { font-size: 13.5px; color: #767A8C; margin: 0; line-height: 1.55; }
  .auth-subtitle b { color: #14151B; font-weight: 600; }

  .auth-field { margin-bottom: 18px; }
  .auth-label { display: block; font-size: 12px; font-weight: 600; color: #3A3C46; margin-bottom: 7px; }
  .auth-input-wrap {
    position: relative; display: flex; align-items: center;
    background: #F7F8FC; border: 1px solid #E7E9F2; border-radius: 12px;
    padding: 0 12px; transition: all 0.15s ease;
  }
  .auth-input-wrap.focused { border-color: #4A63E8; box-shadow: 0 0 0 3px rgba(74,99,232,0.12); background: #fff; }
  .auth-input-icon { color: #9599AA; flex-shrink: 0; }
  .auth-input {
    flex: 1; border: none; outline: none; background: transparent;
    padding: 12px 10px; font-size: 13.5px; color: #14151B; font-family: inherit;
  }
  .auth-input::placeholder { color: #ABAFC0; }

  .auth-submit {
    width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px;
    padding: 13.5px; border-radius: 12px; border: none; cursor: pointer;
    font-size: 13.5px; font-weight: 700; color: #fff; margin-top: 6px;
    background: linear-gradient(135deg, #4A63E8, #7C6BEA);
    box-shadow: 0 10px 24px rgba(74,99,232,0.32); transition: all 0.18s ease;
  }
  .auth-submit:hover { transform: translateY(-1px); box-shadow: 0 14px 28px rgba(74,99,232,0.4); }
  .auth-submit:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

  .auth-submit.ghost {
    background: #fff; color: #3A3C46; border: 1px solid #E7E9F2;
    box-shadow: none;
  }
  .auth-submit.ghost:hover { border-color: #C9CCDA; background: #FAFBFD; box-shadow: none; }

  .auth-footer-text { text-align: center; font-size: 12.5px; color: #767A8C; margin-top: 24px; }
  .auth-link { font-size: 12.5px; font-weight: 600; color: #4A63E8; cursor: pointer; text-decoration: none; }
  .auth-link:hover { text-decoration: underline; }

  .auth-security-note {
    display: flex; align-items: center; gap: 7px; justify-content: center;
    font-size: 11px; color: #9599AA; margin-top: 22px;
  }

  .confirm-icon-wrap {
    width: 54px; height: 54px; border-radius: 16px; margin-bottom: 18px;
    background: linear-gradient(135deg, rgba(74,99,232,0.12), rgba(124,107,234,0.12));
    display: flex; align-items: center; justify-content: center; color: #4A63E8;
  }
  .resend-row { font-size: 12.5px; color: #767A8C; text-align: center; margin-top: 18px; }

  .auth-banner {
    display: flex; align-items: flex-start; gap: 9px;
    background: #FDF3F3; border: 1px solid #F5D9D9; border-radius: 12px;
    padding: 10px 12px; margin-bottom: 18px; font-size: 12px; color: #B23A3A; line-height: 1.5;
  }
`;

export default function ForgotPasswordPage({ onBackToLogin }) {
  const [email, setEmail] = useState("");
  const [focused, setFocused] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const canSubmit = emailValid && !submitting;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError("");
    try {
      // Backend always returns the same generic success message whether or
      // not the account exists — that's intentional (see README_AUTH.md),
      // not a bug. A thrown error here means something actually went wrong
      // (rate limited, or SMTP isn't configured on the server yet).
      await authApi.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err.message || "Couldn't send the reset link — please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-root">
      <style>{styles}</style>

      <div className="auth-left">
        <div className="auth-left-glow" />
        <div className="auth-left-mint" />
        <div className="liquid-blob lb-1" />
        <div className="liquid-blob lb-2" />
        <div className="liquid-blob lb-3" />
        <LeftArcs />

        <div className="auth-logo">
          <div className="auth-logo-mark"><Radio size={14} color="#fff" /></div>
          <span className="auth-logo-text auth-display">ProtoPilot</span>
        </div>

        <div className="auth-left-mid">
          <div className="auth-left-eyebrow"><Sparkles size={11} /> Account recovery</div>
          <h1 className="auth-left-title auth-display">
            Locked out?<br /><span className="grad">Let's fix that</span>
          </h1>
          <p className="auth-left-sub">
            Enter your account email and we'll send a secure link to reset your
            password — your transcripts and prototypes will be right where you left them.
          </p>
        </div>

        <div className="auth-trust-list">
          <div className="auth-trust-item"><span className="auth-trust-icon"><ShieldCheck size={13} /></span> End-to-end encrypted sessions</div>
          <div className="auth-trust-item"><span className="auth-trust-icon"><LockIcon size={13} /></span> Passwords hashed, never stored raw</div>
          <div className="auth-trust-item"><span className="auth-trust-icon"><Check size={13} /></span> Reset links expire after 30 minutes</div>
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-form-wrap">
          <div className="auth-back-link" onClick={onBackToLogin}>
            <ArrowLeft size={14} /> Back to log in
          </div>

          {!sent ? (
            <>
              <div className="auth-form-head">
                <h2 className="auth-title auth-display">Forgot your password?</h2>
                <p className="auth-subtitle">No worries — enter your email and we'll send you a reset link.</p>
              </div>

              {error && (
                <div className="auth-banner">
                  <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleSubmit}>
                <div className="auth-field">
                  <label className="auth-label">Email</label>
                  <div className={`auth-input-wrap ${focused ? "focused" : ""}`}>
                    <Mail size={15} className="auth-input-icon" />
                    <input
                      className="auth-input"
                      type="email"
                      placeholder="you@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onFocus={() => setFocused(true)}
                      onBlur={() => setFocused(false)}
                      autoComplete="email"
                    />
                  </div>
                </div>

                <button type="submit" className="auth-submit" disabled={!canSubmit}>
                  {submitting ? "Sending link…" : "Send reset link"} <ArrowRight size={15} />
                </button>
              </form>

              <div className="auth-footer-text">
                Remembered it? <span className="auth-link" onClick={onBackToLogin}>Log in</span>
              </div>
            </>
          ) : (
            <>
              <div className="confirm-icon-wrap"><MailCheck size={24} /></div>
              <div className="auth-form-head">
                <h2 className="auth-title auth-display">Check your inbox</h2>
                <p className="auth-subtitle">
                  We've sent a password reset link to <b>{email}</b>. It'll expire in 30 minutes.
                </p>
              </div>

              <button className="auth-submit ghost" onClick={onBackToLogin}>
                Back to log in
              </button>

              <div className="resend-row">
                Didn't get it? Check spam, or{" "}
                <span className="auth-link" onClick={() => setSent(false)}>try a different email</span>
              </div>
            </>
          )}

          <div className="auth-security-note">
            <ShieldCheck size={12} /> Your session is encrypted end-to-end
          </div>
        </div>
      </div>
    </div>
  );
}

function LeftArcs() {
  return (
    <svg viewBox="0 0 900 900" preserveAspectRatio="xMidYMid slice"
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.8, zIndex: 1 }}>
      <defs>
        <linearGradient id="fpArc1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="50%" stopColor="#ffffff" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#CBD5F5" stopOpacity="0.2" />
        </linearGradient>
        <linearGradient id="fpArc2" x1="0" y1="0" x2="1" y2="0.3">
          <stop offset="0%" stopColor="#D9E4FF" stopOpacity="0" />
          <stop offset="50%" stopColor="#B9C6F2" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#9FE9CE" stopOpacity="0.25" />
        </linearGradient>
        <filter id="fpBlur"><feGaussianBlur stdDeviation="6" /></filter>
      </defs>
      <path d="M -100 100 C 250 -80, 500 -60, 700 120 C 900 280, 1000 260, 1100 60"
        fill="none" stroke="url(#fpArc1)" strokeWidth="20" filter="url(#fpBlur)" />
      <path d="M -100 780 C 220 580, 560 550, 780 780 C 950 960, 1050 940, 1150 740"
        fill="none" stroke="url(#fpArc2)" strokeWidth="16" filter="url(#fpBlur)" opacity="0.6" />
    </svg>
  );
}
