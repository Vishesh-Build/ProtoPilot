"""
Builds a real ZIP export from whatever a meeting actually produced —
no placeholder/fake content. If an agent hasn't run yet, its file just
isn't included (rather than faking one).
"""

import io
import zipfile

from app.meetings.session import MeetingSession

AGENT_FILENAMES = {
    "pm": "01_PRD.md",
    "architect": "02_architecture.md",
    "database": "03_database_schema.md",
    "api": "04_api_endpoints.md",
    "ui": "05_frontend_screens.md",
    "backend": "06_backend_logic.md",
    "qa": "07_qa_checklist.md",
    "devops": "08_deployment_guide.md",
    "prototype": "09_prototype.html",
}


def build_export_zip(session: MeetingSession) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # --- Requirements (always available once any exist) ---
        if session.requirements:
            lines = ["# Requirements\n"]
            for r in session.requirements:
                lines.append(f"## {r.title}")
                lines.append(f"- Category: {r.category}")
                lines.append(f"- Priority: {r.priority}")
                lines.append(f"- Confidence: {r.confidence}%")
                lines.append(f"- Status: {r.status}")
                lines.append("")
            zf.writestr("00_requirements.md", "\n".join(lines))

        # --- Transcript ---
        if session.transcript:
            lines = ["# Meeting Transcript\n"]
            for line in session.transcript:
                lines.append(f"**{line.speaker}** ({line.language}): {line.original_text}")
                if line.language != "en":
                    lines.append(f"> {line.english_text}")
                lines.append("")
            zf.writestr("00_transcript.md", "\n".join(lines))

        # --- Real agent outputs, only the ones that actually ran ---
        for agent_id, filename in AGENT_FILENAMES.items():
            output = session.agent_outputs.get(agent_id)
            if not output:
                continue
            if agent_id == "prototype":
                # Raw HTML, not wrapped in markdown — this file should open directly in a browser.
                zf.writestr(filename, output)
            else:
                zf.writestr(filename, f"# {filename.replace('_', ' ').replace('.md', '')}\n\n{output}\n")

        # --- Manifest so it's clear what this export actually contains ---
        manifest_lines = [
            f"# ProtoPilot Export — {session.name}",
            f"Meeting ID: {session.meeting_id}",
            f"Created: {session.created_at}",
            f"Requirements: {len(session.requirements)}",
            f"Transcript lines: {len(session.transcript)}",
            f"Agent outputs included: {', '.join(session.agent_outputs.keys()) or 'none — prototype not generated yet'}",
        ]
        zf.writestr("MANIFEST.txt", "\n".join(manifest_lines))

    buffer.seek(0)
    return buffer.read()
