# GuardRail REST & WebSocket API Reference

The GuardRail API is versioned under `/api/v1` and returns standard JSON payloads. All timestamps are in UTC (ISO-8601).

---

## Authentication (`/api/v1/auth`)

### 1. User Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "analyst@guardrail.io",
  "password": "Password123!"
}
```
**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "usr_analyst_01",
    "name": "Sarah Chen",
    "email": "analyst@guardrail.io",
    "role": "ANALYST",
    "team": "Tier 1 Real-time Triage",
    "is_active": true,
    "workload_limit": 10
  }
}
```

### 2. Token Refresh
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsIn..."
}
```

---

## Alert Ingestion & Triage (`/api/v1/alerts`)

### 1. Ingest Transaction
```http
POST /api/v1/alerts/ingest
Content-Type: application/json

{
  "event_id": "evt_custom_optional_id",
  "transaction_id": "tx_9019283",
  "customer_id": "cust_4821",
  "merchant_id": "merch_crypto_exchange",
  "merchant_category": "crypto_exchange",
  "transaction_amount": 14500.00,
  "currency": "USD",
  "transaction_type": "PURCHASE",
  "location": "US",
  "metadata": {
    "velocity_10m": 4,
    "is_vpn_or_tor": true
  }
}
```
**Response (202 Accepted):**
```json
{
  "status": "ACCEPTED",
  "event_id": "evt_custom_optional_id",
  "correlation_id": "corr_91f82a17cb42",
  "topic": "fraud.alerts",
  "received_at": "2026-11-26T00:00:00Z",
  "message": "Event accepted for asynchronous fraud processing"
}
```

### 2. List Alerts
```http
GET /api/v1/alerts?status=NEW&risk_level=CRITICAL&sort_by=priority_sla&page=1&limit=25
Authorization: Bearer <TOKEN>
```
**Query Parameters:**
- `status`: `NEW`, `CLAIMED`, `UNDER_REVIEW`, `ESCALATED`, `RESOLVED`, `REOPENED`
- `risk_level`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `priority`: `P1_CRITICAL`, `P2_HIGH`, `P3_MEDIUM`, `P4_LOW`
- `claimed`: `true` | `false`
- `search`: Searches across ID, customer ID, merchant ID, event ID, reason
- `sort_by`: `priority_sla`, `sla_deadline`, `fraud_score`, `created_at`, `amount`
- `page`: Page index (default: 1)
- `limit`: Items per page (default: 25, max: 100)

### 3. Claim Alert (Atomic Lock)
```http
POST /api/v1/alerts/{alert_id}/claim
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "lease_duration_seconds": 600
}
```
- **Returns 200 OK** if lease acquired.
- **Returns 409 Conflict** if already locked by another active analyst.

### 4. Release Claim
```http
POST /api/v1/alerts/{alert_id}/release
Authorization: Bearer <TOKEN>
```

### 5. Renew Claim Lease
```http
POST /api/v1/alerts/{alert_id}/renew-claim
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "lease_duration_seconds": 600
}
```

### 6. Reassign Alert (Senior Analyst / Supervisor / Admin)
```http
POST /api/v1/alerts/{alert_id}/reassign
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "target_analyst_id": "usr_analyst_02",
  "reason": "Escalated high-value crypto investigation"
}
```

### 7. Resolve Alert
```http
POST /api/v1/alerts/{alert_id}/resolve
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "resolution_reason": "CONFIRMED_FRAUD",
  "notes": "Cardholder denied transaction. Card frozen, SAR filed."
}
```

### 8. Add Investigation Note
```http
POST /api/v1/alerts/{alert_id}/notes
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "note": "Spoke with cardholder via phone. Verified location mismatch."
}
```

### 9. Get Alert Audit Log
```http
GET /api/v1/alerts/{alert_id}/audit
Authorization: Bearer <TOKEN>
```

---

## Dead Letter Queue (`/api/v1/dlq`)

*(Requires Supervisor or Admin role)*

- `GET /api/v1/dlq?status=PENDING&page=1&limit=50`: List failed events.
- `GET /api/v1/dlq/{event_id}`: Inspect raw poison message and stack trace.
- `POST /api/v1/dlq/{event_id}/replay`: Replay specific event to `fraud.alerts`.
- `POST /api/v1/dlq/replay-all`: Batch replay all pending DLQ items.

---

## System Health & Metrics (`/api/v1/system`)

- `GET /api/v1/system/health`: Deep health probe of PostgreSQL, Redis, Kafka, and Circuit Breakers.
- `GET /api/v1/system/metrics`: Prometheus-formatted telemetry scrape target.
- `POST /api/v1/system/circuit-breaker/reset`: Administrative breaker state override.

---

## WebSocket Stream (`/api/v1/ws/alerts`)

Connect with:
```text
WS /api/v1/ws/alerts?token=<JWT_ACCESS_TOKEN>
```

**Real-time Event Payload:**
```json
{
  "event_id": "748583c8-75f3-483e-a3c4-f424a2cefafa",
  "event_type": "alert.claimed",
  "timestamp": "2026-11-26T00:10:00Z",
  "payload": {
    "id": "748583c8-75f3-483e-a3c4-f424a2cefafa",
    "status": "CLAIMED",
    "claimed_by": "Sarah Chen",
    "fraud_score": 88.0,
    "priority": "P1_CRITICAL",
    "sla_deadline": "2026-11-26T00:15:00Z"
  }
}
```
