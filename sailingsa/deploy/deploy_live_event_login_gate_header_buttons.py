#!/usr/bin/env python3
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")
LIVE_JS = Path("/var/www/sailingsa/js/regatta-slot-card.js")
PATCH = Path("/root/patch_live_event_login_gate_header_buttons.py")
NEW_JS = Path("/root/regatta-slot-card.js")
BACKUP_DIR = Path("/root/backups")


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def main():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LIVE_API, BACKUP_DIR / f"api.py.login_gate_{ts}")
    shutil.copy2(LIVE_JS, BACKUP_DIR / f"regatta-slot-card.js.login_gate_{ts}")
    dry = Path("/root/api.py.login_gate_dry")
    shutil.copy2(LIVE_API, dry)
    run(["python3", str(PATCH), str(dry)])
    run(["chattr", "-i", str(LIVE_API)])
    try:
        run(["python3", str(PATCH), str(LIVE_API)])
        run(["chown", "www-data:www-data", str(LIVE_API)])
    finally:
        run(["chattr", "+i", str(LIVE_API)])
    shutil.copy2(NEW_JS, LIVE_JS)
    run(["chown", "www-data:www-data", str(LIVE_JS)])
    run(["systemctl", "restart", "sailingsa-api"])
    time.sleep(3)
    run(["systemctl", "is-active", "sailingsa-api"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
