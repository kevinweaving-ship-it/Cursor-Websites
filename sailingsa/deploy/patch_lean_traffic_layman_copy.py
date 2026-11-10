#!/usr/bin/env python3
"""Rewrite /traffic UI copy to plain English — no tech jargon for laymen."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
t = API.read_text(encoding="utf-8", errors="replace")
bak = Path(f"/root/backups/api.py.traffic_layman.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(API, bak)
print("BACKUP", bak)

repls = [
    # Top scale note
    (
        '  <p class="note" id="scaleNote">Live = last hour (moving wave). Super-admin (Kevin/Tim/agent) ignored. Dev URLs filtered out. Totals = real public visitors only. Bots quarantined / excluded. Direct + Google + Facebook + Other = Visitors. Claim ok + fail + open = attempts.</p>',
        '  <p class="note" id="scaleNote">Pick a range above (Live / 24h / 7d / 30d / Ever) — every number below is for that range only. Staff browsing is ignored. Fake bots are removed. Direct + Google + Facebook + Other = Visitors. Claim: members + blocked + left = total attempts.</p>',
    ),
    # KPI subs
    (
        '<div class="kpi"><div class="l">Live now</div><div class="v" id="kLive">—</div><div class="s" id="kLiveSub">last 15 min</div></div>',
        '<div class="kpi"><div class="l">On the site now</div><div class="v" id="kLive">—</div><div class="s" id="kLiveSub">people browsing right now</div></div>',
    ),
    (
        '<div class="kpi"><div class="l">Visitors</div><div class="v" id="kVis">—</div><div class="s">unique in range</div></div>',
        '<div class="kpi"><div class="l">Visitors</div><div class="v" id="kVis">—</div><div class="s">different people in this range</div></div>',
    ),
    (
        '<div class="kpi"><div class="l">Page hits</div><div class="v" id="kHits">—</div><div class="s">URLs opened</div></div>',
        '<div class="kpi"><div class="l">Pages opened</div><div class="v" id="kHits">—</div><div class="s">how many pages people opened</div></div>',
    ),
    (
        '<div class="kpi"><div class="l" id="kSignedLabel">Signed-in (public)</div><div class="v" id="kSigned">—</div><div class="s" id="kSignedSub">vs guests</div></div>',
        '<div class="kpi"><div class="l" id="kSignedLabel">Signed-in members</div><div class="v" id="kSigned">—</div><div class="s" id="kSignedSub">vs guests</div></div>',
    ),
    (
        '<div class="kpi"><div class="l">Direct</div><div class="v" id="kDirect">—</div><div class="s" id="kDirectSub">no external referrer</div></div>',
        '<div class="kpi"><div class="l">Came direct</div><div class="v" id="kDirect">—</div><div class="s" id="kDirectSub">typed the site / bookmark / app</div></div>',
    ),
    (
        '<div class="kpi"><div class="l">Google</div><div class="v" id="kGoogle">—</div><div class="s" id="kGoogleSub">via Google</div></div>',
        '<div class="kpi"><div class="l">From Google</div><div class="v" id="kGoogle">—</div><div class="s" id="kGoogleSub">arrived via Google search / ads</div></div>',
    ),
    (
        '<div class="kpi"><div class="l">Facebook</div><div class="v" id="kFb">—</div><div class="s" id="kFbSub">via Facebook</div></div>',
        '<div class="kpi"><div class="l">From Facebook</div><div class="v" id="kFb">—</div><div class="s" id="kFbSub">arrived via Facebook</div></div>',
    ),
    (
        '      <div class="l">Claim / sign-up</div><div class="v" id="kClaim">—</div><div class="s" id="kClaimSub">attempts · tap for detail</div>',
        '      <div class="l">Claim / sign-up</div><div class="v" id="kClaim">—</div><div class="s" id="kClaimSub">tap for who tried &amp; why</div>',
    ),
    (
        '    <p class="note" id="claimFunnelNote">Tap the Claim / sign-up card for who tried, which sailor, why they failed, and whether they show on <a href="/users">/users</a> after success.</p>',
        '    <p class="note" id="claimFunnelNote">Tap the Claim card for a plain list: who tried, which sailor, what happened, and if they are on <a href="/users">Registered Users</a>.</p>',
    ),
    # Live note
    (
        '        <p class="note">Last 15 min. Who = IP (unique visitor). Sailor name is only a soft hint from pages in this session — not locked to the IP. ▶ shows URL trail + dwell. New visitors stay on Live while evaluating. Scroll/click = real until done. Idle 30s with no scroll/click = bot final → quarantine.</p>',
        '        <p class="note">People on the site in the last 15 minutes. Tap ▶ to see which pages they opened and how long they stayed. Real people scroll or tap; silent scrapers are filtered out automatically.</p>',
    ),
    # Popular / real visitors notes
    (
        '<section class="card" style="margin-top:12px"><h2>Most popular</h2><p class="note" id="topRangeNote">Real pages (scroll/click visitors). On Live tab this still uses last 24h so the list is not empty.</p><div id="topBox"><p class="note">Loading…</p></div></section>',
        '<section class="card" style="margin-top:12px"><h2>Most popular pages</h2><p class="note" id="topRangeNote">Pages real people opened in this range. On Live, this list uses the last 24 hours so it is not empty.</p><div id="topBox"><p class="note">Loading…</p></div></section>',
    ),
    (
        '<section class="card" style="margin-top:12px"><h2 id="realVisitorsTitle">Real visitors — 24h</h2><p class="note" id="realSinceNote">In selected range — every real visitor (scroll/click). All pages in trail. Nothing hidden if real.</p><div id="offlineBox"><p class="note">Loading…</p></div></section>',
        '<section class="card" style="margin-top:12px"><h2 id="realVisitorsTitle">Real visitors — 24h</h2><p class="note" id="realSinceNote">Everyone who really browsed in this range (scrolled or tapped). Tap ▶ for their page list.</p><div id="offlineBox"><p class="note">Loading…</p></div></section>',
    ),
    (
        '<section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineFbToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Facebook share crawls <span id="offlineFbCount" class="note" style="font-weight:600"></span></h2><p class="note">Link-preview crawls when you post (not people browsing inside Facebook). FB in-app humans count as real.</p><div id="offlineFbBox" hidden><p class="note">Loading…</p></div></section>',
        '<section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineFbToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Facebook link previews <span id="offlineFbCount" class="note" style="font-weight:600"></span></h2><p class="note">Automatic previews when someone posts a SailingSA link on Facebook — not a real person browsing. Real people using Facebook\'s in-app browser still count as visitors.</p><div id="offlineFbBox" hidden><p class="note">Loading…</p></div></section>',
    ),
    (
        '<section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineBotsToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Other bots <span id="offlineBotsCount" class="note" style="font-weight:600"></span></h2><p class="note">Hidden by default. Scrapers / probes — ignore.</p><div id="offlineBotsBox" hidden><p class="note">Loading…</p></div></section>',
        '<section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineBotsToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Fake traffic (bots) <span id="offlineBotsCount" class="note" style="font-weight:600"></span></h2><p class="note">Hidden by default. Automated junk — ignore these; they are not real visitors.</p><div id="offlineBotsBox" hidden><p class="note">Loading…</p></div></section>',
    ),
    (
        '      <h2 id="lookTitle">What they look at</h2>\n      <p class="note">Hover the graph — this panel + popular update for that minute/hour/day.</p>',
        '      <h2 id="lookTitle">What they look at</h2>\n      <p class="note">Hover or tap the activity graph to see what people opened in that time slice.</p>',
    ),
    (
        '        <h2>Live now — who / where</h2>',
        '        <h2>On the site now — who &amp; where</h2>',
    ),
]

n = 0
for old, new in repls:
    if old not in t:
        print("MISSING", old[:80].replace("\n", " "))
        continue
    t = t.replace(old, new, 1)
    n += 1
    print("OK", n)

# JS dynamic strings (may appear multiple times — replace carefully)
js_repls = [
    (
        '+(o.quarantine_ips?(" · "+o.quarantine_ips+" bots quarantined"):"")',
        '+(o.quarantine_ips?(" · "+o.quarantine_ips+" bots filtered out"):"")',
    ),
    (
        '$("kLiveSub").textContent="total online · last "+(o.live_minutes||15)+" min window"+(o.live_signed?(" · "+o.live_signed+" signed"):"")+(o.quarantine_ips?(" · "+o.quarantine_ips+" bots quarantined"):"");',
        '$("kLiveSub").textContent="people online · last "+(o.live_minutes||15)+" min"+(o.live_signed?(" · "+o.live_signed+" signed in"):"")+(o.quarantine_ips?(" · "+o.quarantine_ips+" bots filtered"):"");',
    ),
    (
        'if($("kSignedLabel")) $("kSignedLabel").textContent=(RANGE==="live")?"Signed-in live":"Signed-in";',
        'if($("kSignedLabel")) $("kSignedLabel").textContent=(RANGE==="live")?"Signed-in now":"Signed-in members";',
    ),
    (
        'if($("kSignedSub")) $("kSignedSub").textContent=String(o.guests_card!=null?o.guests_card:o.live_anon||0)+" guests"+(RANGE==="live")?" live":" in range");',
        'if($("kSignedSub")) $("kSignedSub").textContent=String(o.guests_card!=null?o.guests_card:o.live_anon||0)+" guests"+(RANGE==="live"?" now":" in this range");',
    ),
    (
        'if($("kDirectSub")) $("kDirectSub").textContent=String(o.direct_landings||0)+" direct · of "+String(o.visitors||0)+" visitors";',
        'if($("kDirectSub")) $("kDirectSub").textContent=String(o.direct_landings||0)+" came direct · of "+String(o.visitors||0)+" visitors";',
    ),
    (
        'if($("kGoogleSub")) $("kGoogleSub").textContent=String(o.google_landings||0)+" via Google · of "+String(o.visitors||0)+" visitors";',
        'if($("kGoogleSub")) $("kGoogleSub").textContent=String(o.google_landings||0)+" from Google · of "+String(o.visitors||0)+" visitors";',
    ),
    (
        'if($("kFbSub")) $("kFbSub").textContent=String(o.facebook_landings||0)+" via Facebook · of "+String(o.visitors||0)+" visitors";',
        'if($("kFbSub")) $("kFbSub").textContent=String(o.facebook_landings||0)+" from Facebook · of "+String(o.visitors||0)+" visitors";',
    ),
]

for old, new in js_repls:
    c = t.count(old)
    if c == 0:
        print("JS MISSING", old[:70])
        continue
    t = t.replace(old, new)
    print("JS OK", c, old[:50])

# Real visitors title/note JS updates if present
rv_repls = [
    (
        'In selected range — every real visitor (scroll/click). All pages in trail. Nothing hidden if real.',
        'Everyone who really browsed in this range (scrolled or tapped). Tap ▶ for their page list.',
    ),
    (
        'In selected range — every real visitor (scroll/click). All pages in trail. Nothing hidden if real. Matches top range.',
        'Everyone who really browsed in this range (scrolled or tapped). Tap ▶ for their page list.',
    ),
    (
        'Real pages (scroll/click visitors). On Live tab this still uses last 24h so the list is not empty.',
        'Pages real people opened in this range. On Live, this list uses the last 24 hours so it is not empty.',
    ),
    (
        'scroll/click visitors — last 24h (history kept even on Live).',
        'real people — last 24 hours (kept even on Live).',
    ),
    (
        'scroll/click visitors — range ',
        'real people — range ',
    ),
]
for old, new in rv_repls:
    c = t.count(old)
    if c:
        t = t.replace(old, new)
        print("RV OK", c, old[:50])
    else:
        print("RV skip", old[:50])

# Badge labels in live list if very techy
for old, new in [
    ('"Bot "+r.ip', '"Bot"'),
    ('"Guest "+r.ip', '"Guest"'),
    ('"Staff "+r.ip', '"Staff"'),
]:
    # Don't remove IP entirely from display if used for identity - check context
    pass

# Login required message
t2 = t.replace(
    'throw new Error("Login / admin required");',
    'throw new Error("Please sign in as admin to view traffic");',
)
if t2 != t:
    t = t2
    print("OK login msg")

API.write_text(t, encoding="utf-8")
print("DONE")
