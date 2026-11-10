#!/usr/bin/env python3
"""Claim popup: members first; clear who/how/when for successful sign-ups."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
t = API.read_text(encoding="utf-8", errors="replace")
bak = Path(f"/root/backups/api.py.claim_members_first.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(API, bak)
print("BACKUP", bak)

# --- Prefer real email/google rows when loading accounts_in_range ---
old_acc = '''            cur.execute(
                """
                SELECT DISTINCT ON (sas_id::text)
                       sas_id::text AS sas_id,
                       COALESCE(NULLIF(TRIM(email), ''), '') AS email,
                       TRIM(COALESCE(
                         NULLIF(TRIM(full_name), ''),
                         NULLIF(TRIM(COALESCE(first_name,'') || ' ' || COALESCE(last_name,'')), ''),
                         '')) AS name,
                       COALESCE(NULLIF(TRIM(login_method), ''), 'sign-up') AS login_method,
                       created_at
                FROM public.user_accounts
                WHERE sas_id IS NOT NULL
                  AND sas_id::text NOT IN """ + _LEAN_TRAFFIC_STAFF_SAS_SQL + """
                  AND COALESCE(role,'') <> 'super_admin'
                  AND """ + since_acc + """
                ORDER BY sas_id::text, created_at DESC
                """,
                params_acc,
            )
'''

new_acc = '''            cur.execute(
                """
                SELECT DISTINCT ON (sas_id::text)
                       sas_id::text AS sas_id,
                       COALESCE(NULLIF(TRIM(email), ''), '') AS email,
                       TRIM(COALESCE(
                         NULLIF(TRIM(full_name), ''),
                         NULLIF(TRIM(COALESCE(first_name,'') || ' ' || COALESCE(last_name,'')), ''),
                         '')) AS name,
                       COALESCE(NULLIF(TRIM(login_method), ''), 'sign-up') AS login_method,
                       created_at
                FROM public.user_accounts
                WHERE sas_id IS NOT NULL
                  AND sas_id::text NOT IN """ + _LEAN_TRAFFIC_STAFF_SAS_SQL + """
                  AND COALESCE(role,'') <> 'super_admin'
                  AND """ + since_acc + """
                ORDER BY sas_id::text,
                  CASE lower(COALESCE(login_method,''))
                    WHEN 'google' THEN 0
                    WHEN 'facebook' THEN 1
                    WHEN 'email' THEN 2
                    WHEN 'whatsapp' THEN 3
                    WHEN 'sas_id' THEN 4
                    ELSE 5
                  END,
                  CASE WHEN NULLIF(TRIM(email),'') IS NULL THEN 1 ELSE 0 END,
                  created_at DESC
                """,
                params_acc,
            )
'''

if old_acc not in t:
    raise SystemExit("accounts_in_range SQL missing")
t = t.replace(old_acc, new_acc, 1)
print("OK prefer google/email rows")

# --- Richer success problem/entry + sort members first ---
old_prob = '''            problem = "Signed up successfully via " + method_plain + " — on /users"
            existing = by_sas.get(sid)
            if existing:
                existing["outcome"] = "succeeded"
                existing["status"] = "Became a member"
                existing["problem"] = problem
                existing["on_users"] = True
                existing["who"] = who
                existing["who_email"] = email
                existing["profile_owner"] = who
                if created_iso:
                    existing["when"] = created_iso
                if href:
                    existing["sailor_href"] = href
                if sname:
                    existing["sailor_name"] = sname
            else:
                attempts.append({
                    "when": created_iso,
                    "visitor_id": "account:" + sid,
                    "who": who,
                    "who_email": email,
                    "sailor_name": sname,
                    "sailor_href": href,
                    "sailor_sas_id": sid,
                    "entry_how": "Signed up (" + method_plain + ")",
                    "searched_for": "",
                    "outcome": "succeeded",
                    "status": "Became a member",
                    "problem": problem,
                    "on_users": True,
                    "profile_owner": who,
                })
                by_sas[sid] = attempts[-1]

        rank = {"failed": 0, "left": 1, "succeeded": 2}
        attempts.sort(key=lambda x: (rank.get(x.get("outcome") or "left", 9), -_ts_key(x.get("when"))))
'''

new_prob = '''            when_human = ""
            try:
                if hasattr(created, "strftime"):
                    when_human = created.strftime("%d %b %Y at %H:%M")
                elif created_iso:
                    when_human = created_iso.replace("T", " ")[:16]
            except Exception:
                when_human = (created_iso or "")[:16]
            problem = (
                "Signed up "
                + (when_human + " " if when_human else "")
                + "via "
                + method_plain
                + (" · " + _mask_email(email) if email else "")
                + " — on /users"
            )
            entry_how = "Signed up with " + method_plain
            # Prefer sailor personal name when account name empty (Alex/Andrew)
            if (not name or name.lower() in ("new member", "fomo 4750")) and acc_names.get(sid):
                sname = acc_names.get(sid) or sname
            if (who.startswith("New member") or not name) and sname and sname.lower() != "new member":
                who = sname + ((" (" + _mask_email(email) + ")") if email else "")
            existing = by_sas.get(sid)
            if existing:
                existing["outcome"] = "succeeded"
                existing["status"] = "Became a member"
                existing["problem"] = problem
                existing["how_signed_up"] = method_plain
                existing["signed_up_at"] = created_iso
                existing["on_users"] = True
                existing["who"] = who
                existing["who_email"] = email
                existing["profile_owner"] = who
                existing["entry_how"] = entry_how
                if created_iso:
                    existing["when"] = created_iso
                if href:
                    existing["sailor_href"] = href
                if sname:
                    existing["sailor_name"] = sname
            else:
                attempts.append({
                    "when": created_iso,
                    "visitor_id": "account:" + sid,
                    "who": who,
                    "who_email": email,
                    "sailor_name": sname,
                    "sailor_href": href,
                    "sailor_sas_id": sid,
                    "entry_how": entry_how,
                    "searched_for": "",
                    "outcome": "succeeded",
                    "status": "Became a member",
                    "problem": problem,
                    "how_signed_up": method_plain,
                    "signed_up_at": created_iso,
                    "on_users": True,
                    "profile_owner": who,
                })
                by_sas[sid] = attempts[-1]

        # Members first (what you care about), then blocked, then left
        rank = {"succeeded": 0, "failed": 1, "left": 2}
        attempts.sort(key=lambda x: (rank.get(x.get("outcome") or "left", 9), -_ts_key(x.get("when"))))
'''

if old_prob not in t:
    raise SystemExit("success problem block missing")
t = t.replace(old_prob, new_prob, 1)
print("OK members first + how signed up")

# --- Popup UI: members section on top ---
old_js = '''      html+="<p class='note'><b>Blocked</b> = real sign-up problem (fix it). <b>Left</b> = opened claim then walked away (not a bug). <b>Who tried</b> = email/name if they typed one; older visits often show “Didn't leave email” — use the Sailor column. <b>Already on /users?</b> = that sailor profile already has a member (they should Sign in, not Claim).</p>";
      html+="<div class='table-scroll'><table><thead><tr><th>When</th><th>Who tried</th><th>Sailor they wanted</th><th>How they started</th><th>Status</th><th>Problem (plain English)</th><th>Already on /users?</th></tr></thead><tbody>";
      attempts.forEach(function(r){
        var when=String(r.when||"").replace("T"," ").slice(0,19);
        var who=esc(r.who||"Didn't leave email");
        if(r.profile_owner && String(r.who||"").indexOf("Didn't leave")===0 && r.on_users){
          who += "<div class='note' style='margin:2px 0 0'>profile already owned by "+esc(r.profile_owner)+"</div>";
        }
        var sn=esc(r.sailor_name||"Unknown sailor");
        if(r.sailor_href) sn="<a href='"+esc(r.sailor_href)+"' target='_blank' rel='noopener'>"+sn+"</a>";
        if(r.searched_for) sn+="<div class='note' style='margin:2px 0 0'>searched “"+esc(r.searched_for)+"”</div>";
        var oc=r.outcome||"left";
        var badge=oc==="succeeded"?"ok":(oc==="failed"?"fail":"open");
        var onU=r.on_users?"<a href='/users' target='_blank' rel='noopener'><b>Yes — already a member</b></a>":"No";
        html+="<tr><td>"+esc(when)+"</td><td>"+who+"</td><td>"+sn+"</td><td>"+esc(r.entry_how||"—")+"</td><td><span class='badge "+badge+"'>"+esc(r.status||oc)+"</span></td><td><b>"+esc(r.problem||"—")+"</b></td><td>"+onU+"</td></tr>";
      });
      html+="</tbody></table></div>";
'''

# The current JS might differ slightly - find and replace flexibly
marker = 'attempts.forEach(function(r){'
if marker not in t or "Became a member" not in t:
    print("looking for modal render...")

# Simpler: replace thead and add sort note; change forEach to render members first (already sorted)
old_note_js = '''      html+="<p class='note'><b>Blocked</b> = real sign-up problem (fix it). <b>Left</b> = opened claim then walked away (not a bug). <b>Who tried</b> = email/name if they typed one; older visits often show “Didn't leave email” — use the Sailor column. <b>Already on /users?</b> = that sailor profile already has a member (they should Sign in, not Claim).</p>";
'''
# try alternate quotes
found = False
for cand in [
    old_note_js,
    '''      html+="<p class='note'>Read <b>Problem</b> to see what to fix. “Left” is not a bug — they abandoned. “Blocked” is a real sign-up issue.</p>";
''',
]:
    if cand in t:
        t = t.replace(cand, '''      html+="<p class='note'><b>Members are listed first</b> — how they signed up (Google / email / WhatsApp) and when. Then blocked (real failures). Then left (opened claim, never submitted). Alex Schon / Andrew Scott signed up in Feb — pick <b>Ever</b> to see them; Robyn Patrick is in last 30 days via Google. Members also appear on <a href='/users' target='_blank' rel='noopener'>/users</a>.</p>";
''', 1)
        found = True
        print("OK modal note")
        break
if not found:
    # insert after kpi grid closing
    needle = 'html+="</div>";\n      html+="<p class=\'note\'>'
    if needle in t:
        print("WARN using partial note replace")
    else:
        print("WARN modal note not found — dump nearby")
        i = t.find("loadClaimAttemptDetails")
        print(t[i:i+2500][:1500])

# Improve row: show how_signed_up under entry
old_row = '''        html+="<tr><td>"+esc(when)+"</td><td>"+who+"</td><td>"+sn+"</td><td>"+esc(r.entry_how||"—")+"</td><td><span class='badge "+badge+"'>"+esc(r.status||oc)+"</span></td><td><b>"+esc(r.problem||"—")+"</b></td><td>"+onU+"</td></tr>";
'''
new_row = '''        var how=esc(r.entry_how||"—");
        if(r.how_signed_up) how="<b>"+esc(r.how_signed_up)+"</b><div class='note' style='margin:2px 0 0'>"+esc(r.entry_how||"")+"</div>";
        html+="<tr"+(oc==="succeeded"?" style='background:#f0fdf4'":"")+"><td>"+esc(when)+"</td><td>"+who+"</td><td>"+sn+"</td><td>"+how+"</td><td><span class='badge "+badge+"'>"+esc(r.status||oc)+"</span></td><td><b>"+esc(r.problem||"—")+"</b></td><td>"+onU+"</td></tr>";
'''
if old_row not in t:
    raise SystemExit("row render missing")
t = t.replace(old_row, new_row, 1)
print("OK row how_signed_up")

# Summary text already ok; bump members wording
old_sum = '''                "summary": (
                    f"{n_fail} blocked while signing up · {n_left} opened claim then left · {n_ok} became members"
                ),
'''
new_sum = '''                "summary": (
                    f"{n_ok} became members · {n_fail} blocked · {n_left} opened claim then left"
                ),
'''
if old_sum in t:
    t = t.replace(old_sum, new_sum, 1)
    print("OK summary members first")

API.write_text(t, encoding="utf-8")
print("DONE")
