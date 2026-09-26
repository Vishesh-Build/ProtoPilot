import datetime
import logging

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.email import EmailNotConfigured, EmailSendError, send_password_reset_email
from app.core.rate_limit import (
    forgot_password_limiter,
    login_limiter,
    rate_limit_key,
    register_limiter,
    reset_password_limiter,
)
from app.core.security import (
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.core.session_cookies import clear_auth_cookies, issue_session
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)

logger = logging.getLogger("protopilot.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

# Pre-computed bcrypt hash of a random token used to thwart timing attacks.
# If a user is not found, verify_password() is still executed against this hash
# so the request duration matches an authentic password check (~200ms).
_DUMMY_BCRYPT_HASH = "$2b$12$e86g5M2c8z8v3.6gWcE72.Jv57sR7jXnNq29.Oq5o3m2P7e9T9vGe"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    register_limiter.check(rate_limit_key(request, body.email))

    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(email=body.email.lower(), name=body.name.strip(), hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await issue_session(user, db, response)
    return user


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    login_limiter.check(rate_limit_key(request, body.email))

    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    # Same error for "no such user" and "wrong password" — don't leak which one it was.
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if user is None or user.hashed_password is None:
        # user.hashed_password is None for accounts created via Google/GitHub
        # Run dummy verify_password to thwart timing-attacks for user enumeration
        verify_password(body.password, _DUMMY_BCRYPT_HASH)
        raise invalid

    if not verify_password(body.password, user.hashed_password):
        raise invalid

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been disabled.")

    await issue_session(user, db, response)
    return user


@router.post("/refresh", response_model=UserResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired — please log in again.")
    if refresh_token is None:
        raise unauthorized

    token_hash = hash_opaque_token(refresh_token)
    result = await db.execute(select(User).where(User.refresh_token_hash == token_hash))
    user = result.scalar_one_or_none()

    now = datetime.datetime.now(datetime.timezone.utc)
    # SQLite (unlike Postgres/asyncpg) returns naive datetimes even from a
    # timezone-aware column, and comparing naive vs aware raises. Normalise
    # before comparing so the backend works on both databases.
    expires_at = user.refresh_token_expires_at if user is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
    if user is None or expires_at is None or expires_at < now:
        raise unauthorized

    await issue_session(user, db, response)  # rotates the refresh token too
    return user


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.refresh_token_hash = None
    current_user.refresh_token_expires_at = None
    await db.commit()
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    forgot_password_limiter.check(rate_limit_key(request, body.email))

    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    # Always return the same message whether or not the account exists —
    # otherwise this endpoint becomes a way to check who has an account.
    generic_response = MessageResponse(
        message="If an account with that email exists, a reset link has been sent."
    )

    if user is None:
        return generic_response

    raw_token = generate_opaque_token()
    user.reset_token_hash = hash_opaque_token(raw_token)
    user.reset_token_expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.password_reset_token_expire_minutes
    )
    await db.commit()

    reset_link = f"{settings.password_reset_url_base}?token={raw_token}"

    try:
        await send_password_reset_email(user.email, reset_link)
    except EmailNotConfigured as e:
        logger.error("password reset requested but email isn't configured: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset email could not be sent — email service is not configured on the server.",
        ) from e
    except EmailSendError as e:
        logger.error("password reset email failed to send: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    return generic_response


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    reset_password_limiter.check(rate_limit_key(request, "reset_password"))

    token_hash = hash_opaque_token(body.token)
    result = await db.execute(select(User).where(User.reset_token_hash == token_hash))
    user = result.scalar_one_or_none()

    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired.")

    now = datetime.datetime.now(datetime.timezone.utc)
    # Same SQLite/Postgres naive-vs-aware difference as /auth/refresh.
    reset_expires = user.reset_token_expires_at if user is not None else None
    if reset_expires is not None and reset_expires.tzinfo is None:
        reset_expires = reset_expires.replace(tzinfo=datetime.timezone.utc)
    if user is None or reset_expires is None or reset_expires < now:
        raise invalid

    user.hashed_password = hash_password(body.new_password)
    # Single-use: clear it immediately so the same link can't be replayed.
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    # Also kill any existing session — a password reset should log out
    # every device that was using the old password.
    user.refresh_token_hash = None
    user.refresh_token_expires_at = None
    await db.commit()

    return MessageResponse(message="Password updated — please log in with your new password.")


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(token: str = ""):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reset Password — ProtoPilot</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #0B0F19;
      color: #E2E8F0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      position: relative;
      overflow-x: hidden;
    }}
    .glow {{
      position: fixed;
      width: 500px;
      height: 500px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(99, 102, 241, 0.22), rgba(168, 85, 247, 0.12), transparent 70%);
      top: -100px;
      left: 50%;
      transform: translateX(-50%);
      filter: blur(80px);
      pointer-events: none;
    }}
    .card {{
      position: relative;
      z-index: 1;
      width: 100%;
      max-width: 440px;
      background: rgba(17, 24, 39, 0.9);
      border: 1px solid rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(24px);
      border-radius: 20px;
      padding: 36px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 24px;
    }}
    .brand-icon {{
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: linear-gradient(135deg, #4F46E5, #7C3AED);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 18px;
      color: #fff;
    }}
    .brand-name {{
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 700;
      font-size: 18px;
      color: #FFFFFF;
      letter-spacing: -0.02em;
    }}
    h1 {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 24px;
      font-weight: 700;
      color: #FFFFFF;
      margin-bottom: 8px;
      letter-spacing: -0.02em;
    }}
    p.desc {{
      font-size: 14px;
      color: #94A3B8;
      line-height: 1.5;
      margin-bottom: 24px;
    }}
    .form-group {{
      margin-bottom: 18px;
    }}
    label {{
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #CBD5E1;
      margin-bottom: 6px;
    }}
    .input-box {{
      position: relative;
      display: flex;
      align-items: center;
    }}
    input {{
      width: 100%;
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      padding: 12px 42px 12px 14px;
      font-size: 14px;
      color: #FFFFFF;
      outline: none;
      transition: all 0.2s;
      font-family: inherit;
    }}
    input:focus {{
      border-color: #6366F1;
      background: rgba(30, 41, 59, 0.95);
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
    }}
    .toggle-eye {{
      position: absolute;
      right: 12px;
      background: none;
      border: none;
      color: #64748B;
      cursor: pointer;
      font-size: 13px;
      user-select: none;
    }}
    .toggle-eye:hover {{ color: #CBD5E1; }}
    .btn {{
      width: 100%;
      background: linear-gradient(135deg, #4F46E5, #7C3AED);
      color: #FFFFFF;
      font-weight: 600;
      font-size: 14.5px;
      border: none;
      border-radius: 10px;
      padding: 13px;
      cursor: pointer;
      margin-top: 8px;
      transition: all 0.2s;
      box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
    }}
    .btn:hover:not(:disabled) {{
      opacity: 0.95;
      transform: translateY(-1px);
    }}
    .btn:disabled {{
      opacity: 0.6;
      cursor: not-allowed;
    }}
    .alert {{
      padding: 12px;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 18px;
      display: none;
    }}
    .alert-error {{
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #FCA5A5;
    }}
    .success-view {{
      display: none;
      text-align: center;
      padding: 12px 0;
    }}
    .checkmark {{
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #10B981;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 26px;
      margin: 0 auto 16px;
    }}
  </style>
</head>
<body>
  <div class="glow"></div>
  <div class="card">
    <div class="brand">
      <div class="brand-icon">⚡</div>
      <div class="brand-name">ProtoPilot</div>
    </div>

    <div id="resetFormView">
      <h1>Set new password</h1>
      <p class="desc">Enter a secure new password for your ProtoPilot account.</p>

      <div id="alertBox" class="alert alert-error"></div>

      <form id="resetForm">
        <input type="hidden" id="tokenField" value="{token}" />
        <div class="form-group">
          <label for="newPassword">New Password</label>
          <div class="input-box">
            <input type="password" id="newPassword" placeholder="Minimum 8 characters" required minlength="8" />
            <button type="button" class="toggle-eye" onclick="togglePass('newPassword', this)">Show</button>
          </div>
        </div>

        <div class="form-group">
          <label for="confirmPassword">Confirm New Password</label>
          <div class="input-box">
            <input type="password" id="confirmPassword" placeholder="Re-enter new password" required minlength="8" />
            <button type="button" class="toggle-eye" onclick="togglePass('confirmPassword', this)">Show</button>
          </div>
        </div>

        <button type="submit" id="submitBtn" class="btn">Update Password</button>
      </form>
    </div>

    <div id="successView" class="success-view">
      <div class="checkmark">✓</div>
      <h1>Password Updated!</h1>
      <p class="desc" style="margin-bottom: 24px;">Your password has been successfully reset. You can now open the ProtoPilot app and sign in with your new password.</p>
      <button class="btn" onclick="window.close()">Close this window</button>
    </div>
  </div>

  <script>
    function togglePass(id, btn) {{
      const input = document.getElementById(id);
      if (input.type === 'password') {{
        input.type = 'text';
        btn.textContent = 'Hide';
      }} else {{
        input.type = 'password';
        btn.textContent = 'Show';
      }}
    }}

    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token') || '{token}';
    if (tokenFromUrl) {{
      document.getElementById('tokenField').value = tokenFromUrl;
    }}

    const form = document.getElementById('resetForm');
    const alertBox = document.getElementById('alertBox');
    const submitBtn = document.getElementById('submitBtn');

    form.addEventListener('submit', async (e) => {{
      e.preventDefault();
      alertBox.style.display = 'none';

      const token = document.getElementById('tokenField').value.trim();
      const newPassword = document.getElementById('newPassword').value;
      const confirmPassword = document.getElementById('confirmPassword').value;

      if (!token) {{
        alertBox.textContent = 'Missing reset token. Please use the exact link sent to your email.';
        alertBox.style.display = 'block';
        return;
      }}

      if (newPassword.length < 8) {{
        alertBox.textContent = 'Password must be at least 8 characters long.';
        alertBox.style.display = 'block';
        return;
      }}

      if (newPassword !== confirmPassword) {{
        alertBox.textContent = 'Passwords do not match.';
        alertBox.style.display = 'block';
        return;
      }}

      submitBtn.disabled = true;
      submitBtn.textContent = 'Updating...';

      try {{
        const res = await fetch('/auth/reset-password', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ token: token, new_password: newPassword }})
        }});

        const data = await res.json();
        if (!res.ok) {{
          throw new Error(data.detail || 'Failed to reset password.');
        }}

        document.getElementById('resetFormView').style.display = 'none';
        document.getElementById('successView').style.display = 'block';
      }} catch (err) {{
        alertBox.textContent = err.message || 'Something went wrong. Please try again.';
        alertBox.style.display = 'block';
      }} finally {{
        submitBtn.disabled = false;
        submitBtn.textContent = 'Update Password';
      }}
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)
