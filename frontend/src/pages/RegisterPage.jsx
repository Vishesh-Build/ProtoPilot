import React, { useState } from "react";
import {
  Mail, Lock, Eye, EyeOff, ArrowRight, Radio, ShieldCheck,
  Github, Check, Sparkles, Lock as LockIcon, User, X, AlertCircle,
} from "lucide-react";
import { authApi } from "../lib/api.js";

/* ============================================================
   ProtoPilot — Register (desktop split layout)
   Same shell/tokens as LoginPage: fixed inset:0 root, no mobile
   collapse — always the two-panel desktop layout.
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
    background: radial-gradient(circle at 30% 30%, #6FE6C4, #00C88A 60%, transparent 75%);
    animation: liquidMove1 15s ease-in-out infinite; }
  .lb-2 { width: 300px; height: 300px; bottom: 8%; left: 30%;
    background: radial-gradient(circle at 60% 40%, #7C9CFF, #4A63E8 55%, transparent 75%);
    animation: liquidMove2 18s ease-in-out infinite; }
  .lb-3 { width: 220px; height: 220px; top: 40%; right: 6%;
    background: radial-gradient(circle at 50% 50%, #E3B6FF, #B98CF0 55%, transparent 75%);
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
    color: #17A56A; background: rgba(0,200,138,0.1); border: 1px solid rgba(0,200,138,0.2);
    padding: 6px 13px; border-radius: 999px; margin-bottom: 20px;
  }
  .auth-left-title { font-size: 40px; font-weight: 700; line-height: 1.08; letter-spacing: -0.02em; margin: 0 0 16px; }
  .auth-left-title .grad {
    background: linear-gradient(120deg, #14151B 30%, #00C88A 65%, #4A63E8 100%);
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

  .auth-form-head { margin-bottom: 26px; }
  .auth-title { font-size: 26px; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 8px; }
  .auth-subtitle { font-size: 13.5px; color: #767A8C; margin: 0; line-height: 1.55; }

  .auth-field { margin-bottom: 16px; }
  .auth-label { display: block; font-size: 12px; font-weight: 600; color: #3A3C46; margin-bottom: 7px; }
  .auth-input-wrap {
    position: relative; display: flex; align-items: center;
    background: #F7F8FC; border: 1px solid #E7E9F2; border-radius: 12px;
    padding: 0 12px; transition: all 0.15s ease;
  }
  .auth-input-wrap.focused { border-color: #4A63E8; box-shadow: 0 0 0 3px rgba(74,99,232,0.12); background: #fff; }
  .auth-input-wrap.error { border-color: #E14B4B; box-shadow: 0 0 0 3px rgba(225,75,75,0.1); }
  .auth-input-icon { color: #9599AA; flex-shrink: 0; }
  .auth-input {
    flex: 1; border: none; outline: none; background: transparent;
    padding: 12px 10px; font-size: 13.5px; color: #14151B; font-family: inherit;
  }
  .auth-input::placeholder { color: #ABAFC0; }
  .auth-eye-btn { cursor: pointer; color: #9599AA; display: flex; align-items: center; flex-shrink: 0; transition: color 0.15s ease; }
  .auth-eye-btn:hover { color: #4A63E8; }

  .pw-checklist { display: flex; flex-direction: column; gap: 5px; margin: 9px 2px 0; }
  .pw-check-item { display: flex; align-items: center; gap: 7px; font-size: 11.5px; color: #ABAFC0; transition: color 0.15s ease; }
  .pw-check-item.met { color: #17A56A; }
  .pw-check-icon { width: 14px; height: 14px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    background: #F0F1F6; transition: all 0.15s ease; }
  .pw-check-item.met .pw-check-icon { background: #E4F8EF; }

  .auth-row { display: flex; align-items: flex-start; gap: 9px; margin: 18px 0 22px; }
  .auth-checkbox {
    width: 16px; height: 16px; border-radius: 5px; border: 1.5px solid #C9CCDA;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all 0.15s ease;
    cursor: pointer; margin-top: 1px;
  }
  .auth-checkbox.checked { background: #14151B; border-color: #14151B; }
  .auth-terms-text { font-size: 12.5px; color: #5B5F70; line-height: 1.5; cursor: pointer; user-select: none; }
  .auth-link { font-size: 12.5px; font-weight: 600; color: #4A63E8; cursor: pointer; text-decoration: none; }
  .auth-link:hover { text-decoration: underline; }

  .auth-submit {
    width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px;
    padding: 13.5px; border-radius: 12px; border: none; cursor: pointer;
    font-size: 13.5px; font-weight: 700; color: #fff;
    background: linear-gradient(135deg, #4A63E8, #7C6BEA);
    box-shadow: 0 10px 24px rgba(74,99,232,0.32); transition: all 0.18s ease;
  }
  .auth-submit:hover { transform: translateY(-1px); box-shadow: 0 14px 28px rgba(74,99,232,0.4); }
  .auth-submit:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

  .auth-divider { display: flex; align-items: center; gap: 12px; margin: 22px 0; }
  .auth-divider-line { flex: 1; height: 1px; background: #ECEEF5; }
  .auth-divider-text { font-size: 11px; color: #ABAFC0; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }

  .auth-oauth-row { display: flex; gap: 10px; }
  .auth-oauth-btn {
    flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px;
    padding: 11.5px; border-radius: 12px; border: 1px solid #E7E9F2; background: #fff;
    font-size: 12.5px; font-weight: 600; color: #3A3C46; cursor: pointer; transition: all 0.15s ease;
  }
  .auth-oauth-btn:hover { border-color: #C9CCDA; background: #FAFBFD; transform: translateY(-1px); }

  .auth-footer-text { text-align: center; font-size: 12.5px; color: #767A8C; margin-top: 22px; }

  .auth-banner {
    display: flex; align-items: flex-start; gap: 9px;
    background: #FDF3F3; border: 1px solid #F5D9D9; border-radius: 12px;
    padding: 10px 12px; margin-bottom: 18px; font-size: 12px; color: #B23A3A; line-height: 1.5;
  }

  .auth-security-note {
    display: flex; align-items: center; gap: 7px; justify-content: center;
    font-size: 11px; color: #9599AA; margin-top: 20px;
  }
`;

function checkRules(pw) {
  return {
    length: pw.length >= 8,
    case: /[a-z]/.test(pw) && /[A-Z]/.test(pw),
    number: /[0-9]/.test(pw),
    symbol: /[^A-Za-z0-9]/.test(pw),
  };
}

export default function RegisterPage({ onRegister, onGoLogin }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [agree, setAgree] = useState(false);
  const [focused, setFocused] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const rules = checkRules(password);
  const pwValid = Object.values(rules).every(Boolean);
  const confirmValid = confirm.length > 0 && confirm === password;
  const canSubmit = name.trim().length > 1 && emailValid && pwValid && confirmValid && agree && !submitting;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError("");
    try {
      const user = await authApi.register(name.trim(), email, password);
      onRegister?.(user);
    } catch (err) {
      setError(err.message || "Registration failed — please try again.");
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
          <div className="auth-left-eyebrow"><Sparkles size={11} /> Get started free</div>
          <h1 className="auth-left-title auth-display">
            Turn meetings into<br /><span className="grad">working prototypes</span>
          </h1>
          <p className="auth-left-sub">
            Create your account and start converting transcripts and requirements
            into clickable prototypes in minutes.
          </p>
        </div>

        <div className="auth-trust-list">
          <div className="auth-trust-item"><span className="auth-trust-icon"><ShieldCheck size={13} /></span> End-to-end encrypted sessions</div>
          <div className="auth-trust-item"><span className="auth-trust-icon"><LockIcon size={13} /></span> Passwords hashed, never stored raw</div>
          <div className="auth-trust-item"><span className="auth-trust-icon"><Check size={13} /></span> Your prototypes stay private to your team</div>
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-form-wrap">
          <div className="auth-form-head">
            <h2 className="auth-title auth-display">Create your account</h2>
            <p className="auth-subtitle">Start turning meetings into working prototypes.</p>
          </div>

          {error && (
            <div className="auth-banner">
              <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="auth-field">
              <label className="auth-label">Full name</label>
              <div className={`auth-input-wrap ${focused === "name" ? "focused" : ""}`}>
                <User size={15} className="auth-input-icon" />
                <input
                  className="auth-input"
                  type="text"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onFocus={() => setFocused("name")}
                  onBlur={() => setFocused(null)}
                  autoComplete="name"
                />
              </div>
            </div>

            <div className="auth-field">
              <label className="auth-label">Email</label>
              <div className={`auth-input-wrap ${focused === "email" ? "focused" : ""}`}>
                <Mail size={15} className="auth-input-icon" />
                <input
                  className="auth-input"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setFocused("email")}
                  onBlur={() => setFocused(null)}
                  autoComplete="email"
                />
              </div>
            </div>

            <div className="auth-field">
              <label className="auth-label">Password</label>
              <div className={`auth-input-wrap ${focused === "password" ? "focused" : ""}`}>
                <Lock size={15} className="auth-input-icon" />
                <input
                  className="auth-input"
                  type={showPassword ? "text" : "password"}
                  placeholder="Create a strong password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocused("password")}
                  onBlur={() => setFocused(null)}
                  autoComplete="new-password"
                />
                <div className="auth-eye-btn" onClick={() => setShowPassword((s) => !s)}>
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </div>
              </div>
              <div className="pw-checklist">
                <ChecklistItem met={rules.length} label="At least 8 characters" />
                <ChecklistItem met={rules.case} label="Upper & lowercase letters" />
                <ChecklistItem met={rules.number} label="At least one number" />
                <ChecklistItem met={rules.symbol} label="At least one symbol" />
              </div>
            </div>

            <div className="auth-field">
              <label className="auth-label">Confirm password</label>
              <div className={`auth-input-wrap ${focused === "confirm" ? "focused" : ""} ${confirm.length > 0 && !confirmValid ? "error" : ""}`}>
                <Lock size={15} className="auth-input-icon" />
                <input
                  className="auth-input"
                  type={showConfirm ? "text" : "password"}
                  placeholder="Re-enter your password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  onFocus={() => setFocused("confirm")}
                  onBlur={() => setFocused(null)}
                  autoComplete="new-password"
                />
                <div className="auth-eye-btn" onClick={() => setShowConfirm((s) => !s)}>
                  {showConfirm ? <EyeOff size={15} /> : <Eye size={15} />}
                </div>
              </div>
            </div>

            <div className="auth-row">
              <span className={`auth-checkbox ${agree ? "checked" : ""}`} onClick={() => setAgree((a) => !a)}>
                {agree && <svg width="9" height="7" viewBox="0 0 9 7" fill="none"><path d="M1 3.5L3.2 5.7L8 1" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>}
              </span>
              <span className="auth-terms-text" onClick={() => setAgree((a) => !a)}>
                I agree to the <span className="auth-link" onClick={(e) => e.stopPropagation()}>Terms of Service</span> and{" "}
                <span className="auth-link" onClick={(e) => e.stopPropagation()}>Privacy Policy</span>
              </span>
            </div>

            <button type="submit" className="auth-submit" disabled={!canSubmit}>
              {submitting ? "Creating account…" : "Create account"} <ArrowRight size={15} />
            </button>
          </form>

          <div className="auth-divider">
            <div className="auth-divider-line" />
            <span className="auth-divider-text">or continue with</span>
            <div className="auth-divider-line" />
          </div>

          <div className="auth-oauth-row">
            <button className="auth-oauth-btn"><GoogleMark /> Google</button>
            <button className="auth-oauth-btn"><Github size={15} /> GitHub</button>
          </div>

          <div className="auth-footer-text">
            Already have an account? <span className="auth-link" onClick={onGoLogin}>Log in</span>
          </div>

          <div className="auth-security-note">
            <ShieldCheck size={12} /> Passwords are hashed and never stored in plain text
          </div>
        </div>
      </div>
    </div>
  );
}

function ChecklistItem({ met, label }) {
  return (
    <div className={`pw-check-item ${met ? "met" : ""}`}>
      <span className="pw-check-icon">
        {met ? <Check size={9} /> : <X size={9} />}
      </span>
      {label}
    </div>
  );
}

function GoogleMark() {
  return (
    <svg width="15" height="15" viewBox="0 0 18 18">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.88 2.7-6.62z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.95v2.33A9 9 0 0 0 9 18z"/>
      <path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.97H.95A9 9 0 0 0 0 9c0 1.45.35 2.83.95 4.03l3-2.33z"/>
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .95 4.97l3 2.33C4.66 5.17 6.65 3.58 9 3.58z"/>
    </svg>
  );
}

function LeftArcs() {
  return (
    <svg viewBox="0 0 900 900" preserveAspectRatio="xMidYMid slice"
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.8, zIndex: 1 }}>
      <defs>
        <linearGradient id="regArc1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="50%" stopColor="#ffffff" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#CBD5F5" stopOpacity="0.2" />
        </linearGradient>
        <linearGradient id="regArc2" x1="0" y1="0" x2="1" y2="0.3">
          <stop offset="0%" stopColor="#D9E4FF" stopOpacity="0" />
          <stop offset="50%" stopColor="#B9C6F2" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#9FE9CE" stopOpacity="0.25" />
        </linearGradient>
        <filter id="regBlur"><feGaussianBlur stdDeviation="6" /></filter>
      </defs>
      <path d="M -100 100 C 250 -80, 500 -60, 700 120 C 900 280, 1000 260, 1100 60"
        fill="none" stroke="url(#regArc1)" strokeWidth="20" filter="url(#regBlur)" />
      <path d="M -100 780 C 220 580, 560 550, 780 780 C 950 960, 1050 940, 1150 740"
        fill="none" stroke="url(#regArc2)" strokeWidth="16" filter="url(#regBlur)" opacity="0.6" />
    </svg>
  );
}
