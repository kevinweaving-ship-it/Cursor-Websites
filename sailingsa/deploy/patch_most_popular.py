#!/usr/bin/env python3
"""Most popular: use 24h history on Live range; move section above long lists."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

def rep(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f"FAIL {label}")
    text = text.replace(old, new, 1)
    print("OK", label)

# 1) top API: live range still shows 24h popular pages
rep(
    '''    range_key, since_sql, _ = _lean_traffic_parse_range(request.query_params.get("range"))
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SET LOCAL statement_timeout = '12000'")
        except Exception:
            pass
        unified = _lean_traffic_unified_sql(since_sql)
''',
    '''    range_key, since_sql, _ = _lean_traffic_parse_range(request.query_params.get("range"))
    # Live window is too short for a useful Most popular list — use 24h history.
    top_since = "24 hours" if range_key == "live" else since_sql
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SET LOCAL statement_timeout = '12000'")
        except Exception:
            pass
        unified = _lean_traffic_unified_sql(top_since)
''',
    "top 24h on live",
)

# Add popular_range to JSON response
rep(
    '''                "ok": True,
                "range": range_key,
                "top_paths": top_paths,
                "entities": by_type,
                "popularity": "same_hits_visitors_as_pages",
''',
    '''                "ok": True,
                "range": range_key,
                "popular_range": "24h" if range_key == "live" else range_key,
                "top_paths": top_paths,
                "entities": by_type,
                "popularity": "same_hits_visitors_as_pages",
''',
    "popular_range field",
)

# 2) Move Most popular above Real visitors (inside live column, after liveBox)
# Current broken-ish order: liveBox, Real, FB, Bots, /section, Most popular
# Want: liveBox, Most popular, Real, FB, Bots, /section

old_block = '''<div id="liveBox"><p class="note">Loading…</p></div>
<section class="card" style="margin-top:12px"><h2>Real visitors — since reset</h2><p class="note" id="realSinceNote">Every real visitor (scroll/click). All pages in the trail. Nothing hidden if real.</p><div id="offlineBox"><p class="note">Loading…</p></div></section><section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineFbToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Facebook share crawls <span id="offlineFbCount" class="note" style="font-weight:600"></span></h2><p class="note">Link-preview crawls when you post (not people browsing inside Facebook). FB in-app humans count as real.</p><div id="offlineFbBox" hidden><p class="note">Loading…</p></div></section><section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineBotsToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Other bots <span id="offlineBotsCount" class="note" style="font-weight:600"></span></h2><p class="note">Hidden by default. Scrapers / probes — ignore.</p><div id="offlineBotsBox" hidden><p class="note">Loading…</p></div></section>
      </section>
      <section class="card">
        <h2>Most popular</h2>
        <div id="topBox"><p class="note">Loading…</p></div>
      </section>'''

new_block = '''<div id="liveBox"><p class="note">Loading…</p></div>
<section class="card" style="margin-top:12px"><h2>Most popular</h2><p class="note" id="topRangeNote">Real pages (scroll/click visitors). On Live tab this still uses last 24h so the list is not empty.</p><div id="topBox"><p class="note">Loading…</p></div></section>
<section class="card" style="margin-top:12px"><h2>Real visitors — since reset</h2><p class="note" id="realSinceNote">Every real visitor (scroll/click). All pages in the trail. Nothing hidden if real.</p><div id="offlineBox"><p class="note">Loading…</p></div></section><section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineFbToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Facebook share crawls <span id="offlineFbCount" class="note" style="font-weight:600"></span></h2><p class="note">Link-preview crawls when you post (not people browsing inside Facebook). FB in-app humans count as real.</p><div id="offlineFbBox" hidden><p class="note">Loading…</p></div></section><section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineBotsToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Other bots <span id="offlineBotsCount" class="note" style="font-weight:600"></span></h2><p class="note">Hidden by default. Scrapers / probes — ignore.</p><div id="offlineBotsBox" hidden><p class="note">Loading…</p></div></section>
      </section>'''

rep(old_block, new_block, "move most popular up")

# 3) UI: update topRangeNote from API
old_render = '''function renderTop(d){
    TOP_CACHE=d;
    var ents=d.entities||{};
'''
new_render = '''function renderTop(d){
    TOP_CACHE=d;
    var note=$("topRangeNote");
    if(note){
      var pr=d.popular_range||d.range||"";
      note.textContent = (pr==="24h"||pr==="live")
        ? "Real pages from scroll/click visitors — last 24h (history kept even on Live)."
        : ("Real pages from scroll/click visitors — range "+pr+".");
    }
    var ents=d.entities||{};
'''
rep(old_render, new_render, "top note")

# Empty message clearer
rep(
    '''$("topBox").innerHTML="<div class=\\"table-scroll\\">"+(html||"<p class='note'>No popular pages yet.</p>")+"</div>";
  }''',
    '''if(!html || ((!(d.entities)||!Object.keys(d.entities).length) && !(d.top_paths||[]).length)){
      html="<p class='note'>No popular real pages in this window yet.</p>";
    }
    $("topBox").innerHTML="<div class=\\"table-scroll\\">"+html+"</div>";
  }''',
    "empty message",
)

if text == orig:
    sys.exit("NO CHANGE")
compile(text, str(API), "exec")
API.write_text(text, encoding="utf-8")
print("WROTE", len(text) - len(orig))
