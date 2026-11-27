import asyncio
import logging
from app.core.database import AsyncSessionLocal
from app.repositories.outbox_repo import OutboxRepository
from app.kafka.producer import kafka_producer
from app.core.config import settings

logger = logging.getLogger(__name__)

class OutboxPublisherWorker:
    """
    Transactional Outbox Publisher:
    Reads un-published domain events stored in the alert_outbox table and
    reliably publishes them to downstream Kafka topic (fraud.alerts.events).
    Guarantees that database commit and event publishing do not diverge.
    """
    def __init__(self, interval_seconds: int = 5):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._task = None

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Outbox publisher worker started.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Outbox publisher worker stopped.")

    async def _run_loop(self):
        while self.is_running:
            try:
                await self.publish_outbox_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in outbox publisher loop: {e}", exc_info=True)
            await asyncio.sleep(self.interval_seconds)

    async def publish_outbox_events(self):
        async with AsyncSessionLocal() as session:
            try:
                repo = OutboxRepository(session)
                pending_events = await repo.get_pending_events(limit=50)

                for item in pending_events:
                    success = await kafka_producer.publish(
                        topic=settings.KAFKA_TOPIC_EVENTS,
                        value={
                            "event_id": item.id,
                            "aggregate_id": item.aggregate_id,
                            "event_type": item.event_type,
                            "payload": item.payload,
                            "created_at": item.created_at.isoformat() if item.created_at else None,
                        },
                        key=item.aggregate_id
                    )

                    if success:
                        await repo.mark_published(item.id)
                    else:
                        await repo.increment_retry(item.id)

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Outbox publication error: {e}")

outbox_publisher = OutboxPublisherWorker()
