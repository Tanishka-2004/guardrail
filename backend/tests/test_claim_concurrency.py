import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from app.repositories.alert_repo import AlertRepository
from app.models.fraud_alert import FraudAlert
from app.domain.enums import UserRole

@pytest.mark.asyncio
async def test_atomic_claim_locking_concurrency(db_session, seed_analysts):
    repo = AlertRepository(db_session)
    now = datetime.now(timezone.utc)
    alert_id = str(uuid.uuid4())

    alert = FraudAlert(
        id=alert_id,
        event_id=f"evt_claim_{alert_id[:8]}",
        transaction_id="tx_claim_concurrent",
        customer_id="cust_999",
        merchant_id="merch_conc",
        transaction_amount=15000.0,
        currency="USD",
        transaction_type="PURCHASE",
        transaction_timestamp=now,
        fraud_score=88.0,
        risk_level="CRITICAL",
        fraud_reason="Critical transaction",
        status="NEW",
        priority="P1_CRITICAL",
        sla_deadline=now + timedelta(minutes=5),
        sla_duration_minutes=5,
        source_event_metadata={},
    )
    db_session.add(alert)
    await db_session.commit()

    analyst1 = seed_analysts["analyst"]
    analyst2 = seed_analysts["senior"]

    # Analyst 1 claims the alert
    claimed_alert, err1 = await repo.atomic_claim_alert(
        alert_id=alert_id,
        analyst_id=analyst1.id,
        analyst_name=analyst1.name,
        analyst_role=analyst1.role,
        lease_duration_seconds=300,
    )
    await db_session.commit()
    assert err1 is None
    assert claimed_alert.claimed_by == analyst1.name
    assert claimed_alert.status == "CLAIMED"

    # Analyst 2 attempts to claim the same alert while lease is active
    denied_alert, err2 = await repo.atomic_claim_alert(
        alert_id=alert_id,
        analyst_id=analyst2.id,
        analyst_name=analyst2.name,
        analyst_role=analyst2.role,
        lease_duration_seconds=300,
    )
    assert denied_alert is None
    assert "currently locked by Sarah Chen" in err2

    # Supervisor CAN override the claim
    supervisor = seed_analysts["supervisor"]
    sup_alert, err_sup = await repo.atomic_claim_alert(
        alert_id=alert_id,
        analyst_id=supervisor.id,
        analyst_name=supervisor.name,
        analyst_role=supervisor.role,
        lease_duration_seconds=300,
    )
    await db_session.commit()
    assert err_sup is None
    assert sup_alert.claimed_by == supervisor.name

@pytest.mark.asyncio
async def test_lease_expiration_and_stale_reap(db_session, seed_analysts):
    repo = AlertRepository(db_session)
    now = datetime.now(timezone.utc)
    alert_id = str(uuid.uuid4())

    analyst = seed_analysts["analyst"]
    alert = FraudAlert(
        id=alert_id,
        event_id=f"evt_reap_{alert_id[:8]}",
        transaction_id="tx_reap",
        customer_id="cust_777",
        merchant_id="merch_reap",
        transaction_amount=3000.0,
        currency="USD",
        transaction_type="PURCHASE",
        transaction_timestamp=now,
        fraud_score=65.0,
        risk_level="HIGH",
        fraud_reason="High risk lease test",
        status="CLAIMED",
        priority="P2_HIGH",
        sla_deadline=now + timedelta(minutes=15),
        sla_duration_minutes=15,
        claimed_by=analyst.name,
        assigned_analyst_id=analyst.id,
        claimed_at=now - timedelta(minutes=15),
        claim_expires_at=now - timedelta(minutes=5),  # EXPIRED 5 minutes ago!
        source_event_metadata={},
    )
    db_session.add(alert)
    await db_session.commit()

    # Verify stale alerts finder detects it
    stale_list = await repo.get_stale_claimed_alerts()
    assert any(a.id == alert_id for a in stale_list)

    # Reap the stale claim
    reaped = await repo.reap_stale_claim(alert_id)
    await db_session.commit()
    assert reaped is True

    # Alert should now be unlocked and reset to NEW
    reaped_alert = await repo.get_by_id(alert_id)
    assert reaped_alert.claimed_by is None
    assert reaped_alert.claim_expires_at is None
    assert reaped_alert.status == "NEW"
