#!/usr/bin/env python3
"""Temporary pool-exhaustion diagnostics. Does not change get/return semantics."""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = p.read_text(encoding="utf-8", errors="replace")
if "_EXHAUST_DIAG" in text:
    raise SystemExit("already patched")

old_flag = "_worker_req_peak = 0\n"
new_flag = """_worker_req_peak = 0

_EXHAUST_DIAG = True
_EXHAUST_LOG = "/tmp/ssa_pool_exhaust.jsonl"
_exhaust_lock = threading.Lock()
_exhaust_holds = {}
"""
if old_flag not in text:
    raise SystemExit("flag anchor missing")
text = text.replace(old_flag, new_flag, 1)

old_on_get_end = """        try:
            _checkout_diag_on_get(wrapped)
        except Exception:
            pass
        return wrapped
"""
new_on_get_end = """        try:
            _checkout_diag_on_get(wrapped)
        except Exception:
            pass
        try:
            if _EXHAUST_DIAG:
                _tr = _borrowed_conns_cv.get()
                _exhaust_holds_add(wrapped, getattr(_tr, "endpoint", "?") if _tr is not None else "?")
        except Exception:
            pass
        return wrapped
"""
if old_on_get_end not in text:
    raise SystemExit("on_get anchor missing")
text = text.replace(old_on_get_end, new_on_get_end, 1)

old_fail = """        except Exception as e:
            last_err = e
            print(f"[DB] Error getting connection from pool: {e}", flush=True)
            break
"""
new_fail = """        except Exception as e:
            last_err = e
            print(f"[DB] Error getting connection from pool: {e}", flush=True)
            try:
                if _EXHAUST_DIAG:
                    _exhaust_dump(e)
            except Exception:
                pass
            break
"""
if old_fail not in text:
    raise SystemExit("fail anchor missing")
text = text.replace(old_fail, new_fail, 1)

old_ret = """        try:
            _checkout_diag_on_return(conn)
        except Exception:
            pass
"""
new_ret = """        try:
            _checkout_diag_on_return(conn)
        except Exception:
            pass
        try:
            if _EXHAUST_DIAG:
                _exhaust_holds_drop(conn)
        except Exception:
            pass
"""
if old_ret not in text:
    raise SystemExit("return diag anchor missing")
text = text.replace(old_ret, new_ret, 1)

old_borrow = "def _borrow_site() -> str:\n"
new_borrow = '''def _exhaust_holds_add(wrapped, path: str) -> None:
    if wrapped is None:
        return
    rec = {
        "wid": id(wrapped),
        "site": getattr(wrapped, "_borrowed_from", "?"),
        "path": path or "?",
        "t0": time.time(),
        "pid": os.getpid(),
    }
    with _exhaust_lock:
        _exhaust_holds[id(wrapped)] = rec


def _exhaust_holds_drop(conn) -> None:
    if conn is None:
        return
    with _exhaust_lock:
        _exhaust_holds.pop(id(conn), None)


def _exhaust_dump(err) -> None:
    tracker = _borrowed_conns_cv.get()
    path = getattr(tracker, "endpoint", "?") if tracker is not None else "?"
    req_n = 0
    if tracker is not None and hasattr(tracker, "registered_count"):
        try:
            req_n = int(tracker.registered_count())
        except Exception:
            req_n = 0
    now = time.time()
    with _exhaust_lock:
        holds = list(_exhaust_holds.values())
    site = _borrow_site()
    payload = {
        "ev": "exhausted",
        "pid": os.getpid(),
        "path": path,
        "borrow_site": site,
        "req_n": req_n,
        "worker_n": len(holds),
        "err": str(err)[:200],
        "holds": [
            {
                "site": h.get("site"),
                "path": h.get("path"),
                "age_ms": round((now - float(h.get("t0") or now)) * 1000.0, 1),
            }
            for h in holds
        ],
    }
    try:
        with open(_EXHAUST_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, separators=(",", ":")) + "\\n")
    except Exception:
        pass
    print(
        f"[DB] EXHAUST pid={os.getpid()} path={path} req_n={req_n} "
        f"worker_n={len(holds)} site={site}",
        flush=True,
    )


def _borrow_site() -> str:
'''
if old_borrow not in text:
    raise SystemExit("borrow_site anchor missing")
text = text.replace(old_borrow, new_borrow, 1)

p.write_text(text, encoding="utf-8")
print(f"patched exhaust diag {p}")
