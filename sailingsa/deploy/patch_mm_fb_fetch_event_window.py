#!/usr/bin/env python3
"""Idempotent live patch: skip Cape MM fetch when the event is past; reuse one Chrome profile."""
from pathlib import Path

p = Path("/var/www/sailingsa/deploy/mm_fb_fetch_cape.py")
s = p.read_text(encoding="utf-8")
orig = s

marker = 'CHROME = "/usr/bin/google-chrome"'
insert = '''CHROME = "/usr/bin/google-chrome"
CHROME_PROFILE = Path("/var/tmp/ssa-mm-chrome")'''
if "CHROME_PROFILE" not in s:
    if marker not in s:
        raise SystemExit("CHROME marker missing")
    s = s.replace(marker, insert, 1)

old_dump = '''def dump(url: str, budget_ms: int = 9000) -> str:
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--virtual-time-budget={budget_ms}",
        "--timeout=16000",
        f"--user-agent={UA}",
        "--dump-dom",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=50)
    return proc.stdout or ""
'''
new_dump = '''def dump(url: str, budget_ms: int = 9000) -> str:
    CHROME_PROFILE.mkdir(parents=True, exist_ok=True)
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--user-data-dir={CHROME_PROFILE}",
        "--disk-cache-size=67108864",
        f"--virtual-time-budget={budget_ms}",
        "--timeout=16000",
        f"--user-agent={UA}",
        "--dump-dom",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=50)
    return proc.stdout or ""
'''
if "--user-data-dir=" not in s:
    if old_dump not in s:
        raise SystemExit("dump() block not found")
    s = s.replace(old_dump, new_dump, 1)

old_main = '''def main() -> int:
    fetched = fetch()
'''
new_main = '''def main() -> int:
    try:
        from mm_fb_event_window import event_is_active, skip_payload, sync_cape_fb_timers

        if not event_is_active():
            sync_cape_fb_timers(False)
            print(json.dumps(skip_payload()))
            return 0
    except Exception as e:
        print(f"[mm_fb] event window: {e}", flush=True)
    fetched = fetch()
'''
if "event_is_active()" not in s:
    if old_main not in s:
        raise SystemExit("main() block not found")
    s = s.replace(old_main, new_main, 1)

if s == orig:
    print("fetch already patched")
else:
    bak = p.with_suffix(p.suffix + ".bak-event-window")
    if not bak.exists():
        bak.write_text(orig, encoding="utf-8")
    p.write_text(s, encoding="utf-8")
    print("patched", p)
