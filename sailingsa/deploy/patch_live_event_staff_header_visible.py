#!/usr/bin/env python3
"""Show Staff header to guests; keep the list login-gated."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

OLD_HIDDEN = '    ".cape-crew--hidden{display:none}"'
NEW_HIDDEN = '    ".cape-crew--hidden{display:block}"'

OLD_SAILED = '''    note = "" if show else "Hidden from public"
    admin_cls = " cape-crew--admin" if always_show_button else ""
    hidden_cls = "" if show else " cape-crew--hidden"'''

NEW_SAILED = '''    note = "" if show else "Hidden from public"
    admin_cls = " cape-crew--admin" if always_show_button else ""
    hidden_cls = "" if show else " cape-crew--hidden"'''

# sailed line: guests should not see "Hidden from public"
OLD_SAILED_LINE = '''    sailed = html_module.escape(note) if note else "Event staff"'''
NEW_SAILED_LINE = '''    sailed = html_module.escape(note) if (is_editor and note) else "Event staff"'''


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(OLD_HIDDEN) != 1:
        raise SystemExit(f"hidden css count {text.count(OLD_HIDDEN)}")
    if text.count(OLD_SAILED_LINE) != 1:
        raise SystemExit(f"sailed count {text.count(OLD_SAILED_LINE)}")
    text = text.replace(OLD_HIDDEN, NEW_HIDDEN, 1)
    text = text.replace(OLD_SAILED_LINE, NEW_SAILED_LINE, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
