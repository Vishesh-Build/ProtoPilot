"""
Server-side transcription bot.

Joins a meeting's LiveKit room as a hidden ("recorder") participant,
subscribes to every OTHER participant's audio track as they publish it,
and runs each one through its own independent VAD -> Whisper ->
translate pipeline. Because each participant has a separate WebRTC
track, there is no crosstalk/mixing to untangle — the hard part is only
figuring out where one utterance ends for a given person, which is what
the VAD segmentation below solves.

One bot per active meeting (see bot_manager.py) — cancelled when the
host calls /stop-call or /end.
"""

import asyncio
import logging
import time

import webrtcvad
from livekit import api as lk_api
from livekit import rtc

from app.config import settings
from app.core.connection_manager import meeting_connections
from app.meetings.session import session_registry
from app.requirements.extractor import extract_new_requirements
from app.transcription.translate import translate_to_english
from app.transcription.whisper_service import transcribe_utterance

logger = logging.getLogger("protopilot.livekit.bot")

_SAMPLE_RATE = 16000  # matches whisper_service's expected PCM16 input
_FRAME_MS = 30
_FRAME_BYTES = int(_SAMPLE_RATE * (_FRAME_MS / 1000) * 2)  # 2 bytes/sample (16-bit)

# A finished "utterance" shorter than this is almost never real speech — it's
# a mic pop, breath, or a single word wrongly flagged by webrtcvad as speech
# for one or two frames. Sending these to Whisper is what was producing the
# garbled/nonsense transcript: tiny noise fragments (as short as 30-90ms)
# were being transcribed and interleaved with real sentences, and language
# detection on <1s of audio is unreliable (hence 'ur'/'mr' misfires on what
# was actually Hindi/English). Real spoken words are essentially always
# 300ms+, so anything shorter gets dropped here before it ever reaches Whisper.
_MIN_UTTERANCE_MS = 500
_MIN_UTTERANCE_BYTES = int(_SAMPLE_RATE * (_MIN_UTTERANCE_MS / 1000) * 2)

# Bounds how many utterances (across ALL meetings) can be inside an actual
# Whisper call at once — a burst of simultaneous speakers queues instead
# of all hitting the CPU at the same moment.
_transcription_semaphore = asyncio.Semaphore(settings.max_concurrent_transcriptions)


class ParticipantAudioBuffer:
    """
    Tracks one participant's in-progress utterance. Fed 30ms frames;
    flushes (returns the accumulated audio) once enough trailing silence
    has been seen after some speech.
    """

    def __init__(self, vad: webrtcvad.Vad):
        self._vad = vad
        self._speech_buffer = bytearray()
        self._silence_ms = 0
        self._has_speech = False

    def add_frame(self, frame_bytes: bytes) -> bytes | None:
        is_speech = self._vad.is_speech(frame_bytes, _SAMPLE_RATE)

        if is_speech:
            self._speech_buffer.extend(frame_bytes)
            self._silence_ms = 0
            self._has_speech = True
            return None

        if not self._has_speech:
            return None  # still waiting for someone to start talking

        self._silence_ms += _FRAME_MS
        if self._silence_ms >= settings.vad_silence_timeout_seconds * 1000:
            finished = bytes(self._speech_buffer)
            self._speech_buffer = bytearray()
            self._has_speech = False
            self._silence_ms = 0
            return finished

        # Still inside the allowed gap — keep the silence in the buffer too,
        # short pauses mid-sentence shouldn't get clipped out.
        self._speech_buffer.extend(frame_bytes)
        return None


