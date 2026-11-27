import sqlite3

conn = sqlite3.connect(r"C:\Users\tmmud\.gemini\antigravity\scratch\guardrail\guardrail_dev.db")
c = conn.cursor()
c.execute("UPDATE dead_letter_events SET replay_status = 'PENDING' WHERE original_event_id IN ('evt_err_1001', 'evt_err_1002', 'evt_err_1003')")
conn.commit()
c.execute("SELECT original_event_id, replay_status FROM dead_letter_events")
print("DLQ ROWS:", c.fetchall())
conn.close()
