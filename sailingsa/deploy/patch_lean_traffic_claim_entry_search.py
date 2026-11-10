#!/usr/bin/env python3
"""Claim funnel: know entry (sailor CTA vs signup banner), who they searched/picked, why failed.

Patches live api.py + signup.html + index.html claim CTA (lean /traffic popup + beacons).
"""
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
SIGNUP = Path("/var/www/sailingsa/signup.html")
INDEX = Path("/var/www/sailingsa/index.html")


def must_replace(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"PATCH FAIL {label}: count={n}")
    return text.replace(old, new, 1)


def patch_api(text: str) -> str:
    # Allow new step keys
    text = must_replace(
        text,
        '''    allowed = {
        "claim_cta_impression",
        "claim_cta_click",
        "claim_page_loaded",
        "sailor_preselected",
        "registration_started",
''',
        '''    allowed = {
        "claim_cta_impression",
        "claim_cta_click",
        "claim_page_loaded",
        "sailor_search",
        "sailor_selected",
        "sailor_preselected",
        "registration_started",
''',
        "funnel allowed steps",
    )

    # Include new steps in claim-attempts SELECT filter
    start = text.find("def lean_traffic_api_claim_attempts")
    end = text.find("\n@app.get", start) if start >= 0 else -1
    if start >= 0 and end > start and "'sailor_search'" not in text[start:end]:
        text = must_replace(
            text,
            """              AND step_key IN (
                'claim_cta_click',
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
""",
            """              AND step_key IN (
                'claim_cta_click',
                'sailor_preselected',
                'claim_page_loaded',
                'sailor_search',
                'sailor_selected',
                'registration_started',
                'submission_attempted',
                'validation_error',
                'verification_failed',
                'verification_succeeded',
                'account_created',
                'claim_completed'
              )
""",
            "claim-attempts step filter",
        )

    # Prefer sas_id from body or numeric stable_entity_id
    text = must_replace(
        text,
        '''    wrote = _lean_record_funnel_event(
        funnel_name="claim_profile",
        step_key=step_key,
        visitor_id=visitor_id,
        session_id=session_id,
        sas_id=str((data or {}).get("sas_id") or "")[:40],
        stable_entity_id=str((data or {}).get("stable_entity_id") or "").strip()[:120],
''',
        '''    _sid = str((data or {}).get("sas_id") or "").strip()
    _ent = str((data or {}).get("stable_entity_id") or "").strip()
    if (not _sid) and _ent.isdigit():
        _sid = _ent
    wrote = _lean_record_funnel_event(
        funnel_name="claim_profile",
        step_key=step_key,
        visitor_id=visitor_id,
        session_id=session_id,
        sas_id=_sid[:40],
        stable_entity_id=_ent[:120],
''',
        "funnel sas_id fill",
    )

    # Replace claim-attempts function body builder: after rows built, add attempts digest
    # Find marker in current lean claim attempts and inject digest + change JS
    if '"attempts":' in text and "entry_how" in text:
        print("api attempts digest already present")
    else:
        # Insert digest before return JSONResponse in lean_traffic_api_claim_attempts
        marker = '''        fails = [x for x in rows if x.get("outcome") == "failed"]
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
'''
        insert = '''        fails = [x for x in rows if x.get("outcome") == "failed"]
        ok_rows = [x for x in rows if x.get("outcome") == "succeeded"]

        # One layman row per person+sailor attempt (not every micro-step)
        attempts_map = {}
        for r in rows:
            meta = r.get("meta") if isinstance(r.get("meta"), dict) else {}
            sailor_key = (r.get("sailor_sas_id") or r.get("stable_entity_id") or r.get("sailor_name") or "unknown")
            person = (r.get("visitor_id") or "") or "anon"
            key = person + "|" + str(sailor_key)
            a = attempts_map.get(key)
            if not a:
                a = {
                    "when": r.get("occurred_at") or "",
                    "visitor_id": person,
                    "sailor_name": r.get("sailor_name") or "Unknown sailor",
                    "sailor_href": r.get("sailor_href") or "",
                    "sailor_sas_id": r.get("sailor_sas_id") or "",
                    "entry_how": "",
                    "searched_for": "",
                    "furthest": r.get("what") or "",
                    "outcome": r.get("outcome") or "attempt",
                    "why": r.get("why") or "—",
                    "on_users": bool(r.get("on_users")),
                    "steps": 0,
                }
                attempts_map[key] = a
            a["steps"] += 1
            if (r.get("occurred_at") or "") >= (a.get("when") or ""):
                a["when"] = r.get("occurred_at") or a["when"]
            sk = r.get("step_key") or ""
            if sk == "claim_cta_click" or meta.get("entry") == "sailor_claim" or meta.get("from") == "sailor_claim":
                a["entry_how"] = "Clicked Claim on sailor profile"
            elif sk == "claim_page_loaded" and not a["entry_how"]:
                ent = str(meta.get("entry") or meta.get("from") or "")
                if ent in ("signup_banner", "signup", "banner"):
                    a["entry_how"] = "Opened Sign up / claim banner (searched for sailor)"
                elif ent in ("sailor_claim", "claim_cta"):
                    a["entry_how"] = "Clicked Claim on sailor profile"
                elif r.get("sailor_sas_id") or (r.get("stable_entity_id") or "").isdigit():
                    a["entry_how"] = "Opened claim page with sailor already set"
                else:
                    a["entry_how"] = "Opened sign-up page"
            if sk == "sailor_search" and meta.get("query"):
                a["searched_for"] = str(meta.get("query"))[:80]
            if meta.get("search_query") and not a["searched_for"]:
                a["searched_for"] = str(meta.get("search_query"))[:80]
            if meta.get("name") and (a["sailor_name"] in ("", "Unknown sailor") or a["sailor_name"].startswith("SAS ")):
                a["sailor_name"] = str(meta.get("name"))[:80]
            if meta.get("sailor_name"):
                a["sailor_name"] = str(meta.get("sailor_name"))[:80]
            # furthest / outcome priority: failed > succeeded > attempt
            order = {"attempt": 0, "succeeded": 1, "failed": 2}
            if order.get(r.get("outcome") or "attempt", 0) >= order.get(a.get("outcome") or "attempt", 0):
                a["outcome"] = r.get("outcome") or a["outcome"]
                if r.get("why") and r.get("why") not in ("—", "In progress / no error recorded"):
                    a["why"] = r.get("why")
                a["furthest"] = r.get("what") or a["furthest"]
            if r.get("on_users"):
                a["on_users"] = True
            if r.get("sailor_href"):
                a["sailor_href"] = r.get("sailor_href")
        attempts = list(attempts_map.values())
        attempts.sort(key=lambda x: str(x.get("when") or ""), reverse=True)
        for a in attempts:
            if not a.get("entry_how"):
                a["entry_how"] = "Sign-up / claim (entry unknown)"
            if a.get("outcome") == "succeeded" and a.get("on_users"):
                a["why"] = "Success — on /users"
            elif a.get("outcome") == "succeeded":
                a["why"] = "Marked success — check /users"
            elif a.get("outcome") == "failed" and (not a.get("why") or a.get("why") == "—"):
                a["why"] = "Failed — see step detail"

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
                "fail_count": len(fails),
                "success_count": len(ok_rows),
                "users_url": "/users",
                "users_note": "Successful claims create a Registered User — they show on /users.",
            },
'''
        text = must_replace(text, marker, insert, "attempts digest")

    # Popup JS: prefer attempts list
    old_js = '''  function loadClaimAttemptDetails(){
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
    new_js = '''  function loadClaimAttemptDetails(){
    var note=$("claimModalNote"), body=$("claimModalBody");
    if(note) note.textContent="Loading who tried to claim which sailor…";
    if(body) body.innerHTML="<p class='note'>Loading…</p>";
    fetchJson("/traffic/api/claim-attempts?range="+encodeURIComponent(RANGE)).then(function(d){
      if(!d || !d.ok) throw new Error((d && d.error) || "failed");
      var attempts=d.attempts||[];
      var fails=d.fail_count||0, oks=d.success_count||0;
      if(note) note.innerHTML="Range <b>"+esc(d.range||RANGE)+"</b> · <b>"+esc(String(d.attempt_count!=null?d.attempt_count:attempts.length))+" people/attempts</b> · <span class='badge fail'>"+esc(String(fails))+" failed steps</span> · <span class='badge ok'>"+esc(String(oks))+" succeeded</span>. Success → <a href='/users' target='_blank' rel='noopener'>/users</a>.";
      if(!attempts.length){
        if(body) body.innerHTML="<p class='note'>Nobody tried to claim / sign up in this range yet.</p>";
        return;
      }
      var html="<p class='note' style='margin-bottom:8px'>How they started · which sailor · what blocked them. Use this to fix claim/sign-up.</p>";
      html+="<div class='table-scroll'><table><thead><tr><th>When</th><th>How they started</th><th>Sailor</th><th>Searched for</th><th>Got as far as</th><th>Result</th><th>Why</th><th>On /users?</th></tr></thead><tbody>";
      attempts.forEach(function(r){
        var when=String(r.when||"").replace("T"," ").slice(0,19);
        var sn=esc(r.sailor_name||"Unknown sailor");
        if(r.sailor_href) sn="<a href='"+esc(r.sailor_href)+"' target='_blank' rel='noopener'>"+sn+"</a>";
        var oc=r.outcome||"attempt";
        var badge=oc==="succeeded"?"ok":(oc==="failed"?"fail":"open");
        var ocLabel=oc==="succeeded"?"Succeeded":(oc==="failed"?"Failed":"Didn’t finish");
        var onU=r.on_users?"<a href='/users' target='_blank' rel='noopener'>Yes</a>":"No";
        html+="<tr><td>"+esc(when)+"</td><td>"+esc(r.entry_how||"—")+"</td><td>"+sn+"</td><td>"+esc(r.searched_for||"—")+"</td><td>"+esc(r.furthest||"—")+"</td><td><span class='badge "+badge+"'>"+esc(ocLabel)+"</span></td><td>"+esc(r.why||"—")+"</td><td>"+onU+"</td></tr>";
      });
      html+="</tbody></table></div>";
      if(body) body.innerHTML=html;
    }).catch(function(e){
      if(note) note.textContent="Could not load claim details.";
      if(body) body.innerHTML="<p class='err'>"+esc(String(e.message||e))+"</p>";
    });
  }
