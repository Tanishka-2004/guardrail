import pytest
import asyncio
from app.services.scoring import RuleBasedFraudScorer
from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from app.domain.enums import CircuitState, RiskLevel, Priority

@pytest.mark.asyncio
async def test_rule_based_fraud_scoring():
    scorer = RuleBasedFraudScorer()

    # Low risk transaction
    low_event = {
        "transaction_amount": 45.0,
        "merchant_category": "retail",
        "location": "US",
        "metadata": {"velocity_10m": 1, "failed_attempts_prev": 0}
    }
    low_res = await scorer.evaluate_transaction(low_event)
    assert low_res.risk_level == RiskLevel.LOW
    assert low_res.priority == Priority.P4_LOW
    assert low_res.fraud_score < 30.0
    assert low_res.sla_duration_minutes == 240

    # High amount & crypto risk
    critical_event = {
        "transaction_amount": 25000.0,
        "merchant_category": "crypto_exchange",
        "location": "RU",
        "metadata": {"is_vpn_or_tor": True, "velocity_10m": 6}
    }
    crit_res = await scorer.evaluate_transaction(critical_event)
    assert crit_res.risk_level == RiskLevel.CRITICAL
    assert crit_res.priority == Priority.P1_CRITICAL
    assert crit_res.fraud_score >= 85.0
    assert crit_res.sla_duration_minutes == 5
    assert len(crit_res.risk_factors) >= 3

@pytest.mark.asyncio
async def test_circuit_breaker_state_transitions():
    cb = CircuitBreaker(name="TestBreaker", failure_threshold=3, recovery_timeout=0.1, half_open_max_requests=2)
    assert cb.state == CircuitState.CLOSED

    async def succeeding_call():
        return "OK"

    async def failing_call():
        raise RuntimeError("Service failure")

    # Success call keeps it CLOSED
    res = await cb.call(succeeding_call)
    assert res == "OK"
    assert cb.state == CircuitState.CLOSED

    # Trigger consecutive failures up to threshold
    with pytest.raises(RuntimeError):
        await cb.call(failing_call)
    assert cb.state == CircuitState.CLOSED

    with pytest.raises(RuntimeError):
        await cb.call(failing_call)
    assert cb.state == CircuitState.CLOSED

    with pytest.raises(RuntimeError):
        await cb.call(failing_call)
    # Threshold reached -> Transitions to OPEN
    assert cb.state == CircuitState.OPEN

    # In OPEN state, calls fail fast with CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        await cb.call(succeeding_call)

    # Wait for recovery timeout -> Transitions to HALF_OPEN
    await asyncio.sleep(0.15)
    assert cb.state == CircuitState.HALF_OPEN

    # Two successful probe calls in HALF_OPEN should recover circuit to CLOSED
    await cb.call(succeeding_call)
    assert cb.state == CircuitState.HALF_OPEN
    await cb.call(succeeding_call)
    assert cb.state == CircuitState.CLOSED
