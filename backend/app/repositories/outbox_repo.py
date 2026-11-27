from typing import List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import asc
from app.models.outbox import AlertOutbox

class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_pending_events(self, limit: int = 100) -> List[AlertOutbox]:
        stmt = (
            select(AlertOutbox)
            .where(AlertOutbox.published_at.is_(None))
            .order_by(asc(AlertOutbox.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_published(self, outbox_id: str):
        result = await self.session.execute(
            select(AlertOutbox).where(AlertOutbox.id == outbox_id)
        )
        item = result.scalars().first()
        if item:
            item.published_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def increment_retry(self, outbox_id: str):
        result = await self.session.execute(
            select(AlertOutbox).where(AlertOutbox.id == outbox_id)
        )
        item = result.scalars().first()
        if item:
            item.retry_count += 1
            await self.session.flush()
