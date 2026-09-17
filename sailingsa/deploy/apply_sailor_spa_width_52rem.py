#!/usr/bin/env python3
"""Force class gold cards to club 52rem centred width."""
from pathlib import Path

INDEX = Path("/var/www/sailingsa/index.sailor_spa.html")
MARK = "CLASS_GOLD_WIDTH_52REM_v1"

CSS = """
        /* """ + MARK + """ club story cards = 52rem centred */
        .class-gold-page .card.stats-section,
        .class-gold-page .club-story-logo-row,
        .class-gold-page .class-gold-identity-card {
            width: 100%;
            max-width: 52rem;
            margin-left: auto;
            margin-right: auto;
            display: block;
            box-sizing: border-box;
        }
        .class-gold-page .club-story-inner { width: 100%; max-width: 100%; margin: 0 auto; }
        @media (max-width: 768px) {
            .class-gold-page .card.stats-section,
            .class-gold-page .club-story-logo-row,
            .class-gold-page .class-gold-identity-card { max-width: 100%; }
        }
"""


def main():
    text = INDEX.read_text(encoding="utf-8")
    if MARK in text:
        print("ALREADY")
        return
    needle = "/* CLASS_GOLD_WIDTH_WRAP_v1 club-std width + MP keep-together */"
    if needle in text:
        text = text.replace(needle, needle + CSS, 1)
    elif "/* CLASS_GOLD_OUTER_CARDS_v1 */" in text:
        text = text.replace("/* CLASS_GOLD_OUTER_CARDS_v1 */", "/* CLASS_GOLD_OUTER_CARDS_v1 */" + CSS, 1)
    else:
        raise SystemExit("ERROR no insert point")
    bak = Path(str(INDEX) + ".bak.class_gold_52rem")
    if not bak.exists():
        bak.write_text(INDEX.read_text(encoding="utf-8"), encoding="utf-8")
        print("BACKUP", bak)
    INDEX.write_text(text, encoding="utf-8")
    print("OK size", INDEX.stat().st_size)


if __name__ == "__main__":
    main()