'''
    if old_js in text:
        text = must_replace(text, old_js, new_js, "claim modal attempts js")
    else:
        print("WARN: modal js block not exact — skip UI (API digest still added)")

    # plain step labels for new keys
    text = must_replace(
        text,
        '''                "claim_page_loaded": "Opened claim / sign-up page",
                "registration_started": "Started creating account",
''',
        '''                "claim_page_loaded": "Opened claim / sign-up page",
                "sailor_search": "Searched for a sailor",
                "sailor_selected": "Picked a sailor from search",
                "registration_started": "Started creating account",
''',
        "plain step labels",
    )

    # more plain whys
    text = must_replace(
        text,
        '''            if "forbidden" in el or "unauthorized" in el:
                return "Not allowed"
            # Keep short first line only
            return e[:160]
''',
        '''            if "forbidden" in el or "unauthorized" in el:
                return "Not allowed"
            if "already_claimed" in el or "already claimed" in el or "claimed" in el:
                return "That sailor profile is already claimed — they should sign in instead"
            if "password_requirements" in el:
                return "Password did not meet the rules"
            if "whatsapp" in el:
                return "WhatsApp / phone number looked wrong"
            if "email_invalid" in el or "invalid email" in el:
                return "Email address looked wrong"
            if "sas_id_missing" in el or "missing sas" in el:
                return "No sailor profile was selected"
            if "network_error" in el:
                return "Network error — try again"
            if "registration_failed" in el:
                return "Sign-up failed on the server"
            # Keep short first line only
            return e[:160]
