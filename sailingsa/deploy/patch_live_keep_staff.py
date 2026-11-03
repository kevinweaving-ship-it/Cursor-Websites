#!/usr/bin/env python3
"""Stop dropping staff signed-in rows from Live list (empty Live while LIVE NOW=1)."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

OLD = """                # staff IPs (signed-in Tim/Kevin wifi) stay out of public Live
                if ip_r:
                    try:
                        cur.execute(
                            "SELECT 1 WHERE %s IN " + _LEAN_TRAFFIC_STAFF_IP_SQL + " LIMIT 1",
                            (ip_r,),
                        )
                        if cur.fetchone():
                            continue
                    except Exception:
                        pass
"""

NEW = """                # Keep signed-in staff on Live (LIVE NOW already counts them).
                # Only hide guest/bot rows that share a staff wifi IP.
                if ip_r and (r.get("kind") or "") not in ("signed",):
                    try:
                        cur.execute(
                            "SELECT 1 WHERE %s IN " + _LEAN_TRAFFIC_STAFF_IP_SQL + " LIMIT 1",
                            (ip_r,),
                        )
                        if cur.fetchone():
                            continue
                    except Exception:
                        pass
"""

OLD2 = """                if ip_r:
                    try:
                        age = _lean_quarantine_age_seconds(cur, ip_r)
                        if age is not None and age >= 60:
                            continue  # past grace → hide from Live (Done/offline still has audit)
                        if age is not None and r.get("kind") != "bot":
                            # quarantined but still in grace — show as bot
                            r = dict(r)
                            r["kind"] = "bot"
                            r["who"] = f"Bot {ip_r}"
                            r["who_href"] = ""
                            r["likely_name"] = ""
                            r["likely_slug"] = ""
                    except Exception:
                        pass
                filtered.append(r)
"""

NEW2 = """                if ip_r and (r.get("kind") or "") != "signed":
                    try:
                        age = _lean_quarantine_age_seconds(cur, ip_r)
                        if age is not None and age >= 60:
                            continue  # past grace → hide from Live (Done/offline still has audit)
                        if age is not None and r.get("kind") != "bot":
                            # quarantined but still in grace — show as bot
                            r = dict(r)
                            r["kind"] = "bot"
                            r["who"] = f"Bot {ip_r}"
                            r["who_href"] = ""
                            r["likely_name"] = ""
                            r["likely_slug"] = ""
                    except Exception:
                        pass
                filtered.append(r)
"""


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    if "Keep signed-in staff on Live" in text:
        print("SKIP already patched")
    else:
        if OLD not in text:
            raise SystemExit("OLD staff filter missing")
        text = text.replace(OLD, NEW, 1)
        print("OK staff signed kept on Live")
    if OLD2 in text:
        text = text.replace(OLD2, NEW2, 1)
        print("OK quarantine skip for signed")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK compiled")


if __name__ == "__main__":
    main()
