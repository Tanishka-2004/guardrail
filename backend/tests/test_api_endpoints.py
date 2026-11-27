import pytest
import uuid
import httpx

@pytest.mark.asyncio
async def test_auth_and_rbac(async_client: httpx.AsyncClient, auth_headers):
    # 1. Login with valid credentials
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@guardrail.io", "password": "Password123!"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "analyst@guardrail.io"

    # 2. Login with invalid password
    bad_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@guardrail.io", "password": "WrongPassword!"}
    )
    assert bad_resp.status_code == 401

    # 3. RBAC: Analyst attempting DLQ endpoint should be rejected (HTTP 403)
    analyst_hdr = auth_headers("ANALYST")
    dlq_resp = await async_client.get("/api/v1/dlq", headers=analyst_hdr)
    assert dlq_resp.status_code == 403

    # 4. RBAC: Supervisor or Admin accessing DLQ succeeds (HTTP 200)
    admin_hdr = auth_headers("ADMIN")
    admin_dlq = await async_client.get("/api/v1/dlq", headers=admin_hdr)
    assert admin_dlq.status_code == 200

@pytest.mark.asyncio
async def test_alert_lifecycle_api(async_client: httpx.AsyncClient, auth_headers):
    hdr = auth_headers("ANALYST")

    # Ingest event
    evt_id = f"evt_flow_{uuid.uuid4().hex[:8]}"
    ingest_resp = await async_client.post(
        "/api/v1/alerts/ingest",
        json={
            "event_id": evt_id,
            "transaction_id": "tx_flow_1",
            "customer_id": "cust_flow_1",
            "merchant_id": "merch_crypto_flow",
            "merchant_category": "crypto_exchange",
            "transaction_amount": 18000.0,
            "currency": "USD",
        }
    )
    assert ingest_resp.status_code == 202
    assert ingest_resp.json()["event_id"] == evt_id

    # List alerts
    list_resp = await async_client.get(f"/api/v1/alerts?search={evt_id}", headers=hdr)
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    alert_id = items[0]["id"]
    assert items[0]["risk_level"] == "CRITICAL"

    # Claim alert
    claim_resp = await async_client.post(f"/api/v1/alerts/{alert_id}/claim", headers=hdr)
    assert claim_resp.status_code == 200
    assert claim_resp.json()["claimed_by"] == "Sarah Chen"

    # Add Note
    note_resp = await async_client.post(
        f"/api/v1/alerts/{alert_id}/notes",
        json={"note": "Confirmed large wire transaction with customer bank"},
        headers=hdr
    )
    assert note_resp.status_code == 200
    assert "Confirmed large wire transaction" in note_resp.json()["notes"]

    # Audit Trail
    audit_resp = await async_client.get(f"/api/v1/alerts/{alert_id}/audit", headers=hdr)
    assert audit_resp.status_code == 200
    actions = [a["action"] for a in audit_resp.json()]
    assert "INGESTED" in actions
    assert "CLAIMED" in actions
    assert "NOTE_ADDED" in actions

    # Resolve alert
    resolve_resp = await async_client.post(
        f"/api/v1/alerts/{alert_id}/resolve",
        json={"resolution_reason": "CONFIRMED_FRAUD", "notes": "Card terminated"},
        headers=hdr
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "RESOLVED"

@pytest.mark.asyncio
async def test_system_health_and_metrics(async_client: httpx.AsyncClient):
    health_resp = await async_client.get("/api/v1/system/health")
    assert health_resp.status_code == 200
    data = health_resp.json()
    assert "status" in data
    assert "dependencies" in data
    assert len(data["dependencies"]) >= 3

    metrics_resp = await async_client.get("/api/v1/system/metrics")
    assert metrics_resp.status_code == 200
    assert "guardrail_events_processed_total" in metrics_resp.text
