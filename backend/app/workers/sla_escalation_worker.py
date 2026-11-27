import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal
from app.models.fraud_alert import FraudAlert
from app.domain.enums import AlertStatus, Priority, SLAStatus, AuditAction
from app.services.sla_engine import SLAEngine
from app.models.audit_log import AlertAuditLog
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

class SLAEscalationWorker:
    """
    Background worker that monitors active alerts against their SLA deadline.
    Triggers automatic priority escalations and broadcasts SLA warnings & breaches.
    """
    def __init__(self, interval_seconds: int = 15):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._task = None

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("SLA escalation worker started.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("SLA escalation worker stopped.")

    async def _run_loop(self):
        while self.is_running:
            try:
                await self.check_sla_escalations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in SLA escalation worker loop: {e}", exc_info=True)
            await asyncio.sleep(self.interval_seconds)

    async def check_sla_escalations(self):
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            try:
                # Select all un-resolved alerts
                result = await session.execute(
                    select(FraudAlert).where(
                        FraudAlert.status.notin_([AlertStatus.RESOLVED.value])
                    )
                )
                alerts = result.scalars().all()

                for alert in alerts:
                    remaining, percent_consumed, sla_status = SLAEngine.compute_sla_metrics(
                        created_at=alert.created_at,
                        sla_deadline=alert.sla_deadline,
                    )

                    current_priority = Priority(alert.priority)
                    needs_escalate, new_priority = SLAEngine.check_escalation_needed(
                        priority=current_priority,
                        sla_status=sla_status,
                        percent_consumed=percent_consumed,
                    )

                    if needs_escalate and new_priority != current_priority:
                        prev_priority = alert.priority
                        alert.priority = new_priority.value
                        alert.status = AlertStatus.ESCALATED.value
                        alert.version += 1
                        alert.updated_at = now

                        # Record audit log
                        audit = AlertAuditLog(
                            alert_id=alert.id,
                            actor_name="SLA_ENGINE",
                            action=AuditAction.ESCALATED.value,
                            previous_state={"priority": prev_priority},
                            new_state={"priority": alert.priority, "status": alert.status},
                            metadata_info={
                                "sla_status": sla_status.value,
                                "percent_consumed": percent_consumed,
                                "reason": f"SLA threshold reached ({percent_consumed}% elapsed)"
                            },
                        )
                        session.add(audit)

                        logger.warning(
                            f"Auto-escalated alert '{alert.id}' from {prev_priority} to {alert.priority} (SLA {sla_status.value})"
                        )
                        await ws_manager.broadcast("alert.escalated", alert.to_dict())

                    elif sla_status == SLAStatus.BREACHED:
                        await ws_manager.broadcast("alert.sla_breached", alert.to_dict())

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed SLA escalation pass: {e}")

sla_escalation_worker = SLAEscalationWorker()
