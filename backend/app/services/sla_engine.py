from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple
from app.domain.enums import RiskLevel, Priority, SLAStatus
from app.core.config import settings

class SLAEngine:
    """
    Calculates SLA targets, remaining time, percentage consumed,
    and determines when alerts should be automatically escalated.
    """
    @classmethod
    def get_sla_duration_minutes(cls, risk_level: RiskLevel) -> int:
        if risk_level == RiskLevel.CRITICAL:
            return settings.SLA_CRITICAL_MINUTES
        elif risk_level == RiskLevel.HIGH:
            return settings.SLA_HIGH_MINUTES
        elif risk_level == RiskLevel.MEDIUM:
            return settings.SLA_MEDIUM_MINUTES
        else:
            return settings.SLA_LOW_MINUTES

    @classmethod
    def calculate_deadline(cls, created_at: datetime, duration_minutes: int) -> datetime:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at + timedelta(minutes=duration_minutes)

    @classmethod
    def compute_sla_metrics(
        cls,
        created_at: datetime,
        sla_deadline: datetime,
        resolved_at: datetime = None
    ) -> Tuple[int, float, SLAStatus]:
        """
        Returns:
            (time_remaining_seconds, percent_consumed, sla_status)
        """
        now = resolved_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if sla_deadline.tzinfo is None:
            sla_deadline = sla_deadline.replace(tzinfo=timezone.utc)

        total_duration_seconds = max((sla_deadline - created_at).total_seconds(), 1.0)
        time_elapsed_seconds = (now - created_at).total_seconds()
        time_remaining_seconds = int((sla_deadline - now).total_seconds())

        percent_consumed = round((time_elapsed_seconds / total_duration_seconds) * 100.0, 1)

        if time_remaining_seconds <= 0:
            sla_status = SLAStatus.BREACHED
        elif percent_consumed >= settings.SLA_WARNING_THRESHOLD_PERCENT:
            sla_status = SLAStatus.WARNING
        else:
            sla_status = SLAStatus.HEALTHY

        return time_remaining_seconds, percent_consumed, sla_status

    @classmethod
    def check_escalation_needed(
        cls,
        priority: Priority,
        sla_status: SLAStatus,
        percent_consumed: float
    ) -> Tuple[bool, Priority]:
        """
        Determines if alert should be elevated to a higher priority.
        Only escalates when the SLA deadline is truly breached.
        """
        if sla_status == SLAStatus.BREACHED:
            if priority == Priority.P4_LOW:
                return True, Priority.P3_MEDIUM
            elif priority == Priority.P3_MEDIUM:
                return True, Priority.P2_HIGH
            elif priority == Priority.P2_HIGH:
                return True, Priority.P1_CRITICAL
        return False, priority
