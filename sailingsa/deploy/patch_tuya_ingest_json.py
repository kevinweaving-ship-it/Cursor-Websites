#!/usr/bin/env python3
"""Harden tuya-sharing ingest so a bad JSON response cannot kill the push thread."""
from pathlib import Path

p = Path("/opt/tuya-sharing/worker.py")
s = p.read_text(encoding="utf-8")
orig = s

old_push = """        try:
            r = requests.post(INGEST_URL, json=payload, timeout=5,
                              headers={"Authorization": f"Bearer {INGEST_TOKEN}"})
            ok = r.status_code == 200 and r.json().get("ok") is True
            if not ok:
                self.push_errors += 1
                log.warning("ingest %s -> %s %s", reason, r.status_code, r.text[:200])
            else:
                with self.lock:
                    self.last_push = {"at": time.time(), "reason": reason, "ts": ts, "v": n["v"], "a": n["a"],
                                      "w": n["w"], "kwh": n["kwh"], "online": n["online"]}
            return ok
        except requests.RequestException as exc:
            self.push_errors += 1
            log.warning("ingest %s failed: %s", reason, exc)
            return False
"""
new_push = """        try:
            r = requests.post(INGEST_URL, json=payload, timeout=5,
                              headers={"Authorization": f"Bearer {INGEST_TOKEN}"})
            try:
                body = r.json() if r.content else {}
            except ValueError:
                body = {}
            ok = r.status_code == 200 and isinstance(body, dict) and body.get("ok") is True
            if not ok:
                self.push_errors += 1
                log.warning("ingest %s -> %s %s", reason, r.status_code, (r.text or "")[:200])
            else:
                with self.lock:
                    self.last_push = {"at": time.time(), "reason": reason, "ts": ts, "v": n["v"], "a": n["a"],
                                      "w": n["w"], "kwh": n["kwh"], "online": n["online"]}
            return ok
        except Exception as exc:
            self.push_errors += 1
            log.warning("ingest %s failed: %s", reason, exc)
            return False
"""
if "body = r.json() if r.content else {}" not in s:
    if old_push not in s:
        raise SystemExit("ingest block not found")
    s = s.replace(old_push, new_push, 1)

old_loop = """    def push_loop(self) -> None:
        while not self.stop.is_set():
            try:
                reason = self.push_q.get(timeout=1)
            except queue.Empty:
                continue
            self._push_now(reason)
"""
new_loop = """    def push_loop(self) -> None:
        while not self.stop.is_set():
            try:
                reason = self.push_q.get(timeout=1)
            except queue.Empty:
                continue
            try:
                self._push_now(reason)
            except Exception as exc:
                self.push_errors += 1
                log.warning("push_loop: %s", exc)
"""
if "push_loop:" not in s:
    if old_loop not in s:
        raise SystemExit("push_loop not found")
    s = s.replace(old_loop, new_loop, 1)

if s == orig:
    print("worker already patched")
else:
    bak = Path("/opt/tuya-sharing/worker.py.bak-ingest-json")
    if not bak.exists():
        bak.write_text(orig, encoding="utf-8")
    p.write_text(s, encoding="utf-8")
    print("patched", p)
