"""
GuardRail Database Seeding Script (High-Fidelity Production Simulation).
Generates:
- 10 realistic analyst accounts across all 4 RBAC tiers with realistic workloads
- 250 logically correlated fraud alerts with believable SLA distribution:
  * 70% Healthy (>20m remaining)
  * 16% Approaching SLA Warning (<15m remaining)
  * 6% Escalated / Overdue (<25m overdue)
  * 8% Actively Claimed with valid 15-minute leases
  * 45 Resolved alerts for today with real resolution durations and audit notes
- Correlated transaction amounts, merchant categories, fraud scores, and detailed risk factors
- Dead Letter Queue events with realistic states (PENDING, PROCESSING, SUCCEEDED, FAILED_VALIDATION)
"""
import asyncio
import random
import uuid
from datetime import datetime, timezone, timedelta
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import AsyncSessionLocal, async_engine, Base
from app.models.analyst import Analyst
from app.models.fraud_alert import FraudAlert
from app.models.audit_log import AlertAuditLog
from app.models.dead_letter import DeadLetterEvent
from app.core.security import get_password_hash
from app.domain.enums import UserRole, RiskLevel, AlertStatus, Priority, AuditAction
from app.services.circuit_breaker import scoring_circuit_breaker

DEMO_ANALYSTS = [
    {"name": "Admin User", "email": "admin@guardrail.io", "role": UserRole.ADMIN.value, "team": "SecOps & Administration", "workload": 0},
    {"name": "Marcus Vance", "email": "supervisor@guardrail.io", "role": UserRole.SUPERVISOR.value, "team": "Global Fraud Management", "workload": 15},
    {"name": "Elena Rostova", "email": "senior@guardrail.io", "role": UserRole.SENIOR_ANALYST.value, "team": "Tier 2 High-Value Investigations", "workload": 12},
    {"name": "David Kim", "email": "david.kim@guardrail.io", "role": UserRole.SENIOR_ANALYST.value, "team": "Tier 2 High-Value Investigations", "workload": 12},
    {"name": "Sarah Chen", "email": "analyst@guardrail.io", "role": UserRole.ANALYST.value, "team": "Tier 1 Real-time Triage", "workload": 10},
    {"name": "Alex Rivera", "email": "alex.rivera@guardrail.io", "role": UserRole.ANALYST.value, "team": "Tier 1 Real-time Triage", "workload": 10},
    {"name": "Priya Sharma", "email": "priya.sharma@guardrail.io", "role": UserRole.ANALYST.value, "team": "Tier 1 Real-time Triage", "workload": 10},
    {"name": "Liam O'Connor", "email": "liam.oconnor@guardrail.io", "role": UserRole.ANALYST.value, "team": "Tier 1 Real-time Triage", "workload": 10},
    {"name": "Zoe Takahashi", "email": "zoe.takahashi@guardrail.io", "role": UserRole.ANALYST.value, "team": "Tier 1 Real-time Triage", "workload": 10},
    {"name": "Carlos Gomez", "email": "carlos.gomez@guardrail.io", "role": UserRole.ANALYST.value, "team": "Tier 1 Real-time Triage", "workload": 10},
]

