from pydantic import BaseModel


class TranscriptEvent(BaseModel):
    type: str = "transcript"
    speaker: str
    language: str
    language_confidence: float
    original_text: str
    english_text: str
    timestamp: str


class ErrorEvent(BaseModel):
    type: str = "error"
    message: str
