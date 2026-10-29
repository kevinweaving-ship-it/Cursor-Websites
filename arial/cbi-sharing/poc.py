#!/opt/cbi-sharing/venv/bin/python
"""CBI / white-label OEM login — not Home Assistant QR.

HA sharing QR is Smart Life only. This logs in with the OEM app's own AppKey
the same way the phone does, then writes /opt/cbi-sharing/state/session.json
for the isolated CBI collector.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from oem import OemClient, client_from_session, connect_oem, oem_settings, thing_profiles, write_session

ROOT = Path("/opt/cbi-sharing")
STATE = Path(os.getenv("CBI_SHARING_STATE") or str(ROOT / "state"))
SESSION = STATE / "session.json"


def cmd_login(_args: argparse.Namespace) -> int:
    s = oem_settings()
    print("schema", s["schema"])
    print("app_key", s["app_key"])
    print("email_set", bool(s["email"]))
    print("password_set", bool(s["password"]))
    print("region", s["region"] or "auto")
    try:
        client = connect_oem(s)
    except Exception as exc:
        print("LOGIN_FAIL", str(exc)[:400])
        return 2
    write_session(SESSION, client)
    print("LOGIN_OK")
    print("uid", client.uid)
    print("region", client.region)
    print("session", SESSION)
    try:
        homes = client.list_homes()
    except Exception as exc:
        print("HOMES_FAIL", str(exc)[:300])
        return 0
    print("homes", json.dumps([{"id": h["id"], "name": h["name"]} for h in homes]))
    return 0


def cmd_probe(_args: argparse.Namespace) -> int:
    """Token-only: which white-label Thing SDK 5 identity the OEM cloud accepts."""
    s = oem_settings()
    email = s["email"] or "probe@example.com"
    print("schema", s["schema"])
    print("email_set", bool(s["email"]))
    print("profiles", len(thing_profiles(s)))
    client = OemClient(s)
    hits = 0
    for profile in thing_profiles(s):
        for country in (s["country"], ""):
            result = client.probe_token(profile, email, country)
            print(
                "app", profile["app_id"][-4:],
                "et", profile["et"],
                "cc", repr(country),
                result,
            )
            if result == "OK":
                hits += 1
    print("hits", hits)
    return 0 if hits else 2


def cmd_status(_args: argparse.Namespace) -> int:
    if not SESSION.exists():
        print("NO_SESSION")
        return 2
    raw = json.loads(SESSION.read_text(encoding="utf-8"))
    print("kind", raw.get("kind"))
    print("schema", raw.get("schema"))
    print("uid", raw.get("uid"))
    print("region", raw.get("region"))
    print("username_set", bool(raw.get("username")))
    if raw.get("kind") != "oem":
        print("not an OEM session — HA/Smart Life QR is the wrong path for CBI")
        return 3
    try:
        client = client_from_session(SESSION)
        homes = client.list_homes()
    except Exception as exc:
        print("SESSION_DEAD", str(exc)[:300])
        return 4
    print("homes", json.dumps([{"id": h["id"], "name": h["name"]} for h in homes]))
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="CBI / OEM white-label login (not HA QR)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login", help="Log in with CBI Home email/password and write session.json")
    sub.add_parser("probe", help="Token-only: find a working white-label Thing SDK 5 identity")
    sub.add_parser("status", help="Show the current OEM session")
    args = p.parse_args()
    if args.cmd == "login":
        return cmd_login(args)
    if args.cmd == "probe":
        return cmd_probe(args)
    return cmd_status(args)


if __name__ == "__main__":
    sys.exit(main())
