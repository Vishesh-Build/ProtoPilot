from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.meeting_auth import get_session_or_404, require_meeting_host
from app.db.models import User
from app.meetings.session import MeetingSession, session_registry

router = APIRouter(prefix="/meetings", tags=["meetings"])


class CreateMeetingRequest(BaseModel):
    meeting_id: str
    name: str


class RenameMeetingRequest(BaseModel):
    name: str


@router.post("")
async def create_meeting(body: CreateMeetingRequest, current_user: User = Depends(get_current_user)):
    """
    Registers a meeting so it shows up in the Dashboard / Meeting History.
    Called once when the user clicks "Start Meeting" in the Create Meeting screen.
    Whoever creates it becomes the host — only they can manage requirements,
    generate the prototype, export it, or end/delete the meeting later.
    Safe to call again with the same meeting_id (e.g. reconnect) — just
    updates the name; the original host is preserved.
    """
    session = session_registry.get_or_create(body.meeting_id, name=body.name, host_user_id=current_user.id)
    return session.summary()


@router.get("")
async def list_meetings(current_user: User = Depends(get_current_user)):
    """
    Powers the Dashboard's Recent Meetings panel and the Meeting History screen.

    Scoped to meetings this user hosts. The registry is process-wide, so
    returning all of it handed every logged-in user the ids and names of
    everyone else's meetings — and a meeting_id is all you need to join.
    A participant reaches a meeting by its id (GET /meetings/{id}), not
    through this list.
    """
    return {"meetings": [s.summary() for s in session_registry.list_all() if s.is_host(current_user.id)]}


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    session = get_session_or_404(meeting_id)
    return session.summary()


@router.get("/{meeting_id}/agent-outputs")
async def get_agent_outputs(meeting_id: str, current_user: User = Depends(get_current_user)):
    session = get_session_or_404(meeting_id)
    return {"agent_outputs": session.agent_outputs}


@router.get("/{meeting_id}/transcript")
async def get_transcript(meeting_id: str, current_user: User = Depends(get_current_user)):
    session = get_session_or_404(meeting_id)
    # to_dict() carries id + spoken_at, so a client reloading mid-meeting can
    # match up with the lines it already received over the WebSocket.
    return {"transcript": [line.to_dict() for line in session.transcript]}


@router.post("/{meeting_id}/end")
async def end_meeting(session: MeetingSession = Depends(require_meeting_host)):
    """Called when the host hits Stop/End Meeting — marks it ended for
    history/dashboard display, and stops the transcription bot if it's
    still connected to the LiveKit room."""
    from app.livekit.bot_manager import bot_manager
    await bot_manager.stop(session.meeting_id)
    session.mark_ended()
    return session.summary()


@router.patch("/{meeting_id}")
async def rename_meeting(
    body: RenameMeetingRequest,
    session: MeetingSession = Depends(require_meeting_host),
):
    """Rename a meeting from Meeting History's rename action. Host only."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Meeting name can't be empty.")
    session.rename(name)
    return session.summary()


@router.delete("/{meeting_id}")
async def delete_meeting(meeting_id: str, session: MeetingSession = Depends(require_meeting_host)):
    """Called from Meeting History's Delete action — removes it permanently. Host only."""
    from app.requirements.extractor import clear_extraction_state

    session_registry.delete(meeting_id)
    clear_extraction_state(meeting_id)
    return {"deleted": True, "meeting_id": meeting_id}


@router.post("/{meeting_id}/cancel-generation")
async def cancel_meeting_generation(session: MeetingSession = Depends(require_meeting_host)):
    """Cancels an ongoing generation pipeline for this meeting. Host only."""
    from app.ws.generate import cancel_pipeline
    cancelled = cancel_pipeline(session.meeting_id)
    return {"meeting_id": session.meeting_id, "cancelled": cancelled}


