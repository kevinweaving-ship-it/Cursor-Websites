#!/usr/bin/env python3
"""Claim / sign-up popup: mobile-portrait card list (one card per attempt)."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
ts = time.strftime("%Y%m%d_%H%M%S")
if API.exists():
    shutil.copy2(API, Path(f"/root/backups/api.claim_cards_mp_{ts}.py"))
    print("BACKUP", ts)

text = API.read_text(encoding="utf-8", errors="replace")

CSS = """
.modal .badge.open{background:#e0f2fe;color:#075985}
.claim-attempt-cards{display:flex;flex-direction:column;gap:10px;margin-top:8px}
.claim-attempt-card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.claim-attempt-card--ok{border-color:#86efac;background:#f0fdf4}
.claim-attempt-card--fail{border-color:#fecaca;background:#fff5f5}
.claim-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.claim-card-head time{font-size:12px;color:var(--muted);font-weight:700;line-height:1.3}
.claim-card-fields{margin:0;padding:0}
.claim-card-row{display:grid;grid-template-columns:minmax(92px,36%) 1fr;gap:4px 10px;padding:7px 0;border-bottom:1px solid #eef2f7}
.claim-card-row:last-child{border-bottom:none;padding-bottom:0}
.claim-card-row dt{margin:0;font-size:11px;font-weight:800;text-transform:uppercase;color:var(--muted);letter-spacing:.02em;line-height:1.3}
.claim-card-row dd{margin:0;font-size:13px;line-height:1.45;color:var(--navy);word-break:break-word}
.claim-card-row dd a{color:var(--teal);font-weight:700;text-decoration:none}
.claim-card-row dd a:hover{text-decoration:underline}
.claim-summary-kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0 0 12px}
@media (max-width:520px){
  .claim-summary-kpis{grid-template-columns:1fr;gap:6px}
  .claim-card-row{grid-template-columns:1fr;gap:2px;padding:8px 0}
  .claim-card-row dt{font-size:10px}
  .modal-h h3{font-size:14px;line-height:1.25;max-width:calc(100% - 52px)}
}
@media (min-width:521px){.modal-back{align-items:center}.modal{border-radius:12px;max-height:80vh}}
"""

OLD_CSS_ANCHOR = ".modal .badge.open{background:#e0f2fe;color:#075985}\n@media (min-width:700px){.modal-back{align-items:center}.modal{border-radius:12px;max-height:80vh}}"

OLD_TABLE_BLOCK = """      html+="<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0 0 12px'>";
      html+="<div class='kpi' style='padding:8px'><div class='l'>Blocked</div><div class='v' style='font-size:22px;color:#991b1b'>"+nFail+"</div><div class='s'>Tried form — failed</div></div>";
      html+="<div class='kpi' style='padding:8px'><div class='l'>Left</div><div class='v' style='font-size:22px'>"+nLeft+"</div><div class='s'>Opened claim, never submitted</div></div>";
      html+="<div class='kpi' style='padding:8px'><div class='l'>Members</div><div class='v' style='font-size:22px;color:#166534'>"+nOk+"</div><div class='s'>Should be on /users</div></div>";
      html+="</div>";
      html+="<p class='note'><b>Blocked</b> = real sign-up problem (fix it). <b>Left</b> = opened claim then walked away (not a bug). <b>Who tried</b> = email/name if they typed one; older visits often show “Didn't leave email” — use the Sailor column. <b>Already on /users?</b> = that sailor profile already has a member account (they should Sign in, not Claim).</p>";
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
        var how=esc(r.entry_how||"—");
        if(r.how_signed_up) how="<b>"+esc(r.how_signed_up)+"</b><div class='note' style='margin:2px 0 0'>"+esc(r.entry_how||"")+"</div>";
        html+="<tr"+(oc==="succeeded"?" style='background:#f0fdf4'":"")+"><td>"+esc(when)+"</td><td>"+who+"</td><td>"+sn+"</td><td>"+how+"</td><td><span class='badge "+badge+"'>"+esc(r.status||oc)+"</span></td><td><b>"+esc(r.problem||"—")+"</b></td><td>"+onU+"</td></tr>";
      });
      html+="</tbody></table></div>";"""

NEW_CARD_BLOCK = """      html+="<div class='claim-summary-kpis'>";
      html+="<div class='kpi' style='padding:8px'><div class='l'>Blocked</div><div class='v' style='font-size:22px;color:#991b1b'>"+nFail+"</div><div class='s'>Tried form — failed</div></div>";
      html+="<div class='kpi' style='padding:8px'><div class='l'>Left</div><div class='v' style='font-size:22px'>"+nLeft+"</div><div class='s'>Opened claim, never submitted</div></div>";
      html+="<div class='kpi' style='padding:8px'><div class='l'>Members</div><div class='v' style='font-size:22px;color:#166534'>"+nOk+"</div><div class='s'>Should be on /users</div></div>";
      html+="</div>";
      html+="<p class='note'><b>Blocked</b> = real sign-up problem (fix it). <b>Left</b> = opened claim then walked away (not a bug). Each card below is one person who tried.</p>";
      html+="<div class='claim-attempt-cards'>";
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
        var how=esc(r.entry_how||"—");
        if(r.how_signed_up) how="<b>"+esc(r.how_signed_up)+"</b><div class='note' style='margin:2px 0 0'>"+esc(r.entry_how||"")+"</div>";
        var cardCls="claim-attempt-card"+(oc==="succeeded"?" claim-attempt-card--ok":(oc==="failed"?" claim-attempt-card--fail":""));
        html+="<article class='"+cardCls+"'>";
        html+="<div class='claim-card-head'><time datetime='"+esc(String(r.when||""))+"'>"+esc(when)+"</time><span class='badge "+badge+"'>"+esc(r.status||oc)+"</span></div>";
        html+="<dl class='claim-card-fields'>";
        html+="<div class='claim-card-row'><dt>Who tried</dt><dd>"+who+"</dd></div>";
        html+="<div class='claim-card-row'><dt>Sailor</dt><dd>"+sn+"</dd></div>";
        html+="<div class='claim-card-row'><dt>How started</dt><dd>"+how+"</dd></div>";
        html+="<div class='claim-card-row'><dt>Problem</dt><dd><b>"+esc(r.problem||"—")+"</b></dd></div>";
        html+="<div class='claim-card-row'><dt>On /users?</dt><dd>"+onU+"</dd></div>";
        html+="</dl></article>";
      });
      html+="</div>";"""

if OLD_CSS_ANCHOR in text and "claim-attempt-cards" not in text:
    text = text.replace(OLD_CSS_ANCHOR, CSS.strip() + "\n", 1)
    print("ok css")
elif "claim-attempt-cards" in text:
    print("skip css (already patched)")
else:
    print("WARN css anchor missing")

if OLD_TABLE_BLOCK in text:
    text = text.replace(OLD_TABLE_BLOCK, NEW_CARD_BLOCK, 1)
    print("ok card layout")
elif "claim-attempt-cards" in text:
    print("skip js (already patched)")
else:
    print("WARN table block missing")
    raise SystemExit(1)

API.write_text(text, encoding="utf-8")
print("WROTE", API)
