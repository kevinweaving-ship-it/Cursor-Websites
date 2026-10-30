#!/usr/bin/env python3
"""Live: evaluating until scroll/click, or 30s idle → bot final + quarantine."""
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

# 1) 30s idle window
rep(
    "_LEAN_ENGAGE_GRACE_SECONDS = 12",
    "_LEAN_ENGAGE_GRACE_SECONDS = 30  # idle evaluate window: then bot final → quarantine",
    "grace 30s",
)

# 2) Live rule: evaluating if fresh; bot final if idle >= 30s with no scroll/click
old_live = """                # Live = real only: must have scrolled/clicked (bots never do).
                # No grace flash on Live — early backend timer moves sterile to bots.
                if not is_bot:
                    try:
                        if not _lean_trail_has_engagement(_trail_pre):
                            is_bot = True
                    except Exception:
                        is_bot = True"""

new_live = """                # Live flow: new visitor stays while evaluating.
                # Scroll/click → real (stays until done). Idle 30s with no scroll/click → bot final.
                if not is_bot:
                    try:
                        has_eng = _lean_trail_has_engagement(_trail_pre)
                    except Exception:
                        has_eng = False
                    if not has_eng:
                        fresh = False
                        try:
                            cur.execute(
                                "SELECT (%s::timestamptz > NOW() - make_interval(secs => %s))",
                                (d.get("last_activity"), int(_LEAN_ENGAGE_GRACE_SECONDS)),
                            )
                            rr = cur.fetchone()
                            if rr:
                                fresh = bool(rr[0] if not isinstance(rr, dict) else next(iter(rr.values())))
                        except Exception:
                            fresh = False
                        if fresh:
                            # Still evaluating — keep on Live as Guest
                            is_bot = False
                        else:
                            # Idle past window, no scroll/click → bot final
                            is_bot = True
                            if ip:
                                try:
                                    _lean_quarantine_ip(cur, ip, "bot_final_idle_30s")
                                except Exception:
                                    pass"""

rep(old_live, new_live, "live eval flow")

# 3) Classify reason label for idle final
old_q = '_lean_quarantine_ip(cur, ip, "no_engage_sterile")'
new_q = '_lean_quarantine_ip(cur, ip, "bot_final_idle_30s")'
if old_q in text:
    text = text.replace(old_q, new_q, 1)
    print("OK quarantine reason")
else:
    print("WARN no_engage_sterile reason not found")

# 4) Docstring on schedule
old_doc = '    """One-shot: after grace, if still no scroll/click and short trail → quarantine (bots list).'
new_doc = '    """One-shot: after 30s idle, if still no scroll/click → bot final + quarantine (off Live).'
if old_doc in text:
    text = text.replace(old_doc, new_doc, 1)
    print("OK schedule doc")

# 5) Live card note in HTML if present
old_note = "Nobody active in the last "
# leave as-is; maybe update a note in live section header
old_live_hdr = "Active now"
# skip if not exact

if text == orig:
    sys.exit("NO CHANGE")

compile(text, str(API), "exec")
API.write_text(text, encoding="utf-8")
print("WROTE", len(text) - len(orig))
