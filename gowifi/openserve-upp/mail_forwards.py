#!/usr/bin/env python3
"""go-wifi.co.za (old) → gowifi.co.za mail forwards.

Box aliases are already set. Public DNS for go-wifi.co.za has no MX, so
Openserve To: kevin@go-wifi.co.za never arrives here (iCloud still gets a copy).
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

USERS_DB = Path("/home/user-data/mail/users.sqlite")
OLD = "go-wifi.co.za"
NEW = "gowifi.co.za"

# Every live gowifi address must have a go-wifi twin, or it is not fw yet.
EXPECTED = (
    ("kevin@go-wifi.co.za", "kevin@gowifi.co.za"),
    ("robby@go-wifi.co.za", "robby@gowifi.co.za"),
    ("openserve@go-wifi.co.za", "openserve@gowifi.co.za"),
    ("accounts@go-wifi.co.za", "kevin@gowifi.co.za,openserve@gowifi.co.za"),
    ("support@go-wifi.co.za", "kevin@gowifi.co.za"),
    ("admin@go-wifi.co.za", "administrator@box.gowifi.co.za"),
    ("abuse@go-wifi.co.za", "administrator@box.gowifi.co.za"),
    ("postmaster@go-wifi.co.za", "administrator@box.gowifi.co.za"),
)


def _norm(dest: str | None) -> str:
    parts = [p.strip().lower() for p in (dest or "").split(",") if p.strip()]
    return ",".join(sorted(parts))


def _dig_mx(domain: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ["dig", "+short", "MX", domain],
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if line:
            rows.append(line.rstrip("."))
    return rows


def _dig_ns(domain: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ["dig", "+short", "NS", domain],
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    return [l.strip().rstrip(".") for l in out.splitlines() if l.strip()]


def _load_aliases(db: Path = USERS_DB) -> dict[str, str]:
    if not db.exists():
        return {}
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT source, destination FROM aliases UNION SELECT source, destination FROM auto_aliases"
    ).fetchall()
    conn.close()
    return {str(s).lower(): str(d) for s, d in rows}


def forwards_for_export(db: Path = USERS_DB) -> dict:
    aliases = _load_aliases(db)
    rows = []
    not_fw = []
    for source, want in EXPECTED:
        got = aliases.get(source.lower())
        ok = _norm(got) == _norm(want) if got else False
        rows.append(
            {
                "source": source,
                "want": want,
                "got": got,
                "forwarded": ok,
            }
        )
        if not ok:
            not_fw.append(source)
    extra_old = sorted(
        src
        for src in aliases
        if src.endswith(f"@{OLD}") and src not in {s.lower() for s, _w in EXPECTED}
    )
    mx_old = _dig_mx(OLD)
    mx_new = _dig_mx(NEW)
    ns_old = _dig_ns(OLD)
    mx_on_box = any("box.gowifi.co.za" in r.lower() for r in mx_old)
    return {
        "old": OLD,
        "new": NEW,
        "aliases": rows,
        "not_fw": not_fw,
        "extra_old": extra_old,
        "mx_go_wifi": mx_old,
        "mx_gowifi": mx_new,
        "ns_go_wifi": ns_old,
        "mx_on_box": mx_on_box,
        "dns_note": (
            "go-wifi.co.za NS is still Domains.co.za (anycast-ns). "
            "No public MX, so Openserve mail to kevin@go-wifi.co.za never hits the box. "
            "Add MX 10 box.gowifi.co.za at Domains.co.za, or point NS to "
            "ns1.box.gowifi.co.za / ns2.box.gowifi.co.za (zone already has the MX)."
        ),
        "note": (
            "Box aliases are live. Public MX is not. "
            "The 18:49 statements To: kevin@go-wifi.co.za + kevinweaving@icloud.com "
            "landed on iCloud only."
        ),
    }


def self_test() -> int:
    failed = 0
    pack = forwards_for_export(Path("/nonexistent.sqlite"))
    names = [r["source"] for r in pack["aliases"]]
    if "kevin@go-wifi.co.za" not in names or "accounts@go-wifi.co.za" not in names:
        print("FAIL expected-list", names)
        failed += 1
    elif _norm("openserve@gowifi.co.za,kevin@gowifi.co.za") != _norm(
        "kevin@gowifi.co.za,openserve@gowifi.co.za"
    ):
        print("FAIL dest-norm")
        failed += 1
    else:
        print("OK go-wifi-forward-list")
    return failed


if __name__ == "__main__":
    import sys

    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    print(json.dumps(forwards_for_export(), indent=2))
