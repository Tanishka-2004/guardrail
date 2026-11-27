import pytest
import uuid
from datetime import datetime, timezone
from app.repositories.alert_repo import AlertRepository
from app.models.fraud_alert import FraudAlert
from sqlalchemy.future import select

@pytest.mark.asyncio
async def test_zero_duplicate_alert_processing(db_session):
    repo = AlertRepository(db_session)
    event_id = f"evt_idemp_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    alert_data = {
        "event_id": event_id,
        "transaction_id": "tx_test_idemp_1",
        "customer_id": "cust_123",
        "merchant_id": "merch_crypto_abc",
        "transaction_amount": 4500.0,
        "currency": "USD",
        "transaction_type": "PURCHASE",
        "transaction_timestamp": now,
        "fraud_score": 75.0,
        "risk_level": "HIGH",
        "fraud_reason": "High risk test",
        "status": "NEW",
        "priority": "P2_HIGH",
        "sla_deadline": now,
        "sla_duration_minutes": 15,
        "source_event_metadata": {},
    }

    # First attempt: successfully creates alert
    alert1, created1 = await repo.create_alert_idempotent(alert_data)
    await db_session.commit()
    assert created1 is True
    assert alert1.id is not None
    assert alert1.event_id == event_id

    # Second attempt with identical event_id (simulating Kafka redelivery or retry)
    alert2, created2 = await repo.create_alert_idempotent(alert_data)
    await db_session.commit()
    assert created2 is False
    assert alert2.id == alert1.id  # Returns the exact existing alert!

    # Verify database contains EXACTLY 1 alert with this event_id
    result = await db_session.execute(select(FraudAlert).where(FraudAlert.event_id == event_id))
    all_alerts = result.scalars().all()
    assert len(all_alerts) == 1
