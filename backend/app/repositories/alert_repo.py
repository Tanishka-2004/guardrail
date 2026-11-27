from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func, or_, and_, desc, asc
from app.models.fraud_alert import FraudAlert
from app.models.analyst import Analyst
from app.models.audit_log import AlertAuditLog
from app.models.outbox import AlertOutbox
from app.domain.enums import AlertStatus, Priority, AuditAction, UserRole
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AlertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, alert_id: str, for_update: bool = False) -> Optional[FraudAlert]:
        stmt = select(FraudAlert).where(FraudAlert.id == alert_id)
        if for_update:
            # PostgreSQL row-level exclusive lock
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_event_id(self, event_id: str) -> Optional[FraudAlert]:
        result = await self.session.execute(
            select(FraudAlert).where(FraudAlert.event_id == event_id)
        )
        return result.scalars().first()

    async def create_alert_idempotent(self, alert_data: Dict[str, Any]) -> Tuple[FraudAlert, bool]:
        """
        Idempotent creation:
        Checks if event_id already exists.
        If it does, returns (existing_alert, False).
        If not, persists the new alert and an audit log entry in the same transaction.
        """
        existing = await self.get_by_event_id(alert_data["event_id"])
        if existing:
            logger.info(f"Idempotency hit: Alert with event_id '{alert_data['event_id']}' already exists. Skipping duplicate creation.")
            return existing, False

        alert = FraudAlert(**alert_data)
        self.session.add(alert)
        await self.session.flush()

        # Create audit entry
        audit = AlertAuditLog(
            alert_id=alert.id,
            actor_name="INGESTION_ENGINE",
            action=AuditAction.INGESTED.value,
            previous_state={},
            new_state={"status": alert.status, "risk_level": alert.risk_level, "priority": alert.priority},
            metadata_info={"event_id": alert.event_id, "fraud_score": alert.fraud_score},
        )
        self.session.add(audit)

        # Enqueue Outbox event
        outbox = AlertOutbox(
            aggregate_id=alert.id,
            event_type="alert.created",
            payload=alert.to_dict(),
        )
        self.session.add(outbox)

        await self.session.flush()
        return alert, True

    async def atomic_claim_alert(
        self,
        alert_id: str,
        analyst_id: str,
        analyst_name: str,
        analyst_role: str,
        lease_duration_seconds: int = settings.CLAIM_LEASE_DURATION_SECONDS,
    ) -> Tuple[Optional[FraudAlert], Optional[str]]:
        """
        Atomic claim-locking:
        - Locks the row using SELECT FOR UPDATE
        - Validates lease expiration: if already claimed and lease active, only supervisors or same analyst can override
        - Updates claimed_by, claim_expires_at, version, status
        - Logs audit trail
        Returns (alert, error_message)
        """
        now = datetime.now(timezone.utc)
        alert = await self.get_by_id(alert_id, for_update=True)
        if not alert:
            return None, "Alert not found"

        if alert.status == AlertStatus.RESOLVED.value:
            return None, "Cannot claim a resolved alert"

        # Check existing active claim
        is_claimed = alert.claimed_by is not None
        claim_exp = alert.claim_expires_at
        if claim_exp and claim_exp.tzinfo is None:
            claim_exp = claim_exp.replace(tzinfo=timezone.utc)
        has_expired = claim_exp is not None and claim_exp < now

        if is_claimed and not has_expired:
            # Active lease exists
            if alert.assigned_analyst_id != analyst_id:
                # Different analyst attempting to claim
                if analyst_role not in (UserRole.SUPERVISOR.value, UserRole.ADMIN.value):
                    return None, f"Alert is currently locked by {alert.claimed_by} until {alert.claim_expires_at.isoformat()}"

        prev_state = {
            "status": alert.status,
            "claimed_by": alert.claimed_by,
            "assigned_analyst_id": alert.assigned_analyst_id,
            "claim_expires_at": alert.claim_expires_at.isoformat() if alert.claim_expires_at else None,
            "version": alert.version,
        }

        # Apply claim
        expires_at = now + timedelta(seconds=lease_duration_seconds)
        alert.claimed_by = analyst_name
        alert.assigned_analyst_id = analyst_id
        alert.claimed_at = now
        alert.claim_expires_at = expires_at
        alert.status = AlertStatus.CLAIMED.value if alert.status == AlertStatus.NEW.value else alert.status
        alert.version += 1
        alert.updated_at = now

        # Audit log
        audit = AlertAuditLog(
            alert_id=alert.id,
            actor_id=analyst_id,
            actor_name=analyst_name,
            action=AuditAction.CLAIMED.value,
            previous_state=prev_state,
            new_state={
                "status": alert.status,
                "claimed_by": analyst_name,
                "assigned_analyst_id": analyst_id,
                "claim_expires_at": expires_at.isoformat(),
                "version": alert.version,
            },
            metadata_info={"lease_duration_seconds": lease_duration_seconds},
        )
        self.session.add(audit)

        # Outbox event
        outbox = AlertOutbox(
            aggregate_id=alert.id,
            event_type="alert.claimed",
            payload=alert.to_dict(),
        )
        self.session.add(outbox)

        await self.session.flush()
        return alert, None

    async def release_claim(
        self,
        alert_id: str,
        analyst_id: str,
        analyst_name: str,
        analyst_role: str,
    ) -> Tuple[Optional[FraudAlert], Optional[str]]:
        alert = await self.get_by_id(alert_id, for_update=True)
        if not alert:
            return None, "Alert not found"

        if alert.assigned_analyst_id != analyst_id and analyst_role not in (UserRole.SUPERVISOR.value, UserRole.ADMIN.value):
            return None, "Cannot release alert claimed by another analyst"

        prev_state = {
            "claimed_by": alert.claimed_by,
            "status": alert.status,
            "claim_expires_at": alert.claim_expires_at.isoformat() if alert.claim_expires_at else None,
        }

        alert.claimed_by = None
        alert.assigned_analyst_id = None
        alert.claimed_at = None
        alert.claim_expires_at = None
        if alert.status == AlertStatus.CLAIMED.value:
            alert.status = AlertStatus.NEW.value
        alert.version += 1
        alert.updated_at = datetime.now(timezone.utc)

        audit = AlertAuditLog(
            alert_id=alert.id,
            actor_id=analyst_id,
            actor_name=analyst_name,
            action=AuditAction.RELEASED.value,
            previous_state=prev_state,
            new_state={"status": alert.status, "claimed_by": None},
            metadata_info={"reason": "Manual release"},
        )
        self.session.add(audit)

        outbox = AlertOutbox(
            aggregate_id=alert.id,
            event_type="alert.updated",
            payload=alert.to_dict(),
        )
        self.session.add(outbox)

        await self.session.flush()
        return alert, None

    async def renew_claim(
        self,
        alert_id: str,
        analyst_id: str,
        lease_duration_seconds: int = settings.CLAIM_LEASE_DURATION_SECONDS,
    ) -> Tuple[Optional[FraudAlert], Optional[str]]:
        now = datetime.now(timezone.utc)
        alert = await self.get_by_id(alert_id, for_update=True)
        if not alert:
            return None, "Alert not found"

        if alert.assigned_analyst_id != analyst_id:
            return None, "Cannot renew claim owned by another analyst"

        alert.claim_expires_at = now + timedelta(seconds=lease_duration_seconds)
        alert.version += 1
        alert.updated_at = now

        audit = AlertAuditLog(
            alert_id=alert.id,
            actor_id=analyst_id,
            actor_name=alert.claimed_by,
            action=AuditAction.RENEWED.value,
            previous_state={},
            new_state={"claim_expires_at": alert.claim_expires_at.isoformat()},
            metadata_info={"lease_duration_seconds": lease_duration_seconds},
        )
        self.session.add(audit)
        await self.session.flush()
        return alert, None

    async def reassign_alert(
        self,
        alert_id: str,
        target_analyst: Analyst,
        actor_id: str,
        actor_name: str,
        reason: Optional[str] = None,
    ) -> Tuple[Optional[FraudAlert], Optional[str]]:
        now = datetime.now(timezone.utc)
        alert = await self.get_by_id(alert_id, for_update=True)
        if not alert:
            return None, "Alert not found"

        prev_state = {
            "assigned_analyst_id": alert.assigned_analyst_id,
            "claimed_by": alert.claimed_by,
            "status": alert.status,
        }

        alert.assigned_analyst_id = target_analyst.id
        alert.claimed_by = target_analyst.name
        alert.claimed_at = now
        alert.claim_expires_at = now + timedelta(seconds=settings.CLAIM_LEASE_DURATION_SECONDS)
        alert.status = AlertStatus.UNDER_REVIEW.value
        alert.version += 1
        alert.updated_at = now

        audit = AlertAuditLog(
            alert_id=alert.id,
            actor_id=actor_id,
            actor_name=actor_name,
            action=AuditAction.REASSIGNED.value,
            previous_state=prev_state,
            new_state={"assigned_analyst_id": target_analyst.id, "claimed_by": target_analyst.name},
            metadata_info={"reason": reason or "Supervisor reassignment"},
        )
        self.session.add(audit)

        outbox = AlertOutbox(
            aggregate_id=alert.id,
            event_type="alert.reassigned",
            payload=alert.to_dict(),
        )
        self.session.add(outbox)

        await self.session.flush()
        return alert, None

    async def resolve_alert(
        self,
        alert_id: str,
        resolution_reason: str,
        notes: Optional[str],
        actor_id: str,
        actor_name: str,
    ) -> Tuple[Optional[FraudAlert], Optional[str]]:
        now = datetime.now(timezone.utc)
        alert = await self.get_by_id(alert_id, for_update=True)
        if not alert:
            return None, "Alert not found"

        prev_state = {
            "status": alert.status,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        }

        alert.status = AlertStatus.RESOLVED.value
        alert.resolved_at = now
        alert.resolution_reason = resolution_reason
        if notes:
            alert.notes = (alert.notes + "\n" if alert.notes else "") + f"[{now.isoformat()}] {actor_name}: {notes}"
        alert.claimed_by = None
        alert.claim_expires_at = None
        alert.version += 1
        alert.updated_at = now

        audit = AlertAuditLog(
            alert_id=alert.id,
            actor_id=actor_id,
            actor_name=actor_name,
            action=AuditAction.RESOLVED.value,
            previous_state=prev_state,
            new_state={"status": alert.status, "resolution_reason": resolution_reason},
            metadata_info={"notes": notes},
        )
        self.session.add(audit)

        outbox = AlertOutbox(
            aggregate_id=alert.id,
            event_type="alert.resolved",
            payload=alert.to_dict(),
        )
        self.session.add(outbox)

        await self.session.flush()
        return alert, None

    async def reopen_alert(
        self,
        alert_id: str,
        reason: str,
        actor_id: str,
        actor_name: str,
    ) -> Tuple[Optional[FraudAlert], Optional[str]]:
        now = datetime.now(timezone.utc)
        alert = await self.get_by_id(alert_id, for_update=True)
        if not alert:
            return None, "Alert not found"

        prev_state = {"status": alert.status}
        alert.status = AlertStatus.REOPENED.value
        alert.resolved_at = None
        alert.resolution_reason = None
        alert.version += 1
        alert.updated_at = now

        audit = AlertAuditLog(
            alert_id=alert.id,
            actor_id=actor_id,
            actor_name=actor_name,
            action=AuditAction.REOPENED.value,
            previous_state=prev_state,
            new_state={"status": alert.status},
            metadata_info={"reason": reason},
        )
        self.session.add(audit)

        outbox = AlertOutbox(
            aggregate_id=alert.id,
            event_type="alert.updated",
            payload=alert.to_dict(),
        )
        self.session.add(outbox)

        await self.session.flush()
        return alert, None

    async def add_note(
        self,
        alert_id: str,
        note: str,
        actor_id: str,
        actor_name: str,
    ) -> Tuple[Optional[FraudAlert], Optional[str]]:
        now = datetime.now(timezone.utc)
        alert = await self.get_by_id(alert_id, for_update=True)
        if not alert:
            return None, "Alert not found"

        formatted_note = f"[{now.strftime('%Y-%m-%d %H:%M:%S UTC')}] {actor_name}: {note}"
        alert.notes = (alert.notes + "\n" if alert.notes else "") + formatted_note
        alert.updated_at = now

        audit = AlertAuditLog(
            alert_id=alert.id,
            actor_id=actor_id,
            actor_name=actor_name,
            action=AuditAction.NOTE_ADDED.value,
            previous_state={},
            new_state={},
            metadata_info={"note": note},
        )
        self.session.add(audit)
        await self.session.flush()
        return alert, None

    async def list_alerts(
        self,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_analyst_id: Optional[str] = None,
        claimed: Optional[bool] = None,
        search: Optional[str] = None,
        sort_by: str = "priority_sla",
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[FraudAlert], int]:
        query = select(FraudAlert)

        # Filters
        if status:
            query = query.where(FraudAlert.status == status)
        if risk_level:
            query = query.where(FraudAlert.risk_level == risk_level)
        if priority:
            query = query.where(FraudAlert.priority == priority)
        if assigned_analyst_id:
            query = query.where(FraudAlert.assigned_analyst_id == assigned_analyst_id)
        if claimed is not None:
            if claimed:
                query = query.where(FraudAlert.claimed_by.isnot(None))
            else:
                query = query.where(FraudAlert.claimed_by.is_(None))
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    FraudAlert.id.ilike(search_pattern),
                    FraudAlert.event_id.ilike(search_pattern),
                    FraudAlert.transaction_id.ilike(search_pattern),
                    FraudAlert.customer_id.ilike(search_pattern),
                    FraudAlert.merchant_id.ilike(search_pattern),
                    FraudAlert.fraud_reason.ilike(search_pattern),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # Sorting
        if sort_by == "priority_sla":
            # Priority first (P1 -> P4), then urgent SLA deadline
            query = query.order_by(asc(FraudAlert.sla_deadline), desc(FraudAlert.fraud_score))
        elif sort_by == "sla_deadline":
            query = query.order_by(asc(FraudAlert.sla_deadline))
        elif sort_by == "fraud_score":
            query = query.order_by(desc(FraudAlert.fraud_score))
        elif sort_by == "created_at":
            query = query.order_by(desc(FraudAlert.created_at))
        elif sort_by == "amount":
            query = query.order_by(desc(FraudAlert.transaction_amount))
        else:
            query = query.order_by(desc(FraudAlert.created_at))

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        items = result.scalars().all()
        return list(items), total

    async def get_stale_claimed_alerts(self) -> List[FraudAlert]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(FraudAlert)
            .where(
                FraudAlert.claimed_by.isnot(None),
                FraudAlert.claim_expires_at < now,
                FraudAlert.status.notin_([AlertStatus.RESOLVED.value])
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reap_stale_claim(self, alert_id: str) -> bool:
        alert = await self.get_by_id(alert_id, for_update=True)
        if not alert or alert.claim_expires_at is None:
            return False
        
        now = datetime.now(timezone.utc)
        claim_exp = alert.claim_expires_at
        if claim_exp and claim_exp.tzinfo is None:
            claim_exp = claim_exp.replace(tzinfo=timezone.utc)
        if claim_exp >= now:
            return False  # Claim was renewed in the meantime

        prev_owner = alert.claimed_by
        alert.claimed_by = None
        alert.assigned_analyst_id = None
        alert.claimed_at = None
        alert.claim_expires_at = None
        if alert.status == AlertStatus.CLAIMED.value:
            alert.status = AlertStatus.NEW.value
        alert.version += 1
        alert.updated_at = now

        audit = AlertAuditLog(
            alert_id=alert.id,
            actor_name="CLAIM_REAPER_WORKER",
            action=AuditAction.RELEASED.value,
            previous_state={"claimed_by": prev_owner},
            new_state={"claimed_by": None, "status": alert.status},
            metadata_info={"reason": "Lease expired automatically"},
        )
        self.session.add(audit)
        await self.session.flush()
        return True
