#!/usr/bin/env python3
"""Patch live api.py: ignore tracker T+/T-/no-T- after Lipton day close.

Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_TRACKER_OVERNIGHT_GUARD_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

GUARD = (
    "    var pgDone=document.querySelector('.regatta-page[data-live-board-tint-rid=\"'+rid+'\"]');\n"
    "    if(pgDone && pgDone.getAttribute('data-live-day-done')==='1') return false; /* "
    + MARKER
    + " */\n"
)

OLD_NO = '''  function applyTrackerNoTMinus(rid){
    /* No T-/T+ on tracker → POSTPONED (AP flag + blink).
       Prefer race-officer Start (data-live-board-start-tm, e.g. 13:55);
       else provisional next full hour. Never auto-gun. Tracker T- corrects. */
    rid=String(rid||'').trim();
    if(!rid) return false;
'''

NEW_NO = '''  function applyTrackerNoTMinus(rid){
    /* No T-/T+ on tracker → POSTPONED (AP flag + blink).
       Prefer race-officer Start (data-live-board-start-tm, e.g. 13:55);
       else provisional next full hour. Never auto-gun. Tracker T- corrects. */
    rid=String(rid||'').trim();
    if(!rid) return false;
''' + GUARD

OLD_PLUS = '''  function applyTrackerTPlus(rid, tPlus, raceKey){
    /* Tracker T+ → race started / underway. Green header clock; Racing Rn label. */
    rid=String(rid||'').trim();
    var elapsedMs=parseTMinusToMs(String(tPlus||'').replace(/^T\\+/i,'T-'));
    if(!(elapsedMs>=0) || !rid) return false;
'''

# In the live file the regex is /^T\+/i inside a JS string in a Python string.
# Use the exact live bytes via a second pattern that we verify by count.

OLD_PLUS2 = """  function applyTrackerTPlus(rid, tPlus, raceKey){
    /* Tracker T+ → race started / underway. Green header clock; Racing Rn label. */
    rid=String(rid||'').trim();
"""

NEW_PLUS2 = """  function applyTrackerTPlus(rid, tPlus, raceKey){
    /* Tracker T+ → race started / underway. Green header clock; Racing Rn label. */
    rid=String(rid||'').trim();
    if(!rid) return false;
""" + GUARD

OLD_MINUS = '''  function applyTrackerTMinus(rid, tMinus, opts){
    /* Vakaros GPS T- + capture wall → lock start on the minute (e.g. 14:05:00).
       Never use server clock. Red T- counts down; green T+ only after gun. */
    opts=opts||{};
    rid=String(rid||'').trim();
'''

NEW_MINUS = '''  function applyTrackerTMinus(rid, tMinus, opts){
    /* Vakaros GPS T- + capture wall → lock start on the minute (e.g. 14:05:00).
       Never use server clock. Red T- counts down; green T+ only after gun. */
    opts=opts||{};
    rid=String(rid||'').trim();
    if(!rid) return false;
''' + GUARD


def _patch_once(text: str, label: str, old: str, new: str) -> tuple[str, bool]:
    n = text.count(old)
    if n == 0 and MARKER in text and label in ("no", "plus", "minus"):
        print(f"maybe already {label}")
    if n != 1:
        print(f"FAIL {label}: found {n}", file=sys.stderr)
        return text, False
    return text.replace(old, new, 1), True


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    ok = True
    text, p = _patch_once(text, "no", OLD_NO, NEW_NO)
    ok = ok and p
    text, p = _patch_once(text, "plus", OLD_PLUS2, NEW_PLUS2)
    ok = ok and p
    text, p = _patch_once(text, "minus", OLD_MINUS, NEW_MINUS)
    ok = ok and p
    if not ok:
        return 1
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
