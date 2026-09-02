from pydantic import BaseModel


class TranscriptEvent(BaseModel):
    """A new line appearing on screen. Sent as soon as Whisper returns."""

    type: str = "transcript"
    line_id: int
    speaker: str
    language: str
    language_confidence: float
    original_text: str
    # The original text until the translation lands, so a caption is never
    # blank. `translation_pending` says which of the two this currently is.
    english_text: str
    translation_pending: bool = True
    spoken_at: str


class TranscriptUpdateEvent(BaseModel):
    """Patches a line already on screen once its translation arrives."""

    type: str = "transcript_update"
    line_id: int
    english_text: str
    translation_pending: bool = False


class ErrorEvent(BaseModel):
    type: str = "error"
    message: str
