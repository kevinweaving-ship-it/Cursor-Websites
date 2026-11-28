#!/usr/bin/env python3
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")
LIVE_SLOT = Path("/var/www/sailingsa/js/regatta-slot-card.js")
LIVE_MM = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")
PATCH = Path("/root/patch_live_outstanding_wait_jesus.py")
NEW_SLOT = Path("/root/regatta-slot-card.js")
NEW_MM = Path("/root/mm-lipton-reels-card.js")
BACKUP_DIR = Path("/root/backups")
CAM_DIR = Path("/var/www/sailingsa/assets/adverts/mm-cape-classic")


def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.check_call(cmd)


def main():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LIVE_API, BACKUP_DIR / f"api.py.outstanding_{ts}")
    shutil.copy2(LIVE_SLOT, BACKUP_DIR / f"regatta-slot-card.js.outstanding_{ts}")
    shutil.copy2(LIVE_MM, BACKUP_DIR / f"mm-lipton-reels-card.js.outstanding_{ts}")
    dry = Path("/root/api.py.outstanding_dry")
    shutil.copy2(LIVE_API, dry)
    run(["python3", str(PATCH), str(dry)])
    run(["chattr", "-i", str(LIVE_API)])
    try:
        run(["python3", str(PATCH), str(LIVE_API)])
        run(["chown", "www-data:www-data", str(LIVE_API)])
    finally:
        run(["chattr", "+i", str(LIVE_API)])
    shutil.copy2(NEW_SLOT, LIVE_SLOT)
    shutil.copy2(NEW_MM, LIVE_MM)
    run(["chown", "www-data:www-data", str(LIVE_SLOT), str(LIVE_MM)])
    CAM_DIR.mkdir(parents=True, exist_ok=True)
    run(["chown", "www-data:www-data", str(CAM_DIR)])
    run(["systemctl", "restart", "sailingsa-api"])
    time.sleep(12)
    run(["systemctl", "is-active", "sailingsa-api"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
