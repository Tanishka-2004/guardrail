import pytest
from datetime import datetime, timezone, timedelta
from app.services.sla_engine import SLAEngine
from app.domain.enums import RiskLevel, Priority, SLAStatus

def test_sla_durations():
    assert SLAEngine.get_sla_duration_minutes(RiskLevel.CRITICAL) == 5
    assert SLAEngine.get_sla_duration_minutes(RiskLevel.HIGH) == 15
    assert SLAEngine.get_sla_duration_minutes(RiskLevel.MEDIUM) == 60
    assert SLAEngine.get_sla_duration_minutes(RiskLevel.LOW) == 240

def test_sla_metrics_computation():
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(minutes=4)
    deadline = created_at + timedelta(minutes=5)

    remaining, pct, status = SLAEngine.compute_sla_metrics(created_at, deadline)
    assert remaining <= 60
    assert pct >= 75.0
    assert status == SLAStatus.WARNING

    # Test Breached
    past_deadline = now - timedelta(minutes=1)
    rem_b, pct_b, status_b = SLAEngine.compute_sla_metrics(created_at, past_deadline)
    assert rem_b < 0
    assert status_b == SLAStatus.BREACHED

def test_sla_priority_escalation():
    # If healthy, no escalation
    needed, prio = SLAEngine.check_escalation_needed(Priority.P4_LOW, SLAStatus.HEALTHY, 50.0)
    assert not needed
    assert prio == Priority.P4_LOW

    # If breached, escalate P4 -> P3, P3 -> P2, P2 -> P1
    needed, prio = SLAEngine.check_escalation_needed(Priority.P4_LOW, SLAStatus.BREACHED, 105.0)
    assert needed
    assert prio == Priority.P3_MEDIUM

    needed, prio = SLAEngine.check_escalation_needed(Priority.P3_MEDIUM, SLAStatus.BREACHED, 105.0)
    assert needed
    assert prio == Priority.P2_HIGH

    needed, prio = SLAEngine.check_escalation_needed(Priority.P2_HIGH, SLAStatus.BREACHED, 105.0)
    assert needed
    assert prio == Priority.P1_CRITICAL