''',
        "plain why codes",
    )
    return text


def patch_signup(text: str) -> str:
    if "entry_how_claim_v1" in text:
        print("signup already patched")
        return text

    # Enhance trackClaimFunnel + entry detection
    old = '''        function trackClaimFunnel(stepKey, stableEntityId, okFlag, errCode, metaValue) {
            try {
                const body = {
                    funnel_name: 'claim_profile',
                    step_key: String(stepKey || ''),
                    stable_entity_id: stableEntityId != null ? String(stableEntityId) : '',
                    url_path: (window.location && window.location.pathname) ? String(window.location.pathname) : '',
                    ok: okFlag !== false,
                    error_code: errCode != null ? String(errCode) : '',
                    meta: (metaValue && typeof metaValue === 'object') ? metaValue : {}
                };
                fetch(window.location.origin + '/api/funnel-event', {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                }).catch(function() {});
            } catch (e) {}
        }
'''
    new = '''        /* entry_how_claim_v1 */
        var claimEntry = 'direct';
        var claimSearchQuery = '';
        var claimSailorName = '';
        function trackClaimFunnel(stepKey, stableEntityId, okFlag, errCode, metaValue) {
            try {
                var meta = (metaValue && typeof metaValue === 'object') ? Object.assign({}, metaValue) : {};
                if (!meta.entry) meta.entry = claimEntry;
                if (claimSearchQuery && !meta.search_query) meta.search_query = claimSearchQuery;
                if (claimSailorName && !meta.sailor_name && !meta.name) meta.sailor_name = claimSailorName;
                var ent = stableEntityId != null ? String(stableEntityId) : '';
                const body = {
                    funnel_name: 'claim_profile',
                    step_key: String(stepKey || ''),
                    sas_id: (/^\\d+$/.test(ent) ? ent : ''),
                    stable_entity_id: ent,
                    url_path: (window.location && window.location.pathname) ? String(window.location.pathname) : '',
                    ok: okFlag !== false,
                    error_code: errCode != null ? String(errCode) : '',
                    meta: meta
                };
                fetch(window.location.origin + '/api/funnel-event', {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                }).catch(function() {});
            } catch (e) {}
        }