async def _handle_finished_utterance(meeting_id: str, speaker_name: str, audio_bytes: bytes):
    session = session_registry.get(meeting_id)
    if session is None:
        return

    utterance_seconds = len(audio_bytes) / (_SAMPLE_RATE * 2)
    t_queued = time.monotonic()

    async with _transcription_semaphore:
        wait_time = time.monotonic() - t_queued
        if wait_time > 1.0:
            # Longer than ~1s means the semaphore (max_concurrent_transcriptions)
            # was the bottleneck, not Whisper itself — a backlog of utterances
            # queued up faster than they could be processed.
            logger.warning(
                "meeting %s: utterance for %s waited %.2fs in queue before a Whisper slot freed up",
                meeting_id, speaker_name, wait_time,
            )
        t_whisper = time.monotonic()
        try:
            result = await transcribe_utterance(audio_bytes)
        except Exception:  # noqa: BLE001 — one bad utterance shouldn't kill the bot
            logger.exception("meeting %s: transcription failed for %s", meeting_id, speaker_name)
            return
        whisper_time = time.monotonic() - t_whisper

    if not result.text:
        return

    t_translate = time.monotonic()
    english_text = await translate_to_english(result.text, result.language)
    translate_time = time.monotonic() - t_translate

    total_time = time.monotonic() - t_queued
    logger.info(
        "meeting %s: %.2fs of audio -> transcript in %.2fs total (queue_wait=%.2fs whisper=%.2fs translate=%.2fs)",
        meeting_id, utterance_seconds, total_time, wait_time, whisper_time, translate_time,
    )

    session.add_transcript_line(
        speaker=speaker_name,
        language=result.language,
        original_text=result.text,
        english_text=english_text,
    )

    await meeting_connections.broadcast(meeting_id, {
        "type": "transcript",
        "speaker": speaker_name,
        "language": result.language,
        "language_confidence": round(result.language_probability, 3),
        "original_text": result.text,
        "english_text": english_text,
    })

    t_extract = time.monotonic()
    new_req_dicts = await extract_new_requirements(session)
    extract_time = time.monotonic() - t_extract
    if extract_time > 2.0:
        logger.warning(
            "meeting %s: requirement extraction took %.2fs — this is what delays the Points panel specifically",
            meeting_id, extract_time,
        )
    if new_req_dicts:
        added = session.add_requirements(new_req_dicts)
        await meeting_connections.broadcast(meeting_id, {
            "type": "requirements",
            "new": [
                {"id": r.id, "title": r.title, "category": r.category, "priority": r.priority, "confidence": r.confidence, "status": r.status}
                for r in added
            ],
            "readiness_percent": session.readiness_percent(),
        })


async def _consume_participant_audio(meeting_id: str, participant_identity: str, participant_name: str, track: rtc.Track):
    vad = webrtcvad.Vad(settings.vad_aggressiveness)
    buffer = ParticipantAudioBuffer(vad)

    # Resamples to exactly what VAD + Whisper expect, regardless of what
    # sample rate/channel count the publisher's mic actually captured at.
    audio_stream = rtc.AudioStream(track, sample_rate=_SAMPLE_RATE, num_channels=1)

    pending = bytearray()
    try:
        async for event in audio_stream:
            frame = event.frame
            pending.extend(bytes(frame.data))

            while len(pending) >= _FRAME_BYTES:
                chunk = bytes(pending[:_FRAME_BYTES])
                del pending[:_FRAME_BYTES]

                finished_utterance = buffer.add_frame(chunk)
                if finished_utterance and len(finished_utterance) > _MIN_UTTERANCE_BYTES:
                    asyncio.create_task(
                        _handle_finished_utterance(meeting_id, participant_name, finished_utterance)
                    )
    except Exception:  # noqa: BLE001 — a stream error for one participant shouldn't kill the bot for everyone else
        logger.exception("meeting %s: audio stream ended for %s (%s)", meeting_id, participant_name, participant_identity)


async def run_transcription_bot(meeting_id: str):
    room = rtc.Room()
    tasks: dict[str, asyncio.Task] = {}

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication, participant: rtc.RemoteParticipant):
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return  # video/screen-share tracks aren't transcribed
        key = participant.identity
        if key in tasks and not tasks[key].done():
            return  # already consuming this participant's audio
        display_name = participant.name or participant.identity
        tasks[key] = asyncio.create_task(
            _consume_participant_audio(meeting_id, key, display_name, track)
        )
        logger.info("meeting %s: now transcribing %s separately", meeting_id, display_name)

    @room.on("track_unsubscribed")
    def on_track_unsubscribed(track: rtc.Track, publication, participant: rtc.RemoteParticipant):
        task = tasks.pop(participant.identity, None)
        if task is not None:
            task.cancel()

    token = (
        lk_api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(f"protopilot-transcriber-{meeting_id}")
        .with_name("ProtoPilot Transcriber")
        .with_grants(
            lk_api.VideoGrants(
                room_join=True,
                room=meeting_id,
                can_publish=False,   # the bot never sends audio/video, only listens
                can_subscribe=True,
                hidden=True,          # doesn't show up as a visible participant tile
            )
        )
        .to_jwt()
    )

    try:
        await room.connect(settings.livekit_url, token)
        logger.info("meeting %s: transcription bot connected to LiveKit room", meeting_id)
        # Stay connected until cancelled (by /stop-call, /end, or bot_manager.stop_all).
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("meeting %s: transcription bot crashed", meeting_id)
    finally:
        for task in tasks.values():
            task.cancel()
        await room.disconnect()
        logger.info("meeting %s: transcription bot disconnected", meeting_id)
