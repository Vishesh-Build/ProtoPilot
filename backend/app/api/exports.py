from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.meeting_auth import require_meeting_host
from app.exports.builder import AGENT_FILENAMES, build_export_zip
from app.meetings.session import MeetingSession

router = APIRouter(prefix="/meetings", tags=["exports"])


@router.get("/{meeting_id}/export/status")
async def export_status(session: MeetingSession = Depends(require_meeting_host)):
    """
    Tells the Export Center screen exactly what's real and available right
    now — so it can show an honest list instead of guessing. Host only,
    same as the actual export/code download.
    """
    return {
        "has_requirements": len(session.requirements) > 0,
        "has_transcript": len(session.transcript) > 0,
        "agent_outputs_available": list(session.agent_outputs.keys()),
        "all_agent_files": list(AGENT_FILENAMES.values()),
        "ready_to_export": bool(session.requirements or session.transcript or session.agent_outputs),
    }


@router.get("/{meeting_id}/export")
async def export_meeting(session: MeetingSession = Depends(require_meeting_host)):
    """Downloads a real ZIP of everything this meeting actually produced. Host only."""
    if not (session.requirements or session.transcript or session.agent_outputs):
        raise HTTPException(status_code=400, detail="Nothing to export yet — nothing has been recorded or generated for this meeting.")

    zip_bytes = build_export_zip(session)
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in session.name).strip() or "protopilot-export"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.zip"'},
    )
