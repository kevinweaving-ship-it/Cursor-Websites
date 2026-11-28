#!/usr/bin/env python3
"""Claim maths: KPI matches popup; include real /users signups in selected range (e.g. Google)."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
t = API.read_text(encoding="utf-8", errors="replace")
bak = Path(f"/root/backups/api.py.claim_maths.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(API, bak)
print("BACKUP", bak)

# --- Inject accounts-created into claim-attempts after merge, before counts ---
old = '''        attempts = merged

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

new = '''        attempts = merged

        # Real members created in this range (Google / WhatsApp / email) — funnel often missed these
        accounts_in_range = []
        try:
            since_acc = "TRUE" if not since_sql else "created_at >= NOW() - INTERVAL %s"
            params_acc = () if not since_sql else (since_sql,)
            cur.execute(
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
            accounts_in_range = list(cur.fetchall() or [])
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            accounts_in_range = []

        by_sas = {}
        for a in attempts:
            sid = (a.get("sailor_sas_id") or "").strip()
            if sid:
                by_sas[sid] = a

        def _mask_email(em: str) -> str:
            em = (em or "").strip()
            if "@" not in em:
                return em
            try:
                local, dom = em.split("@", 1)
                return (local[:1] + "***@" + dom) if local else em
            except Exception:
                return em

        acc_sids = []
        for rr in accounts_in_range:
            sid = str((rr.get("sas_id") if isinstance(rr, dict) else rr[0]) or "").strip()
            if sid:
                acc_sids.append(sid)
        acc_slugs = {}
        acc_names = dict(name_by_sas) if isinstance(name_by_sas, dict) else {}
        if acc_sids:
            try:
                acc_slugs = _batch_sailor_slugs_for_sas_ids(acc_sids) or {}
            except Exception:
                acc_slugs = {}
            missing = [s for s in acc_sids if s not in acc_names]
            if missing:
                try:
                    cur.execute(
                        """
                        SELECT p.sa_sailing_id::text AS sas_id,
                               TRIM(COALESCE(NULLIF(TRIM(p.full_name), ''),
                                 TRIM(COALESCE(p.first_name,'') || ' ' || COALESCE(p.last_name,'')))) AS name
                        FROM public.sas_id_personal p
                        WHERE p.sa_sailing_id::text = ANY(%s)
                        """,
                        (missing,),
                    )
                    for nr in cur.fetchall() or []:
                        if isinstance(nr, dict):
                            acc_names[str(nr.get("sas_id") or "")] = str(nr.get("name") or "").strip()
                        else:
                            acc_names[str(nr[0] or "")] = str(nr[1] or "").strip()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

        for rr in accounts_in_range:
            if isinstance(rr, dict):
                sid = str(rr.get("sas_id") or "").strip()
                email = str(rr.get("email") or "").strip()
                name = str(rr.get("name") or "").strip()
                method = str(rr.get("login_method") or "sign-up").strip()
                created = rr.get("created_at")
            else:
                sid = str(rr[0] or "").strip()
                email = str(rr[1] or "").strip()
                name = str(rr[2] or "").strip()
                method = str(rr[3] or "sign-up").strip()
                created = rr[4]
            if not sid:
                continue
            created_iso = created.isoformat() if hasattr(created, "isoformat") else str(created or "")
            method_plain = {
                "google": "Google",
                "email": "email form",
                "whatsapp": "WhatsApp",
                "sas_id": "SAS ID",
                "facebook": "Facebook",
            }.get(method.lower(), method)
            who = name or _mask_email(email) or "New member"
            if name and email:
                who = name + " (" + _mask_email(email) + ")"
            sl = acc_slugs.get(sid) or ""
            href = ("/sailor/" + str(sl)) if sl else (("/sailor/" + sid) if sid.isdigit() else "")
            sname = acc_names.get(sid) or name or ("SAS " + sid)
            problem = "Signed up successfully via " + method_plain + " — on /users"
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

if old not in t:
    raise SystemExit("attempts return anchor missing")
t = t.replace(old, new, 1)

# --- KPI: attempts = everyone who opened/selected/submitted (not only submitters); ok includes accounts ---
old_kpi = '''            # Distinct people who tried to register/submit
            cur.execute(
                """
                SELECT COUNT(DISTINCT COALESCE(NULLIF(visitor_id,''), NULLIF(session_id,''), NULLIF(stable_entity_id,'')))::int AS n
                FROM public.traffic_funnel_events
                WHERE funnel_name = 'claim_profile'
                  AND step_key IN ('submission_attempted', 'registration_started')
                  AND """ + c_where + """
                """,
                c_params,
            )
            crow = cur.fetchone() or {}
            claim_attempts = int((crow.get("n") if isinstance(crow, dict) else crow[0]) or 0)
'''

new_kpi = '''            # Distinct people who opened / picked / submitted (matches popup rows, not submit-only)
            cur.execute(
                """
                SELECT COUNT(DISTINCT COALESCE(NULLIF(visitor_id,''), NULLIF(session_id,''), NULLIF(stable_entity_id,'')))::int AS n
                FROM public.traffic_funnel_events
                WHERE funnel_name = 'claim_profile'
                  AND step_key IN (
                    'claim_cta_click', 'claim_page_loaded', 'sailor_preselected', 'sailor_selected',
                    'sailor_search', 'registration_started', 'submission_attempted',
                    'validation_error', 'verification_failed',
                    'verification_succeeded', 'account_created', 'claim_completed'
                  )
                  AND """ + c_where + """
                  AND COALESCE(NULLIF(visitor_id,''), NULLIF(session_id,''), NULLIF(stable_entity_id,'')) IS NOT NULL
                  AND lower(COALESCE(stable_entity_id,'')) <> 'probe'
                """,
                c_params,
            )
            crow = cur.fetchone() or {}
            claim_attempts = int((crow.get("n") if isinstance(crow, dict) else crow[0]) or 0)
'''

if old_kpi not in t:
    raise SystemExit("kpi attempts anchor missing")
t = t.replace(old_kpi, new_kpi, 1)

# After claim_open computed, also set open from page-opens minus ok/fail more honestly:
# Keep existing lift logic but ensure claim_open includes abandoners:
old_lift = '''            # Succeeded = max(funnel successes, accounts created) so card matches reality when funnel was down
            claim_ok = max(funnel_ok, claim_accounts_created)
            # If accounts imply success but attempts undercount (logging gap), lift attempts
            claim_attempts = max(claim_attempts, claim_ok + claim_fail)
            claim_open = max(0, claim_attempts - claim_ok - claim_fail)
'''

new_lift = '''            # Succeeded = max(funnel successes, accounts created) so card matches reality when funnel was down
            claim_ok = max(funnel_ok, claim_accounts_created)
            # Distinct abandoners = opened/selected but never failed or succeeded
            try:
                cur.execute(
                    """
                    WITH people AS (
                      SELECT COALESCE(NULLIF(visitor_id,''), NULLIF(session_id,''), NULLIF(stable_entity_id,'')) AS pid,
                             bool_or(ok = false AND step_key IN ('verification_failed','validation_error')) AS failed,
                             bool_or(ok = true AND step_key IN ('claim_completed','account_created','verification_succeeded')) AS succeeded,
                             bool_or(step_key IN (
                               'claim_cta_click','claim_page_loaded','sailor_preselected','sailor_selected',
                               'sailor_search','registration_started','submission_attempted'
                             )) AS opened
                      FROM public.traffic_funnel_events
                      WHERE funnel_name = 'claim_profile'
                        AND """ + c_where + """
                        AND COALESCE(NULLIF(visitor_id,''), NULLIF(session_id,''), NULLIF(stable_entity_id,'')) IS NOT NULL
                        AND lower(COALESCE(stable_entity_id,'')) <> 'probe'
                      GROUP BY 1
                    )
                    SELECT COUNT(*) FILTER (WHERE opened AND NOT failed AND NOT succeeded)::int AS left_n
                    FROM people
                    """,
                    c_params,
                )
                lrow = cur.fetchone() or {}
                left_n = int((lrow.get("left_n") if isinstance(lrow, dict) else lrow[0]) or 0)
            except Exception:
                left_n = 0
            claim_open = max(left_n, max(0, claim_attempts - claim_ok - claim_fail))
            # Card total must equal ok + fail + left (same story as popup)
            claim_attempts = max(claim_attempts, claim_ok + claim_fail + claim_open)
'''

if old_lift not in t:
    raise SystemExit("kpi lift anchor missing")
t = t.replace(old_lift, new_lift, 1)

# Card subtitle: layman
old_sub = '''        var okN=Number(o.claim_ok||0), failN=Number(o.claim_fail||0), openN=Number(o.claim_open||0);'''
# find surrounding subtext update
if 'kClaimSub' in t:
    pass

old_card_js = '''          if($("kClaim")) $("kClaim").textContent=String(o.claim_attempts||0);
          if($("kClaimSub")) $("kClaimSub").textContent=String(o.claim_ok||0)+" succeeded · "+String(o.claim_fail||0)+" failed · "+String(o.claim_accounts_created||0)+" accounts";'''

new_card_js = '''          if($("kClaim")) $("kClaim").textContent=String(o.claim_attempts||0);
          if($("kClaimSub")) $("kClaimSub").textContent=String(o.claim_ok||0)+" members · "+String(o.claim_fail||0)+" blocked · "+String(o.claim_open||0)+" left (this range)";'''

if old_card_js in t:
    t = t.replace(old_card_js, new_card_js)

API.write_text(t, encoding="utf-8")
print("OK")
