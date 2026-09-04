#!/usr/bin/env python3
"""Make /traffic claim popup layman-clear: which sailor, what failed, link to /users."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def must_replace(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"PATCH FAIL {label}: count={n}")
    return text.replace(old, new, 1)


NEW_FN = r'''
def lean_traffic_api_claim_attempts(request: Request):
    """Claim/sign-up attempts for /traffic popup — sailor name, plain why, /users link."""
    denied = _lean_traffic_gate(request)
    if denied is not None:
        if isinstance(denied, RedirectResponse):
            return denied
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    range_key, since_sql, _bucket = _lean_traffic_parse_range(request.query_params.get("range"))
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SET LOCAL statement_timeout = '10000'")
        except Exception:
            pass
        since_clause = "" if not since_sql else f" AND occurred_at >= NOW() - INTERVAL '{since_sql}'"
        cur.execute(
            f"""
            SELECT
              funnel_event_id,
              occurred_at,
              step_key,
              ok,
              COALESCE(NULLIF(TRIM(split_part(COALESCE(error_code,''), E'\\n', 1)), ''), '') AS error_code,
              COALESCE(NULLIF(TRIM(url_path), ''), '—') AS url_path,
              COALESCE(NULLIF(TRIM(sas_id), ''), '') AS sas_id,
              COALESCE(NULLIF(TRIM(stable_entity_id), ''), '') AS stable_entity_id,
              COALESCE(NULLIF(TRIM(visitor_id), ''), '') AS visitor_id,
              COALESCE(meta_value_json, '{{}}'::jsonb) AS meta
            FROM public.traffic_funnel_events
            WHERE funnel_name = 'claim_profile'
              {since_clause}
              AND step_key IN (
                'claim_cta_click',
                'claim_cta_impression',
                'sailor_preselected',
                'claim_page_loaded',
                'registration_started',
                'submission_attempted',
                'validation_error',
                'verification_failed',
                'verification_succeeded',
                'account_created',
                'claim_completed'
              )
            ORDER BY occurred_at DESC
            LIMIT 250
            """
        )
        raw = list(cur.fetchall() or [])

        def _plain_step(sk: str) -> str:
            return {
                "claim_cta_impression": "Saw Claim button on sailor page",
                "claim_cta_click": "Tapped Claim on sailor page",
                "sailor_preselected": "Sailor chosen for claim",
                "claim_page_loaded": "Opened claim / sign-up page",
                "registration_started": "Started creating account",
                "submission_attempted": "Submitted the form",
                "validation_error": "Form rejected (details below)",
                "verification_failed": "Verification failed — not signed up",
                "verification_succeeded": "Verified OK",
                "account_created": "Account created — should appear on /users",
                "claim_completed": "Claim finished — should appear on /users",
            }.get(sk or "", sk or "—")

        def _plain_why(err: str, sk: str, ok: bool) -> str:
            e = (err or "").strip()
            el = e.lower()
            if not e:
                if sk in ("claim_completed", "account_created") and ok:
                    return "Success — check Registered Users (/users)"
                if sk in ("claim_cta_click", "claim_page_loaded", "sailor_preselected", "registration_started", "submission_attempted"):
                    return "In progress / no error recorded"
                return "—"
            if "probe" in el:
                return "Internal test probe (ignore)"
            if "more target columns than expressions" in el or "login_method" in el:
                return "Sign-up bug (since fixed) — account was not created"
            if "email" in el and ("taken" in el or "exists" in el or "already" in el):
                return "That email is already registered"
            if "password" in el:
                return "Password problem — too weak or mismatch"
            if "code" in el or "otp" in el or "verif" in el:
                return "Verification code wrong or expired"
            if "sas" in el or "sailor" in el:
                return "Could not match / claim that sailor profile"
            if "forbidden" in el or "unauthorized" in el:
                return "Not allowed"
            # Keep short first line only
            return e[:160]

        def _slug_from_path(path: str) -> str:
            p = (path or "").strip()
            if "/sailor/" in p:
                part = p.split("/sailor/", 1)[1]
                return part.split("?", 1)[0].split("#", 1)[0].strip("/")
            return ""

        # Collect sas ids + slugs to resolve names
        sas_ids = set()
        slugs = set()
        parsed = []
        for r in raw:
            if isinstance(r, dict):
                occ = r.get("occurred_at")
                meta = r.get("meta") or {}
                row = {
                    "id": r.get("funnel_event_id"),
                    "occurred_at": occ.isoformat() if hasattr(occ, "isoformat") else str(occ or ""),
                    "step_key": r.get("step_key") or "",
                    "ok": bool(r.get("ok")),
                    "error_code": r.get("error_code") or "",
                    "url_path": r.get("url_path") or "—",
                    "sas_id": str(r.get("sas_id") or "").strip(),
                    "stable_entity_id": str(r.get("stable_entity_id") or "").strip(),
                    "visitor_id": (str(r.get("visitor_id") or ""))[:24],
                    "meta": meta if isinstance(meta, dict) else {},
                }
            else:
                occ = r[1]
                meta = r[9] or {}
                row = {
                    "id": r[0],
                    "occurred_at": occ.isoformat() if hasattr(occ, "isoformat") else str(occ or ""),
                    "step_key": r[2] or "",
                    "ok": bool(r[3]),
                    "error_code": r[4] or "",
                    "url_path": r[5] or "—",
                    "sas_id": str(r[6] or "").strip(),
                    "stable_entity_id": str(r[7] or "").strip(),
                    "visitor_id": (str(r[8] or ""))[:24],
                    "meta": meta if isinstance(meta, dict) else {},
                }
            sk = row["step_key"]
            if sk in ("claim_completed", "account_created", "verification_succeeded") and row["ok"]:
                row["outcome"] = "succeeded"
            elif (not row["ok"]) or sk in ("verification_failed", "validation_error"):
                row["outcome"] = "failed"
            else:
                row["outcome"] = "attempt"
            # Sailor id preference
            sid = row["sas_id"]
            ent = row["stable_entity_id"]
            if (not sid) and ent and ent.isdigit():
                sid = ent
            if sid and sid.lower() not in ("probe",):
                sas_ids.add(sid)
            slug = ""
            meta = row["meta"] if isinstance(row["meta"], dict) else {}
            rt = str(meta.get("returnTo") or meta.get("return_to") or "")
            slug = _slug_from_path(row["url_path"]) or _slug_from_path(rt)
            if slug:
                slugs.add(slug.lower())
            row["_sid"] = sid
            row["_slug"] = slug
            row["what"] = _plain_step(sk)
            row["why"] = _plain_why(row["error_code"], sk, row["ok"])
            parsed.append(row)

        name_by_sas = {}
        slug_by_sas = {}
        if sas_ids:
            try:
                cur.execute(
                    """
                    SELECT p.sa_sailing_id::text AS sas_id,
                           TRIM(COALESCE(NULLIF(TRIM(p.full_name), ''),
                             TRIM(COALESCE(p.first_name,'') || ' ' || COALESCE(p.last_name,'')))) AS name
                    FROM public.sas_id_personal p
                    WHERE p.sa_sailing_id::text = ANY(%s)
                    """,
                    (list(sas_ids),),
                )
                for rr in cur.fetchall() or []:
                    if isinstance(rr, dict):
                        name_by_sas[str(rr.get("sas_id") or "")] = str(rr.get("name") or "").strip()
                    else:
                        name_by_sas[str(rr[0] or "")] = str(rr[1] or "").strip()
            except Exception:
                _lean_db_rollback(conn)
            try:
                slug_by_sas = _batch_sailor_slugs_for_sas_ids(list(sas_ids)) or {}
            except Exception:
                slug_by_sas = {}

        name_by_slug = {}
        # Prefer path/returnTo slug → human name; DB slug tables vary by deploy.

        on_users = set()
        if sas_ids:
            try:
                cur.execute(
                    """
                    SELECT DISTINCT sas_id::text FROM public.user_accounts
                    WHERE sas_id::text = ANY(%s)
                    """,
                    (list(sas_ids),),
                )
                for rr in cur.fetchall() or []:
                    if isinstance(rr, dict):
                        on_users.add(str(rr.get("sas_id") or ""))
                    else:
                        on_users.add(str(rr[0] or ""))
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        rows = []
        for row in parsed:
            sid = row.pop("_sid", "") or ""
            slug = row.pop("_slug", "") or ""
            sname = name_by_sas.get(sid) or name_by_slug.get(slug.lower()) or ""
            if not sname and slug:
                # humanize slug
                sname = slug.replace("-", " ").strip().title()
            if not sname and sid and sid.lower() != "probe":
                sname = "SAS " + sid
            if sid and sid.lower() == "probe":
                sname = "(test probe)"
            href = ""
            if slug:
                href = "/sailor/" + slug
            elif sid and slug_by_sas.get(sid):
                href = "/sailor/" + str(slug_by_sas.get(sid))
            elif sid and sid.isdigit():
                href = "/sailor/" + sid
            row["sailor_name"] = sname or "Unknown sailor"
            row["sailor_href"] = href
            row["sailor_sas_id"] = sid if sid.lower() != "probe" else ""
            row["on_users"] = bool(sid and sid in on_users)
            rows.append(row)

        fails = [x for x in rows if x.get("outcome") == "failed"]
        ok_rows = [x for x in rows if x.get("outcome") == "succeeded"]
        return JSONResponse(
            {
                "ok": True,
                "range": range_key,
                "rows": rows,
                "failures": fails,
                "successes": ok_rows,
                "count": len(rows),
                "fail_count": len(fails),
                "success_count": len(ok_rows),
                "users_url": "/users",
                "users_note": "Successful claims create a Registered User — they show on /users.",
            },
            headers={"Cache-Control": "no-store"},
        )
    except Exception as e:
        _lean_db_rollback(conn)
        return JSONResponse({"ok": False, "error": str(e)[:200]}, status_code=500, headers={"Cache-Control": "no-store"})
    finally:
        if conn:
            return_db_connection(conn)


'''


OLD_JS = r'''  function loadClaimAttemptDetails(){
    var note=$("claimModalNote"), body=$("claimModalBody");
    if(note) note.textContent="Loading claim / sign-up attempts for "+RANGE+"…";
    if(body) body.innerHTML="<p class='note'>Loading…</p>";
    fetchJson("/traffic/api/claim-attempts?range="+encodeURIComponent(RANGE)).then(function(d){
      if(!d || !d.ok) throw new Error((d && d.error) || "failed");
      var rows=d.rows||[];
      if(note) note.textContent=(d.count||0)+" events · "+(d.fail_count||0)+" failures · range "+(d.range||RANGE)+". Fix items with outcome Failed.";
      if(!rows.length){
        if(body) body.innerHTML="<p class='note'>No claim / sign-up funnel events in this range yet.</p>";
        return;
      }
      var html="<div class='table-scroll'><table><thead><tr><th>When</th><th>Step</th><th>Where</th><th>Who</th><th>Outcome</th><th>Why / detail</th></tr></thead><tbody>";
      rows.forEach(function(r){
        var when=String(r.occurred_at||"").replace("T"," ").slice(0,19);
        var step=esc(r.step_key||"");
        var where=esc(r.url_path||"—");
        if(r.url_path && String(r.url_path).indexOf("/")===0){
          where="<a href='"+esc(r.url_path)+"' target='_blank' rel='noopener'>"+esc(r.url_path)+"</a>";
        }
        var who=[];
        if(r.sas_id) who.push("sas "+r.sas_id);
        if(r.stable_entity_id && r.stable_entity_id!==r.sas_id) who.push("entity "+r.stable_entity_id);
        if(r.visitor_id) who.push("vid "+r.visitor_id);
        var whoHtml=esc(who.join(" · ")||"—");
        var oc=r.outcome||"attempt";
        var badge=oc==="succeeded"?"ok":(oc==="failed"?"fail":"open");
        var why=r.error_code||"";
        if(!why && r.meta && r.meta.source) why="source="+r.meta.source;
        if(!why && oc==="succeeded") why="ok";
        if(!why) why="—";
        html+="<tr><td>"+esc(when)+"</td><td>"+step+"</td><td>"+where+"</td><td>"+whoHtml+"</td><td><span class='badge "+badge+"'>"+esc(oc)+"</span></td><td>"+esc(why)+"</td></tr>";
      });
      html+="</tbody></table></div>";
      if(body) body.innerHTML=html;
    }).catch(function(e){
      if(note) note.textContent="Could not load details.";
      if(body) body.innerHTML="<p class='err'>"+esc(String(e.message||e))+"</p>";
    });
  }
'''

NEW_JS = r'''  function loadClaimAttemptDetails(){
    var note=$("claimModalNote"), body=$("claimModalBody");
    if(note) note.textContent="Loading who tried to claim which sailor…";
    if(body) body.innerHTML="<p class='note'>Loading…</p>";
    fetchJson("/traffic/api/claim-attempts?range="+encodeURIComponent(RANGE)).then(function(d){
      if(!d || !d.ok) throw new Error((d && d.error) || "failed");
      var rows=d.rows||[];
      var fails=d.fail_count||0, oks=d.success_count||0;
      if(note) note.innerHTML="Range <b>"+esc(d.range||RANGE)+"</b> · "+esc(String(d.count||0))+" events · <span class='badge fail'>"+esc(String(fails))+" failed</span> · <span class='badge ok'>"+esc(String(oks))+" succeeded</span>. Successful accounts appear on <a href='/users' target='_blank' rel='noopener'>/users</a>.";
      if(!rows.length){
        if(body) body.innerHTML="<p class='note'>Nobody tried to claim / sign up in this range yet.</p>";
        return;
      }
      var html="<div class='table-scroll'><table><thead><tr><th>When</th><th>Sailor they tried to claim</th><th>What happened</th><th>Result</th><th>Why (plain English)</th><th>On /users?</th></tr></thead><tbody>";
      rows.forEach(function(r){
        var when=String(r.occurred_at||"").replace("T"," ").slice(0,19);
        var sn=esc(r.sailor_name||"Unknown sailor");
        if(r.sailor_href){
          sn="<a href='"+esc(r.sailor_href)+"' target='_blank' rel='noopener'>"+sn+"</a>";
        }
        var what=esc(r.what||r.step_key||"—");
        var oc=r.outcome||"attempt";
        var badge=oc==="succeeded"?"ok":(oc==="failed"?"fail":"open");
        var ocLabel=oc==="succeeded"?"Succeeded":(oc==="failed"?"Failed":"In progress");
        var why=esc(r.why||r.error_code||"—");
        var onU=r.on_users?"<a href='/users' target='_blank' rel='noopener'>Yes — on /users</a>":(oc==="succeeded"?"Should be — refresh /users":"No");
        html+="<tr><td>"+esc(when)+"</td><td>"+sn+"</td><td>"+what+"</td><td><span class='badge "+badge+"'>"+esc(ocLabel)+"</span></td><td>"+why+"</td><td>"+onU+"</td></tr>";
      });
      html+="</tbody></table></div>";
      if(body) body.innerHTML=html;
    }).catch(function(e){
      if(note) note.textContent="Could not load claim details.";
      if(body) body.innerHTML="<p class='err'>"+esc(String(e.message||e))+"</p>";
    });
  }
'''


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    if "Successful accounts appear on /users" in text and "sailor_name" in text[text.find("def lean_traffic_api_claim_attempts"): text.find("def lean_traffic_api_claim_attempts") + 8000]:
        print("ALREADY_PATCHED")
        return

    bak = Path(f"/root/backups/api.py.claim_popup.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    start = text.find("def lean_traffic_api_claim_attempts(request: Request):")
    if start < 0:
        raise SystemExit("FN not found")
    end = text.find("\n@app.get(\"/traffic/api/summary\")", start)
    if end < 0:
        end = text.find("\ndef lean_traffic_api_summary_alias", start)
    if end < 0:
        raise SystemExit("FN end not found")
    text = text[:start] + NEW_FN.strip() + "\n\n\n" + text[end:].lstrip("\n")

    text = must_replace(text, OLD_JS, NEW_JS, "claim modal js")

    # Modal title + funnel note
    if ">Claim / sign-up detail</h3>" in text:
        text = must_replace(
            text,
            ">Claim / sign-up detail</h3>",
            ">Who tried to claim which sailor</h3>",
            "modal title",
        )
    if 'id="claimFunnelNote">' in text:
        # replace note content carefully
        old_note_start = text.find('id="claimFunnelNote">')
        old_note_end = text.find("</p>", old_note_start)
        if old_note_start > 0 and old_note_end > old_note_start:
            text = (
                text[:old_note_start]
                + 'id="claimFunnelNote">Tap the Claim / sign-up card for who tried, which sailor, why they failed, and whether they show on <a href="/users">/users</a> after success.'
                + text[old_note_end:]
            )

    API.write_text(text, encoding="utf-8")
    print("PATCHED")


if __name__ == "__main__":
    main()
