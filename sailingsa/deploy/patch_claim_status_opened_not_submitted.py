#!/usr/bin/env python3
"""registration_started is NOT a form submit — stop false 'Submitted form' labels."""
from pathlib import Path
import shutil
import time
import py_compile

API = Path("/var/www/sailingsa/api/api.py")
ts = time.strftime("%Y%m%d_%H%M%S")
bak = Path(f"/root/backups/api_claim_opened_not_submitted_{ts}.py")
shutil.copy2(API, bak)
print("BACKUP", bak)
t = API.read_text(encoding="utf-8", errors="replace")

old = '''            if sk in ("submission_attempted", "registration_started"):
                a["had_submit"] = True'''
new = '''            if sk == "registration_started":
                a["had_form_open"] = True
            if sk == "submission_attempted":
                a["had_submit"] = True'''
if old not in t:
    raise SystemExit("missing had_submit anchor")
t = t.replace(old, new)
print("ok had_submit split")

# Ensure attempts_map init includes had_form_open
# Find where had_submit is initialized
init_old = None
for cand in [
    '"had_submit": False',
    "'had_submit': False",
]:
    if cand in t:
        print("init cand", cand, t.count(cand))

# Add had_form_open next to had_submit in dict init — may appear once in claim attempts
if '"had_submit": False' in t and '"had_form_open"' not in t:
    t = t.replace('"had_submit": False', '"had_form_open": False, "had_submit": False', 1)
    print("ok init had_form_open")
elif "'had_submit': False" in t and "had_form_open" not in t.split("had_submit")[0][-200:]:
    # try once
    t = t.replace("'had_submit': False", "'had_form_open': False, 'had_submit': False", 1)
    print("ok init had_form_open sq")

old2 = '''            elif a["had_submit"]:
                a["outcome"] = "failed"
                a["status"] = "Submitted form — no account created"
                base = a.get("fail_why") or "Form sent but no success recorded — likely a server/sign-up bug"
                if a.get("on_users") and owner_label:
                    a["problem"] = base + " — sailor already listed on /users as " + owner_label
                else:
                    a["problem"] = base
            elif a["had_select"] or a["had_open"]:
                a["outcome"] = "left"
                a["status"] = "Opened claim, then left"
                if a.get("on_users") and owner_label:
                    a["problem"] = (
                        "Never submitted — this sailor is already a member ("
                        + owner_label
                        + "). They should Sign in, not Claim."
                    )
                elif a.get("on_users"):
                    a["problem"] = "Never submitted — this sailor is already a member on /users (they should Sign in)"
                else:
                    a["problem"] = "Never filled in / submitted the sign-up form (clicked away)"'''

new2 = '''            elif a["had_submit"]:
                a["outcome"] = "failed"
                a["status"] = "Submitted form — no account created"
                base = a.get("fail_why") or "Form sent but no success recorded — likely a server/sign-up bug"
                if a.get("on_users") and owner_label:
                    a["problem"] = base + " — sailor already listed on /users as " + owner_label
                else:
                    a["problem"] = base
            elif a.get("had_form_open"):
                a["outcome"] = "left"
                a["status"] = "Opened form, didn't finish"
                a["problem"] = "Opened the sign-up form but left before creating an account (did not tap Complete)"
            elif a["had_select"] or a["had_open"]:
                a["outcome"] = "left"
                a["status"] = "Opened claim, then left"
                if a.get("on_users") and owner_label:
                    a["problem"] = (
                        "Never submitted — this sailor is already a member ("
                        + owner_label
                        + "). They should Sign in, not Claim."
                    )
                elif a.get("on_users"):
                    a["problem"] = "Never submitted — this sailor is already a member on /users (they should Sign in)"
                else:
                    a["problem"] = "Never filled in / submitted the sign-up form (clicked away)"'''

if old2 not in t:
    raise SystemExit("missing outcome branch anchor")
t = t.replace(old2, new2, 1)
print("ok outcome opened-form branch")

API.write_text(t, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print("SYNTAX_OK")
