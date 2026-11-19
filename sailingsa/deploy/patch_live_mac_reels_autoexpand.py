#!/usr/bin/env python3
"""MAC Event URL: auto-expand + play when a new WhatsApp video arrives.

Same path as Midmar / Dart / Dam Bottle: queueFreshMidmar → openDartAuto.
Run on the box against /var/www/sailingsa/js/mm-lipton-reels-card.js
"""
from __future__ import annotations

from pathlib import Path

REELS = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")

SWAPS = (
    (
        "if (!(isMidmar() || isDartNats() || isDamBottle()) || !root._mmAutoPlaying) return;",
        "if (!(isMidmar() || isDartNats() || isDamBottle() || isMacTsl()) || !root._mmAutoPlaying) return;",
        "auto-end",
    ),
    (
        "if (!(isMidmar() || isDartNats() || isDamBottle()) || !root) return;",
        "if (!(isMidmar() || isDartNats() || isDamBottle() || isMacTsl()) || !root) return;",
        "mark-browse",
    ),
    (
        "if (!isMidmar() && !isDartNats() && !isDamBottle()) return;",
        "if (!isMidmar() && !isDartNats() && !isDamBottle() && !isMacTsl()) return;",
        "queue-fresh",
    ),
)


def apply(text: str) -> str:
    for old, new, name in SWAPS:
        if new in text:
            print(f"skip {name}: already present")
            continue
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: expected 1 match, got {n}")
        text = text.replace(old, new, 1)
        print(f"patch {name}")
    return text


def main() -> int:
    text = REELS.read_text()
    patched = apply(text)
    if patched != text:
        bak = REELS.with_name("mm-lipton-reels-card.js.bak_mac_autoexpand")
        if not bak.exists():
            bak.write_text(text)
            print("backup", bak)
        REELS.write_text(patched)
        print("wrote", REELS)
    else:
        print("no file change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
