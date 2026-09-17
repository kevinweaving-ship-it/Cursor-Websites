#!/usr/bin/env python3
"""Replace class Regattas table with club Upcoming/Past event cards."""
from pathlib import Path

INDEX = Path("/var/www/sailingsa/index.sailor_spa.html")
NEW_JS = Path("/tmp/class_event_cards.js").read_text(encoding="utf-8")
NEW_FILTER = Path("/tmp/class_event_filter.js").read_text(encoding="utf-8")
MARK = "CLASS_GOLD_EVENT_CARDS_v1"

OLD_SECTION = "section('regattas', 'Regattas (' + regattas.length + ')', 'class-regattas-table', regattaTable) +"
NEW_SECTION = "eventCardsHtml +"

OLD_TABLE = """            var regattaTable = '<table class="table" id="class-regattas-table"><thead><tr><th>#</th><th>Event</th><th>Date</th><th class="hide-mobile">Host</th><th>Entries</th><th>' + esc(className || 'Class') + '</th><th class="hide-mobile">Races</th></tr></thead><tbody>' +
                (regattaRows || '<tr><td colspan="7">No regattas</td></tr>') + '</tbody></table>';
"""

FILTER_NEEDLE = "            if (typeof attachSortableTables === 'function') attachSortableTables(cv);"


def main():
    text = INDEX.read_text(encoding="utf-8")
    if MARK in text:
        print("ALREADY")
        return
    a = text.find("            var regattaRows = regattas.map")
    b = text.find("            var clubRows = clubs.map")
    if a < 0 or b < 0 or b <= a:
        raise SystemExit("ERROR rows block %s %s" % (a, b))
    text = text[:a] + "            /* " + MARK + " */\n" + NEW_JS + text[b:]
    if OLD_SECTION not in text:
        raise SystemExit("ERROR section")
    text = text.replace(OLD_SECTION, NEW_SECTION, 1)
    if OLD_TABLE in text:
        text = text.replace(OLD_TABLE, "", 1)
    if NEW_FILTER.strip() not in text:
        if FILTER_NEEDLE not in text:
            raise SystemExit("ERROR filter insert")
        text = text.replace(FILTER_NEEDLE, NEW_FILTER + FILTER_NEEDLE, 1)
    bak = Path(str(INDEX) + ".bak.class_gold_event_cards")
    if not bak.exists():
        bak.write_text(INDEX.read_text(encoding="utf-8"), encoding="utf-8")
        print("BACKUP", bak)
    INDEX.write_text(text, encoding="utf-8")
    print("OK size", INDEX.stat().st_size, "cards", text.count("classEventCard"), "upcoming", text.count("Upcoming events"))


if __name__ == "__main__":
    main()
