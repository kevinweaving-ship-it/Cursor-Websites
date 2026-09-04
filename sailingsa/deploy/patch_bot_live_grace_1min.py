#!/usr/bin/env python3
"""Confirmed bots stay on Live for 60s after ID, then hide."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HELPER = '''def _lean_quarantine_age_seconds(cur, ip_address: Optional[str]) -> Optional[float]:
    """Seconds since IP was first quarantined (bot confirmed). None if not quarantined."""
    ip = (ip_address or "").strip()
    if not ip:
        return None
    try:
        _lean_ensure_quarantine_table(cur)
        cur.execute(
            """
            SELECT EXTRACT(EPOCH FROM (NOW() - COALESCE(first_seen_at, last_seen_at)))::float
            FROM public.traffic_quarantine_ips
            WHERE ip_address = %s AND COALESCE(active, true) = true
            LIMIT 1
            """,
            (ip,),
        )
        row = cur.fetchone()
        if not row:
            return None
        val = row[0] if not isinstance(row, dict) else next(iter(row.values()))
        if val is None:
            return 0.0
        return float(val)
    except Exception:
        return None


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-bot-grace-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    if "def _lean_quarantine_age_seconds" not in text:
        anchor = text.find("def _lean_ip_is_quarantined")
        if anchor < 0:
            raise SystemExit("quarantine helper missing")
        text = text[:anchor] + HELPER + text[anchor:]

    old = '''                # Confirmed bot → quarantine and remove from Live (audit via Done/offline)
                if r.get("kind") == "bot":
                    if ip_r:
                        try:
                            _lean_quarantine_ip(cur, ip_r, "live_bot")
                        except Exception:
                            pass
                    continue
                if ip_r:
                    try:
                        if _lean_ip_is_quarantined(cur, ip_r):
                            continue
                    except Exception:
                        pass
                filtered.append(r)
'''
    new = '''                # Confirmed bot: quarantine, keep on Live for ~60s so you can see it, then hide
                if r.get("kind") == "bot" and ip_r:
                    try:
                        _lean_quarantine_ip(cur, ip_r, "live_bot")
                    except Exception:
                        pass
                if ip_r:
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
'''
    if old not in text:
        raise SystemExit("hide-bot block not found — apply hide patch first or check live text")
    text = text.replace(old, new, 1)

    # Update note
    old_note = "Confirmed bots are hidden from Live (see Done/offline)."
    new_note = "Confirmed bots stay on Live ~1 min, then hide (see Done/offline)."
    if old_note in text:
        text = text.replace(old_note, new_note, 1)
    elif "Confirmed bots stay on Live" not in text:
        text = text.replace(
            "▶ shows URL trail + dwell.",
            "▶ shows URL trail + dwell. Confirmed bots stay on Live ~1 min, then hide.",
            1,
        )

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK bot live grace 60s (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
