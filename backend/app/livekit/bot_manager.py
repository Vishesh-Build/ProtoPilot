"""
Tracks the running transcription-bot asyncio task per meeting, so
start-call is idempotent (calling it twice doesn't spawn two bots
fighting over the same room) and stop-call/meeting-end can cleanly
cancel it.
"""

import asyncio
import logging

logger = logging.getLogger("protopilot.livekit.bot_manager")


class BotManager:
    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}

    async def start(self, meeting_id: str) -> None:
        existing = self._tasks.get(meeting_id)
        if existing is not None and not existing.done():
            logger.info("meeting %s: transcription bot already running", meeting_id)
            return

        from app.livekit.transcription_bot import run_transcription_bot

        task = asyncio.create_task(run_transcription_bot(meeting_id), name=f"livekit-bot-{meeting_id}")
        self._tasks[meeting_id] = task
        logger.info("meeting %s: transcription bot starting", meeting_id)

    async def stop(self, meeting_id: str) -> None:
        task = self._tasks.pop(meeting_id, None)
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("meeting %s: transcription bot stopped", meeting_id)

    async def stop_all(self) -> None:
        for meeting_id in list(self._tasks.keys()):
            await self.stop(meeting_id)


bot_manager = BotManager()