'''
    text = must_replace(text, old, new, "signup trackClaimFunnel")

    # DOMContentLoaded entry detection
    old2 = '''                var urlSasId = params.get('sas_id') || params.get('sasId') || params.get('sas') || '';
                urlName = params.get('name') || params.get('q') || params.get('sailor') || '';
                if (urlSasId) {
                    claimSelectedSasId = String(urlSasId);
                    trackClaimFunnel('claim_page_loaded', claimSelectedSasId, true, '', { returnTo: urlReturnTo || '', name: urlName || '' });
                }
'''
    new2 = '''                var urlSasId = params.get('sas_id') || params.get('sasId') || params.get('sas') || '';
                urlName = params.get('name') || params.get('q') || params.get('sailor') || '';
                var isSignupBanner = params.get('signup') === '1' || params.get('signup') === 'true';
                if (urlSasId) claimEntry = 'sailor_claim';
                else if (isSignupBanner) claimEntry = 'signup_banner';
                else claimEntry = 'direct';
                if (urlName) claimSailorName = String(urlName);
                if (urlSasId) {
                    claimSelectedSasId = String(urlSasId);
                    trackClaimFunnel('claim_page_loaded', claimSelectedSasId, true, '', { returnTo: urlReturnTo || '', name: urlName || '', entry: claimEntry });
                } else {
                    trackClaimFunnel('claim_page_loaded', '', true, '', { returnTo: urlReturnTo || '', name: urlName || '', entry: claimEntry });
                }
'''
    text = must_replace(text, old2, new2, "signup entry detect")

    # On sailor_preselected include name
    text = must_replace(
        text,
        '''                            trackClaimFunnel('sailor_preselected', currentProfile.sas_id || claimSelectedSasId, true, '', {});
                            displayProfileConfirmation(currentProfile);
