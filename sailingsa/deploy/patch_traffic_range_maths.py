#!/usr/bin/env python3
"""Make /traffic maths + section labels follow selected range; Claim card == popup."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
t = API.read_text(encoding="utf-8", errors="replace")
bak = Path(f"/root/backups/api.py.range_maths.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(API, bak)
print("BACKUP", bak)

# --- 1) Overview claim_* = same digest as claim-attempts popup ---
old_ov = '''            claim_open = max(left_n, max(0, claim_attempts - claim_ok - claim_fail))
            # Card total must equal ok + fail + left (same story as popup)
            claim_attempts = max(claim_attempts, claim_ok + claim_fail + claim_open)
            cur.execute("RELEASE SAVEPOINT claimref")
        except Exception:
            try:
                cur.execute("ROLLBACK TO SAVEPOINT claimref")
            except Exception:
                pass

        # Card value: live window when range=live, else signed humans in range
'''

new_ov = '''            claim_open = max(left_n, max(0, claim_attempts - claim_ok - claim_fail))
            # Card total must equal ok + fail + left (same story as popup)
            claim_attempts = max(claim_attempts, claim_ok + claim_fail + claim_open)
            cur.execute("RELEASE SAVEPOINT claimref")
        except Exception:
            try:
                cur.execute("ROLLBACK TO SAVEPOINT claimref")
            except Exception:
                pass

        # Force Claim KPI to the SAME digest as the popup (authoritative)
        try:
            dig = lean_traffic_api_claim_attempts(request)
            if hasattr(dig, "body") and dig.body:
                import json as _json
                _cd = _json.loads(dig.body)
                if isinstance(_cd, dict) and _cd.get("ok"):
                    claim_attempts = int(_cd.get("attempt_count") or 0)
                    claim_ok = int(_cd.get("success_count") or 0)
                    claim_fail = int(_cd.get("fail_count") or 0)
                    claim_open = int(_cd.get("left_count") or 0)
                    claim_accounts_created = max(int(claim_accounts_created or 0), claim_ok)
        except Exception:
            pass

        # Card value: live window when range=live, else signed humans in range
'''

if old_ov not in t:
    raise SystemExit("overview claim lift anchor missing")
t = t.replace(old_ov, new_ov, 1)
print("OK overview=claim digest")

# --- 2) Most popular on Live uses Live window (1 hour), not 24h ---
old_top = '''    # Live window is too short for a useful Most popular list — use 24h history.
    top_since = "24 hours" if range_key == "live" else since_sql
'''
new_top = '''    # Always match the selected range (Live = last hour).
    top_since = since_sql
'''
if old_top not in t:
    print("WARN top_since already changed")
else:
    t = t.replace(old_top, new_top, 1)
    print("OK top uses selected range")

old_pop = '''                "popular_range": "24h" if range_key == "live" else range_key,
'''
new_pop = '''                "popular_range": range_key,
'''
if old_pop in t:
    t = t.replace(old_pop, new_pop, 1)
    print("OK popular_range label")

# --- 3) Raise claim-attempts event limit so Ever/30d is not truncated ---
old_lim = '''            ORDER BY occurred_at DESC
            LIMIT 250
'''
# only first occurrence inside claim-attempts - be specific
marker = 'WHERE funnel_name = \'claim_profile\''
# find claim-attempts LIMIT 250 near claim_page_loaded list
idx = t.find('def lean_traffic_api_claim_attempts')
if idx < 0:
    raise SystemExit("claim-attempts missing")
chunk = t[idx:idx+8000]
if "LIMIT 250" not in chunk:
    print("WARN LIMIT 250 not in claim-attempts head")
else:
    t = t[:idx] + chunk.replace("LIMIT 250", "LIMIT 2000", 1) + t[idx+8000:]
    print("OK claim limit 2000")

# --- 4) UI: range banner + labels follow RANGE; Claim card never uses overview estimate ---
old_scale = '''  <p class="note" id="scaleNote">Live = last hour (moving wave). Super-admin (Kevin/Tim/agent) ignored. Dev URLs filtered out. Totals = real public visitors only. Bots quarantined / excluded. Direct + Google + Facebook + Other = Visitors. Claim ok + fail + open = attempts.</p>
'''
# may already have been partially updated
if 'id="scaleNote"' in t:
    import re
    t2, n = re.subn(
        r'  <p class="note" id="scaleNote">[\s\S]*?</p>\n',
        '  <p class="note" id="rangeBanner" style="font-weight:800;color:#08184a;font-size:13px;margin:0 0 6px">Showing: <span id="rangeBannerVal">—</span></p>\n'
        '  <p class="note" id="scaleNote">Every box below is for the range you picked only. Staff browsing ignored. Fake bots removed. Direct + Google + Facebook + Other = Visitors. Claim card = popup (members + blocked + left).</p>\n',
        t,
        count=1,
    )
    if n:
        t = t2
        print("OK range banner")
    else:
        print("WARN scaleNote replace failed")

# Hardcoded Real visitors / Most popular notes
t = t.replace(
    '<section class="card" style="margin-top:12px"><h2>Most popular</h2><p class="note" id="topRangeNote">Real pages (scroll/click visitors). On Live tab this still uses last 24h so the list is not empty.</p>',
    '<section class="card" style="margin-top:12px"><h2>Most popular pages</h2><p class="note" id="topRangeNote">Pages people opened in the selected range.</p>',
    1,
)
t = t.replace(
    '<h2 id="realVisitorsTitle">Real visitors — 24h</h2><p class="note" id="realSinceNote">In selected range — every real visitor (scroll/click). All pages in trail. Nothing hidden if real.</p>',
    '<h2 id="realVisitorsTitle">Real visitors</h2><p class="note" id="realSinceNote">Real people who browsed in the selected range. Tap ▶ for pages.</p>',
    1,
)

# JS: update range banner on loadAll / range change
old_set = '''  function setRangeButtons(){
    document.querySelectorAll("#ranges button").forEach(function(b){
      b.classList.toggle("on", b.getAttribute("data-r")===RANGE);
    });
  }
'''
new_set = '''  function rangeLabel(){
    return RANGE==="live"?"Live (last hour)":(RANGE==="24h"?"Last 24 hours":(RANGE==="7d"?"Last 7 days":(RANGE==="30d"?"Last 30 days":(RANGE==="ever"?"Ever (all time)":RANGE))));
  }
  function setRangeButtons(){
    document.querySelectorAll("#ranges button").forEach(function(b){
      b.classList.toggle("on", b.getAttribute("data-r")===RANGE);
    });
    var rb=$("rangeBannerVal"); if(rb) rb.textContent=rangeLabel();
  }
'''
if old_set not in t:
    print("WARN setRangeButtons missing")
else:
    t = t.replace(old_set, new_set, 1)
    print("OK rangeLabel")

# renderTop note must say selected range
old_rn = '''    var note=$("topRangeNote");
'''
# find renderTop body for note text
import re
m = re.search(r'function renderTop\([\s\S]{0,800}?topRangeNote[\s\S]{0,400}?textContent\s*=\s*[^;]+;', t)
if m:
    print("renderTop note block found", m.group(0)[-120:])

# Patch common top note assignments
for old, new in [
    (
        'Real pages (scroll/click visitors). On Live tab this still uses last 24h so the list is not empty.',
        'Pages people opened in the selected range.',
    ),
    (
        'scroll/click visitors — last 24h (history kept even on Live).',
        'for the selected range.',
    ),
    (
        'scroll/click visitors — range ',
        'for range ',
    ),
]:
    if old in t:
        t = t.replace(old, new)
        print("OK note", old[:40])

# Claim sub default in HTML
t = t.replace(
    '<div class="s" id="kClaimSub">attempts · tap for detail</div>',
    '<div class="s" id="kClaimSub">for selected range · tap for detail</div>',
    1,
)

# Ensure loadAll sets claim from digest AND mirrors into OVERVIEW_CACHE so nothing else shows stale 5
old_claim_js = '''      fetchJson("/traffic/api/claim-attempts?range="+encodeURIComponent(RANGE)).then(function(cd){
        if(!cd || !cd.ok) return;
        var nTry=Number(cd.attempt_count||0), nOk=Number(cd.success_count||0), nFail=Number(cd.fail_count||0), nLeft=Number(cd.left_count||0);
        if($("kClaim")) $("kClaim").textContent=String(nTry);
        if($("kClaimSub")) $("kClaimSub").textContent=nOk+" members · "+nFail+" blocked · "+nLeft+" left · tap for detail";
'''
new_claim_js = '''      if($("kClaim")) $("kClaim").textContent="…";
      if($("kClaimSub")) $("kClaimSub").textContent="loading for "+rangeLabel()+"…";
      fetchJson("/traffic/api/claim-attempts?range="+encodeURIComponent(RANGE)).then(function(cd){
        if(!cd || !cd.ok) return;
        var nTry=Number(cd.attempt_count||0), nOk=Number(cd.success_count||0), nFail=Number(cd.fail_count||0), nLeft=Number(cd.left_count||0);
        if($("kClaim")) $("kClaim").textContent=String(nTry);
        if($("kClaimSub")) $("kClaimSub").textContent=nOk+" members · "+nFail+" blocked · "+nLeft+" left · "+rangeLabel();
        try{
          if(OVERVIEW_CACHE){
            OVERVIEW_CACHE.claim_attempts=nTry;
            OVERVIEW_CACHE.claim_ok=nOk;
            OVERVIEW_CACHE.claim_fail=nFail;
            OVERVIEW_CACHE.claim_open=nLeft;
          }
        }catch(eC){}
'''
if old_claim_js not in t:
    raise SystemExit("claim js anchor missing")
t = t.replace(old_claim_js, new_claim_js, 1)
print("OK claim js")

# Modal note must stress range
old_modal = '''      if(note) note.innerHTML="<b>"+esc(String(d.summary||("")))+"</b><br>Range "+esc(d.range||RANGE)+". Members list: <a href='/users' target='_blank' rel='noopener'>/users</a>.";
'''
new_modal = '''      if(note) note.innerHTML="<b>"+esc(String(d.summary||("")))+"</b><br>Only <b>"+esc(rangeLabel())+"</b> (range "+esc(d.range||RANGE)+"). Same total as the Claim card. Members: <a href='/users' target='_blank' rel='noopener'>/users</a>.";
'''
if old_modal in t:
    t = t.replace(old_modal, new_modal, 1)
    print("OK modal note")

API.write_text(t, encoding="utf-8")
print("DONE")
