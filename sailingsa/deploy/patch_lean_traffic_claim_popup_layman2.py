#!/usr/bin/env python3
"""Make claim popup layman-clear: who, sailor, left vs blocked, why — no 'in progress' nonsense."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
SIGNUP = Path("/var/www/sailingsa/signup.html")


def must_replace(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"PATCH FAIL {label}: count={n}")
    return text.replace(old, new, 1)


DIGEST_OLD_START = "        # One layman row per person+sailor attempt (not every micro-step)\n"


NEW_DIGEST = r'''        # Layman digest: one story per person+sailor (merge noise; clear left vs blocked)
        attempts_map = {}
        for r in rows:
            meta = r.get("meta") if isinstance(r.get("meta"), dict) else {}
            sid = (r.get("sailor_sas_id") or "").strip()
            sname = (r.get("sailor_name") or "").strip() or "Unknown sailor"
            if sname.lower() in ("(test probe)", "unknown sailor") and (r.get("stable_entity_id") or "").lower() == "probe":
                continue  # ignore internal probes
            person = (r.get("visitor_id") or "").strip() or "anon"
            key = person + "|" + (sid or sname.lower())
            a = attempts_map.get(key)
            if not a:
                who = str(meta.get("email") or meta.get("who") or "").strip()
                if who and "@" in who:
                    # mask: j***@gmail.com
                    try:
                        local, dom = who.split("@", 1)
                        who_show = (local[:1] + "***@" + dom) if local else who
                    except Exception:
                        who_show = who
                else:
                    who_show = "Someone"
                    if person and person != "anon":
                        who_show = "Someone (" + person[-6:] + ")"
                a = {
                    "when": r.get("occurred_at") or "",
                    "visitor_id": person,
                    "who": who_show,
                    "who_email": who,
                    "sailor_name": sname,
                    "sailor_href": r.get("sailor_href") or "",
                    "sailor_sas_id": sid,
                    "entry_how": "",
                    "searched_for": "",
                    "had_open": False,
                    "had_select": False,
                    "had_submit": False,
                    "had_fail": False,
                    "had_ok": False,
                    "fail_why": "",
                    "outcome": "left",
                    "status": "",
                    "problem": "",
                    "on_users": bool(r.get("on_users")),
                }
                attempts_map[key] = a
            if (r.get("occurred_at") or "") >= (a.get("when") or ""):
                a["when"] = r.get("occurred_at") or a["when"]
            sk = r.get("step_key") or ""
            meta_email = str(meta.get("email") or "").strip()
            if meta_email and "@" in meta_email:
                a["who_email"] = meta_email
                try:
                    local, dom = meta_email.split("@", 1)
                    a["who"] = (local[:1] + "***@" + dom) if local else meta_email
                except Exception:
                    a["who"] = meta_email
            if sk == "claim_cta_click" or meta.get("entry") in ("sailor_claim", "claim_cta"):
                a["entry_how"] = "From sailor profile (Claim button)"
            elif meta.get("entry") in ("signup_banner", "signup", "banner") and not a["entry_how"]:
                a["entry_how"] = "From Sign-up banner (had to search)"
            elif sk == "claim_page_loaded" and not a["entry_how"]:
                if sid or (r.get("stable_entity_id") or "").isdigit():
                    a["entry_how"] = "From sailor profile (Claim button)"
                else:
                    a["entry_how"] = "Opened sign-up page"
            if sk in ("claim_page_loaded", "claim_cta_click"):
                a["had_open"] = True
            if sk in ("sailor_preselected", "sailor_selected"):
                a["had_select"] = True
            if sk == "sailor_search" and meta.get("query"):
                a["searched_for"] = str(meta.get("query"))[:80]
            if meta.get("search_query") and not a["searched_for"]:
                a["searched_for"] = str(meta.get("search_query"))[:80]
            if meta.get("sailor_name"):
                a["sailor_name"] = str(meta.get("sailor_name"))[:80]
            if sk in ("submission_attempted", "registration_started"):
                a["had_submit"] = True
            if sk in ("validation_error", "verification_failed") or r.get("outcome") == "failed":
                a["had_fail"] = True
                why = (r.get("why") or r.get("error_code") or "").strip()
                if why and why not in ("—", "In progress / no error recorded"):
                    a["fail_why"] = why
            if sk in ("account_created", "claim_completed", "verification_succeeded") and r.get("ok"):
                a["had_ok"] = True
            if r.get("on_users"):
                a["on_users"] = True
            if r.get("sailor_href"):
                a["sailor_href"] = r.get("sailor_href")

        attempts = []
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
            attempts.append(a)

        # Sort: blocked first, then left, then members; newest first within each
        rank = {"failed": 0, "left": 1, "succeeded": 2}
        attempts.sort(key=lambda x: (rank.get(x.get("outcome") or "left", 9), -_ts_key(x.get("when"))))

        n_fail = sum(1 for x in attempts if x.get("outcome") == "failed")
        n_left = sum(1 for x in attempts if x.get("outcome") == "left")
        n_ok = sum(1 for x in attempts if x.get("outcome") == "succeeded")

        return JSONResponse(
            {
                "ok": True,
                "range": range_key,
                "rows": rows,
                "attempts": attempts,
                "failures": fails,
                "successes": ok_rows,
                "count": len(rows),
                "attempt_count": len(attempts),
                "fail_count": n_fail,
                "left_count": n_left,
                "success_count": n_ok,
                "users_url": "/users",
                "users_note": "If sign-up worked, they appear on /users as a Registered User.",
                "summary": (
                    f"{n_fail} blocked while signing up · {n_left} opened claim then left · {n_ok} became members"
                ),
            },
'''

# helper must exist before digest uses it — inject near function top or inline
TS_HELPER = '''
        def _ts_key(iso):
            try:
                s = str(iso or "")
                return int("".join(ch for ch in s if ch.isdigit())[:14] or "0")
            except Exception:
                return 0

'''


NEW_JS = r'''  function loadClaimAttemptDetails(){
    var note=$("claimModalNote"), body=$("claimModalBody");
    if(note) note.textContent="Loading claim / sign-up attempts…";
    if(body) body.innerHTML="<p class='note'>Loading…</p>";
    fetchJson("/traffic/api/claim-attempts?range="+encodeURIComponent(RANGE)).then(function(d){
      if(!d || !d.ok) throw new Error((d && d.error) || "failed");
      var attempts=d.attempts||[];
      var nFail=d.fail_count||0, nLeft=d.left_count||0, nOk=d.success_count||0;
      if(note) note.innerHTML="<b>"+esc(String(d.summary||("")))+"</b><br>Range "+esc(d.range||RANGE)+". Members list: <a href='/users' target='_blank' rel='noopener'>/users</a>.";
      if(!attempts.length){
        if(body) body.innerHTML="<p class='note'>Nobody started a claim / sign-up in this range.</p>";
        return;
      }
      var html="";
      html+="<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0 0 12px'>";
      html+="<div class='kpi' style='padding:8px'><div class='l'>Blocked</div><div class='v' style='font-size:22px;color:#991b1b'>"+nFail+"</div><div class='s'>Tried form — failed</div></div>";
      html+="<div class='kpi' style='padding:8px'><div class='l'>Left</div><div class='v' style='font-size:22px'>"+nLeft+"</div><div class='s'>Opened claim, never submitted</div></div>";
      html+="<div class='kpi' style='padding:8px'><div class='l'>Members</div><div class='v' style='font-size:22px;color:#166534'>"+nOk+"</div><div class='s'>Should be on /users</div></div>";
      html+="</div>";
      html+="<p class='note'>Read <b>Problem</b> to see what to fix. “Left” is not a bug — they abandoned. “Blocked” is a real sign-up issue.</p>";
      html+="<div class='table-scroll'><table><thead><tr><th>When</th><th>Who tried</th><th>Sailor they wanted</th><th>How they started</th><th>Status</th><th>Problem (plain English)</th><th>Member on /users?</th></tr></thead><tbody>";
      attempts.forEach(function(r){
        var when=String(r.when||"").replace("T"," ").slice(0,19);
        var who=esc(r.who||"Someone");
        var sn=esc(r.sailor_name||"Unknown sailor");
        if(r.sailor_href) sn="<a href='"+esc(r.sailor_href)+"' target='_blank' rel='noopener'>"+sn+"</a>";
        if(r.searched_for) sn+="<div class='note' style='margin:2px 0 0'>searched “"+esc(r.searched_for)+"”</div>";
        var oc=r.outcome||"left";
        var badge=oc==="succeeded"?"ok":(oc==="failed"?"fail":"open");
        var onU=r.on_users?"<a href='/users' target='_blank' rel='noopener'><b>Yes</b></a>":"No";
        html+="<tr><td>"+esc(when)+"</td><td>"+who+"</td><td>"+sn+"</td><td>"+esc(r.entry_how||"—")+"</td><td><span class='badge "+badge+"'>"+esc(r.status||oc)+"</span></td><td><b>"+esc(r.problem||"—")+"</b></td><td>"+onU+"</td></tr>";
      });
      html+="</tbody></table></div>";
      if(body) body.innerHTML=html;
    }).catch(function(e){
      if(note) note.textContent="Could not load claim details.";
      if(body) body.innerHTML="<p class='err'>"+esc(String(e.message||e))+"</p>";
    });
  }
'''


def patch_api(text: str) -> str:
    # Replace from digest comment through return JSONResponse users_note block
    start = text.find(DIGEST_OLD_START)
    if start < 0:
        raise SystemExit("digest start not found")
    # Find the return JSONResponse that follows attempts digest — ends before except Exception as e:
    # Look for users_note line then closing of return
    end_marker = '"users_note": "Successful claims create a Registered User — they show on /users.",\n            },'
    end = text.find(end_marker, start)
    if end < 0:
        # maybe already changed
        end_marker = '"users_note": "Successful claims create a Registered User — they show on /users.",'
        end = text.find(end_marker, start)
        if end < 0:
            raise SystemExit("digest end not found")
        # find closing }, after
        end2 = text.find("},\n", end)
        end = end2 + 2
    else:
        end = end + len(end_marker)

    # include trailing newline after },
    while end < len(text) and text[end] in " \t":
        end += 1
    if text[end:end+1] == "\n":
        end += 1

    helper_anchor = "        fails = [x for x in rows if x.get(\"outcome\") == \"failed\"]\n        ok_rows = [x for x in rows if x.get(\"outcome\") == \"succeeded\"]\n"
    # Insert helper before digest if not present
    if "def _ts_key" not in text[start - 400 : start + 50]:
        ha = text.rfind(helper_anchor, 0, start + 10)
        if ha < 0:
            raise SystemExit("fails anchor not found")
        text = text[: ha + len(helper_anchor)] + TS_HELPER + text[ha + len(helper_anchor) :]
        start = text.find(DIGEST_OLD_START)

    end_marker = '"users_note": "Successful claims create a Registered User — they show on /users.",\n            },'
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit("digest end not found after helper")
    end = end + len(end_marker)
    if text[end:end+1] == "\n":
        end += 1

    text = text[:start] + NEW_DIGEST + "\n" + text[end:]

    # Replace modal JS
    js_start = text.find("  function loadClaimAttemptDetails(){")
    if js_start < 0:
        raise SystemExit("js not found")
    js_end = text.find("  (function bindClaimModal(){", js_start)
    if js_end < 0:
        raise SystemExit("js end not found")
    text = text[:js_start] + NEW_JS + "\n" + text[js_end:]

    # Modal title
    if "Who tried to claim which sailor" in text:
        text = text.replace(
            "Who tried to claim which sailor",
            "Claim / sign-up — who tried & why it failed",
            1,
        )
    return text


def patch_signup(text: str) -> str:
    """Attach email (for who) on submission_attempted."""
    old = """            try { trackClaimFunnel('submission_attempted', currentProfile.sas_id || claimSelectedSasId || '', true, '', {}); } catch (e0) {}
"""
    new = """            try {
                var _em = '';
                try { _em = (document.getElementById('emailInput') || document.getElementById('email') || {}).value || ''; } catch (eEm) {}
                trackClaimFunnel('submission_attempted', currentProfile.sas_id || claimSelectedSasId || '', true, '', {
                    email: String(_em || '').trim().slice(0, 120),
                    sailor_name: claimSailorName || '',
                    entry: claimEntry
                });
            } catch (e0) {}
"""
    if old not in text:
        print("WARN submission_attempted hook not found")
        return text
    return text.replace(old, new, 1)


def main() -> None:
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = Path(f"/root/backups/api.py.claim_layman2.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak)
    api = API.read_text(encoding="utf-8", errors="replace")
    API.write_text(patch_api(api), encoding="utf-8")
    print("API OK")
    if SIGNUP.exists():
        shutil.copy2(SIGNUP, Path(f"/root/backups/signup.html.claim_who.{ts}"))
        SIGNUP.write_text(patch_signup(SIGNUP.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
        print("SIGNUP OK")


if __name__ == "__main__":
    main()
