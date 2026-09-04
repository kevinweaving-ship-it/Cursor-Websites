#!/usr/bin/env python3
from pathlib import Path
import py_compile
import subprocess
import time

p = Path("/var/www/sailingsa/api/api.py")
t = p.read_text(encoding="utf-8", errors="replace")
old = '''                    "had_open": False,
                    "had_select": False,
                    "had_submit": False,'''
new = '''                    "had_open": False,
                    "had_select": False,
                    "had_form_open": False,
                    "had_submit": False,'''
if '"had_form_open": False' in t:
    print("already inited")
elif old not in t:
    raise SystemExit("missing init")
else:
    p.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("inited")
py_compile.compile(str(p), doraise=True)
print("SYNTAX_OK")
subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
time.sleep(2)
print(subprocess.check_output(["systemctl", "is-active", "sailingsa-api"], text=True).strip())
