#!/usr/bin/env python3
"""Delete owner IPs from traffic_quarantine_ips."""
import psycopg2

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
IPS = ("100.72.251.223", "41.247.20.198")

conn = psycopg2.connect(DSN)
cur = conn.cursor()
cur.execute(
    "SELECT ip_address, reason, active FROM traffic_quarantine_ips WHERE ip_address::text = ANY(%s) ORDER BY 1",
    (list(IPS),),
)
print("BEFORE", cur.fetchall())
cur.execute(
    "DELETE FROM traffic_quarantine_ips WHERE ip_address::text = ANY(%s)",
    (list(IPS),),
)
print("DELETED", cur.rowcount)
conn.commit()
cur.execute(
    "SELECT ip_address, reason, active FROM traffic_quarantine_ips WHERE ip_address::text = ANY(%s) ORDER BY 1",
    (list(IPS),),
)
left = cur.fetchall()
print("AFTER", left)
if left:
    raise SystemExit("STILL_PRESENT")
cur.close()
conn.close()
print("GONE")
