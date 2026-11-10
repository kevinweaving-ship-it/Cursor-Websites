#!/usr/bin/env python3
"""Live patch: sailors copy only + events keep SSR cards on load."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

# --- sailors page copy ---
new_about = '        "Search active South Australian sailors"'
for old in (
    '        "Search active South African sailors — those with regatta results on SailingSA. "\n        "This is not the full SA Sailing ID register; only sailors who have raced appear here."',
    '        "Search all South African sailors with complete regatta results, rankings, and performance history. "\n        "SailingSA is the most comprehensive South African sailing results database for sailors."',
):
    if old in t:
        t = t.replace(old, new_about, 1)
        print("patched sailors about")
        break

t = t.replace(
    '<script src="/js/hub-sailor-directory.js?v=20260823dir4"></script>',
    '<script src="/js/hub-sailor-directory.js?v=20260823dir5"></script>',
)
t = t.replace(
    '<script src="/js/hub-sailor-directory.js?v=20260823dir3"></script>',
    '<script src="/js/hub-sailor-directory.js?v=20260823dir5"></script>',
)
t = t.replace(
    '<p class="sailor-directory-hint" id="sailors-hint">Search active sailors by name, SA ID, club, or class.</p>',
    "",
)
t = t.replace(
    '<p class="sailor-directory-hint" id="sailors-hint">Loading sailors…</p>',
    "",
)
if '.sailor-directory-hint{display:none!important;}' not in t:
    t = t.replace(
        '.profile-card{background:#fff;border-radius:8px;border:2px solid #001f3f;padding:0.5rem 0.85rem;cursor:pointer;line-height:1.35;}',
        '.profile-card{background:#fff;border-radius:8px;border:2px solid #001f3f;padding:0.5rem 0.85rem;cursor:pointer;line-height:1.35;}.sailor-directory-hint{display:none!important;}',
        1,
    )

# --- events: keep SSR cards; only re-render on search ---
old_events_init = """  var searchEl = document.getElementById("events-dashboard-search");
  if(searchEl) searchEl.addEventListener("input", function(){ applyEventsFilter(); });
  try {
    applyEventsFilter();
  } catch (err) {
    try { activateTab(hasLiveTab() && document.getElementById("cards-live") ? "live" : "upcoming"); } catch (e2) {}
  }
})();"""

new_events_init = """  function wireShowMore(panelId, list){
    var container = document.getElementById("cards-" + panelId);
    var btnWrap = document.getElementById("show-more-" + panelId);
    var btn = document.getElementById("btn-more-" + panelId);
    if(!container || !btn) return;
    var shown = container.querySelectorAll(".sa-home-regatta-card, .event-card").length;
    if(btnWrap) btnWrap.classList.toggle("hidden", shown >= list.length);
    btn.onclick = function(){
      var cur = container.querySelectorAll(".sa-home-regatta-card, .event-card").length;
      var end = Math.min(cur + INITIAL, list.length);
      for(var i = cur; i < end; i++)
        container.insertAdjacentHTML("beforeend", renderCard(list[i], panelId, i + 1, list.length));
      if(btnWrap) btnWrap.classList.toggle("hidden", end >= list.length);
    };
  }
  function initEventsPage(){
    var fu = DATA.upcoming || [];
    var fl = DATA.live || [];
    var fp = DATA.past || [];
    try { updateTabCounts(fu, fl, fp); } catch (e0) {}
    var hasSsr = !!document.querySelector("#cards-upcoming .sa-home-regatta-card, #cards-past .sa-home-regatta-card, #cards-live .sa-home-regatta-card");
    if(hasSsr){
      wireShowMore("upcoming", fu);
      wireShowMore("live", fl);
      wireShowMore("past", fp);
      try { activateTab(firstTabWithEvents()); } catch (e1) {}
      return;
    }
    try { applyEventsFilter(); } catch (err) {
      try { activateTab(firstTabWithEvents()); } catch (e2) {}
    }
  }
  var searchEl = document.getElementById("events-dashboard-search");
  if(searchEl) searchEl.addEventListener("input", function(){ applyEventsFilter(); });
  initEventsPage();
})();"""

if old_events_init in t:
    t = t.replace(old_events_init, new_events_init, 1)
    print("patched events init (keep SSR)")
elif "function initEventsPage()" in t:
    print("events init already patched")
else:
    print("WARN: events init anchor not found")

path.write_text(t, encoding="utf-8")
print("done", path)
