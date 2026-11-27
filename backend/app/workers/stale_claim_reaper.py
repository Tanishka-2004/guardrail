import asyncio
import logging
from datetime import datetime, timezone
from app.core.database import AsyncSessionLocal
from app.repositories.alert_repo import AlertRepository
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

class StaleClaimReaperWorker:
    """
    Background worker that reclaims abandoned or timed-out alerts.
    If an analyst claims an alert but does not resolve or renew it before
    claim_expires_at, this worker resets the claim and makes it available again.
    """
    def __init__(self, interval_seconds: int = 15):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._task = None

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Stale claim reaper worker started.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stale claim reaper worker stopped.")

    async def _run_loop(self):
        while self.is_running:
            try:
                await self.reap_stale_claims()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in stale claim reaper loop: {e}", exc_info=True)
            await asyncio.sleep(self.interval_seconds)

    async def reap_stale_claims(self):
        async with AsyncSessionLocal() as session:
            try:
                alert_repo = AlertRepository(session)
                stale_alerts = await alert_repo.get_stale_claimed_alerts()
                if stale_alerts:
                    for alert in stale_alerts:
                        reaped = await alert_repo.reap_stale_claim(alert.id)
                        if reaped:
                            logger.info(f"Reaped expired claim on alert '{alert.id}' (was claimed by {alert.claimed_by})")
                            await ws_manager.broadcast("alert.updated", alert.to_dict())
                    await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to reap stale claims: {e}")

stale_claim_reaper = StaleClaimReaperWorker()
