from typing import Optional, List, Dict, Any, Tuple
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.alert_repo import AlertRepository
from app.repositories.analyst_repo import AnalystRepository
from app.services.sla_engine import SLAEngine
from app.services.redis_service import redis_service
from app.websocket.manager import ws_manager
from app.models.fraud_alert import FraudAlert
from app.domain.enums import AlertStatus
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AlertTriageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.alert_repo = AlertRepository(session)
        self.analyst_repo = AnalystRepository(session)

    def _enrich_alert_sla(self, alert: FraudAlert) -> Dict[str, Any]:
        data = alert.to_dict()
        now = datetime.now(timezone.utc)
        resolved_at = alert.resolved_at
        
        remaining, percent_consumed, sla_status = SLAEngine.compute_sla_metrics(
            created_at=alert.created_at,
            sla_deadline=alert.sla_deadline,
            resolved_at=resolved_at,
        )
        
        is_expired = False
        if alert.claim_expires_at:
            claim_exp = alert.claim_expires_at
            if claim_exp.tzinfo is None:
                claim_exp = claim_exp.replace(tzinfo=timezone.utc)
            if claim_exp < now and alert.status != AlertStatus.RESOLVED.value:
                is_expired = True

        data.update({
            "sla_time_remaining_seconds": remaining,
            "sla_percent_consumed": percent_consumed,
            "sla_status": sla_status.value,
            "is_claim_expired": is_expired,
        })
        return data

    async def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        # Check cache
        cache_key = f"guardrail:alert:{alert_id}"
        cached = await redis_service.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

        alert = await self.alert_repo.get_by_id(alert_id)
        if not alert:
            return None

        enriched = self._enrich_alert_sla(alert)
        # Store in cache
        await redis_service.set(cache_key, json.dumps(enriched, default=str), ttl_seconds=30)
        return enriched

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
    ) -> Tuple[List[Dict[str, Any]], int]:
        alerts, total = await self.alert_repo.list_alerts(
            status=status,
            risk_level=risk_level,
            priority=priority,
            assigned_analyst_id=assigned_analyst_id,
            claimed=claimed,
            search=search,
            sort_by=sort_by,
            page=page,
            limit=limit,
        )
        enriched = [self._enrich_alert_sla(a) for a in alerts]
        return enriched, total

    async def claim_alert(
        self,
        alert_id: str,
        analyst_id: str,
        analyst_name: str,
        analyst_role: str,
        lease_duration_seconds: int = settings.CLAIM_LEASE_DURATION_SECONDS,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        alert, error = await self.alert_repo.atomic_claim_alert(
            alert_id=alert_id,
            analyst_id=analyst_id,
            analyst_name=analyst_name,
            analyst_role=analyst_role,
            lease_duration_seconds=lease_duration_seconds,
        )
        if error:
            return None, error

        # Invalidate cache
        await redis_service.delete(f"guardrail:alert:{alert_id}")
        await redis_service.delete_pattern("guardrail:dashboard:*")

        enriched = self._enrich_alert_sla(alert)
        # Broadcast via WebSockets
        await ws_manager.broadcast("alert.claimed", enriched)
        return enriched, None

    async def release_claim(
        self,
        alert_id: str,
        analyst_id: str,
        analyst_name: str,
        analyst_role: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        alert, error = await self.alert_repo.release_claim(
            alert_id=alert_id,
            analyst_id=analyst_id,
            analyst_name=analyst_name,
            analyst_role=analyst_role,
        )
        if error:
            return None, error

        await redis_service.delete(f"guardrail:alert:{alert_id}")
        await redis_service.delete_pattern("guardrail:dashboard:*")

        enriched = self._enrich_alert_sla(alert)
        await ws_manager.broadcast("alert.updated", enriched)
        return enriched, None

    async def renew_claim(
        self,
        alert_id: str,
        analyst_id: str,
        lease_duration_seconds: int = settings.CLAIM_LEASE_DURATION_SECONDS,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        alert, error = await self.alert_repo.renew_claim(
            alert_id=alert_id,
            analyst_id=analyst_id,
            lease_duration_seconds=lease_duration_seconds,
        )
        if error:
            return None, error

        await redis_service.delete(f"guardrail:alert:{alert_id}")
        enriched = self._enrich_alert_sla(alert)
        await ws_manager.broadcast("alert.updated", enriched)
        return enriched, None

    async def reassign_alert(
        self,
        alert_id: str,
        target_analyst_id: str,
        actor_id: str,
        actor_name: str,
        reason: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        target_analyst = await self.analyst_repo.get_by_id(target_analyst_id)
        if not target_analyst:
            return None, "Target analyst not found"

        alert, error = await self.alert_repo.reassign_alert(
            alert_id=alert_id,
            target_analyst=target_analyst,
            actor_id=actor_id,
            actor_name=actor_name,
            reason=reason,
        )
        if error:
            return None, error

        await redis_service.delete(f"guardrail:alert:{alert_id}")
        await redis_service.delete_pattern("guardrail:dashboard:*")

        enriched = self._enrich_alert_sla(alert)
        await ws_manager.broadcast("alert.reassigned", enriched)
        return enriched, None

    async def resolve_alert(
        self,
        alert_id: str,
        resolution_reason: str,
        notes: Optional[str],
        actor_id: str,
        actor_name: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        alert, error = await self.alert_repo.resolve_alert(
            alert_id=alert_id,
            resolution_reason=resolution_reason,
            notes=notes,
            actor_id=actor_id,
            actor_name=actor_name,
        )
        if error:
            return None, error

        await redis_service.delete(f"guardrail:alert:{alert_id}")
        await redis_service.delete_pattern("guardrail:dashboard:*")

        enriched = self._enrich_alert_sla(alert)
        await ws_manager.broadcast("alert.resolved", enriched)
        return enriched, None

    async def reopen_alert(
        self,
        alert_id: str,
        reason: str,
        actor_id: str,
        actor_name: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        alert, error = await self.alert_repo.reopen_alert(
            alert_id=alert_id,
            reason=reason,
            actor_id=actor_id,
            actor_name=actor_name,
        )
        if error:
            return None, error

        await redis_service.delete(f"guardrail:alert:{alert_id}")
        await redis_service.delete_pattern("guardrail:dashboard:*")

        enriched = self._enrich_alert_sla(alert)
        await ws_manager.broadcast("alert.updated", enriched)
        return enriched, None

    async def add_note(
        self,
        alert_id: str,
        note: str,
        actor_id: str,
        actor_name: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        alert, error = await self.alert_repo.add_note(
            alert_id=alert_id,
            note=note,
            actor_id=actor_id,
            actor_name=actor_name,
        )
        if error:
            return None, error

        await redis_service.delete(f"guardrail:alert:{alert_id}")
        enriched = self._enrich_alert_sla(alert)
        await ws_manager.broadcast("alert.updated", enriched)
        return enriched, None
