#!/usr/bin/env python3
from pathlib import Path
import sys

JS = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")
OLD = "    window.setInterval(tick, (payload.videos || []).length ? 300000 : 60000);"
NEW = (
    "    var pollMs = 60000;"
    "    try {"
    "      if (isCapeClassic()) pollMs = 8000;"
    "      else if ((payload.videos || []).length) pollMs = 300000;"
    "    } catch (e1) {}"
    "    window.setInterval(tick, pollMs);"
)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else JS
    text = path.read_text(encoding="utf-8")
    if "pollMs = 8000" in text:
        print("already patched", path)
        return 0
    if text.count(OLD) != 1:
        raise SystemExit(f"poll interval count {text.count(OLD)}")
    path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
