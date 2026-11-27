# GuardRail Failure Recovery & Chaos Engineering Manual

This operational manual documents failure modes, resilience mechanisms, and runbook remediation procedures for GuardRail components.

---

## 1. Kafka Broker Outage / Network Partition

### Failure Symptom
- Ingestion API cannot publish to `fraud.alerts`.
- Consumer logs connection timeouts to bootstrap server `kafka:9092`.

### Automated Resilience
1. **Producer In-Memory Buffer**: The `KafkaProducerService` intercepts broker connection errors and buffers events in memory while logging warnings without crashing the FastAPI process.
2. **Exponential Reconnection**: Consumers use background exponential backoff loops (`aiokafka` client reconnect timers) to restore partition assignments automatically upon broker restoration.
3. **Offset Persistence**: Kafka offsets remain securely committed to `__consumer_offsets`; no already-committed transactions are re-processed.

### Runbook
```bash
# Check Kafka container health
docker compose ps kafka

# Inspect KRaft broker logs
docker compose logs kafka --tail 100

# Restart Kafka broker if hung
docker compose restart kafka
```

---

## 2. PostgreSQL Temporary Unavailability

### Failure Symptom
- Consumer database transactions fail.
- REST API queries return database connection errors.

### Automated Resilience
1. **Uncommitted Kafka Offsets**: The Kafka consumer commits message offsets **ONLY AFTER** `session.commit()` completes. When the database is offline, the transaction is rolled back, and the Kafka offset is NOT committed.
2. **Automatic Retry Topic**: Events failing DB commit are re-routed to `fraud.alerts.retry` with an incremented `retry_count`.
3. **Connection Pooling Pre-Ping**: SQLAlchemy `pool_pre_ping=True` proactively detects dead socket connections and refreshes the pool when PostgreSQL returns.

---

## 3. Redis Downtime / Cache Degradation

### Failure Symptom
- Redis connection fails or port 6379 is unreachable.

### Automated Resilience
1. **Seamless Fallback**: `RedisService` catches Redis connection exceptions and immediately serves reads directly from PostgreSQL.
2. **In-Memory Cache & Pub/Sub**: WebSocket distributions gracefully degrade to local in-memory fanout on the current node.
3. **Zero 500 Errors**: Core triage, claims, and resolutions remain 100% operational in degraded mode.
4. **Cache Recovery**: As soon as Redis responds to `PING`, `RedisService` automatically resumes caching without requiring a backend restart.

---

## 4. Fraud Scoring Dependency Failure (Circuit Breaker Tripping)

### Failure Symptom
- Downstream fraud scoring model or third-party risk API experiences latency spikes or outages.

### Automated Resilience
1. **Breaker Trip to OPEN**: After 5 consecutive failures, `scoring_circuit_breaker` flips from `CLOSED` to `OPEN`.
2. **Fast-Failing Protection**: In `OPEN` state, requests fail fast with `CircuitBreakerOpenException` without waiting for 3000ms timeouts.
3. **DLQ Preservation**: Unprocessed alerts are safely pushed to `fraud.alerts.retry` and then to the `DeadLetterEvent` database table with the full payload intact.
4. **Half-Open Canary Testing**: After 30 seconds, the breaker enters `HALF_OPEN` and tests 3 probe requests. Once they succeed, normal scoring automatically resumes.
5. **Dashboard Visibility**: The dashboard banner and `/system` page immediately display `CIRCUIT BREAKER: OPEN` in amber.

### Runbook
```bash
# Force manual reset of Circuit Breaker to CLOSED via Admin API
curl -X POST http://localhost:8000/api/v1/system/circuit-breaker/reset \
  -H "Authorization: Bearer <ADMIN_JWT>"
```

---

## 5. Poison Message Handling & DLQ Replay

### Failure Symptom
- A corrupt event (negative transaction amount, malformed JSON, unparseable date) arrives on Kafka.

### Automated Resilience
1. Consumer validates schema with Pydantic.
2. On 3 failed processing attempts, the event is permanently written to `dead_letter_events` table and published to `fraud.alerts.dlq`.
3. Poison message is ACKed / committed on `fraud.alerts`, preventing head-of-line blocking for legitimate alerts.

### Runbook
1. Navigate to **Dead Letter Queue** in the GuardRail console (`/dlq`).
2. Click **Inspect** to review the error trace and raw JSON payload.
3. Click **Replay** on the event or use the API:
```bash
curl -X POST http://localhost:8000/api/v1/dlq/{event_id}/replay \
  -H "Authorization: Bearer <ADMIN_JWT>"
```
