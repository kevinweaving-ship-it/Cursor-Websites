#!/usr/bin/env python3
"""Use the small Dart 18 class logo on the landing card chip, same as 420."""

from __future__ import annotations

from pathlib import Path

DART_CHIP = (
    '<a class="sa-home-regatta-single-class" href="/class/dart-18" title="Dart 18" '
    'aria-label="Dart 18">'
    '<img class="sa-home-regatta-chip-logo" src="/artwork/Class Logo/Dart-18-Class-Logo.png" '
    'alt="Dart 18" width="46" height="24" loading="lazy" decoding="async" '
    'style="width:46px;height:24px;max-width:46px;max-height:24px;object-fit:contain"></a>'
)
DART_TEXT = (
    '<a class="sa-home-regatta-single-class" href="/class/dart-18">'
    '<span class="sa-home-regatta-chip-text">Dart 18</span></a>'
)

PY_OLD = '''_CLASS_LOGO = {
    "420": "/artwork/Class Logo/420-Class-Logo.png",
'''
PY_NEW = '''_CLASS_LOGO = {
    "420": "/artwork/Class Logo/420-Class-Logo.png",
    "dart 18": "/artwork/Class Logo/Dart-18-Class-Logo.png",
    "dart18": "/artwork/Class Logo/Dart-18-Class-Logo.png",
'''

JS_OLD = "                    '420': '/artwork/Class Logo/420-Class-Logo.png',\n"
JS_NEW = (
    "                    '420': '/artwork/Class Logo/420-Class-Logo.png',\n"
    "                    'dart 18': '/artwork/Class Logo/Dart-18-Class-Logo.png',\n"
    "                    'dart18': '/artwork/Class Logo/Dart-18-Class-Logo.png',\n"
)

PATHS = [
    Path("/var/www/sailingsa/index.html"),
    Path("/var/www/sailingsa/blank.html"),
    Path("/var/www/sailingsa/js/hub-regatta-list.js"),
    Path("/var/www/sailingsa/sailingsa/backend/landing_event_story_cards.py"),
]


def main() -> int:
    for path in PATHS:
        if not path.is_file():
            print("skip missing", path)
            continue
        text = path.read_text(encoding="utf-8")
        changed = False
        if DART_TEXT in text:
            text = text.replace(DART_TEXT, DART_CHIP)
            changed = True
            print("chip html", path)
        if PY_OLD in text and "dart 18" not in text[text.find("_CLASS_LOGO") : text.find("_CLASS_LOGO") + 400]:
            text = text.replace(PY_OLD, PY_NEW, 1)
            changed = True
            print("class map py", path)
        if JS_OLD in text and "'dart 18': '/artwork/Class Logo/Dart-18-Class-Logo.png'" not in text:
            text = text.replace(JS_OLD, JS_NEW)
            changed = True
            print("class map js", path)
        if changed:
            path.write_text(text, encoding="utf-8")
        else:
            print("no change", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