# Scenarios with logically correlated [Amount, Category, Merchant, Score, Risk, Priority, SLA Mins, Reason]
FRAUD_SCENARIOS = [
    {
        "min_amt": 8500.0, "max_amt": 28500.0,
        "category": "luxury_jewelry", "merch": ("merch_rolex_5th", "Rolex Fifth Avenue Flagship"),
        "score_range": (88, 96), "risk": RiskLevel.CRITICAL, "priority": Priority.P1_CRITICAL, "sla_mins": 30,
        "reason_template": "Unusually large luxury jewelry transaction (${amount:,.2f}) exceeding 8x customer 30-day baseline ($450.00).",
        "factors": ["High Transaction Amount (+45)", "New Merchant Category (+20)", "Rapid Funds Outflow (+15)", "High-Risk MCC (+12)"]
    },
    {
        "min_amt": 2400.0, "max_amt": 7200.0,
        "category": "crypto_exchange", "merch": ("merch_binance_p2p", "Binance P2P Trading"),
        "score_range": (84, 92), "risk": RiskLevel.CRITICAL, "priority": Priority.P1_CRITICAL, "sla_mins": 30,
        "reason_template": "Crypto cashout (${amount:,.2f}) initiated via unregistered device and residential VPN proxy mask.",
        "factors": ["High-Risk Crypto MCC (+35)", "Residential Proxy Mask (+25)", "New Device Fingerprint (+15)", "Off-Hours Withdrawal (+12)"]
    },
    {
        "min_amt": 180.0, "max_amt": 650.0,
        "category": "travel", "merch": ("merch_sq_air", "Singapore Airlines Changi"),
        "score_range": (76, 84), "risk": RiskLevel.HIGH, "priority": Priority.P2_HIGH, "sla_mins": 45,
        "reason_template": "Impossible travel velocity: Physical POS terminal in London, followed by overseas ATM attempt in Singapore 14m later.",
        "factors": ["Geo-Velocity Mismatch (+35)", "Cross-Border Terminal (+20)", "Unregistered Travel Profile (+15)", "ATM Cashout (+10)"]
    },
    {
        "min_amt": 1.25, "max_amt": 3.99,
        "category": "retail", "merch": ("merch_steam_games", "Valve Steam Online"),
        "score_range": (68, 76), "risk": RiskLevel.HIGH, "priority": Priority.P2_HIGH, "sla_mins": 45,
        "reason_template": "Rapid micro-charge sequence: 6 consecutive transactions in 90 seconds matching automated BIN testing.",
        "factors": ["High Velocity Micro-Burst (+35)", "Automated Bot Pattern (+20)", "Consecutive Auth Probes (+15)"]
    },
    {
        "min_amt": 350.0, "max_amt": 950.0,
        "category": "high_risk_electronics", "merch": ("merch_apple_regent", "Apple Store Regent Street"),
        "score_range": (48, 62), "risk": RiskLevel.MEDIUM, "priority": Priority.P3_MEDIUM, "sla_mins": 90,
        "reason_template": "First-time purchase at luxury electronics retailer with shipping address deviating from billing zip.",
        "factors": ["AVS Zip Mismatch (+25)", "First Time Merchant (+15)", "Expedited Shipping (+12)"]
    },
    {
        "min_amt": 35.0, "max_amt": 140.0,
        "category": "retail", "merch": ("merch_amazon_us", "Amazon Marketplace"),
        "score_range": (20, 36), "risk": RiskLevel.LOW, "priority": Priority.P4_LOW, "sla_mins": 180,
        "reason_template": "Minor geographical deviation from customary home metro area during weekend travel hours.",
        "factors": ["Minor Geo Deviation (+15)", "Standard Verified Device (+5)"]
    },
]

COUNTRIES = ["US", "GB", "DE", "FR", "SG", "JP", "AE", "CA", "AU"]

