import abc
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.domain.enums import RiskLevel, Priority
from app.services.circuit_breaker import scoring_circuit_breaker, CircuitBreakerOpenException
import logging

logger = logging.getLogger(__name__)

class ScoringResult:
    def __init__(
        self,
        fraud_score: float,
        risk_level: RiskLevel,
        fraud_reason: str,
        priority: Priority,
        sla_duration_minutes: int,
        risk_factors: List[str],
    ):
        self.fraud_score = fraud_score
        self.risk_level = risk_level
        self.fraud_reason = fraud_reason
        self.priority = priority
        self.sla_duration_minutes = sla_duration_minutes
        self.risk_factors = risk_factors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fraud_score": self.fraud_score,
            "risk_level": self.risk_level.value,
            "fraud_reason": self.fraud_reason,
            "priority": self.priority.value,
            "sla_duration_minutes": self.sla_duration_minutes,
            "risk_factors": self.risk_factors,
        }

class BaseFraudScorer(abc.ABC):
    @abc.abstractmethod
    async def evaluate_transaction(self, event_payload: Dict[str, Any]) -> ScoringResult:
        pass

class RuleBasedFraudScorer(BaseFraudScorer):
    """
    Deterministic rule-based fraud scoring engine.
    Calculates composite score from financial risk indicators, velocity,
    merchant categories, geographical anomalies, and transaction characteristics.
    """
    SUSPICIOUS_MERCHANT_CATEGORIES = {
        "crypto_exchange": 35.0,
        "gambling": 30.0,
        "prepaid_giftcards": 25.0,
        "wire_transfer": 20.0,
        "luxury_jewelry": 20.0,
        "high_risk_electronics": 15.0,
    }

    HIGH_RISK_COUNTRIES = {"RU", "KP", "IR", "SY", "NG"}

    def __init__(self, simulate_latency_ms: float = 0.0, failure_rate: float = 0.0):
        self.simulate_latency_ms = simulate_latency_ms
        self.failure_rate = failure_rate
        self.should_fail: bool = False

    def set_forced_failure(self, fail: bool):
        self.should_fail = fail

    async def _raw_evaluation(self, event_payload: Dict[str, Any]) -> ScoringResult:
        if self.should_fail:
            raise RuntimeError("Scoring dependency service unavailable (simulated outage)")

        if self.simulate_latency_ms > 0:
            await asyncio.sleep(self.simulate_latency_ms / 1000.0)

        score = 5.0  # Base nominal score
        risk_factors = []

        amount = float(event_payload.get("transaction_amount", 0.0))
        merchant_cat = str(event_payload.get("merchant_category", "retail")).lower()
        location = str(event_payload.get("location", "US")).upper()
        metadata = event_payload.get("metadata", {}) or {}

        # 1. Transaction Amount Evaluation
        if amount >= 15000.0:
            score += 45.0
            risk_factors.append(f"Very high transaction amount (${amount:,.2f} >= $15,000)")
        elif amount >= 5000.0:
            score += 25.0
            risk_factors.append(f"Elevated transaction amount (${amount:,.2f} >= $5,000)")
        elif amount >= 2000.0:
            score += 10.0

        # 2. Merchant Category Evaluation
        for cat, weight in self.SUSPICIOUS_MERCHANT_CATEGORIES.items():
            if cat in merchant_cat:
                score += weight
                risk_factors.append(f"Suspicious merchant category: {cat}")
                break

        # 3. Location & IP Anomaly Evaluation
        if location in self.HIGH_RISK_COUNTRIES:
            score += 35.0
            risk_factors.append(f"High risk originating jurisdiction ({location})")

        if metadata.get("is_vpn_or_tor", False):
            score += 25.0
            risk_factors.append("Anonymized network connection detected (VPN/TOR)")

        # 4. Behavioral & Velocity Flags
        velocity_count = int(metadata.get("velocity_10m", 1))
        if velocity_count >= 5:
            score += 30.0
            risk_factors.append(f"Rapid repeated transactions velocity ({velocity_count} tx in 10m)")
        elif velocity_count >= 3:
            score += 15.0
            risk_factors.append(f"Elevated velocity ({velocity_count} tx in 10m)")

        failed_attempts = int(metadata.get("failed_attempts_prev", 0))
        if failed_attempts >= 3:
            score += 25.0
            risk_factors.append(f"Multiple previous failed payment attempts ({failed_attempts})")

        if metadata.get("is_new_device", False):
            score += 15.0
            risk_factors.append("Transaction initiated from unverified new device")

        if metadata.get("account_age_days", 365) < 7:
            score += 15.0
            risk_factors.append("Recently created customer account (< 7 days)")

        # Clamp score between 0.0 and 100.0
        final_score = min(max(round(score, 1), 0.0), 100.0)

        # Determine Risk Level, Priority, and SLA duration
        if final_score >= 85.0:
            risk_level = RiskLevel.CRITICAL
            priority = Priority.P1_CRITICAL
            sla_duration = 5  # 5 minutes SLA
            reason = f"CRITICAL FRAUD RISK: {'; '.join(risk_factors[:3])}"
        elif final_score >= 60.0:
            risk_level = RiskLevel.HIGH
            priority = Priority.P2_HIGH
            sla_duration = 15  # 15 minutes SLA
            reason = f"HIGH RISK: {'; '.join(risk_factors[:3]) if risk_factors else 'Multi-factor risk threshold exceeded'}"
        elif final_score >= 30.0:
            risk_level = RiskLevel.MEDIUM
            priority = Priority.P3_MEDIUM
            sla_duration = 60  # 60 minutes SLA
            reason = f"MEDIUM RISK: {'; '.join(risk_factors[:2]) if risk_factors else 'Moderate transaction risk'}"
        else:
            risk_level = RiskLevel.LOW
            priority = Priority.P4_LOW
            sla_duration = 240  # 240 minutes (4 hours) SLA
            reason = "LOW RISK: Standard baseline transaction characteristics"

        return ScoringResult(
            fraud_score=final_score,
            risk_level=risk_level,
            fraud_reason=reason,
            priority=priority,
            sla_duration_minutes=sla_duration,
            risk_factors=risk_factors,
        )

    async def evaluate_transaction(self, event_payload: Dict[str, Any]) -> ScoringResult:
        """
        Executes scoring with protection from the Circuit Breaker.
        If circuit is open or call fails, raises exception so Kafka consumer can route
        to retry topic or DLQ.
        """
        return await scoring_circuit_breaker.call(self._raw_evaluation, event_payload)

# Global default fraud scoring engine
fraud_scoring_engine = RuleBasedFraudScorer()
