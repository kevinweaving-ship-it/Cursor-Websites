#!/usr/bin/env python3
"""Session total = first arrival → last action (not 15m / NOW open inflation). Offline box HTML."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-session-total-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # --- 1) Idle finalize: close at last_activity, not NOW ---
    old_idle = '''            UPDATE public.public_page_hits h
            SET left_at = NOW(),
                dwell_seconds = GREATEST(
                    0,
                    EXTRACT(EPOCH FROM (NOW() - h.occurred_at))::int
                )
            FROM public.public_sessions s
            WHERE h.left_at IS NULL
              AND h.ip_address IS NOT NULL
              AND TRIM(h.ip_address) <> ''
              AND s.ip_address = h.ip_address
              AND s.last_activity IS NOT NULL
              AND s.last_activity < NOW() - make_interval(secs => %s)
              AND h.occurred_at <= s.last_activity
'''
    new_idle = '''            UPDATE public.public_page_hits h
            SET left_at = s.last_activity,
                dwell_seconds = GREATEST(
                    0,
                    EXTRACT(EPOCH FROM (s.last_activity - h.occurred_at))::int
                )
            FROM public.public_sessions s
            WHERE h.left_at IS NULL
              AND h.ip_address IS NOT NULL
              AND TRIM(h.ip_address) <> ''
              AND s.ip_address = h.ip_address
              AND s.last_activity IS NOT NULL
              AND s.last_activity < NOW() - make_interval(secs => %s)
              AND h.occurred_at <= s.last_activity
'''
    if old_idle not in text:
        raise SystemExit("idle finalize SQL not found")
    text = text.replace(old_idle, new_idle, 1)

    # --- 2) Open dwell in trail: use session last_activity, not NOW ---
    # Replace the open-hit dwell calc block inside _lean_session_page_trail
    old_open = '''            open_hit = left is None
            if dwell is None and open_hit and occ is not None:
                try:
                    cur.execute(
                        "SELECT GREATEST(0, EXTRACT(EPOCH FROM (NOW() - %s::timestamptz))::int)",
                        (occ,),
                    )
                    dr = cur.fetchone()
                    if dr:
                        dwell = dr[0] if not isinstance(dr, dict) else next(iter(dr.values()))
                except Exception:
                    dwell = None
'''
    new_open = '''            open_hit = left is None
            if dwell is None and open_hit and occ is not None:
                # End open dwell at last real action (session last_activity), not clock-NOW
                # and not the 15-minute live window.
                try:
                    end_at = None
                    if ip_s:
                        cur.execute(
                            """
                            SELECT last_activity FROM public.public_sessions
                            WHERE ip_address = %s
                            ORDER BY last_activity DESC NULLS LAST
                            LIMIT 1
                            """,
                            (ip_s,),
                        )
                        sr = cur.fetchone()
                        if sr:
                            end_at = sr[0] if not isinstance(sr, dict) else next(iter(sr.values()))
                    if end_at is not None:
                        cur.execute(
                            "SELECT GREATEST(0, EXTRACT(EPOCH FROM (%s::timestamptz - %s::timestamptz))::int)",
                            (end_at, occ),
                        )
                    else:
                        cur.execute(
                            "SELECT GREATEST(0, EXTRACT(EPOCH FROM (NOW() - %s::timestamptz))::int)",
                            (occ,),
                        )
                    dr = cur.fetchone()
                    if dr:
                        dwell = dr[0] if not isinstance(dr, dict) else next(iter(dr.values()))
                except Exception:
                    dwell = None
'''
    if old_open not in text:
        raise SystemExit("open dwell block not found")
    text = text.replace(old_open, new_open, 1)

    # --- 3) Helper: session total seconds from trail + last_activity ---
    if "def _lean_session_total_seconds" not in text:
        helper = '''def _lean_session_total_seconds(trail: list, *, first_seen=None, last_activity=None) -> int:
    """Session clock: first page arrival → last action on last URL (not 15m live timeout)."""
    from datetime import datetime as _dt

    def _parse(v):
        if v is None or v == "":
            return None
        if hasattr(v, "timestamp"):
            return v
        s = str(v).strip()
        if not s:
            return None
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return _dt.fromisoformat(s)
        except Exception:
            return None

    first = _parse(first_seen)
    last = _parse(last_activity)
    for pt in trail or []:
        if not isinstance(pt, dict):
            continue
        occ = _parse(pt.get("occurred_at"))
        if occ is not None and (first is None or occ < first):
            first = occ
        # closed stay end ≈ occurred + dwell
        try:
            ds = pt.get("dwell_seconds")
            if occ is not None and ds is not None and not pt.get("open"):
                end = occ
                try:
                    from datetime import timedelta
                    end = occ + timedelta(seconds=int(ds))
                except Exception:
                    end = occ
                if last is None or end > last:
                    last = end
        except Exception:
            pass
    if first is None or last is None:
        return 0
    try:
        sec = int((last - first).total_seconds())
        return max(0, sec)
    except Exception:
        return 0


'''
        anchor = text.find("def _lean_session_page_trail")
        if anchor < 0:
            raise SystemExit("trail fn missing for helper insert")
        text = text[:anchor] + helper + text[anchor:]

    # --- 4) Attach session_total to live rows (signed + anon) ---
    # After pages_count in signed append
    old_signed_tail = '''                    "page_trail": trail,
                    "pages_count": len(trail),
                })
        if table_exists("public_sessions"):'''
    new_signed_tail = '''                    "page_trail": trail,
                    "pages_count": len(trail),
                    "session_seconds": _lean_session_total_seconds(trail, last_activity=la),
                    "session_dwell_label": _lean_fmt_dwell_seconds(
                        _lean_session_total_seconds(trail, last_activity=la)
                    ),
                })
        if table_exists("public_sessions"):'''
    if old_signed_tail not in text:
        raise SystemExit("signed row append not found")
    text = text.replace(old_signed_tail, new_signed_tail, 1)

    # Anon/bot rows - find the similar block. Need unique context.
    # Look for likely_slug nearby
    old_anon_tail = '''                    "page_trail": trail,
                    "pages_count": len(trail),
                })
'''
    # May appear twice - signed already changed. Remaining should be anon.
    if text.count(old_anon_tail) < 1:
        # try with different spacing after bot filter
        raise SystemExit("anon pages_count tail not found")
    # Replace all remaining (offline helper may also have pages_count without session)
    # Only replace inside lean_traffic_api_live by doing one replace after signed was done
    # Find anon-specific: likely_name in same dict
    marker = '"likely_slug": likely_slug if not is_bot else "",'
    mpos = text.find(marker)
    if mpos < 0:
        raise SystemExit("anon marker missing")
    # find pages_count after marker within 800 chars
    chunk = text[mpos : mpos + 1200]
    old_a = '''                    "page_trail": trail,
                    "pages_count": len(trail),
                })'''
    if old_a not in chunk:
        raise SystemExit("anon trail tail not near marker")
    new_a = '''                    "page_trail": trail,
                    "pages_count": len(trail),
                    "session_seconds": _lean_session_total_seconds(
                        trail, first_seen=None, last_activity=la
                    ),
                    "session_dwell_label": _lean_fmt_dwell_seconds(
                        _lean_session_total_seconds(trail, last_activity=la)
                    ),
                })'''
    text = text[:mpos] + chunk.replace(old_a, new_a, 1) + text[mpos + 1200 :]

    # Offline rows too
    old_off = '''                    "page_trail": trail,
                    "pages_count": len(trail),
                    "done": True,
                }'''
    if old_off in text:
        text = text.replace(
            old_off,
            '''                    "page_trail": trail,
                    "pages_count": len(trail),
                    "session_seconds": _lean_session_total_seconds(
                        trail, first_seen=first_seen, last_activity=la
                    ),
                    "session_dwell_label": _lean_fmt_dwell_seconds(
                        _lean_session_total_seconds(
                            trail, first_seen=first_seen, last_activity=la
                        )
                    ),
                    "done": True,
                }''',
            1,
        )

    # --- 5) UI: top line shows last page + session total (not open-page NOW clock) ---
    old_ui = '''      var dwellNow="";
      for(var ti=trail.length-1;ti>=0;ti--){
        var tp=trail[ti]||{};
        var tpath=tp.path||"";
        if(tpath===path || ((path==="/"||path==="/index.html")&&(tpath==="/"||tpath==="/index.html"))){
          dwellNow=tp.dwell_label||"";
          break;
        }
      }
      if(!dwellNow && trail.length){
        var last=trail[trail.length-1]||{};
        if((last.path||"")===path || path==="/"||path==="/index.html") dwellNow=last.dwell_label||"";
      }
      var link=r.href?("<a href='"+esc(r.href)+"'>"+esc(pathLabel)+"</a>"):esc(pathLabel);
      if(dwellNow) link+=" <span class='dwell'>· "+esc(dwellNow)+"</span>";
'''
    new_ui = '''      // Last page + session total time (first arrival → last action), not 15m live window
      var sessTot=r.session_dwell_label||"";
      var link=r.href?("<a href='"+esc(r.href)+"'>"+esc(pathLabel)+"</a>"):esc(pathLabel);
      if(sessTot) link+=" <span class='dwell'>· session "+esc(sessTot)+"</span>";
'''
    if old_ui not in text:
        raise SystemExit("renderLive dwell UI not found")
    text = text.replace(old_ui, new_ui, 1)

    # Offline table: show last page + session total
    old_off_row = '''      html+="<tr class='live-main' data-trail='"+esc(key)+"'><td>"+arrow+"<span class='badge "+badge+"'>"+badgeLabel+"</span> "+who+" · done</td><td>"+n+"</td><td>"+esc(when)+"</td></tr>";'''
    if old_off_row in text:
        text = text.replace(
            old_off_row,
            '''      var lastP=r.path||"—";
      var lastLab=(lastP==="/"||lastP==="/index.html")?"home":lastP;
      var lastHref=lastP.indexOf("/")===0?lastP:"";
      var lastLink=lastHref?("<a href='"+esc(lastHref)+"'>"+esc(lastLab)+"</a>"):esc(lastLab);
      var sess=r.session_dwell_label?(" · session "+esc(r.session_dwell_label)):"";
      html+="<tr class='live-main' data-trail='"+esc(key)+"'><td>"+arrow+"<span class='badge "+badge+"'>"+badgeLabel+"</span> "+who+" · done</td><td>"+lastLink+sess+" · "+n+"p</td><td>"+esc(when)+"</td></tr>";''',
            1,
        )
        # fix header Pages -> Last page
        text = text.replace(
            "var html=\"<table><thead><tr><th>Who</th><th>Pages</th><th>When done</th></tr></thead><tbody>\";",
            "var html=\"<table><thead><tr><th>Who</th><th>Last page / total</th><th>When done</th></tr></thead><tbody>\";",
            1,
        )

    # --- 6) offlineBox HTML (liveBox has Loading… child) ---
    if 'id="offlineBox"' not in text:
        markers = [
            '<div id="liveBox"><p class="note">Loading…</p></div>',
            "<div id=\"liveBox\"><p class=\"note\">Loading…</p></div>",
            '<div id="liveBox"></div>',
        ]
        replaced = False
        for m in markers:
            if m in text:
                text = text.replace(
                    m,
                    m
                    + '\n<section class="card" style="margin-top:12px"><h2>Done / offline — last 24h</h2>'
                    + '<p class="note">Outside the live window. ▶ show/hide URL trail. Session total = first page → last action (not 15m timeout). Staff/agent hidden.</p>'
                    + '<div id="offlineBox"><p class="note">Loading…</p></div></section>',
                    1,
                )
                replaced = True
                break
        if not replaced:
            raise SystemExit("liveBox HTML not found for offlineBox")

    # Overview human totals: if live poll returns human_live, page may already use rows length —
    # also patch overview card JS if it shows visitors from live length
    # Prefer updating the live empty/count note near poll
    if "human_live" in text and "d.human_live" not in text:
        # add a small note under live when human_live present - optional
        old_empty = 'if(!rows.length){$("liveBox").innerHTML="<p class=\'note\'>Nobody active in the last "+(d.live_minutes||15)+" minutes.</p>"; return;}'
        if old_empty in text:
            text = text.replace(
                old_empty,
                'if(!rows.length){$("liveBox").innerHTML="<p class=\'note\'>Nobody active in the last "+(d.live_minutes||15)+" minutes."+(d.human_live!=null?(" · humans "+d.human_live+" / "+(d.human_pages||0)+" pages"):"")+"</p>"; return;}',
                1,
            )

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK session-total (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
