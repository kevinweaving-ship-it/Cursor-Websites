"""Quarantine agent/cloud noise so overview 24h totals match Done/offline humans."""
from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-ov-match-{stamp}"))
text = API.read_text(encoding="utf-8")

# Ensure offline bot classify also quarantines (so overview drops them)
old = '''            if is_bot:
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
'''
# find in offline helper - might be slightly different
if old not in text:
    old = '''            if is_bot:
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
    except Exception:
        return humans, bots
'''
new = '''            if is_bot:
                if ip:
                    try:
                        _lean_quarantine_ip(cur, ip, "offline_bot")
                    except Exception:
                        pass
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
'''
if old not in text:
    # try without except block attached
    idx = text.find("if is_bot:\n                bots.append(item)")
    print("ctx", repr(text[idx:idx+200]) if idx>=0 else "no")
    raise SystemExit("append block missing")
text = text.replace(
    '''            if is_bot:
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
''',
    '''            if is_bot:
                if ip:
                    try:
                        _lean_quarantine_ip(cur, ip, "offline_bot")
                    except Exception:
                        pass
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
''',
    1,
)

# When skipping agent junk IPs in offline, also quarantine them
old_agent = '''                if cur.fetchone():
                    continue
            except Exception:
                pass
            if not trail:
                continue
'''
new_agent = '''                if cur.fetchone():
                    try:
                        _lean_quarantine_ip(cur, ip, "agent_junk_path")
                    except Exception:
                        pass
                    continue
            except Exception:
                pass
            if not trail:
                continue
'''
if old_agent in text:
    text = text.replace(old_agent, new_agent, 1)

API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print("OK quarantine wire")
