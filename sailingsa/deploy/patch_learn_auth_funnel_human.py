#!/usr/bin/env python3
"""Learn: land → signup/login → browse = typical real human (Robyn Patrick example).

Keeps auth funnel URLs in Done trails and never bot-classifies that shape.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

HELPERS = '''
def _lean_is_auth_funnel_path(path: Optional[str]) -> bool:
    """Signup/login pages — real humans hit these; not scanner junk.

    Learned 2026-08-15: Robyn Patrick (#6903) IP 165.73.122.145 —
    land home → signup → login → browse club/sailor/regatta while signed-in.
    """
    p = (path or "").split("?", 1)[0].strip().lower().rstrip("/") or "/"
    if p in (
        "/signup",
        "/signup.html",
        "/login",
        "/login.html",
        "/signin",
        "/register",
    ):
        return True
    return False


def _lean_trail_is_auth_funnel_human(page_trail: list, current_path: str = "") -> bool:
    """Land (home) → signup/login → look around = typical real human.

    Same IP often goes guest → signed-in; engagement + multi-URL after auth
    is enough. Never treat as sterile/bounce bot.
    """
    trail = page_trail if isinstance(page_trail, list) else []
    paths = []
    for pt in trail:
        if not isinstance(pt, dict):
            continue
        pp = (pt.get("path") or "").split("?", 1)[0].strip() or "/"
        paths.append(pp)
    if not paths:
        p0 = (current_path or "").split("?", 1)[0].strip() or "/"
        paths = [p0]
    has_home = any(p in ("/", "/index.html") for p in paths)
    has_auth = any(_lean_is_auth_funnel_path(p) for p in paths)
    if not (has_home and has_auth):
        return False
    # After auth, real people open other site URLs (club/sailor/regatta/rankings/…)
    browse = [
        p
        for p in paths
        if p not in ("/", "/index.html") and not _lean_is_auth_funnel_path(p)
    ]
    if browse:
        return True
    # Or they engage on home/auth before navigating further
    try:
        if _lean_trail_has_engagement(trail):
            return True
    except Exception:
        pass
    return False

'''

# Insert helpers after _lean_trail_has_engagement (once)
if "_lean_trail_is_auth_funnel_human" in text:
    print("SKIP helpers already present")
else:
    anchor = "def _lean_trail_has_engagement(page_trail: list) -> bool:"
    i = text.find(anchor)
    if i < 0:
        print("FAIL no _lean_trail_has_engagement", file=sys.stderr)
        sys.exit(1)
    # find end of function: next \ndef at column 0 after body
    j = text.find("\ndef ", i + len(anchor))
    if j < 0:
        print("FAIL no next def after engagement", file=sys.stderr)
        sys.exit(2)
    text = text[:j] + "\n" + HELPERS + text[j:]
    print("OK inserted auth-funnel helpers")

# --- Offline public paths: keep signup/login.html in human trails ---
old_junk = '''    junk = {
        "/account", "/app", "/console", "/dashboard", "/login", "/manage", "/my",
        "/portal", "/profile", "/settings", "/signin", "/signup", "/register",
        "/user", "/user/login", "/users", "/graphql", "/v1/graphql", "/class", "/club",
    }
    if low in junk:
        return False
    return True'''

new_junk = '''    junk = {
        "/account", "/app", "/console", "/dashboard", "/manage", "/my",
        "/portal", "/profile", "/settings",
        "/user", "/user/login", "/users", "/graphql", "/v1/graphql", "/class", "/club",
    }
    # Auth funnel (/login.html, /signup.html, …) stays in trails — learned human path
    if _lean_is_auth_funnel_path(low):
        return True
    if low in junk:
        return False
    return True'''

if "_lean_is_auth_funnel_path(low)" in text and '"/login"' not in text.split("def _lean_offline_path_is_public", 1)[-1][:900].split("return True", 1)[0]:
    # already patched if login removed from junk near offline_path
    pass

if "Auth funnel (/login.html" in text:
    print("SKIP offline junk")
elif old_junk not in text:
    print("WARN offline junk block mismatch", file=sys.stderr)
else:
    text = text.replace(old_junk, new_junk, 1)
    print("OK offline auth paths kept")

# --- behavior_confident_bot: pardon auth funnel early ---
old_beh = '''def _lean_behavior_confident_bot(page_trail: list, current_path: str = "", ip: str = "") -> bool:
    """High-confidence scraper pattern (not a maybe).

    Confirmed shapes:
      A) deep-link only on /boat/ or /sailor/ (no home) — classic Alibaba/cloud entry
      B) short hop trail (3–8) no home, mostly <=2s dwell
      C) agent junk paths (/workspace, etc.)
    """
    trail = page_trail if isinstance(page_trail, list) else []
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass
    try:
        if _lean_trail_is_club_share_only(trail, current_path):
            return False
    except Exception:
        pass'''

new_beh = '''def _lean_behavior_confident_bot(page_trail: list, current_path: str = "", ip: str = "") -> bool:
    """High-confidence scraper pattern (not a maybe).

    Confirmed shapes:
      A) deep-link only on /boat/ or /sailor/ (no home) — classic Alibaba/cloud entry
      B) short hop trail (3–8) no home, mostly <=2s dwell
      C) agent junk paths (/workspace, etc.)

    Not bot (learned): home → signup/login → browse (same IP guest→signed-in).
    """
    trail = page_trail if isinstance(page_trail, list) else []
    try:
        if _lean_trail_is_auth_funnel_human(trail, current_path):
            return False
    except Exception:
        pass
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass
    try:
        if _lean_trail_is_club_share_only(trail, current_path):
            return False
    except Exception:
        pass'''

if "_lean_trail_is_auth_funnel_human(trail, current_path)" in text.split("def _lean_behavior_confident_bot", 1)[-1][:600]:
    print("SKIP behavior pardon")
elif old_beh not in text:
    print("FAIL behavior block", file=sys.stderr)
    sys.exit(3)
else:
    text = text.replace(old_beh, new_beh, 1)
    print("OK behavior auth-funnel pardon")

# --- bounce_home: auth funnel never bounce-bot ---
bh_i = text.find("def _lean_bounce_home_bot")
bh_end = text.find("\ndef ", bh_i + 10) if bh_i >= 0 else -1
if bh_i >= 0 and bh_end > bh_i:
    bh = text[bh_i:bh_end]
    if "_lean_trail_is_auth_funnel_human(trail, current_path)" in bh:
        print("SKIP bounce_home")
    elif "if _lean_trail_has_engagement(trail):\n            return False" in bh:
        bh2 = bh.replace(
            """    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass""",
            """    try:
        if _lean_trail_is_auth_funnel_human(trail, current_path):
            return False
    except Exception:
        pass
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass""",
            1,
        )
        text = text[:bh_i] + bh2 + text[bh_end:]
        print("OK bounce_home auth pardon")
    else:
        print("WARN bounce_home block mismatch", file=sys.stderr)
else:
    print("WARN bounce_home not found", file=sys.stderr)

# --- sterile classify: auth funnel = real ---
old_sterile_eng = '''    # Real scroll/click — phone especially: never sterile-quarantine
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass'''

new_sterile_eng = '''    # Auth funnel (land → signup/login → browse) — learned real human
    try:
        if _lean_trail_is_auth_funnel_human(trail):
            return False
    except Exception:
        pass
    # Real scroll/click — phone especially: never sterile-quarantine
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass'''

if "Auth funnel (land → signup/login" in text:
    print("SKIP sterile classify")
elif old_sterile_eng not in text:
    print("WARN sterile classify block missing", file=sys.stderr)
else:
    text = text.replace(old_sterile_eng, new_sterile_eng, 1)
    print("OK sterile classify auth pardon")

# Safer: after the whole try/except bot block, force is_bot False if auth human
MARKER = "            # All real visitors (staff included when scrolled/clicked)\n            if is_bot:"
FORCE = '''            # Learned: auth-funnel humans stay real even if a prior rule flipped is_bot
            try:
                if (not is_staff) and _lean_trail_is_auth_funnel_human(trail, path):
                    is_bot = False
            except Exception:
                pass
            # All real visitors (staff included when scrolled/clicked)
            if is_bot:'''

if "Learned: auth-funnel humans stay real" in text:
    print("SKIP offline force human")
elif MARKER not in text:
    print("FAIL offline marker", file=sys.stderr)
    sys.exit(4)
else:
    text = text.replace(MARKER, FORCE, 1)
    print("OK offline force auth-funnel human")

# Frontend junkExact: do not treat signup/login.html as probe junk in client filters
old_fe = 'var junkExact={"/account":1,"/app":1,"/console":1,"/dashboard":1,"/login":1,"/login.html":1,"/manage":1,"/my":1,"/portal":1,"/profile":1,"/settings":1,"/signin":1,"/signup":1,"/register":1,'
new_fe = 'var junkExact={"/account":1,"/app":1,"/console":1,"/dashboard":1,"/manage":1,"/my":1,"/portal":1,"/profile":1,"/settings":1,'

if '"/login.html":1' not in text and "junkExact" in text:
    print("SKIP frontend junk (already clean)")
elif old_fe in text:
    text = text.replace(old_fe, new_fe, 1)
    print("OK frontend junkExact auth kept")
else:
    print("WARN frontend junkExact mismatch", file=sys.stderr)

if text == orig:
    print("NO CHANGE", file=sys.stderr)
    sys.exit(5)

try:
    compile(text, str(API), "exec")
except SyntaxError as e:
    print("SYNTAX", e, file=sys.stderr)
    sys.exit(6)

API.write_text(text, encoding="utf-8")
print("WROTE", API, "delta", len(text) - len(orig))
