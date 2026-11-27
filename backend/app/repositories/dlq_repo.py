from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from app.models.dead_letter import DeadLetterEvent
from app.domain.enums import DLQReplayStatus

class DLQRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_dlq_event(
        self,
        original_event_id: str,
        topic: str,
        payload: dict,
        error_type: str,
        error_message: str,
        partition: int = 0,
        offset: int = 0,
        retry_count: int = 0,
    ) -> DeadLetterEvent:
        dlq_event = DeadLetterEvent(
            original_event_id=original_event_id,
            topic=topic,
            partition=partition,
            offset=offset,
            payload=payload,
            error_type=error_type,
            error_message=str(error_message)[:1000],
            retry_count=retry_count,
            replay_status=DLQReplayStatus.PENDING.value,
        )
        self.session.add(dlq_event)
        await self.session.flush()
        return dlq_event

    async def get_by_event_id(self, event_id: str) -> Optional[DeadLetterEvent]:
        result = await self.session.execute(
            select(DeadLetterEvent).where(DeadLetterEvent.original_event_id == event_id)
        )
        return result.scalars().first()

    async def get_by_id(self, dlq_id: str) -> Optional[DeadLetterEvent]:
        result = await self.session.execute(
            select(DeadLetterEvent).where(DeadLetterEvent.id == dlq_id)
        )
        return result.scalars().first()

    async def list_dlq(self, replay_status: Optional[str] = None, page: int = 1, limit: int = 50) -> Tuple[List[DeadLetterEvent], int]:
        query = select(DeadLetterEvent)
        if replay_status:
            query = query.where(DeadLetterEvent.replay_status == replay_status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        query = query.order_by(desc(DeadLetterEvent.created_at))
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def mark_replayed(self, event_id: str, success: bool = True):
        dlq_event = await self.get_by_event_id(event_id)
        if dlq_event:
            dlq_event.replay_status = DLQReplayStatus.REPLAYED.value if success else DLQReplayStatus.FAILED.value
            dlq_event.replayed_at = datetime.now(timezone.utc)
            dlq_event.retry_count += 1
            await self.session.flush()
