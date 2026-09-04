#!/usr/bin/env python3
"""Live traffic: IP is the unique visitor. Sailor-from-pages is a soft hint only."""
from __future__ import annotations

import pathlib
import sys
import py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

# Limit likely-sailor helper to recent hits (session indication, not forever lock)
old_likely_sql = '''        cur.execute(
            """
            SELECT path, COUNT(*)::int AS hits
            FROM public.public_page_hits
            WHERE ip_address = %s
            GROUP BY path
            """,
            (ip,),
        )'''
new_likely_sql = '''        cur.execute(
            """
            SELECT path, COUNT(*)::int AS hits
            FROM public.public_page_hits
            WHERE ip_address = %s
              AND occurred_at > NOW() - INTERVAL '45 minutes'
            GROUP BY path
            """,
            (ip,),
        )'''
if old_likely_sql not in text:
    if "occurred_at > NOW() - INTERVAL '45 minutes'" in text[text.find("def _public_likely_sailor_for_ip"): text.find("def _public_likely_sailor_for_ip") + 1500]:
        print("likely sql already scoped")
    else:
        raise SystemExit("likely sailor sql not found")
else:
    text = text.replace(old_likely_sql, new_likely_sql, 1)

# Docstring
text = text.replace(
    '''def _public_likely_sailor_for_ip(cur, ip: str, current_path: str = "") -> dict:
    """Most-visited /sailor/{slug} for this IP → likely sailor.
    Name from /sailor/{slug} viewed (prefer 2+ hits; else top sailor page this IP).
    """''',
    '''def _public_likely_sailor_for_ip(cur, ip: str, current_path: str = "") -> dict:
    """Soft hint only: most-visited /sailor/{slug} for this IP in the last 45 minutes.

    Not an identity lock. Unique visitor key is always the IP / visitor_id.
    """''',
    1,
)

# Replace both lean live who-assignment blocks (main + orphan) — same pattern
old_who = '''                likely_name = (likely.get("name") or "").strip()
                likely_slug = (likely.get("slug") or "").strip()
                if is_bot:
                    who = f"Bot {vid}" if vid else "Bot"
                    who_href = ""
                else:
                    who = likely_name if likely_name else (f"Guest {vid}" if vid else "Guest")
                    who_href = f"/sailor/{likely_slug}" if likely_slug else ""'''

new_who = '''                likely_name = (likely.get("name") or "").strip()
                likely_slug = (likely.get("slug") or "").strip()
                # Identity = IP (unique). Sailor name is indication only — never the who key.
                if is_bot:
                    who = f"Bot {ip}" if ip else (f"Bot {vid}" if vid else "Bot")
                    who_href = ""
                else:
                    who = f"Guest {ip}" if ip else (f"Guest {vid}" if vid else "Guest")
                    who_href = ""'''

# Also orphan block uses 4-space less? check - both use same indent in file from earlier
count = text.count(old_who)
if count < 1:
    # try orphan indent (20 spaces vs 16)
    old_who2 = old_who.replace("                ", "                    ")
    new_who2 = new_who.replace("                ", "                    ")
    c2 = text.count(old_who2)
    if c2 < 1:
        raise SystemExit(f"who blocks not found count={count}")
    text = text.replace(old_who2, new_who2)
    print("replaced orphan-style who", c2)
else:
    text = text.replace(old_who, new_who)
    print("replaced who blocks", count)

# Ensure row still carries hint fields — already has likely_hits, sas_id, guessed.
# Change guessed to False always for lean (hint shown separately), keep likely_* fields.
# Update append dicts to set guessed False and add likely_name/likely_slug explicitly.

# renderLive + note + liveTrailKey prefer IP
old_note = "Last 15 min. ▶ next to a name shows/hides every URL in that session with dwell time. Guests guessed from IP + sailor pages."
new_note = "Last 15 min. Who = IP (unique visitor). Sailor name is only a soft hint from pages in this session — not locked to the IP. ▶ shows URL trail + dwell."
if old_note in text:
    text = text.replace(old_note, new_note, 1)

