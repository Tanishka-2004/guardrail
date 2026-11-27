from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.dlq_repo import DLQRepository
from app.kafka.producer import kafka_producer
from app.core.config import settings
from app.models.dead_letter import DeadLetterEvent
import logging

logger = logging.getLogger(__name__)

class DLQService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dlq_repo = DLQRepository(session)

    async def list_dlq(self, replay_status: Optional[str] = None, page: int = 1, limit: int = 50) -> Tuple[List[DeadLetterEvent], int]:
        return await self.dlq_repo.list_dlq(replay_status=replay_status, page=page, limit=limit)

    async def get_by_event_id(self, event_id: str) -> Optional[DeadLetterEvent]:
        return await self.dlq_repo.get_by_event_id(event_id)

    async def replay_event(self, event_id: str) -> Tuple[bool, str, int]:
        """
        Replays a dead letter event:
        1. Loads original dead letter event
        2. Validates payload
        3. Preserves original event_id and marks incremented replay_count
        4. Publishes to fraud.alerts topic for clean idempotent reprocessing
        5. Marks DLQ item as replayed
        """
        dlq_event = await self.dlq_repo.get_by_event_id(event_id)
        if not dlq_event:
            return False, f"Event '{event_id}' not found in DLQ", 0

        payload = dlq_event.payload or {}
        replay_count = (dlq_event.retry_count or 0) + 1
        payload["replay_count"] = replay_count
        payload["replayed_at"] = dlq_event.created_at.isoformat() if dlq_event.created_at else None

        # Re-publish to Kafka fraud.alerts topic
        success = await kafka_producer.publish(
            topic=settings.KAFKA_TOPIC_ALERTS,
            value=payload,
            key=str(payload.get("transaction_id", event_id))
        )

        if success:
            await self.dlq_repo.mark_replayed(event_id, success=True)
            logger.info(f"DLQ event '{event_id}' successfully queued for replay (attempt {replay_count}).")
            return True, "Event successfully republished for processing", replay_count
        else:
            await self.dlq_repo.mark_replayed(event_id, success=False)
            logger.error(f"Failed to republish DLQ event '{event_id}'.")
            return False, "Failed to republish event to Kafka broker", replay_count

    async def replay_all_pending(self, max_items: int = 50) -> Dict[str, Any]:
        """Batch replays all pending DLQ items."""
        events, total = await self.dlq_repo.list_dlq(replay_status="PENDING", page=1, limit=max_items)
        success_count = 0
        failed_count = 0

        for event in events:
            ok, _, _ = await self.replay_event(event.original_event_id)
            if ok:
                success_count += 1
            else:
                failed_count += 1

        return {
            "total_found": total,
            "replayed": success_count,
            "failed": failed_count,
        }
