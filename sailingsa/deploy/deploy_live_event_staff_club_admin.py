#!/usr/bin/env python3
"""Deploy Cape Classic Staff club-admin toggle + Login label to live."""
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")
LIVE_JS = Path("/var/www/sailingsa/js/regatta-slot-card.js")
PATCH = Path("/root/patch_live_event_staff_club_admin.py")
NEW_JS = Path("/root/regatta-slot-card.js")
BACKUP_DIR = Path("/root/backups")


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    api_bak = BACKUP_DIR / f"api.py.staff_club_{ts}"
    js_bak = BACKUP_DIR / f"regatta-slot-card.js.staff_club_{ts}"
    shutil.copy2(LIVE_API, api_bak)
    if LIVE_JS.exists():
        shutil.copy2(LIVE_JS, js_bak)
    print("backed up", api_bak, js_bak if LIVE_JS.exists() else "")

    dry = Path("/root/api.py.staff_club_dry")
    shutil.copy2(LIVE_API, dry)
    run(["python3", str(PATCH), str(dry)])

    run(["chattr", "-i", str(LIVE_API)])
    try:
        run(["python3", str(PATCH), str(LIVE_API)])
        run(["chown", "www-data:www-data", str(LIVE_API)])
    finally:
        run(["chattr", "+i", str(LIVE_API)])

    if not NEW_JS.exists():
        raise SystemExit("missing /root/regatta-slot-card.js")
    shutil.copy2(NEW_JS, LIVE_JS)
    run(["chown", "www-data:www-data", str(LIVE_JS)])
    print("copied js", LIVE_JS, "bytes", LIVE_JS.stat().st_size)

    run(["systemctl", "restart", "sailingsa-api"])
    time.sleep(3)
    run(["systemctl", "is-active", "sailingsa-api"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