''',
        '''                            claimSailorName = currentProfile.full_name || ((currentProfile.first_name||'') + ' ' + (currentProfile.last_name||'')).trim() || claimSailorName;
                            trackClaimFunnel('sailor_preselected', currentProfile.sas_id || claimSelectedSasId, true, '', { sailor_name: claimSailorName, entry: claimEntry });
                            displayProfileConfirmation(currentProfile);
''',
        "preselected name",
    )

    # Result click → sailor_selected
    text = must_replace(
        text,
        '''                div.onclick = () => {
                    console.log('[DEBUG] displayProfileResults: Profile clicked:', profile);
                    displayProfileConfirmation(profile);
                };
''',
        '''                div.onclick = () => {
                    console.log('[DEBUG] displayProfileResults: Profile clicked:', profile);
                    try {
                        currentProfile = profile;
                        claimSelectedSasId = String(profile.sas_id || profile.sasId || claimSelectedSasId || '');
                        claimSailorName = profile.full_name || ((profile.first_name||'') + ' ' + (profile.last_name||'')).trim() || claimSailorName;
                        trackClaimFunnel('sailor_selected', claimSelectedSasId, true, '', {
                            sailor_name: claimSailorName,
                            search_query: claimSearchQuery || '',
                            entry: claimEntry
                        });
                    } catch (eSel) {}
                    displayProfileConfirmation(profile);
                };
''',
        "result click selected",
    )

    # Hook search — find searchProfiles calls / search button
    # Add after function searchProfiles definition start tracking when called
    if "async function searchProfiles" in text or "function searchProfiles" in text:
        m = re.search(r"(async )?function searchProfiles\s*\(([^)]*)\)\s*\{", text)
        if m:
            insert_at = m.end()
            hook = "\n            try { claimSearchQuery = String(arguments[0] || '').trim(); if (claimSearchQuery) trackClaimFunnel('sailor_search', claimSelectedSasId || '', true, '', { query: claimSearchQuery, entry: claimEntry }); } catch (eSearch) {}\n"
            text = text[:insert_at] + hook + text[insert_at:]
            print("signup searchProfiles hook added")
        else:
            print("WARN searchProfiles signature not found")
    return text


def patch_index(text: str) -> str:
    old = '''                                    var claimHref = '/signup.html?sas_id=' + encodeURIComponent(String(sid)) + '&returnTo=' + encodeURIComponent(claimReturnTo);
                                    if (window.__trackFunnelEvent) window.__trackFunnelEvent('claim_cta_impression', String(sid), true, '', { returnTo: claimReturnTo });
                                    claimCtaHtml = '<a class="sailor-claim-cta" id="sailorClaimCta" data-sas-id="' + escapeHtml(String(sid)) + '" href="' + escapeHtml(claimHref) + '" onclick="try{window.__trackFunnelEvent&&window.__trackFunnelEvent(\\'claim_cta_click\\',this.getAttribute(\\'data-sas-id\\')||\\'\\',true,\\'\\',{returnTo:(window.location&&window.location.pathname)?String(window.location.pathname):\\'/\\'});}catch(e){}">Is this you? Claim this profile</a>';