@router.get("/{meeting_id}/generation-status")
async def get_generation_status(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Returns whether generation is currently running and overall progress."""
    session = get_session_or_404(meeting_id)
    from app.ws.generate import get_pipeline_status
    status = get_pipeline_status(session.meeting_id)
    has_prototype = bool(session.agent_outputs.get("prototype"))
    return {
        "meeting_id": session.meeting_id,
        "has_prototype": has_prototype,
        **status,
    }


# ============================================================
# Waiting Room / Host Admission (Knocking) System
# ============================================================

@router.post("/{meeting_id}/join-requests")
async def request_join_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Participant knocks to enter the meeting. Host is notified in real time."""
    session = get_session_or_404(meeting_id)
    if session.is_user_admitted(current_user.id):
        return {"status": "approved", "admitted": True}

    req = session.request_join(current_user.id, current_user.name, current_user.email)
    from app.core.connection_manager import meeting_connections
    await meeting_connections.broadcast(session.meeting_id, {
        "type": "knock",
        "request": req,
    })
    return {"status": "pending", "admitted": False, "request": req}


@router.get("/{meeting_id}/join-requests/status")
async def check_join_status(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Participant checks if host has approved their knock."""
    session = get_session_or_404(meeting_id)
    admitted = session.is_user_admitted(current_user.id)
    if admitted:
        return {"status": "approved", "admitted": True}
    req = session.join_requests.get(current_user.id, {})
    return {"status": req.get("status", "pending"), "admitted": False}


@router.get("/{meeting_id}/join-requests")
async def list_pending_join_requests(session: MeetingSession = Depends(require_meeting_host)):
    """Host views pending participant knocking requests."""
    pending = [r for r in session.join_requests.values() if r.get("status") == "pending"]
    return {"requests": pending}


@router.post("/{meeting_id}/join-requests/{target_user_id}/approve")
async def approve_join_request(target_user_id: str, session: MeetingSession = Depends(require_meeting_host)):
    """Host admits participant into the meeting."""
    session.approve_join(target_user_id)
    from app.core.connection_manager import meeting_connections
    await meeting_connections.broadcast(session.meeting_id, {
        "type": "knock_approved",
        "user_id": target_user_id,
    })
    return {"approved": True, "user_id": target_user_id}


@router.post("/{meeting_id}/join-requests/{target_user_id}/reject")
async def reject_join_request(target_user_id: str, session: MeetingSession = Depends(require_meeting_host)):
    """Host denies participant entry into the meeting."""
    session.reject_join(target_user_id)
    from app.core.connection_manager import meeting_connections
    await meeting_connections.broadcast(session.meeting_id, {
        "type": "knock_rejected",
        "user_id": target_user_id,
    })
    return {"rejected": True, "user_id": target_user_id}


# ============================================================
# Transcript & Meeting Notes Export
# ============================================================

from fastapi.responses import PlainTextResponse

@router.get("/{meeting_id}/export-transcript", response_class=PlainTextResponse)
async def export_meeting_transcript(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Exports full meeting transcript and extracted requirements as a clean Markdown document."""
    session = get_session_or_404(meeting_id)

    lines = [
        f"# Meeting Transcript: {session.name}",
        f"**Meeting ID:** `{session.meeting_id}`",
        f"**Date:** {session.created_at}",
        f"**Status:** {session.status.upper()}",
        "",
        "---",
        "",
        "## 📝 Discussion Transcript",
        "",
    ]

    if not session.transcript:
        lines.append("*No speech recorded in this session.*")
    else:
        for item in session.transcript:
            speaker = item.speaker or "Speaker"
            time_str = item.spoken_at[:19].replace("T", " ") if item.spoken_at else ""
            lang = f" ({item.language})" if item.language else ""
            lines.append(f"**[{time_str}] {speaker}{lang}:**")
            lines.append(f"> {item.display_text()}")
            if item.english_text and item.original_text != item.english_text:
                lines.append(f"> *Original:* {item.original_text}")
            lines.append("")

    lines.extend([
        "",
        "---",
        "",
        "## 💡 Extracted Requirements",
        "",
    ])

    if not session.requirements:
        lines.append("*No requirement points were extracted or approved.*")
    else:
        for req in session.requirements:
            status_emoji = "✅" if req.status == "approved" else "❌" if req.status == "rejected" else "⏳"
            lines.append(f"- {status_emoji} **[{req.category}]** {req.title} *(Priority: {req.priority}, Confidence: {req.confidence}%)*")

    lines.extend([
        "",
        "---",
        "*Generated by ProtoPilot AI Collaboration Engine*",
    ])

    content = "\n".join(lines)
    clean_filename = "".join(c for c in session.name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    headers = {"Content-Disposition": f'attachment; filename="ProtoPilot_{clean_filename or "Meeting"}_Transcript.md"'}
    return PlainTextResponse(content=content, headers=headers)


# ============================================================
# AI Prototype Quick-Tweak (Conversational Refinement)
# ============================================================

class TweakPrototypeRequest(BaseModel):
    prompt: str


@router.post("/{meeting_id}/tweak-prototype")
async def tweak_prototype(
    meeting_id: str,
    body: TweakPrototypeRequest,
    current_user: User = Depends(get_current_user),
):
    """
    AI Quick-Tweak: Iteratively refines the existing prototype HTML using a prompt
    (e.g., 'Switch theme to dark mode', 'Add pricing comparison table').
    """
    from app.llm.router import llm_router

    prompt_text = body.prompt.strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail="Tweak prompt cannot be empty.")

    session = session_registry.get(meeting_id)
    current_html = session.agent_outputs.get("prototype") if session else None

    if not current_html:
        raise HTTPException(
            status_code=400,
            detail="No prototype has been generated for this meeting yet. Generate one first before tweaking."
        )

    system_prompt = (
        "You are an expert Senior Frontend UX Engineer and rapid prototyping master. "
        "You are given an existing single-file interactive HTML prototype (which includes inline CSS/Tailwind CDN and interactive JS). "
        "The user wants to make a specific modification or addition to this prototype: "
        f"\"{prompt_text}\". "
        "Apply the requested change directly into the prototype HTML, carefully preserving all other existing styling, features, and interactivity. "
        "STRICT CLIENT PRESENTATION RULE: This is an end-user client prototype. NEVER add database schema names, SQL tables, REST API paths (like POST /...), or developer debug toasts. All user feedback must be clean, natural product UI messages. "
        "Return ONLY the complete revised executable HTML document starting with <!DOCTYPE html> and ending with </html>. "
        "Do NOT include markdown code blocks, backticks, or any conversational explanation before or after the code."
    )

    user_prompt = f"User Request: {prompt_text}\n\nExisting Prototype HTML:\n```html\n{current_html}\n```"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        result = await llm_router.chat(messages, max_tokens=8192)
        raw_output = result.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI refinement failed: {str(e)}")

    # Clean markdown code blocks if the model wrapped it
    cleaned_html = raw_output
    if cleaned_html.startswith("```html"):
        cleaned_html = cleaned_html[7:]
    elif cleaned_html.startswith("```"):
        cleaned_html = cleaned_html[3:]
    if cleaned_html.endswith("```"):
        cleaned_html = cleaned_html[:-3]
    cleaned_html = cleaned_html.strip()

    from app.services.stitch_service import sanitize_prototype_html
    cleaned_html = sanitize_prototype_html(cleaned_html)

    if session:
        session.agent_outputs["prototype"] = cleaned_html
        session.replace_agent_outputs(session.agent_outputs)

        # Broadcast update to all live meeting participants
        from app.core.connection_manager import meeting_connections
        await meeting_connections.broadcast(session.meeting_id, {
            "type": "prototype_tweaked",
            "prototype": cleaned_html,
        })

    return {"prototype": cleaned_html, "status": "success"}


