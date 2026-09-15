#!/usr/bin/env python3
"""Idempotent live patch: event-window skip + delete Chrome profile after each peek."""
from pathlib import Path

p = Path("/var/www/sailingsa/deploy/mm_fb_fetch_cape.py")
s = p.read_text(encoding="utf-8")
orig = s

new_dump = '''def dump(url: str, budget_ms: int = 9000) -> str:
    """Peek at a Facebook page, then delete this check's Chrome folder."""
    from mm_fb_event_window import chrome_env, delete_chrome_run_dir, make_chrome_run_dir

    profile = make_chrome_run_dir()
    try:
        cmd = [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            f"--user-data-dir={profile}",
            "--disk-cache-size=1",
            f"--virtual-time-budget={budget_ms}",
            "--timeout=16000",
            f"--user-agent={UA}",
            "--dump-dom",
            url,
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=50, env=chrome_env(profile)
        )
        return proc.stdout or ""
    finally:
        delete_chrome_run_dir(profile)
'''

start = s.find("def dump(url:")
if start < 0:
    raise SystemExit("dump() not found")
end = s.find("\n\ndef ", start)
if end < 0:
    raise SystemExit("dump() end not found")
s = s[:start] + new_dump.rstrip() + s[end:]

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
    bak = p.with_suffix(p.suffix + ".bak-chrome-delete")
    if not bak.exists():
        bak.write_text(orig, encoding="utf-8")
    p.write_text(s, encoding="utf-8")
    print("patched", p)
