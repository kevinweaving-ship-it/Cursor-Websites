#!/usr/bin/env python3
"""Live signed-in list: show sailor profile URL under name (all logged-in users)."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

HELPER = '''
def _lean_signed_in_profile(cur, sas_id: str, display_name: str = "") -> dict:
    """Resolve public /sailor/{slug} for a logged-in Live row.

    Always prefer a real name slug (never /sailor/{SAS_ID}). Used so every
    signed-in visitor shows a clickable profile URL under their name.
    """
    sid = str(sas_id or "").strip()
    out = {"who_href": "", "profile_slug": "", "who": (display_name or "").strip()}
    if not sid:
        return out
    full_name = (display_name or "").strip()
    slug = ""
    try:
        cur.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(full_name), ''),
                            NULLIF(TRIM(CONCAT(COALESCE(first_name, ''), ' ', COALESCE(last_name, ''))), '')) AS full_name,
                   COALESCE(NULLIF(TRIM(ssl_profile_slug), ''), '') AS ssl_slug
            FROM public.sas_id_personal
            WHERE sa_sailing_id::text = %s
            LIMIT 1
            """,
            (sid,),
        )
        row = cur.fetchone()
        if row:
            if isinstance(row, dict):
                full_name = (row.get("full_name") or full_name or "").strip()
                slug = (row.get("ssl_slug") or "").strip()
            else:
                full_name = (row[0] or full_name or "").strip()
                slug = (row[1] or "").strip() if len(row) > 1 else ""
    except Exception:
        pass
    if full_name and (not out["who"] or out["who"].isdigit() or out["who"] in ("Signed-in", "Staff")):
        out["who"] = full_name
    if slug and slug.isdigit():
        slug = ""
    if not slug and full_name:
        try:
            slug = _sailor_canonical_slug(full_name, sid, False)
        except Exception:
            try:
                slug = _slug_from_name(full_name)
            except Exception:
                slug = ""
    if slug and not str(slug).isdigit():
        out["profile_slug"] = slug
        out["who_href"] = f"/sailor/{slug}"
    return out

'''

if "_lean_signed_in_profile" in text:
    print("SKIP helper")
else:
    # Insert near other lean traffic helpers (after auth funnel if present, else after engagement)
    for anchor in (
        "def _lean_trail_is_auth_funnel_human",
        "def _lean_trail_has_engagement",
    ):
        i = text.find(anchor)
        if i < 0:
            continue
        j = text.find("\ndef ", i + 10)
        if j < 0:
            continue
        # If auth funnel exists, insert after its following function ends
        if anchor.endswith("auth_funnel_human"):
            # skip past auth funnel fn body to next def, then insert before that next def's... 
            # Actually insert BEFORE the next def after auth funnel
            text = text[:j] + "\n" + HELPER + text[j:]
            print("OK helper after auth funnel")
            break
        else:
            text = text[:j] + "\n" + HELPER + text[j:]
            print("OK helper after engagement")
            break
    else:
        print("FAIL no insert anchor", file=sys.stderr)
        sys.exit(1)

# --- Fill who_href on signed Live rows ---
old_row = '''                rows.append({
                    "kind": "signed",
                    "who": d.get("who") or ("Staff" if is_staff_row else "Signed-in"),
                    "who_href": "",
                    "guessed": False,
                    "likely_hits": 0,
                    "sas_id": d.get("sas_id") or "",
                    "ip": ip,
                    "visitor_id": sess_vid,
                    "session_id": sid,
                    "path": path,
                    "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                    "device": (d.get("device") or "")[:80],
                    "device_type": "",
                    "browser": "",
                    "href": path if str(path).startswith("/") else "",
                    "page_trail": trail,
                    "pages_count": len(trail),
                    "session_seconds": _lean_session_total_seconds(trail, last_activity=la),
                    "session_dwell_label": _lean_fmt_dwell_seconds(
                        _lean_session_total_seconds(trail, last_activity=la)
                    ),
                })'''

new_row = '''                who_name = d.get("who") or ("Staff" if is_staff_row else "Signed-in")
                prof = {"who_href": "", "profile_slug": "", "who": who_name}
                try:
                    prof = _lean_signed_in_profile(cur, str(d.get("sas_id") or ""), who_name)
                except Exception:
                    try:
                        _lean_db_rollback(conn)
                    except Exception:
                        pass
                    prof = {"who_href": "", "profile_slug": "", "who": who_name}
                rows.append({
                    "kind": "signed",
                    "who": prof.get("who") or who_name,
                    "who_href": prof.get("who_href") or "",
                    "profile_slug": prof.get("profile_slug") or "",
                    "guessed": False,
                    "likely_hits": 0,
                    "sas_id": d.get("sas_id") or "",
                    "ip": ip,
                    "visitor_id": sess_vid,
                    "session_id": sid,
                    "path": path,
                    "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                    "device": (d.get("device") or "")[:80],
                    "device_type": "",
                    "browser": "",
                    "href": path if str(path).startswith("/") else "",
                    "page_trail": trail,
                    "pages_count": len(trail),
                    "session_seconds": _lean_session_total_seconds(trail, last_activity=la),
                    "session_dwell_label": _lean_fmt_dwell_seconds(
                        _lean_session_total_seconds(trail, last_activity=la)
                    ),
                })'''

if '"profile_slug": prof.get("profile_slug")' in text:
    print("SKIP signed row who_href")
elif old_row not in text:
    print("FAIL signed row block", file=sys.stderr)
    sys.exit(2)
else:
    text = text.replace(old_row, new_row, 1)
    print("OK signed Live who_href")

# --- renderLive: name link + profile URL under name ---
old_ui = '''      // Unique identity = IP (API already sets who to Guest/Bot + IP)
      var who=esc(r.who||(r.ip?("Guest "+r.ip):"Guest"));
      var meta="";
      if(r.kind==="signed" && r.sas_id) meta+=" · sas "+esc(r.sas_id);'''

new_ui = '''      // Signed-in: name + profile URL under name (all logged-in sailors)
      var whoName=esc(r.who||(r.ip?("Guest "+r.ip):"Guest"));
      var who=whoName;
      if(r.kind==="signed" && r.who_href){
        who="<a href='"+esc(r.who_href)+"'>"+whoName+"</a>";
        who+="<div class='trail-engage'><a href='"+esc(r.who_href)+"'>"+esc(r.who_href)+"</a></div>";
      } else if(r.kind==="signed" && r.profile_slug){
        var ph="/sailor/"+esc(r.profile_slug);
        who="<a href='"+ph+"'>"+whoName+"</a>";
        who+="<div class='trail-engage'><a href='"+ph+"'>"+ph+"</a></div>";
      }
      var meta="";
      if(r.kind==="signed" && r.sas_id) meta+=" · sas "+esc(r.sas_id);'''

if "Signed-in: name + profile URL under name" in text:
    print("SKIP renderLive UI")
elif old_ui not in text:
    print("FAIL renderLive who block", file=sys.stderr)
    sys.exit(3)
else:
    text = text.replace(old_ui, new_ui, 1)
    print("OK renderLive profile under name")

if text == orig:
    print("NO CHANGE", file=sys.stderr)
    sys.exit(4)

try:
    compile(text, str(API), "exec")
except SyntaxError as e:
    print("SYNTAX", e, file=sys.stderr)
    sys.exit(5)

API.write_text(text, encoding="utf-8")
print("WROTE", API, "delta", len(text) - len(orig))
