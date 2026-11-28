#!/usr/bin/env python3
"""Signup page: use 'Sign up with' (not 'Continue with') on all social/email buttons."""
from pathlib import Path
import shutil
import time

SIGNUP = Path("/var/www/sailingsa/signup.html")
ts = time.strftime("%Y%m%d_%H%M%S")
if SIGNUP.exists():
    shutil.copy2(SIGNUP, Path(f"/root/backups/signup.sign_up_with_{ts}.html"))
    print("BACKUP", ts)

html = SIGNUP.read_text(encoding="utf-8", errors="replace")

REPLACEMENTS = [
    ("Google — sign up", "Sign up with Google"),
    ("Facebook — sign up", "Sign up with Facebook"),
    ("Use email instead", "Sign up with email"),
    ("Continue with Google — fastest", "Sign up with Google — fastest"),
    ("Continue with Facebook — easy", "Sign up with Facebook — easy"),
    ("Continue with Google", "Sign up with Google"),
    ("Continue with Facebook", "Sign up with Facebook"),
    ("Please use Continue with Google", "Please use Sign up with Google"),
    ("Please try Continue with Google", "Please try Sign up with Google"),
    ("Tap Google or Facebook ↓", "Sign up with Google or Facebook ↓"),
]

for old, new in REPLACEMENTS:
    if old in html:
        html = html.replace(old, new)
        print("ok", old, "->", new)

SIGNUP.write_text(html, encoding="utf-8")
print("WROTE", SIGNUP)
