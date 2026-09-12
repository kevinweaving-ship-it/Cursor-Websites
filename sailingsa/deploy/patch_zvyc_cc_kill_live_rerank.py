#!/usr/bin/env python3
"""Surgical live api.py patch: REMOVE client re-rank that ignores Appendix A8.2.

Cape Classic Open official sheet (PDF checksum):
  Sean 585 R1=2 R2=1 tot=3 nett=3 → A8.2 last race 1 → rank 1
  Gordon 589 R1=1 R2=2 tot=3 nett=3 → A8.2 last race 2 → rank 2

Wrong live JS (must not run on this regatta):
  sortRowsBySheetNett  — equal nett → DOM / data-sheet-order / result_id
  sortRowsFromCompleted / sortByRankings — tracker places, not sheet scores
  sortRowsByOfficialRank — still mutates rank-col / row order on every paint

Never replace live api.py wholesale. Run on the server against
/var/www/sailingsa/api/api.py after chattr -i.
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
CC = "2026-09-13-zvyc-cape-classic"


def must_swap(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)


def main() -> int:
    if not API.is_file():
        raise SystemExit(f"missing {API}")
    src = API.read_text(encoding="utf-8")
    orig = src

    src = must_swap(
        src,
        "def _regatta_live_race_autoscore_script() -> str:\n"
        '    """On RACING → scroll to score sheet; sort by bow live ranks; apply finishes → Rn."""\n'
        '    return r"""\n',
        "def _regatta_live_race_autoscore_script(regatta_id=None) -> str:\n"
        '    """On RACING → scroll to score sheet; sort by bow live ranks; apply finishes → Rn."""\n'
        f'    if str(regatta_id or "").strip() == "{CC}":\n'
        "        return \"\"\n"
        '    return r"""\n',
        "skip autoscore script injection for Cape Classic",
    )

    src = must_swap(
        src,
        "  var page=document.querySelector('.regatta-page[data-live-board-tint-rid]');\n"
        "  if(!page) return;\n"
        "  var rid=page.getAttribute('data-live-board-tint-rid');\n"
        "  if(!rid) return;\n"
        "  var lastSig='';\n"
        "  var applying=false;\n",
        "  var page=document.querySelector('.regatta-page[data-live-board-tint-rid]');\n"
        "  if(!page) return;\n"
        "  var rid=page.getAttribute('data-live-board-tint-rid');\n"
        "  if(!rid) return;\n"
        f"  if(rid==='{CC}') return;\n"
        "  function officialSheetLocked(){\n"
        "    return !!document.querySelector('.fleet-results-table tbody tr[data-official-rank]');\n"
        "  }\n"
        "  var lastSig='';\n"
        "  var applying=false;\n",
        "JS bail out for Cape Classic plus official-sheet lock helper",
    )

    src = must_swap(
        src,
        "    if(document.querySelector('.fleet-results-table tbody tr[data-official-rank]')){\n"
        "      sortRowsByOfficialRank();\n"
        "    } else if(String((st&&st.phase)||'').toLowerCase()==='racing'){\n"
        "      sortRowsBySheetNett();\n"
        "    } else {\n"
        "      sortRowsFromCompleted(st);\n"
        "    }\n",
        "    if(officialSheetLocked()){\n"
        "      /* Official PDF + A8 already in the HTML. Do not rewrite ranks. */\n"
        "    } else if(String((st&&st.phase)||'').toLowerCase()==='racing'){\n"
        "      sortRowsBySheetNett();\n"
        "    } else {\n"
        "      sortRowsFromCompleted(st);\n"
        "    }\n",
        "stop calling sortRowsByOfficialRank rewrite",
    )

    src = must_swap(
        src,
        "  function sortRowsByOfficialRank(){\n"
        "    /* PDF + A8 ranks already on the sheet. Keep that order; never invent 1st/2nd from tracker. */\n"
        "    var tb=tbody();\n",
        "  function sortRowsByOfficialRank(){\n"
        "    return;\n"
        "    var tb=tbody();\n",
        "no-op sortRowsByOfficialRank",
    )

    src = must_swap(
        src,
        "  function sortRowsBySheetNett(){\n"
        "    /* Lowest sheet Nett = 1st. Ties keep original sheet order (A8 already applied). */\n"
        "    var tb=tbody();\n",
        "  function sortRowsBySheetNett(){\n"
        "    /* Equal nett is A8, not DOM/result_id order. Official sheets must not be rewritten. */\n"
        "    if(officialSheetLocked()) return;\n"
        "    var tb=tbody();\n",
        "no-op sortRowsBySheetNett on official sheets",
    )

    src = must_swap(
        src,
        "  function sortRowsFromCompleted(st){\n"
        "    /* Sort/rank from completed race_times only — never wipe order when current race has no finishes yet.\n",
        "  function sortRowsFromCompleted(st){\n"
        "    if(officialSheetLocked()) return;\n"
        "    /* Sort/rank from completed race_times only — never wipe order when current race has no finishes yet.\n",
        "no-op sortRowsFromCompleted on official sheets",
    )

    src = must_swap(
        src,
        "  function sortByRankings(rankings){\n"
        "    var tb=tbody();\n"
        "    if(!tb||!rankings||!rankings.length) return;\n",
        "  function sortByRankings(rankings){\n"
        "    if(officialSheetLocked()) return;\n"
        "    var tb=tbody();\n"
        "    if(!tb||!rankings||!rankings.length) return;\n",
        "no-op sortByRankings on official sheets",
    )

    src = must_swap(
        src,
        "            paintFinishTimes(st);\n"
        "            sortRowsBySheetNett();\n"
        "          }\n"
        "          return;\n",
        "            paintFinishTimes(st);\n"
        "            if(!officialSheetLocked()) sortRowsBySheetNett();\n"
        "          }\n"
        "          return;\n",
        "tick lastSig skip sheet-nett rewrite when official",
    )

    src = must_swap(
        src,
        "          paintFinishTimes(st);\n"
        "          sortRowsBySheetNett();\n"
        "        }\n"
        "        /* Not racing: leave checksum sheet still. Do not paint/sort from tracker. */\n",
        "          paintFinishTimes(st);\n"
        "          if(!officialSheetLocked()) sortRowsBySheetNett();\n"
        "        }\n"
        "        /* Not racing: leave checksum sheet still. Do not paint/sort from tracker. */\n",
        "tick skip sheet-nett rewrite when official",
    )

    src = must_swap(
        src,
        "        paintFinishTimes(st);\n"
        "        sortByRankings(st.rankings||[]);\n"
        "        applying=false;\n",
        "        paintFinishTimes(st);\n"
        "        if(!officialSheetLocked()) sortByRankings(st.rankings||[]);\n"
        "        applying=false;\n",
        "applyFinishes skip tracker re-rank when official",
    )

    src = must_swap(
        src,
        "      } else if(d.rankings&&d.rankings.length){\n"
        "        sortByRankings(d.rankings);\n"
        "      }\n",
        "      } else if(d.rankings&&d.rankings.length){\n"
        "        if(!officialSheetLocked()) sortByRankings(d.rankings);\n"
        "      }\n",
        "BroadcastChannel skip tracker re-rank when official",
    )

    src = must_swap(
        src,
        'f"{_regatta_live_board_toggle_script()}{_regatta_live_race_autoscore_script()}{_regatta_as_at_live_clock_script()}"',
        'f"{_regatta_live_board_toggle_script()}{_regatta_live_race_autoscore_script(str(regatta_id))}{_regatta_as_at_live_clock_script()}"',
        "standalone class page skip CC autoscore",
    )

    src = must_swap(
        src,
        "live_board_script = _regatta_live_board_toggle_script() + _regatta_live_race_autoscore_script() + _regatta_as_at_live_clock_script()",
        "live_board_script = _regatta_live_board_toggle_script() + _regatta_live_race_autoscore_script(str(regatta_id)) + _regatta_as_at_live_clock_script()",
        "regatta page skip CC autoscore",
    )

    if src == orig:
        raise SystemExit("no changes applied")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(f"/root/backups/api.py.kill_live_rerank_{ts}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    API.write_text(src, encoding="utf-8")
    print(f"patched {API} backup={bak} bytes={len(src)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
