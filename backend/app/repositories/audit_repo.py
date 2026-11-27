from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from app.models.audit_log import AlertAuditLog

class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_alert_id(self, alert_id: str) -> List[AlertAuditLog]:
        result = await self.session.execute(
            select(AlertAuditLog)
            .where(AlertAuditLog.alert_id == alert_id)
            .order_by(desc(AlertAuditLog.timestamp))
        )
        return list(result.scalars().all())

    async def record_audit(
        self,
        alert_id: str,
        action: str,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None,
        previous_state: Dict[str, Any] = None,
        new_state: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ) -> AlertAuditLog:
        audit = AlertAuditLog(
            alert_id=alert_id,
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            previous_state=previous_state or {},
            new_state=new_state or {},
            metadata_info=metadata or {},
        )
        self.session.add(audit)
        await self.session.flush()
        return audit
