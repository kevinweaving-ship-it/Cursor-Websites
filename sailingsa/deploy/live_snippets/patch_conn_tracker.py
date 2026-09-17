#!/usr/bin/env python3
"""Replace ContextVar list tracking with a request-owned thread-safe tracker."""
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
    '''_db_tls = threading.local()
_borrowed_conns_cv = contextvars.ContextVar("ssa_borrowed_conns", default=None)
''',
    '''_db_tls = threading.local()
_borrowed_conns_cv = contextvars.ContextVar("ssa_borrowed_conns", default=None)


class _RequestConnTracker:
    """One object per HTTP request. ContextVar holds this object so
    threadpool copies share the same registry (not a replaced list).
    """

    def __init__(self, req_id: str, endpoint: str):
        self.req_id = req_id
        self.endpoint = endpoint
        self._lock = threading.Lock()
        self._wrappers = {}

    def register(self, wrapped) -> None:
        if wrapped is None:
            return
        with self._lock:
            self._wrappers[id(wrapped)] = wrapped

    def unregister(self, conn, real=None) -> None:
        if conn is None and real is None:
            return
        with self._lock:
            drop = [
                k
                for k, w in self._wrappers.items()
                if w is conn or (real is not None and getattr(w, "_conn", None) is real)
            ]
            for k in drop:
                self._wrappers.pop(k, None)

    def still_registered(self):
        with self._lock:
            return list(self._wrappers.values())
''',
    "add-tracker-class",
)

once(
    '''        wrapped = _ConnectionWrapper(conn)
        try:
            wrapped._borrowed_from = _borrow_site()
        except Exception:
            wrapped._borrowed_from = "?"
        borrowed = _borrowed_conns_cv.get()
        if borrowed is None:
            borrowed = []
            _borrowed_conns_cv.set(borrowed)
        borrowed.append(wrapped)
        _db_tls.borrowed_conns = borrowed
        return wrapped
''',
    '''        wrapped = _ConnectionWrapper(conn)
        try:
            wrapped._borrowed_from = _borrow_site()
        except Exception:
            wrapped._borrowed_from = "?"
        tracker = _borrowed_conns_cv.get()
        if tracker is not None and hasattr(tracker, "register"):
            try:
                tracker.register(wrapped)
            except Exception:
                pass
        return wrapped
''',
    "get-db-register",
)

once(
    '''    if hasattr(conn, "_returned"):
        conn._returned = True
    real = getattr(conn, "_conn", conn)
    for borrowed in (_borrowed_conns_cv.get(), getattr(_db_tls, "borrowed_conns", None)):
        if isinstance(borrowed, list):
            try:
                borrowed[:] = [
                    w for w in borrowed
                    if w is not conn and getattr(w, "_conn", None) is not real
                ]
            except Exception:
                try:
                    while conn in borrowed:
                        borrowed.remove(conn)
                except Exception:
                    pass
    from_pool = hasattr(conn, "_conn")
    try:
        if not getattr(real, "closed", 1):
            real.rollback()
    except Exception:
        pass
    if from_pool and DB_POOL:
        try:
            if getattr(real, "closed", 1):
                DB_POOL.putconn(real, close=True)
            else:
                DB_POOL.putconn(real)
            if hasattr(conn, "_put_done"):
                conn._put_done = True
            else:
                try:
                    conn._put_done = True
                except Exception:
                    pass
        except Exception as e:
            print(f"[DB] Error returning connection to pool: {e}", flush=True)
            try:
                real.close()
            except Exception:
                pass
    else:
        try:
            real.close()
        except Exception:
            pass
        try:
            conn._put_done = True
        except Exception:
            pass
''',
    '''    if hasattr(conn, "_returned"):
        conn._returned = True
    real = getattr(conn, "_conn", conn)
    from_pool = hasattr(conn, "_conn")
    try:
        if not getattr(real, "closed", 1):
            real.rollback()
    except Exception:
        pass
    put_ok = False
    if from_pool and DB_POOL:
        try:
            if getattr(real, "closed", 1):
                DB_POOL.putconn(real, close=True)
            else:
                DB_POOL.putconn(real)
            put_ok = True
            if hasattr(conn, "_put_done"):
                conn._put_done = True
            else:
                try:
                    conn._put_done = True
                except Exception:
                    pass
        except Exception as e:
            print(f"[DB] Error returning connection to pool: {e}", flush=True)
            try:
                real.close()
            except Exception:
                pass
    else:
        try:
            real.close()
        except Exception:
            pass
        try:
            conn._put_done = True
            put_ok = True
        except Exception:
            pass
    if put_ok:
        tracker = _borrowed_conns_cv.get()
        if tracker is not None and hasattr(tracker, "unregister"):
            try:
                tracker.unregister(conn, real)
            except Exception:
                pass
''',
    "return-db-unregister-after-put",
)

once(
    '''    _db_tls.db_query_count = 0
    _borrowed_token = _borrowed_conns_cv.set([])
    _db_tls.borrowed_conns = _borrowed_conns_cv.get()
''',
    '''    _db_tls.db_query_count = 0
    _req_tracker = _RequestConnTracker(req_id, endpoint)
    _borrowed_token = _borrowed_conns_cv.set(_req_tracker)
''',
    "middleware-create-tracker",
)

once(
    '''    finally:
        leaked = []
        for item in list(_borrowed_conns_cv.get() or []) or list(getattr(_db_tls, "borrowed_conns", []) or []):
            if getattr(item, "_returned", False) and getattr(item, "_put_done", False):
                continue
            leaked.append(item)
        if leaked:
            sites = [getattr(c, "_borrowed_from", "?") for c in leaked]
            print(f"[DB] reclaiming {len(leaked)} leaked conn(s) after {endpoint} from={sites}", flush=True)
            for c in leaked:
                try:
                    return_db_connection(c)
                except Exception:
                    pass
        try:
            _borrowed_conns_cv.reset(_borrowed_token)
        except Exception:
            pass
        _db_tls.borrowed_conns = None
''',
    '''    finally:
        leaked = []
        for item in _req_tracker.still_registered():
            if getattr(item, "_returned", False) and getattr(item, "_put_done", False):
                try:
                    _req_tracker.unregister(item, getattr(item, "_conn", None))
                except Exception:
                    pass
                continue
            leaked.append(item)
        if leaked:
            sites = [getattr(c, "_borrowed_from", "?") for c in leaked]
            print(
                f"[DB] reclaiming {len(leaked)} leaked conn(s) after {endpoint} "
                f"tracker={_req_tracker.endpoint} from={sites}",
                flush=True,
            )
            for c in leaked:
                try:
                    return_db_connection(c)
                except Exception:
                    pass
        try:
            _borrowed_conns_cv.reset(_borrowed_token)
        except Exception:
            pass
''',
    "middleware-reclaim-local-tracker",
)

if text.count("class _RequestConnTracker") != 1:
    raise SystemExit("tracker class count")
if "borrowed.append(wrapped)" in text:
    raise SystemExit("old list append still present")
if "_db_tls.borrowed_conns" in text:
    raise SystemExit("old tls borrowed_conns still present")

SRC.write_text(text, encoding="utf-8")
print(f"WROTE {SRC} lines={text.count(chr(10))}")
