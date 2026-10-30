#!/usr/bin/env python3
"""Clarify who-tried vs profile-already-owned on claim popup."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
t = API.read_text(encoding="utf-8", errors="replace")
bak = Path(f"/root/backups/api.py.claim_who_owner.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(API, bak)
print("BACKUP", bak)

old = '''            # Fill who from account when this sailor is already registered (identity for you)
            acc = account_by_sas.get(a.get("sailor_sas_id") or "") or {}
            if (not a.get("who_email")) and acc.get("email"):
                em = acc["email"]
                a["who_email"] = em
                try:
                    local, dom = em.split("@", 1)
                    a["who"] = (local[:1] + "***@" + dom) if local else em
                except Exception:
                    a["who"] = em
                if acc.get("name"):
                    a["who"] = acc["name"] + " (" + a["who"] + ")"
            elif (not a.get("who_email")) and acc.get("name") and a.get("on_users"):
                a["who"] = acc["name"] + " (already a member)"

            # Outcome = what THIS visit did — not whether the sailor profile is already claimed
            if a["had_ok"]:
                a["outcome"] = "succeeded"
                a["status"] = "Became a member"
                a["problem"] = "None — they signed up"
            elif a["had_fail"]:
                a["outcome"] = "failed"
                a["status"] = "Tried to sign up — blocked"
                a["problem"] = a.get("fail_why") or "Sign-up failed (see error)"
            elif a["had_submit"]:
                a["outcome"] = "failed"
                a["status"] = "Submitted form — no account created"
                a["problem"] = a.get("fail_why") or "Form sent but no success recorded — likely a server/sign-up bug"
            elif a["had_select"] or a["had_open"]:
                a["outcome"] = "left"
                a["status"] = "Opened claim, then left"
                if a.get("on_users"):
                    a["problem"] = "Opened claim but never submitted — this sailor is already a member on /users (they should Sign in)"
                else:
                    a["problem"] = "Never filled in / submitted the sign-up form (clicked away)"
            else:
                continue  # ignore junk
            if not a.get("entry_how"):
                a["entry_how"] = "Sign-up / claim"
            if a.get("who") in ("", "Someone", "Didn't leave email") and not a.get("who_email"):
                a["who"] = "Didn't leave email"'''

new = '''            acc = account_by_sas.get(a.get("sailor_sas_id") or "") or {}
            owner_label = ""
            if acc.get("name") or acc.get("email"):
                owner_label = (acc.get("name") or "").strip()
                if acc.get("email"):
                    try:
                        local, dom = acc["email"].split("@", 1)
                        em_show = (local[:1] + "***@" + dom) if local else acc["email"]
                    except Exception:
                        em_show = acc["email"]
                    owner_label = (owner_label + " · " + em_show).strip(" ·") if owner_label else em_show
            a["profile_owner"] = owner_label

            # Outcome = what THIS visit did — not whether the sailor profile is already claimed
            if a["had_ok"]:
                a["outcome"] = "succeeded"
                a["status"] = "Became a member"
                a["problem"] = "None — they signed up"
                # If funnel had no email, show the new member from /users
                if (not a.get("who_email")) and owner_label:
                    a["who"] = owner_label
            elif a["had_fail"]:
                a["outcome"] = "failed"
                a["status"] = "Tried to sign up — blocked"
                a["problem"] = a.get("fail_why") or "Sign-up failed (see error)"
            elif a["had_submit"]:
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
                    a["problem"] = "Never filled in / submitted the sign-up form (clicked away)"
            else:
                continue  # ignore junk
            if not a.get("entry_how"):
                a["entry_how"] = "Sign-up / claim"
            if not a.get("who_email"):
                # Visitor identity unknown unless they typed email on the form
                a["who"] = "Didn't leave email"'''

if old not in t:
    raise SystemExit("anchor missing")
t = t.replace(old, new, 1)

# JS: show owner hint under who when present and who is unknown
old_js = '''        var who=esc(r.who||"Someone");
        var sn=esc(r.sailor_name||"Unknown sailor");'''
new_js = '''        var who=esc(r.who||"Didn't leave email");
        if(r.profile_owner && String(r.who||"").indexOf("Didn't leave")===0 && r.on_users){
          who += "<div class='note' style='margin:2px 0 0'>profile already owned by "+esc(r.profile_owner)+"</div>";
        }
        var sn=esc(r.sailor_name||"Unknown sailor");'''
if old_js not in t:
    raise SystemExit("js who anchor missing")
t = t.replace(old_js, new_js, 1)

API.write_text(t, encoding="utf-8")
print("OK")
