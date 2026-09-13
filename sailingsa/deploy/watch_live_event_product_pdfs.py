#!/usr/bin/env python3
"""Keep stored product PDFs current for every live event.

Cape Classic is the live event today; the rule is the same for any
live event: fingerprint the Event URL, skip if it matches the last PDF,
rebuild when scores / boats / the Results-are line change.

  PYTHONPATH=/var/www/sailingsa:/var/www/sailingsa/api \
    /var/www/sailingsa/api/venv/bin/python3 \
    /var/www/sailingsa/deploy/watch_live_event_product_pdfs.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = os.environ.get("SSA_ROOT", "/var/www/sailingsa")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))
os.chdir(os.path.join(ROOT, "api"))


def _adopt_api_env() -> None:
    """Copy DB settings from the running API without printing them."""
    try:
        import subprocess

        pid = subprocess.check_output(
            ["systemctl", "show", "sailingsa-api", "-p", "MainPID", "--value"],
            text=True,
        ).strip()
        if not pid or pid == "0":
            return
        raw = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    except Exception:
        return
    for item in raw:
        if not item or b"=" not in item:
            continue
        key, _, val = item.partition(b"=")
        try:
            ks = key.decode("utf-8")
            vs = val.decode("utf-8", "replace")
        except Exception:
            continue
        if ks in ("_", "PWD", "OLDPWD"):
            continue
        if not os.environ.get(ks):
            os.environ[ks] = vs


def main() -> int:
    _adopt_api_env()
    import api as api_mod
    from sailingsa.backend.regatta_pdf_diff import (
        list_live_parent_ids,
        needs_rebuild,
        write_stamp,
    )

    rebuild = getattr(api_mod, "_rebuild_regatta_stored_pdfs", None)
    if rebuild is None:
        raise SystemExit("api module is missing _rebuild_regatta_stored_pdfs")

    only = (os.environ.get("SSA_PDF_RID") or "").strip()
    if only:
        live = [only]
    else:
        live = list_live_parent_ids(api_mod.q)
    print(
        json.dumps({"ok": True, "live": live, "n": len(live)}),
        flush=True,
    )
    skipped = rebuilt = failed = 0
    for rid in live:
        try:
            need, fp, stored = needs_rebuild(api_mod.q, rid)
            if not need:
                skipped += 1
                print(
                    json.dumps(
                        {
                            "rid": rid,
                            "action": "skip",
                            "reason": "no_diff",
                            "fp": fp[:12],
                        }
                    ),
                    flush=True,
                )
                continue
            rebuild(rid)
            if fp:
                write_stamp(rid, fp)
            rebuilt += 1
            print(
                json.dumps(
                    {
                        "rid": rid,
                        "action": "rebuild",
                        "reason": "missing_pdf" if not stored else "diff",
                        "fp": (fp or "")[:12],
                    }
                ),
                flush=True,
            )
        except Exception as exc:
            failed += 1
            print(
                json.dumps({"rid": rid, "action": "fail", "error": str(exc)[:240]}),
                flush=True,
            )
    print(
        json.dumps(
            {
                "ok": failed == 0,
                "skipped": skipped,
                "rebuilt": rebuilt,
                "failed": failed,
            }
        ),
        flush=True,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
