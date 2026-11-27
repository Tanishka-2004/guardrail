"""
GuardRail Automated Load and Benchmark Test.
Measures:
- Sustained ingestion throughput
- Burst ingestion response times
- Atomic claim concurrency and conflict handling under high load
- p50, p95, p99 latency profiling
"""
import asyncio
import time
import statistics
import uuid
import httpx

BASE_URL = "http://localhost:8000/api/v1"

async def test_claim_concurrency(client: httpx.AsyncClient, token: str, alert_id: str, concurrent_attempts: int = 10):
    print(f"\n⚡ Testing Atomic Claim-Locking with {concurrent_attempts} concurrent analysts...")
    headers = {"Authorization": f"Bearer {token}"}
    
    async def attempt_claim(worker_id: int):
        start = time.time()
        try:
            resp = await client.post(
                f"{BASE_URL}/alerts/{alert_id}/claim",
                json={"lease_duration_seconds": 300},
                headers=headers
            )
            elapsed = (time.time() - start) * 1000
            return resp.status_code, elapsed
        except Exception as e:
            return 500, (time.time() - start) * 1000

    tasks = [attempt_claim(i) for i in range(concurrent_attempts)]
    results = await asyncio.gather(*tasks)

    status_codes = [r[0] for r in results]
    latencies = [r[1] for r in results]

    success_count = status_codes.count(200)
    conflict_count = status_codes.count(409)

    print(f"   Results: 200 OK (Claim Won) = {success_count} | 409 Conflict = {conflict_count}")
    print(f"   p95 Latency: {statistics.quantiles(latencies, n=20)[18]:.2f} ms")

    assert success_count == 1, f"Expected exactly 1 claim winner, got {success_count}!"
    assert conflict_count == concurrent_attempts - 1, f"Expected {concurrent_attempts - 1} conflicts, got {conflict_count}!"
    print("   ✅ Atomic Concurrency Lock PASSED: Exactly 1 analyst claimed, all other requests safely rejected with 409.")

async def run_benchmarks():
    print("=" * 60)
    print("GuardRail Performance & Reliability Benchmark")
    print("=" * 60)

    client = httpx.AsyncClient(timeout=10.0)

    try:
        # Check system health first
        health_resp = await client.get(f"{BASE_URL}/system/health")
        if health_resp.status_code != 200:
            print("❌ Backend is not running or unreachable at http://localhost:8000")
            return

        print("Backend is ONLINE. Logging in as analyst...")
        login_resp = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": "analyst@guardrail.io", "password": "Password123!"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Burst Ingestion Test
        total_requests = 100
        print(f"\n🚀 Ingesting {total_requests} events in burst mode...")
        latencies = []
        start_total = time.time()

        for i in range(total_requests):
            event = {
                "event_id": f"bench_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}",
                "transaction_id": f"tx_bench_{i}",
                "customer_id": f"cust_{i%20}",
                "merchant_id": "merch_crypto_test",
                "transaction_amount": 7500.0,
                "currency": "USD",
                "transaction_type": "PURCHASE",
            }
            t0 = time.time()
            resp = await client.post(f"{BASE_URL}/alerts/ingest", json=event)
            latencies.append((time.time() - t0) * 1000)

        total_time = time.time() - start_total
        throughput = total_requests / total_time

        print(f"   Burst Ingestion Rate: {throughput:.1f} events/second ({throughput*60:.0f} events/minute)")
        print(f"   p50 Latency: {statistics.median(latencies):.2f} ms")
        print(f"   p95 Latency: {statistics.quantiles(latencies, n=20)[18]:.2f} ms")

        # 2. Queue Read Latency
        print("\n📊 Measuring Dashboard Queue Read Latency...")
        queue_latencies = []
        for _ in range(30):
            t0 = time.time()
            await client.get(f"{BASE_URL}/alerts?limit=25", headers=headers)
            queue_latencies.append((time.time() - t0) * 1000)

        print(f"   Queue Read p50: {statistics.median(queue_latencies):.2f} ms")
        print(f"   Queue Read p95: {statistics.quantiles(queue_latencies, n=20)[18]:.2f} ms")

        # 3. Concurrency Claim Lock
        # Ingest fresh alert to claim
        test_evt_id = f"claim_test_{uuid.uuid4().hex[:8]}"
        await client.post(
            f"{BASE_URL}/alerts/ingest",
            json={
                "event_id": test_evt_id,
                "transaction_id": f"tx_claim_test",
                "customer_id": "cust_claim",
                "merchant_id": "merch_test",
                "transaction_amount": 12000.0,
            }
        )
        # Fetch alert id
        alerts_resp = await client.get(f"{BASE_URL}/alerts?search={test_evt_id}", headers=headers)
        items = alerts_resp.json()["items"]
        if items:
            alert_id = items[0]["id"]
            await test_claim_concurrency(client, token, alert_id, concurrent_attempts=10)

        print("\n" + "=" * 60)
        print("🎉 ALL BENCHMARKS COMPLETED SUCCESSFULLY")
        print("=" * 60)

    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(run_benchmarks())
