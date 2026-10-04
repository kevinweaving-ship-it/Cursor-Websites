#!/usr/bin/env python3
"""Drop stale 420 preload PDF so the next request rebuilds from live Final results."""
import os
import shutil
from datetime import datetime
from pathlib import Path

RID = "2026-09-25-tsc-420-nationals"
ROOT = Path("/var/www/sailingsa/data/regatta-pdfs") / RID


def main() -> None:
    if not ROOT.is_dir():
        print("NO_DIR", ROOT)
        raise SystemExit(2)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(f"/root/backup_420_preload_pdf_{ts}")
    bak.mkdir(parents=True, exist_ok=True)
    for p in sorted(ROOT.iterdir()):
        print("HAD", p.name, p.stat().st_size)
        shutil.copy2(p, bak / p.name)
        if p.suffix.lower() == ".pdf" or p.name.startswith(".event-truth"):
            p.unlink()
            print("DEL", p.name)
    os.chown(ROOT, 33, 33)
    os.chmod(ROOT, 0o775)
    print("BACKUP", bak)
    print("LEFT", [x.name for x in ROOT.iterdir()] if ROOT.is_dir() else "GONE")


if __name__ == "__main__":
    main()
