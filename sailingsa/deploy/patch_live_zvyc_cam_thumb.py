#!/usr/bin/env python3
"""Remember the browser-scraped Skyline token so ZVYC thumbs can refresh."""
from pathlib import Path
import sys

OLD = '''    except Exception as e:
        print(f"[zvyc_live_cam] resolve failed: {e}", flush=True)
    return ""
'''
NEW = '''    except Exception as e:
        print(f"[zvyc_live_cam] resolve failed: {e}", flush=True)
    with _ZVYC_GRAB_LOCK:
        saved = str(_ZVYC_GRAB_MEM.get("tok") or "")
        saved_at = float(_ZVYC_GRAB_MEM.get("tok_t") or 0)
    if saved and (time.time() - saved_at) < 240:
        return "https://hd-auth.skylinewebcams.com/live.m3u8?a=" + saved
    return ""
'''

OLD_TOK = '''    tok = _zvyc_normalize_cam_token(explicit_token)
    if tok:
        return "https://hd-auth.skylinewebcams.com/live.m3u8?a=" + tok
'''
NEW_TOK = '''    tok = _zvyc_normalize_cam_token(explicit_token)
    if tok:
        with _ZVYC_GRAB_LOCK:
            _ZVYC_GRAB_MEM["tok"] = tok
            _ZVYC_GRAB_MEM["tok_t"] = time.time()
        return "https://hd-auth.skylinewebcams.com/live.m3u8?a=" + tok
'''

OLD_JS = "mm-lipton-reels-card.js?v=mmr125"
NEW_JS = "mm-lipton-reels-card.js?v=mmr126"


def apply(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    if t.count(OLD_TOK) != 1:
        raise SystemExit(f"token branch count {t.count(OLD_TOK)}")
    if t.count(OLD) != 1:
        raise SystemExit(f"resolve fallback count {t.count(OLD)}")
    if t.count(OLD_JS) != 1:
        raise SystemExit(f"{OLD_JS} count {t.count(OLD_JS)}")
    t = t.replace(OLD_TOK, NEW_TOK, 1).replace(OLD, NEW, 1).replace(OLD_JS, NEW_JS, 1)
    path.write_text(t, encoding="utf-8")
    print("patched", path)


if __name__ == "__main__":
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/var/www/sailingsa/api/api.py"))
