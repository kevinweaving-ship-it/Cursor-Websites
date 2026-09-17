#!/usr/bin/env python3
"""Force navy outer cards on class sailors/clubs/events like club gold."""
from pathlib import Path
import shutil
import time

INDEX = Path("/var/www/sailingsa/index.sailor_spa.html")
MARK = "CLASS_SAILOR_OUTER_v2"

OLD_HEAD = """        .class-gold-page .card.stats-section,
        .class-gold-page .club-story-logo-row,
        .class-gold-page .class-gold-identity-card {
            width: 100%;
            max-width: 52rem;
            margin-left: auto;
            margin-right: auto;
            display: block;
            box-sizing: border-box;
        }"""

NEW_HEAD = """        .class-gold-page .card.stats-section,
        .class-gold-page .club-story-logo-row,
        .class-gold-page .class-gold-identity-card {
            width: 100%;
            max-width: 52rem;
            margin-left: auto;
            margin-right: auto;
            margin-bottom: 1.25rem;
            display: block;
            box-sizing: border-box;
            background: #fff;
            border: 2px solid #001f3f;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 31, 63, 0.08);
            padding: 1rem 1.25rem;
        }"""

OLD_SAIL = """                '<style id="class-gold-sailor-cards-style">' +
                '.class-gold-page .club-home-sailor-list{display:flex;flex-direction:column;gap:10px;width:100%;}' +"""

NEW_SAIL = """                '<style id="class-gold-sailor-cards-style">' +
                '.class-gold-page .club-sailors-section.card.stats-section,.class-gold-page .club-home-cards-stack .card.stats-section,.class-gold-page #clubs.card.stats-section,.class-gold-page .club-upcoming-events-section.card,.class-gold-page .club-past-events-section.card{background:#fff!important;border:2px solid #001f3f!important;border-radius:8px!important;box-shadow:0 1px 3px rgba(0,31,63,.08)!important;padding:1rem 1.25rem!important;margin:0 auto 1.25rem!important;width:100%!important;max-width:52rem!important;box-sizing:border-box!important;display:block!important;}' +
                '.class-gold-page .club-home-sailor-list{display:flex;flex-direction:column;gap:10px;width:100%;}' +"""


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")
    if MARK in text:
        print("ALREADY")
        return
    miss = []
    if OLD_HEAD not in text:
        miss.append("HEAD")
    if OLD_SAIL not in text:
        miss.append("SAIL")
    if miss:
        raise SystemExit("MISSING:" + ",".join(miss))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = INDEX.with_name(INDEX.name + ".bak.class_sailors_v2." + ts)
    shutil.copy2(INDEX, bak)
    text = text.replace(OLD_HEAD, NEW_HEAD)
    text = text.replace(OLD_SAIL, NEW_SAIL, 1)
    text = text.replace("</head>", "<!-- " + MARK + " --></head>", 1)
    INDEX.write_text(text)
    print("OK", MARK, "HEAD", text.count("border: 2px solid #001f3f"), "BAK", str(bak))


if __name__ == "__main__":
    main()
