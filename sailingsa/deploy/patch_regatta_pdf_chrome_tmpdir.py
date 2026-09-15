#!/usr/bin/env python3
"""Force PDF Chrome scratch into the throwaway folder (set TMPDIR)."""
from pathlib import Path

p = Path("/var/www/sailingsa/sailingsa/backend/regatta_stored_pdf.py")
s = p.read_text(encoding="utf-8")
orig = s
old = '''        env["HOME"] = str(home)
        env["XDG_CONFIG_HOME"] = str(home / ".config")
        env["XDG_CACHE_HOME"] = str(home / ".cache")
        env["PATH"] = "/usr/bin:/bin:" + (env.get("PATH") or "")
'''
new = '''        env["HOME"] = str(home)
        env["XDG_CONFIG_HOME"] = str(home / ".config")
        env["XDG_CACHE_HOME"] = str(home / ".cache")
        tmpdir = Path(td) / "tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)
        env["TMPDIR"] = str(tmpdir)
        env["TMP"] = str(tmpdir)
        env["TEMP"] = str(tmpdir)
        env["PATH"] = "/usr/bin:/bin:" + (env.get("PATH") or "")
'''
if 'env["TMPDIR"]' in s and "ssa-regatta-pdf" in s:
    print("pdf chrome TMPDIR already set")
else:
    if old not in s:
        raise SystemExit("pdf chrome env block not found")
    s = s.replace(old, new, 1)
    bak = p.with_suffix(p.suffix + ".bak-chrome-tmpdir")
    if not bak.exists():
        bak.write_text(orig, encoding="utf-8")
    p.write_text(s, encoding="utf-8")
    print("patched", p)