old_key = '''  function liveTrailKey(r){
    if(r.visitor_id) return "v:"+String(r.visitor_id);
    if(r.session_id) return "s:"+String(r.session_id);
    if(r.ip) return "ip:"+String(r.ip);
    if(r.sas_id) return "sas:"+String(r.sas_id);
    return "who:"+String(r.kind||"")+"|"+String(r.who||"");
  }'''
new_key = '''  function liveTrailKey(r){
    if(r.ip) return "ip:"+String(r.ip);
    if(r.visitor_id) return "v:"+String(r.visitor_id);
    if(r.session_id) return "s:"+String(r.session_id);
    return "who:"+String(r.kind||"")+"|"+String(r.who||"");
  }'''
if old_key not in text:
    raise SystemExit("liveTrailKey not found")
text = text.replace(old_key, new_key, 1)

# Replace renderLive who rendering section
idx = text.find("  function renderLive(d){")
idx2 = text.find("  function mediaSrc(u){", idx)
if idx < 0 or idx2 < 0:
    raise SystemExit("renderLive bounds missing")
block = text[idx:idx2]
old_bits = '''      var badge=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":(r.guessed?"guess":"anon"));
      var badgeLabel=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":(r.guessed?"guess":"guest"));
      var path=r.path||"—";
      var link=r.href?("<a href='"+esc(r.href)+"'>"+esc(path)+"</a>"):esc(path);
      var when=(r.last_activity||"").replace("T"," ").slice(0,19);
      var who=esc(r.who||"");
      if(r.who_href){ who="<a href='"+esc(r.who_href)+"' title='Guessed from IP sailor page visits'>"+who+"</a>"; }
      var meta="";
      if(r.sas_id) meta+=" · "+esc(r.sas_id);
      if(r.guessed && r.likely_hits) meta+=" · "+r.likely_hits+" sailor hits";'''

new_bits = '''      var badge=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":"anon");
      var badgeLabel=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":"guest");
      var path=r.path||"—";
      var link=r.href?("<a href='"+esc(r.href)+"'>"+esc(path)+"</a>"):esc(path);
      var when=(r.last_activity||"").replace("T"," ").slice(0,19);
      // Unique identity = IP (API already sets who to Guest/Bot + IP)
      var who=esc(r.who||(r.ip?("Guest "+r.ip):"Guest"));
      var meta="";
      if(r.kind==="signed" && r.sas_id) meta+=" · sas "+esc(r.sas_id);
      // Soft hint only — never the identity
      var hintName=r.likely_name||"";
      var hintSlug=r.likely_slug||"";
      if(!hintName && r.guessed && r.who_href){ /* legacy */ }
      if(r.likely_name){ hintName=r.likely_name; hintSlug=r.likely_slug||""; }
      // fall back: older payloads put sailor in who — ignore for display identity
      if(hintName){
        var hint=esc(hintName);
        if(hintSlug){ hint="<a href='/sailor/"+esc(hintSlug)+"' title='Soft hint from sailor pages this session — not locked to IP'>"+hint+"</a>"; }
        meta+=" · maybe "+hint;
        if(r.likely_hits) meta+=" ("+r.likely_hits+")";
      }'''

if old_bits not in block:
    raise SystemExit("renderLive who bits not found")
block2 = block.replace(old_bits, new_bits, 1)
text = text[:idx] + block2 + text[idx2:]

# Add likely_name / likely_slug to row appends in lean live
# Pattern in append dict
old_app = '''                    "guessed": bool(likely_name) and not is_bot,
                    "likely_hits": int(likely.get("hits") or 0) if not is_bot else 0,
                    "sas_id": (likely.get("sas_id") or "") if not is_bot else "",'''
new_app = '''                    "guessed": False,
                    "likely_name": likely_name if not is_bot else "",
                    "likely_slug": likely_slug if not is_bot else "",
                    "likely_hits": int(likely.get("hits") or 0) if not is_bot else 0,
                    "sas_id": (likely.get("sas_id") or "") if not is_bot else "",'''
c = text.count(old_app)
if c < 1:
    raise SystemExit("append guessed fields not found")
text = text.replace(old_app, new_app)
print("append fields", c)

if text == orig:
    raise SystemExit("no changes")
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK (+{len(text)-len(orig)} bytes)")
