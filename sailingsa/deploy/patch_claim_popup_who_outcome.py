#!/usr/bin/env python3
"""Fix claim popup: outcome = this visit succeeded (not sailor already on /users);
   who = email / account name / 'Didn't leave email' (no visitor hex)."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
t = API.read_text(encoding="utf-8", errors="replace")
bak = Path(f"/root/backups/api.py.claim_who_outcome.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(API, bak)
print("BACKUP", bak)

# --- 1) who without email: plain English, no hex ---
old_who = '''                else:
                    who_show = "Someone"
                    if person and person != "anon":
                        who_show = "Someone (" + person[-6:] + ")"
                a = {
                    "when": r.get("occurred_at") or "",
                    "visitor_id": person,
                    "who": who_show,
                    "who_email": who,'''

new_who = '''                else:
                    # No email yet — don't show cryptic visitor ids
                    who_show = "Didn't leave email"
                a = {
                    "when": r.get("occurred_at") or "",
                    "visitor_id": person,
                    "who": who_show,
                    "who_email": who,'''

if old_who not in t:
    raise SystemExit("who anchor missing")
t = t.replace(old_who, new_who, 1)

# --- 2) outcome: only had_ok = became member; on_users is separate fact ---
old_out = '''        attempts = []
        for a in attempts_map.values():
            if a["had_ok"] or a.get("on_users"):
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
                a["problem"] = "Never filled in / submitted the sign-up form (clicked away)"
            else:
                continue  # ignore junk
            if not a.get("entry_how"):
                a["entry_how"] = "Sign-up / claim"
            # Drop probe leftovers
            if "probe" in (a.get("sailor_name") or "").lower():
                continue
            attempts.append(a)'''

new_out = '''        # Resolve account holder name/email for sailors already on /users
        account_by_sas = {}
        try:
            need = [a.get("sailor_sas_id") for a in attempts_map.values() if a.get("sailor_sas_id") and a.get("on_users")]
            need = list({x for x in need if x})
            if need:
                cur.execute(
                    """
                    SELECT sas_id::text,
                           COALESCE(NULLIF(TRIM(email), ''), '') AS email,
                           TRIM(COALESCE(
                             NULLIF(TRIM(full_name), ''),
                             NULLIF(TRIM(COALESCE(first_name,'') || ' ' || COALESCE(last_name,'')), ''),
                             '')) AS name
                    FROM public.user_accounts
                    WHERE sas_id::text = ANY(%s)
                    """,
                    (need,),
                )
                for rr in cur.fetchall() or []:
                    if isinstance(rr, dict):
                        sid = str(rr.get("sas_id") or "")
                        account_by_sas[sid] = {
                            "email": str(rr.get("email") or "").strip(),
                            "name": str(rr.get("name") or "").strip(),
                        }
                    else:
                        account_by_sas[str(rr[0] or "")] = {
                            "email": str(rr[1] or "").strip(),
                            "name": str(rr[2] or "").strip(),
                        }
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            account_by_sas = {}

        attempts = []
        for a in attempts_map.values():
            # Fill who from account when this sailor is already registered (identity for you)
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
                a["who"] = "Didn't leave email"
            # Drop probe leftovers
            if "probe" in (a.get("sailor_name") or "").lower():
                continue
            attempts.append(a)'''

if old_out not in t:
    raise SystemExit("outcome anchor missing")
t = t.replace(old_out, new_out, 1)

# --- 3) modal note + on_users column wording in JS ---
old_js_note = '''      html+="<p class='note'>Read <b>Problem</b> to see what to fix. “Left” is not a bug — they abandoned. “Blocked” is a real sign-up issue.</p>";
      html+="<div class='table-scroll'><table><thead><tr><th>When</th><th>Who tried</th><th>Sailor they wanted</th><th>How they started</th><th>Status</th><th>Problem (plain English)</th><th>Member on /users?</th></tr></thead><tbody>";'''

new_js_note = '''      html+="<p class='note'><b>Blocked</b> = real sign-up problem (fix it). <b>Left</b> = opened claim then walked away (not a bug). <b>Who tried</b> = email/name if they typed one; older visits often show “Didn't leave email” — use the Sailor column. <b>Already on /users?</b> = that sailor profile already has a member account (they should Sign in, not Claim).</p>";
      html+="<div class='table-scroll'><table><thead><tr><th>When</th><th>Who tried</th><th>Sailor they wanted</th><th>How they started</th><th>Status</th><th>Problem (plain English)</th><th>Already on /users?</th></tr></thead><tbody>";'''

if old_js_note not in t:
    raise SystemExit("js note anchor missing")
t = t.replace(old_js_note, new_js_note, 1)

old_users_cell = '''        var onU=r.on_users?"<a href='/users' target='_blank' rel='noopener'><b>Yes</b></a>":"No";'''
new_users_cell = '''        var onU=r.on_users?"<a href='/users' target='_blank' rel='noopener'><b>Yes — already a member</b></a>":"No";'''
if old_users_cell not in t:
    raise SystemExit("onU anchor missing")
t = t.replace(old_users_cell, new_users_cell, 1)

# modal title
old_title = "Claim / sign-up — who tried & why it failed"
new_title = "Claim / sign-up — who tried, which sailor, what went wrong"
if old_title in t:
    t = t.replace(old_title, new_title, 1)

API.write_text(t, encoding="utf-8")
print("OK")
