#!/usr/bin/env python3
"""Add temporary per-worker / per-request checkout-hold instrumentation."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/api.py.patchwork")
text = SRC.read_text(encoding="utf-8", errors="replace")


def once(old: str, new: str, label: str) -> None:
    global text
    c = text.count(old)
    if c != 1:
        raise SystemExit(f"FAIL {label}: count={c}")
    text = text.replace(old, new, 1)
    print(f"OK {label}")


once(
    '''    def still_registered(self):
        with self._lock:
            return list(self._wrappers.values())
''',
    '''    def still_registered(self):
        with self._lock:
            return list(self._wrappers.values())

    def registered_count(self) -> int:
        with self._lock:
            return len(self._wrappers)
''',
    "tracker-registered-count",
)

once(
    '''def get_db_connection(request_id: str = None):
''',
    '''_CHECKOUT_DIAG = True
_CHECKOUT_LOG = "/tmp/ssa_checkout_hold.jsonl"
_worker_hold_lock = threading.Lock()
_worker_hold_n = 0
_worker_hold_peak = 0
_worker_hold_peak_path = ""
_worker_req_peak = 0


def _checkout_diag_write(payload: dict) -> None:
    if not _CHECKOUT_DIAG:
        return
    try:
        payload["pid"] = os.getpid()
        with open(_CHECKOUT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, separators=(",", ":")) + "\\n")
    except Exception:
        pass


def _checkout_diag_on_get(wrapped) -> None:
    global _worker_hold_n, _worker_hold_peak, _worker_hold_peak_path, _worker_req_peak
    if not _CHECKOUT_DIAG:
        return
    try:
        wrapped._checkout_t0 = time.time()
    except Exception:
        pass
    tracker = _borrowed_conns_cv.get()
    path = "?"
    req_n = 0
    if tracker is not None:
        path = getattr(tracker, "endpoint", "?") or "?"
        try:
            req_n = tracker.registered_count() if hasattr(tracker, "registered_count") else len(tracker.still_registered())
        except Exception:
            req_n = 0
    with _worker_hold_lock:
        _worker_hold_n += 1
        if _worker_hold_n > _worker_hold_peak:
            _worker_hold_peak = _worker_hold_n
            _worker_hold_peak_path = path
        if req_n > _worker_req_peak:
            _worker_req_peak = req_n
        w_n = _worker_hold_n
        w_peak = _worker_hold_peak
        r_peak = _worker_req_peak
    site = getattr(wrapped, "_borrowed_from", "?")
    _checkout_diag_write({
        "ev": "+",
        "path": path,
        "req_n": req_n,
        "worker_n": w_n,
        "worker_peak": w_peak,
        "req_peak": r_peak,
        "site": site,
    })
    if req_n >= 2:
        print(
            f"[DB] CHECKOUT_NEST pid={os.getpid()} path={path} req_n={req_n} "
            f"worker_n={w_n} from={site}",
            flush=True,
        )


def _checkout_diag_on_return(conn) -> None:
    global _worker_hold_n
    if not _CHECKOUT_DIAG:
        return
    t0 = getattr(conn, "_checkout_t0", None)
    dur_ms = round((time.time() - t0) * 1000.0, 1) if t0 else None
    tracker = _borrowed_conns_cv.get()
    path = "?"
    req_n = 0
    if tracker is not None:
        path = getattr(tracker, "endpoint", "?") or "?"
        try:
            req_n = tracker.registered_count() if hasattr(tracker, "registered_count") else len(tracker.still_registered())
        except Exception:
            req_n = 0
    site = getattr(conn, "_borrowed_from", "?")
    with _worker_hold_lock:
        if _worker_hold_n > 0:
            _worker_hold_n -= 1
        w_n = _worker_hold_n
        w_peak = _worker_hold_peak
    _checkout_diag_write({
        "ev": "-",
        "path": path,
        "req_n": req_n,
        "worker_n": w_n,
        "worker_peak": w_peak,
        "site": site,
        "dur_ms": dur_ms,
    })


def get_db_connection(request_id: str = None):
''',
    "add-checkout-diag-helpers",
)

once(
    '''        tracker = _borrowed_conns_cv.get()
        if tracker is not None and hasattr(tracker, "register"):
            try:
                tracker.register(wrapped)
            except Exception:
                pass
        return wrapped
''',
    '''        tracker = _borrowed_conns_cv.get()
        if tracker is not None and hasattr(tracker, "register"):
            try:
                tracker.register(wrapped)
            except Exception:
                pass
        try:
            _checkout_diag_on_get(wrapped)
        except Exception:
            pass
        return wrapped
''',
    "get-db-diag-hook",
)

once(
    '''    if put_ok:
        tracker = _borrowed_conns_cv.get()
        if tracker is not None and hasattr(tracker, "unregister"):
            try:
                tracker.unregister(conn, real)
            except Exception:
                pass
''',
    '''    if put_ok:
        tracker = _borrowed_conns_cv.get()
        if tracker is not None and hasattr(tracker, "unregister"):
            try:
                tracker.unregister(conn, real)
            except Exception:
                pass
        try:
            _checkout_diag_on_return(conn)
        except Exception:
            pass
''',
    "return-db-diag-hook",
)

if text.count("_checkout_diag_on_get") != 2:
    raise SystemExit("diag get hook count")
if text.count("_checkout_diag_on_return") != 2:
    raise SystemExit("diag return hook count")
if text.count("def get_db_connection") != 1:
    raise SystemExit("get_db count")

SRC.write_text(text, encoding="utf-8")
print(f"WROTE {SRC} lines={text.count(chr(10))}")