'''
    # The onclick escaping in file is different - read exact from file style
    if "claim_cta_click" not in text:
        return text
    # Softer replace for href only
    old_href = "var claimHref = '/signup.html?sas_id=' + encodeURIComponent(String(sid)) + '&returnTo=' + encodeURIComponent(claimReturnTo);"
    if text.count(old_href) == 1:
        text = text.replace(
            old_href,
            "var claimName = (typeof sailor !== 'undefined' && sailor && (sailor.full_name || sailor.name)) ? String(sailor.full_name || sailor.name) : ((typeof name !== 'undefined' && name) ? String(name) : '');\n"
            "                                    var claimHref = '/signup.html?sas_id=' + encodeURIComponent(String(sid)) + '&name=' + encodeURIComponent(claimName) + '&returnTo=' + encodeURIComponent(claimReturnTo);",
            1,
        )
        print("index claimHref +name")
    else:
        print("WARN claimHref count", text.count(old_href))

    # Improve onclick meta — MUST keep \\' escapes (this string sits inside a single-quoted JS literal).
    # A prior unescaped replace broke the whole SPA (sailor/regatta search).
    old_click_esc = (
        r"window.__trackFunnelEvent&&window.__trackFunnelEvent(\'claim_cta_click\',"
        r"this.getAttribute(\'data-sas-id\')||\'\',true,\'\',"
        r"{returnTo:(window.location&&window.location.pathname)?String(window.location.pathname):\'/\'})"
    )
    new_click_esc = (
        r"window.__trackFunnelEvent&&window.__trackFunnelEvent(\'claim_cta_click\',"
        r"this.getAttribute(\'data-sas-id\')||\'\',true,\'\',"
        r"{returnTo:(window.location&&window.location.pathname)?String(window.location.pathname):\'/\',"
        r"entry:\'sailor_claim\',name:(this.getAttribute(\'data-sailor-name\')||\'\')})"
    )
    if old_click_esc in text:
        text = text.replace(old_click_esc, new_click_esc, 1)
        print("index click meta (escaped)")
    elif new_click_esc in text:
        print("index click meta already present")
    else:
        print("WARN click meta not replaced")

    # add data-sailor-name on anchor if we can find it
    old_a = 'id="sailorClaimCta" data-sas-id="'
    if text.count(old_a) == 1:
        # Need claimName in scope - we added claimName above
        text = text.replace(
            'id="sailorClaimCta" data-sas-id="' + "' + escapeHtml(String(sid)) + '\"",
            'id="sailorClaimCta" data-sas-id="' + "' + escapeHtml(String(sid)) + '\" data-sailor-name=\"' + escapeHtml(claimName || '') + '\"",
            1,
        )
        # Actually the pattern uses escapeHtml differently
    # Try exact live pattern
    pat = 'id="sailorClaimCta" data-sas-id="' + '" + escapeHtml(String(sid)) + "'
    # In file: data-sas-id="' + escapeHtml(String(sid)) + '"
    frag = 'id="sailorClaimCta" data-sas-id="\' + escapeHtml(String(sid)) + \'"'
    # Raw in py string from file content:
    frag2 = 'id="sailorClaimCta" data-sas-id="' + "' + escapeHtml(String(sid)) + '"
    # Let's just do:
    s = 'data-sas-id="\' + escapeHtml(String(sid)) + \'" href="'
    # File has: data-sas-id="' + escapeHtml(String(sid)) + '" href="'
    needle = """data-sas-id="' + escapeHtml(String(sid)) + '" href=\""""
    if text.count(needle) == 1:
        text = text.replace(
            needle,
            """data-sas-id="' + escapeHtml(String(sid)) + '" data-sailor-name="' + escapeHtml(claimName || '') + '" href=\"""",
            1,
        )
        print("index data-sailor-name")
    return text


def main() -> None:
    bak_dir = Path("/root/backups")
    bak_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    api = API.read_text(encoding="utf-8", errors="replace")
    shutil.copy2(API, bak_dir / f"api.py.claim_entry.{ts}")
    API.write_text(patch_api(api), encoding="utf-8")
    print("API done")

    if SIGNUP.exists():
        su = SIGNUP.read_text(encoding="utf-8", errors="replace")
        shutil.copy2(SIGNUP, bak_dir / f"signup.html.claim_entry.{ts}")
        SIGNUP.write_text(patch_signup(su), encoding="utf-8")
        print("SIGNUP done")

    if INDEX.exists():
        ix = INDEX.read_text(encoding="utf-8", errors="replace")
        shutil.copy2(INDEX, bak_dir / f"index.html.claim_entry.{ts}")
        INDEX.write_text(patch_index(ix), encoding="utf-8")
        print("INDEX done")


if __name__ == "__main__":
    main()
