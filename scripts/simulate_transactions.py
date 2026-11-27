"""
Continuous Transaction Simulator for GuardRail.
Generates realistic financial transactions and sends them to the ingestion endpoint.
"""
import asyncio
import random
import time
import uuid
import httpx

MERCHANTS = [
    ("merch_binance_global", "crypto_exchange"),
    ("merch_coinbase_pro", "crypto_exchange"),
    ("merch_stake_casino", "gambling"),
    ("merch_rolex_luxury", "luxury_jewelry"),
    ("merch_apple_store", "high_risk_electronics"),
    ("merch_amazon_prime", "retail"),
    ("merch_wire_transfer_corp", "wire_transfer"),
    ("merch_uber_technologies", "travel"),
]

LOCATIONS = ["US", "GB", "DE", "FR", "SG", "JP", "AE", "RU", "NG", "BR"]

async def simulate(
    target_url: str = "http://localhost:8000/api/v1/alerts/ingest",
    rate_per_second: float = 2.0,
    burst_mode: bool = False,
):
    print(f"🚀 GuardRail Transaction Simulator running against {target_url}")
    print(f"   Rate: {rate_per_second} tx/sec | Burst Mode: {burst_mode}")

    client = httpx.AsyncClient(timeout=5.0)
    counter = 0

    try:
        while True:
            counter += 1
            merch_id, merch_cat = random.choice(MERCHANTS)
            amount = round(random.choice([
                random.uniform(15.0, 180.0),
                random.uniform(250.0, 1400.0),
                random.uniform(2500.0, 7500.0),
                random.uniform(9000.0, 45000.0),
            ]), 2)

            event = {
                "event_id": f"sim_evt_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}",
                "transaction_id": f"tx_sim_{counter}_{uuid.uuid4().hex[:4]}",
                "customer_id": f"cust_{random.randint(1000, 9999)}",
                "merchant_id": merch_id,
                "merchant_category": merch_cat,
                "transaction_amount": amount,
                "currency": "USD",
                "transaction_type": "PURCHASE" if amount < 10000 else "TRANSFER",
                "location": random.choice(LOCATIONS),
                "ip_address": f"198.51.{random.randint(1, 254)}.{random.randint(1, 254)}",
                "metadata": {
                    "velocity_10m": random.choice([1, 1, 2, 4, 7]),
                    "failed_attempts_prev": random.choice([0, 0, 1, 3]),
                    "is_vpn_or_tor": random.random() < 0.15,
                    "is_new_device": random.random() < 0.20,
                    "account_age_days": random.randint(2, 800),
                }
            }

            try:
                resp = await client.post(target_url, json=event)
                if resp.status_code == 202:
                    data = resp.json()
                    print(f"[{counter}] Ingested: {data['event_id']} (amt: ${amount:,.2f}, merch: {merch_cat})")
                else:
                    print(f"[{counter}] Ingestion returned {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"[{counter}] Ingestion failed: {e}")

            delay = (1.0 / rate_per_second) if not burst_mode else random.uniform(0.01, 0.1)
            await asyncio.sleep(delay)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nSimulator stopped.")
    finally:
        await client.aclose()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GuardRail Transaction Simulator")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/alerts/ingest")
    parser.add_argument("--rate", type=float, default=2.0, help="Transactions per second")
    parser.add_argument("--burst", action="store_true", help="Burst mode")
    args = parser.parse_args()

    asyncio.run(simulate(target_url=args.url, rate_per_second=args.rate, burst_mode=args.burst))
