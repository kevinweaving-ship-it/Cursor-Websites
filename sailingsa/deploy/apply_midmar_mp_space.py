#!/usr/bin/env python3
"""MP hides Crew only when width is actually tight (race columns overflow)."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "MIDMAR_MP_SPACE_HIDE_v1"

BOOT_OLD = "function mpBoot(){mpBind();mpOff();mpHide();}"
BOOT_NEW = (
    "function mpSpace(){"
    "document.querySelectorAll('.fleet-section .table-wrapper table.fleet-results-table').forEach(function(t){"
    "t.classList.remove('mp-tight-crew');"
    "if(!mpP())return;"
    "var w=t.closest('.table-wrapper');if(!w)return;"
    "if(!t.querySelector('th.race-col'))return;"
    "if(w.scrollWidth>w.clientWidth+16)t.classList.add('mp-tight-crew');"
    "});}"
    "function mpBoot(){mpBind();mpOff();mpSpace();mpHide();}"
)

CSS_OLD = (
    '    "display:table-cell!important;white-space:nowrap!important;min-width:max-content}"'
)
CSS_NEW = (
    '    "display:table-cell!important;white-space:nowrap!important;min-width:max-content}"\n'
    '    "/* MIDMAR_MP_SPACE_HIDE_v1: hide Crew only when MP width is tight (race cols overflow). */"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table.mp-tight-crew th.crew-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table.mp-tight-crew td.crew-col{display:none!important}"'
)


def main() -> None:
    api = API.read_text()
    if MARK in api and BOOT_NEW in api:
        print("API_ALREADY", MARK)
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.midmar_mp_space.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak)
    missing = []
    for name, old in (("BOOT", BOOT_OLD), ("CSS", CSS_OLD)):
        n = api.count(old)
        print("COUNT", name, n)
        if n != 1:
            missing.append(f"{name}:{n}")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    api = api.replace(BOOT_OLD, BOOT_NEW, 1)
    api = api.replace(CSS_OLD, CSS_NEW, 1)
    API.write_text(api)
    print("API_OK", MARK)


if __name__ == "__main__":
    main()
