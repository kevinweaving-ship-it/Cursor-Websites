#!/usr/bin/env python3
"""Point landing/regatta-list fleet chips at Event /class-{slug} child URLs."""
from pathlib import Path
import sys

OLD = "chip.href = '/regatta/' + encodeURIComponent(childId);"
NEW = """var parentRid = String((ch.parent_regatta_id || rid) || '').trim();
                        var classSlug = String(ch.class_slug || '').trim();
                        if (!classSlug && parentRid && childId.indexOf(parentRid + '-') === 0) {
                            classSlug = childId.slice(parentRid.length + 1).replace(/-fleet$/i, '');
                        }
                        chip.href = (parentRid && classSlug)
                            ? ('/regatta/' + encodeURIComponent(parentRid) + '/class-' + encodeURIComponent(classSlug))
                            : ('/regatta/' + encodeURIComponent(childId));"""


def main() -> int:
    paths = [Path(p) for p in (sys.argv[1:] or ["/var/www/sailingsa/index.html", "/var/www/sailingsa/blank.html"])]
    for path in paths:
        if not path.is_file():
            print("skip missing", path)
            continue
        text = path.read_text(encoding="utf-8")
        n = text.count(OLD)
        if n == 0:
            print("already patched or different", path)
            continue
        if n != 1:
            raise SystemExit(f"{path}: expected 1 chip.href, found {n}")
        path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
        print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
