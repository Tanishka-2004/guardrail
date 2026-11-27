import asyncio
import logging
from app.core.database import AsyncSessionLocal
from app.services.dlq_service import DLQService

logger = logging.getLogger(__name__)

class DLQAutoReplayWorker:
    """
    Scheduled background worker that checks for transient DLQ failures
    and automatically re-attempts processing with bounded attempts and exponential backoff.
    """
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._task = None

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("DLQ auto-replay worker started.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("DLQ auto-replay worker stopped.")

    async def _run_loop(self):
        while self.is_running:
            try:
                await self.auto_replay_transient()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in DLQ auto-replay loop: {e}", exc_info=True)
            await asyncio.sleep(self.interval_seconds)

    async def auto_replay_transient(self):
        async with AsyncSessionLocal() as session:
            try:
                service = DLQService(session)
                # Replay bounded batch of pending events
                result = await service.replay_all_pending(max_items=10)
                if result.get("replayed", 0) > 0:
                    logger.info(f"DLQ Auto-replay pass replayed {result['replayed']} items.")
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"DLQ auto-replay pass failed: {e}")

dlq_auto_replayer = DLQAutoReplayWorker()