async def seed():
    print("🌱 Starting GuardRail High-Fidelity Data Seeding...")
    random.seed(1337)

    async with async_engine.begin() as conn:
        # Clear existing tables to ensure no dirty state
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Seed Analysts
        print("👤 Seeding 10 analyst accounts across 4 RBAC tiers...")
        analyst_objs = []
        default_pw = get_password_hash("Password123!")

        for a in DEMO_ANALYSTS:
            analyst = Analyst(
                name=a["name"],
                email=a["email"],
                hashed_password=default_pw,
                role=a["role"],
                team=a["team"],
                workload_limit=a["workload"],
                is_active=True,
            )
            session.add(analyst)
            analyst_objs.append(analyst)

        await session.flush()
        print(f"✅ {len(analyst_objs)} Analysts successfully seeded.")

        # Filter analysts by role
        supervisors = [a for a in analyst_objs if a.role in (UserRole.SUPERVISOR.value, UserRole.SENIOR_ANALYST.value)]
        triagers = [a for a in analyst_objs if a.role == UserRole.ANALYST.value]

        # 2. Seed 250 Alerts with realistic temporal distribution
        print("🚨 Seeding 250 realistic fraud alerts with consistent SLAs and correlated factors...")
        now = datetime.now(timezone.utc)

        # Telemetry counters
        counts = {"healthy": 0, "warning": 0, "breached": 0, "claimed": 0, "resolved": 0}

        for i in range(250):
            scenario = random.choices(
                FRAUD_SCENARIOS,
                weights=[0.18, 0.22, 0.25, 0.15, 0.12, 0.08],
                k=1
            )[0]

            amount = round(random.uniform(scenario["min_amt"], scenario["max_amt"]), 2)
            score = round(random.uniform(*scenario["score_range"]), 1)
            risk = scenario["risk"].value
            priority = scenario["priority"].value
            sla_mins = scenario["sla_mins"]
            reason = scenario["reason_template"].format(amount=amount)
            merch_id, merch_name = scenario["merch"]
            event_id = f"evt_live_{i+1:04d}_{uuid.uuid4().hex[:6]}"
            tx_id = f"tx_2026_{500000 + i}"
            cust_id = f"cust_{10000 + (i % 60)}"

            # Determine temporal status with robust forward-anchored deadlines:
            # - 45 are RESOLVED earlier today
            # - 12 are ESCALATED / OVERDUE (breached by 4-18m)
            # - 33 are APPROACHING WARNING (4-14m remaining)
            # - 20 are CLAIMED / IN_PROGRESS (active 15m lease)
            # - 140 are HEALTHY NEW alerts (25-150m remaining)
            if i < 45:
                # RESOLVED
                status = AlertStatus.RESOLVED.value
                created_offset_min = random.randint(45, 240)
                created_at = now - timedelta(minutes=created_offset_min)
                resolution_time_min = random.randint(6, 18)
                resolved_at = created_at + timedelta(minutes=resolution_time_min)
                sla_deadline = created_at + timedelta(minutes=sla_mins)
                
                assigned = random.choice(triagers + supervisors)
                claimed_by = None
                claimed_at = created_at + timedelta(minutes=2)
                claim_expires = None
                
                res_type = "CONFIRMED_FRAUD" if score >= 80 else "FALSE_POSITIVE"
                resolution_reason = f"{res_type} - Verified by {assigned.name} via customer call & device audit"
                notes = f"[{resolved_at.strftime('%H:%M:%S UTC')}] {assigned.name}: Case concluded. Action: {res_type}."
                counts["resolved"] += 1

            elif i < 57:
                # ESCALATED / OVERDUE (12 alerts)
                status = AlertStatus.ESCALATED.value
                overdue_min = random.randint(4, 18)
                sla_deadline = now - timedelta(minutes=overdue_min)
                created_at = sla_deadline - timedelta(minutes=sla_mins)
                priority = Priority.P1_CRITICAL.value  # Auto-escalated to P1!
                reason = f"[SLA BREACHED: {overdue_min}m overdue] {reason}"
                assigned = None
                claimed_by = None
                claimed_at = None
                claim_expires = None
                resolved_at = None
                resolution_reason = None
                notes = f"[{sla_deadline.strftime('%H:%M:%S UTC')}] SLA_ENGINE: Target breached ({sla_mins}m). Auto-escalated to P1 Critical."
                counts["breached"] += 1

            elif i < 90:
                # APPROACHING WARNING (33 alerts, 4-14m remaining)
                status = AlertStatus.NEW.value
                remaining_min = random.randint(4, 14)
                sla_deadline = now + timedelta(minutes=remaining_min)
                created_at = sla_deadline - timedelta(minutes=sla_mins)
                assigned = None
                claimed_by = None
                claimed_at = None
                claim_expires = None
                resolved_at = None
                resolution_reason = None
                notes = None
                counts["warning"] += 1

            elif i < 110:
                # CLAIMED / IN_PROGRESS (20 alerts)
                status = AlertStatus.CLAIMED.value
                sla_deadline = now + timedelta(minutes=random.randint(18, 45))
                created_at = sla_deadline - timedelta(minutes=sla_mins)
                assigned = random.choice(triagers)
                claimed_by = assigned.name
                claimed_at = now - timedelta(minutes=random.randint(1, 6))
                claim_expires = now + timedelta(minutes=random.randint(9, 14)) # Valid active lease!
                resolved_at = None
                resolution_reason = None
                notes = f"[{claimed_at.strftime('%H:%M:%S UTC')}] {assigned.name}: Claim lock acquired. Investigation in progress."
                counts["claimed"] += 1

            else:
                # HEALTHY NEW (140 alerts, 25-150m remaining)
                status = AlertStatus.NEW.value
                remaining_min = random.randint(25, 150)
                sla_deadline = now + timedelta(minutes=remaining_min)
                created_at = sla_deadline - timedelta(minutes=sla_mins)
                assigned = None
                claimed_by = None
                claimed_at = None
                claim_expires = None
                resolved_at = None
                resolution_reason = None
                notes = None
                counts["healthy"] += 1

            alert_id = str(uuid.uuid4())
            alert = FraudAlert(
                id=alert_id,
                event_id=event_id,
                transaction_id=tx_id,
                customer_id=cust_id,
                merchant_id=merch_id,
                transaction_amount=amount,
                currency="USD",
                transaction_type="PURCHASE" if amount < 15000 else "TRANSFER",
                transaction_timestamp=created_at,
                fraud_score=score,
                risk_level=risk,
                fraud_reason=reason,
                status=status,
                priority=priority,
                sla_deadline=sla_deadline,
                sla_duration_minutes=sla_mins,
                assigned_analyst_id=assigned.id if assigned else None,
                claimed_by=claimed_by,
                claimed_at=claimed_at,
                claim_expires_at=claim_expires,
                version=1,
                created_at=created_at,
                updated_at=now,
                resolved_at=resolved_at,
                resolution_reason=resolution_reason,
                notes=notes,
                replay_count=0,
                source_event_metadata={
                    "merchant_name": merch_name,
                    "merchant_category": scenario["category"],
                    "location": random.choice(COUNTRIES),
                    "ip_address": f"198.51.{random.randint(1, 254)}.{random.randint(1, 254)}",
                    "device_id": f"dev_fp_{uuid.uuid4().hex[:10]}",
                    "risk_factors": scenario["factors"],
                }
            )
            session.add(alert)

            # Audit trail
            session.add(AlertAuditLog(
                alert_id=alert_id,
                actor_name="INGESTION_SIMULATOR",
                action=AuditAction.INGESTED.value,
                previous_state={},
                new_state={"status": alert.status, "risk": alert.risk_level, "score": score},
                metadata_info={"event_id": event_id, "amount": amount},
                timestamp=created_at
            ))

            if claimed_by:
                session.add(AlertAuditLog(
                    alert_id=alert_id,
                    actor_name=claimed_by,
                    action=AuditAction.CLAIMED.value,
                    previous_state={"status": AlertStatus.NEW.value},
                    new_state={"status": AlertStatus.CLAIMED.value, "claimed_by": claimed_by},
                    metadata_info={"lease_duration_minutes": 15},
                    timestamp=claimed_at
                ))

            if resolved_at:
                session.add(AlertAuditLog(
                    alert_id=alert_id,
                    actor_name=assigned.name,
                    action=AuditAction.RESOLVED.value,
                    previous_state={"status": AlertStatus.CLAIMED.value},
                    new_state={"status": AlertStatus.RESOLVED.value, "reason": resolution_reason},
                    metadata_info={"duration_minutes": resolution_time_min},
                    timestamp=resolved_at
                ))

        await session.flush()
        print(f"✅ Alerts seeded: {counts}")

        # 3. Seed Realistic DLQ Records with clear distinct states
        print("📦 Seeding 10 Dead Letter Queue records with varied error states...")
        dlq_records = [
            # PENDING (transient issues ready for replay)
            ("evt_err_1001", "fraud.alerts", 0, 14201, "ScoringServiceTimeout", "External scoring upstream HTTP 504 Gateway Timeout after 3000ms", 1, "PENDING"),
            ("evt_err_1002", "fraud.alerts", 1, 14208, "DatabaseLockWaitTimeout", "PostgreSQL transaction lock wait timeout on customer ledger row", 2, "PENDING"),
            ("evt_err_1003", "fraud.alerts", 2, 14215, "CircuitBreakerOpenException", "Scoring dependency circuit breaker OPEN. Call fast-failed.", 1, "PENDING"),
            
            # PROCESSING (currently inflight)
            ("evt_err_1004", "fraud.alerts", 0, 14220, "TransientNetworkDrop", "Socket connection dropped during payload ingestion", 2, "PROCESSING"),
            
            # SUCCEEDED (successfully replayed & processed)
            ("evt_err_1005", "fraud.alerts", 1, 14190, "ScoringServiceTimeout", "Upstream scoring timeout (replayed successfully)", 3, "SUCCEEDED"),
            ("evt_err_1006", "fraud.alerts", 2, 14192, "DatabaseLockWaitTimeout", "Row lock contention resolved on replay", 2, "SUCCEEDED"),
            ("evt_err_1007", "fraud.alerts", 0, 14195, "TransientNetworkDrop", "Re-transmitted payload verified", 2, "SUCCEEDED"),
            ("evt_err_1008", "fraud.alerts", 1, 14199, "ScoringServiceTimeout", "Retry succeeded with fallback heuristic scorer", 1, "SUCCEEDED"),
            
            # FAILED_VALIDATION (quarantined schema error, cannot replay without code fix)
            ("evt_err_1009", "fraud.alerts", 0, 14230, "SchemaValidationError", "Invalid ISO-4217 currency code 'USDD'; strict validation failed", 0, "FAILED_VALIDATION"),
            ("evt_err_1010", "fraud.alerts", 2, 14235, "MalformedJsonPayload", "JSON decode error at line 1 column 48: unescaped control char", 0, "FAILED_VALIDATION"),
        ]

        for orig_id, topic, part, offset, err_type, err_msg, retries, status in dlq_records:
            dlq = DeadLetterEvent(
                original_event_id=orig_id,
                topic=topic,
                partition=part,
                offset=offset,
                payload={
                    "event_id": orig_id,
                    "transaction_id": f"tx_err_{orig_id}",
                    "amount": 420.0,
                    "currency": "USD" if "USDD" not in err_msg else "USDD",
                },
                error_type=err_type,
                error_message=err_msg,
                retry_count=retries,
                replay_status=status,
                created_at=now - timedelta(minutes=random.randint(10, 120)),
                replayed_at=now - timedelta(minutes=random.randint(2, 25)) if status == "SUCCEEDED" else None
            )
            session.add(dlq)

        # 4. Initialize Circuit Breaker baseline metrics
        scoring_circuit_breaker.total_calls = 2840
        scoring_circuit_breaker.successful_calls = 2836
        scoring_circuit_breaker.failed_calls = 4
        scoring_circuit_breaker.rejected_calls = 0
        scoring_circuit_breaker.state_transitions = 0
        scoring_circuit_breaker._consecutive_success_count = 142

        await session.commit()
        print("🎉 Database successfully re-seeded with realistic production-simulated data!")

if __name__ == "__main__":
    asyncio.run(seed())
