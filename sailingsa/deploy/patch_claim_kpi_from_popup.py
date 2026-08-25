#!/usr/bin/env python3
"""Drive Claim KPI + funnel note from claim-attempts (same maths as popup)."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
t = API.read_text(encoding="utf-8", errors="replace")
bak = Path(f"/root/backups/api.py.claim_kpi_sync.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(API, bak)
print("BACKUP", bak)

old = '''      if($("kClaim")) $("kClaim").textContent=String(o.claim_attempts||0);
      if($("kClaimSub")){
        var okN=Number(o.claim_ok||0), failN=Number(o.claim_fail||0), openN=Number(o.claim_open||0);
        $("kClaimSub").textContent=okN+" ok · "+failN+" fail · tap for detail";
      }
      try{
        var box=$("claimFunnelBody");
        if(box){
          var steps=o.claim_steps||{};
          var reasons=o.claim_fail_reasons||[];
          var html="<p class='note'>People: <b>"+String(o.claim_attempts||0)+"</b> attempts = "
            +"<b>"+String(o.claim_ok||0)+"</b> ok + <b>"+String(o.claim_fail||0)+"</b> fail + <b>"+String(o.claim_open||0)+"</b> open. "
            +"Accounts created: <b>"+String(o.claim_accounts_created||0)+"</b>. "
            +"Signup page visitors: <b>"+String(o.claim_signup_views||0)+"</b>. "
            +"Sources check: Direct "+String(o.direct_landings||0)+" + Google "+String(o.google_landings||0)
            +" + Facebook "+String(o.facebook_landings||0)+" + Other "+String(o.other_landings||0)
            +" = <b>"+String(o.sources_sum!=null?o.sources_sum:((o.direct_landings||0)+(o.google_landings||0)+(o.facebook_landings||0)+(o.other_landings||0)))+"</b> (visitors "+String(o.visitors||0)+").</p>";
          if(reasons.length){
            html+="<table><thead><tr><th>Failure reason</th><th>Count</th></tr></thead><tbody>";
            reasons.forEach(function(r){ html+="<tr><td>"+esc(r.reason||"unknown")+"</td><td>"+String(r.n||0)+"</td></tr>"; });
            html+="</tbody></table>";
          } else {
            html+="<p class='note'>No recorded failures in this range"
              +(Number(o.claim_attempts||0)===0?" — funnel logging was down after early August until restored":"")
              +".</p>";
          }
          box.innerHTML=html;
        }
      }catch(eClaim){}
'''

new = '''      // Claim card numbers come from claim-attempts (same digest as the popup) so maths match
      fetchJson("/traffic/api/claim-attempts?range="+encodeURIComponent(RANGE)).then(function(cd){
        if(!cd || !cd.ok) return;
        var nTry=Number(cd.attempt_count||0), nOk=Number(cd.success_count||0), nFail=Number(cd.fail_count||0), nLeft=Number(cd.left_count||0);
        if($("kClaim")) $("kClaim").textContent=String(nTry);
        if($("kClaimSub")) $("kClaimSub").textContent=nOk+" members · "+nFail+" blocked · "+nLeft+" left · tap for detail";
        try{
          var box=$("claimFunnelBody");
          if(box){
            var html="<p class='note'><b>"+esc(String(cd.summary||""))+"</b> for range <b>"+esc(RANGE)+"</b>. "
              +"These are the same numbers as the Claim card and the popup. "
              +"Members = on <a href='/users' target='_blank' rel='noopener'>/users</a>.</p>";
            var fails=(cd.attempts||[]).filter(function(a){ return a.outcome==="failed"; });
            if(fails.length){
              html+="<table><thead><tr><th>Who / sailor</th><th>Problem</th></tr></thead><tbody>";
              fails.slice(0,8).forEach(function(a){
                html+="<tr><td>"+esc(a.who||"Didn't leave email")+" → "+esc(a.sailor_name||"?")+"</td><td>"+esc(a.problem||"—")+"</td></tr>";
              });
              html+="</tbody></table>";
            } else {
              html+="<p class='note'>No blocked sign-ups in this range (people who left without submitting are not failures).</p>";
            }
            box.innerHTML=html;
          }
        }catch(eClaim){}
      }).catch(function(){});
'''

if old not in t:
    raise SystemExit("loadAll claim block missing")
t = t.replace(old, new, 1)

# Poll path should not overwrite with stale overview claim counts
old_poll = '''          if($("kClaim")) $("kClaim").textContent=String(o.claim_attempts||0);
          if($("kClaimSub")) $("kClaimSub").textContent=String(o.claim_ok||0)+" members · "+String(o.claim_fail||0)+" blocked · "+String(o.claim_open||0)+" left (this range)";'''
new_poll = '''          // Claim KPI refreshed from claim-attempts in loadAll — do not overwrite with overview estimate'''
if old_poll in t:
    t = t.replace(old_poll, new_poll, 1)
else:
    print("WARN poll claim overwrite not found")

API.write_text(t, encoding="utf-8")
print("OK")
