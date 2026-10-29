#!/usr/bin/env python3
"""Patch hikpoc bridge_cam.py to re-login on every Hik-Connect 401."""
from __future__ import annotations

import time
from pathlib import Path

p = Path("/opt/hikpoc/bridge_cam.py")
text = p.read_text(encoding="utf-8")
if "Always re-login on 401" in text:
    print("already_patched", p)
    raise SystemExit(0)

bak = p.with_suffix(p.suffix + ".bak_relogin_" + time.strftime("%Y%m%dT%H%M%SZ"))
bak.write_text(text, encoding="utf-8")

old = """        except Exception as e:
            log("reconnect:", repr(e)[:140])
            if from_cache:   # cached session may be stale: one fresh login, then retry immediately
                from_cache = False
                try: fresh_login(client, env); continue
                except Exception as e2: log("re-login failed:", repr(e2)[:100])
            time.sleep(1.0)
"""

new = """        except Exception as e:
            log("reconnect:", repr(e)[:140])
            err = repr(e)
            # Hik-Connect sessions expire / get invalidated by sibling bridges.
            # Always re-login on 401 (not only the first cached attempt), else ring
            # stays empty forever and WA cards show "no image".
            if "401" in err or "Unauthorized" in err or from_cache:
                from_cache = False
                try:
                    fresh_login(client, env)
                    continue
                except Exception as e2:
                    log("re-login failed:", repr(e2)[:100])
                    time.sleep(5.0)
                    continue
            time.sleep(1.0)
"""

if old not in text:
    raise SystemExit("bridge reconnect block not found")
p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched", p, "backup", bak)
