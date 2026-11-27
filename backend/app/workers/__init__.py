import asyncio
from app.workers.stale_claim_reaper import stale_claim_reaper
from app.workers.sla_escalation_worker import sla_escalation_worker
from app.workers.outbox_publisher import outbox_publisher
from app.workers.dlq_auto_replay import dlq_auto_replayer
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class BackgroundWorkersManager:
    """Orchestrates all background workers."""
    @classmethod
    async def start_all(cls):
        if not settings.ENABLE_BACKGROUND_WORKERS:
            logger.info("Background workers are disabled by configuration.")
            return

        logger.info("Starting all GuardRail background workers...")
        await stale_claim_reaper.start()
        await sla_escalation_worker.start()
        await outbox_publisher.start()
        await dlq_auto_replayer.start()
        logger.info("All background workers started successfully.")

    @classmethod
    async def stop_all(cls):
        logger.info("Stopping all GuardRail background workers...")
        await dlq_auto_replayer.stop()
        await outbox_publisher.stop()
        await sla_escalation_worker.stop()
        await stale_claim_reaper.stop()
        logger.info("All background workers stopped successfully.")

background_workers = BackgroundWorkersManager
