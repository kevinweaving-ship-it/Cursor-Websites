#!/usr/bin/env python3
"""Set Voëlklip Smart Life switch_type from flip (toggle) to sync (on/off).

Only touches devices in Tuya home "Voelklip - Home" that already expose
switch_type and are currently flip. Leaves button (garage pulse) and sync
alone. Does not talk to CBI. Does not re-pair.

Run on the live box with the tuya-sharing venv:

  /opt/tuya-sharing/venv/bin/python arial/keypad/set_voelklip_switch_type_sync.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from tuya_sharing import Manager, SharingTokenListener

HOME = "Voelklip - Home"
SESSION = Path("/opt/tuya-sharing/state/session.json")
CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
# 2-gang inching off (6 zero bytes). Latch on/off; do not pulse.
INCHING_OFF_2G = "AAAAAAAAAAA="


class TokenPersist(SharingTokenListener):
    def update_token(self, token_info: dict) -> None:
        sess = json.loads(SESSION.read_text())
        sess["token_info"] = token_info
        sess["last_refresh_at"] = int(time.time())
        tmp = SESSION.with_suffix(".tmp")
        tmp.write_text(json.dumps(sess, separators=(",", ":"), default=str))
        tmp.chmod(0o600)
        tmp.replace(SESSION)


def main() -> None:
    sess = json.loads(SESSION.read_text())
    mgr = Manager(
        CLIENT_ID,
        sess["user_code"],
        sess["terminal_id"],
        sess["endpoint"],
        sess["token_info"],
        TokenPersist(),
    )
    found = []
    for h in mgr.home_repository.query_homes():
        if str(h.name).strip() != HOME:
            continue
        for d in mgr.device_repository.query_devices_by_home(h.id):
            fn = d.function or {}
            if "switch_type" not in fn:
                continue
            cur = (d.status or {}).get("switch_type")
            found.append((d, cur))

    print(f"voelklip devices with switch_type: {len(found)}")
    for d, cur in found:
        print(f"  {d.name.strip()} {d.id} online={bool(d.online)} type={cur}")

    changed = 0
    for d, cur in found:
        if cur != "flip":
            print(f"skip {d.name.strip()} type={cur}")
            continue
        cmds = [{"code": "switch_type", "value": "sync"}]
        inch = (d.status or {}).get("switch_inching")
        if inch:
            cmds.append({"code": "switch_inching", "value": INCHING_OFF_2G})
        print(f"SET {d.name.strip()} {d.id} {cmds}")
        try:
            mgr.send_commands(d.id, cmds)
            print(f"  ok sent (online={bool(d.online)})")
            changed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {type(exc).__name__}: {exc}")
    print(f"changed={changed}")


if __name__ == "__main__":
    main()
