import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect(r"C:\Users\tmmud\.gemini\antigravity\scratch\guardrail\guardrail_dev.db")
c = conn.cursor()
now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
print("CURRENT UTC TIME:", now_str)

c.execute("SELECT count(*) FROM fraud_alerts WHERE status != 'RESOLVED'")
print("TOTAL ACTIVE:", c.fetchone()[0])

c.execute("SELECT count(*) FROM fraud_alerts WHERE status != 'RESOLVED' AND sla_deadline < ?", (now_str,))
print("BREACHED COUNT:", c.fetchone()[0])

c.execute("SELECT min(sla_deadline), max(sla_deadline) FROM fraud_alerts WHERE status != 'RESOLVED'")
print("MIN/MAX SLA:", c.fetchone())
