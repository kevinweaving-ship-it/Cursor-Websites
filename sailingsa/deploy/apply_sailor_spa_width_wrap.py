#!/usr/bin/env python3
"""Widen class gold cards to club std width and keep count+label pairs together."""
from pathlib import Path

INDEX = Path("/var/www/sailingsa/index.sailor_spa.html")
MARK = "CLASS_GOLD_WIDTH_WRAP_v1"

CSS_BLOCK = """
        /* """ + MARK + """ club-std width + MP keep-together */
        .class-gold-page { max-width: 1100px; width: 100%; margin: 0 auto; padding: 1.25rem 0 2rem; box-sizing: border-box; }
        .class-gold-page .card.stats-section,
        .class-gold-page .club-story-logo-row,
        .class-gold-page .class-gold-identity-card {
            width: 100%;
            max-width: 100%;
            margin-left: auto;
            margin-right: auto;
            display: block;
            box-sizing: border-box;
        }
        .class-gold-page .club-story-inner { width: 100%; max-width: 100%; margin: 0 auto; }
        .class-gold-page .club-story-meta {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            align-items: flex-start;
            gap: 0.45rem 1.1rem;
            width: 100%;
            text-align: center;
        }
        .class-gold-page .club-story-meta-item {
            display: inline-flex;
            flex-direction: row;
            align-items: baseline;
            gap: 0.28rem;
            white-space: nowrap;
        }
        .class-gold-page .club-story-meta-n,
        .class-gold-page .club-story-meta-w { display: inline-block; }
        .class-gold-page .class-gold-title-phrase { white-space: nowrap; }
        .class-gold-page .club-story-logo-row-label {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: center;
            gap: 0.45rem;
        }
        .class-gold-page .club-story-chip-count {
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            justify-content: center;
            align-items: baseline;
            gap: 0.15rem 0.28rem;
        }
        .class-gold-page .club-story-chip-count-n,
        .class-gold-page .club-story-chip-count-w { display: inline-block; white-space: nowrap; }
        .class-gold-page .club-story-chip-label { word-break: normal; overflow-wrap: break-word; hyphens: none; }
        @media (max-width: 640px) and (orientation: portrait) {
            .class-gold-page .club-story-meta-item {
                flex-direction: column;
                align-items: center;
                white-space: normal;
                line-height: 1.15;
            }
            .class-gold-page .club-story-chip-count { flex-direction: column; align-items: center; }
        }
"""

OLD_INNER = ".class-gold-page .club-story-inner { width: 100%; max-width: 42rem; margin: 0 auto; display: flex; flex-direction: column; align-items: center; gap: 0.85rem; }"
NEW_INNER = ".class-gold-page .club-story-inner { width: 100%; max-width: 100%; margin: 0 auto; display: flex; flex-direction: column; align-items: center; gap: 0.85rem; }"

OLD_META_JOIN = "(meta.length ? '<p class=\"club-story-meta\">' + esc(meta.join(' · ')) + '</p>' : '') +"
NEW_META_JOIN = "(meta.length ? '<p class=\"club-story-meta\">' + meta.join('') + '</p>' : '') +"

OLD_META_PUSH = """            if (sailorsN) meta.push(sailorsN + ' sailor' + (sailorsN === 1 ? '' : 's'));
            if (regN) meta.push(regN + ' regatta' + (regN === 1 ? '' : 's'));
            if (raceN) meta.push(raceN.toLocaleString() + ' race' + (raceN === 1 ? '' : 's'));
            if (clubs.length) meta.push(clubs.length + ' club' + (clubs.length === 1 ? '' : 's'));"""

NEW_META_PUSH = """            function metaPair(n, word) {
                return '<span class="club-story-meta-item"><span class="club-story-meta-n">' + esc(String(n)) + '</span><span class="club-story-meta-w">' + esc(word) + '</span></span>';
            }
            if (sailorsN) meta.push(metaPair(sailorsN, 'sailor' + (sailorsN === 1 ? '' : 's')));
            if (regN) meta.push(metaPair(regN, 'regatta' + (regN === 1 ? '' : 's')));
            if (raceN) meta.push(metaPair(raceN.toLocaleString(), 'race' + (raceN === 1 ? '' : 's')));
            if (clubs.length) meta.push(metaPair(clubs.length, 'club' + (clubs.length === 1 ? '' : 's')));"""

OLD_COUNT = """                var countLab = row.n + ' event' + (row.n === 1 ? '' : 's');
                var logo = '<span class="club-story-chip-logo"><img src="' + esc(p) + '" alt="' + esc(lab) + '" loading="lazy" decoding="async" onerror="this.style.display=\\'none\\'"></span>';
                var inner = logo +
                    '<span class="club-story-chip-count">' + esc(countLab) + '</span>' +
                    '<span class="club-story-chip-label">' + esc(lab) + '</span>';"""

NEW_COUNT = """                var countWord = 'event' + (row.n === 1 ? '' : 's');
                var countLab = row.n + ' ' + countWord;
                var logo = '<span class="club-story-chip-logo"><img src="' + esc(p) + '" alt="' + esc(lab) + '" loading="lazy" decoding="async" onerror="this.style.display=\\'none\\'"></span>';
                var inner = logo +
                    '<span class="club-story-chip-count"><span class="club-story-chip-count-n">' + esc(String(row.n)) + '</span><span class="club-story-chip-count-w">' + esc(countWord) + '</span></span>' +
                    '<span class="club-story-chip-label">' + esc(lab) + '</span>';"""


def main():
    text = INDEX.read_text(encoding="utf-8")
    if MARK in text:
        print("ALREADY")
        return
    changed = []
    if OLD_INNER in text:
        text = text.replace(OLD_INNER, NEW_INNER, 1)
        changed.append("inner")
    if OLD_META_PUSH in text:
        text = text.replace(OLD_META_PUSH, NEW_META_PUSH, 1)
        changed.append("meta_push")
    if OLD_META_JOIN in text:
        text = text.replace(OLD_META_JOIN, NEW_META_JOIN, 1)
        changed.append("meta_join")
    if OLD_COUNT in text:
        text = text.replace(OLD_COUNT, NEW_COUNT, 1)
        changed.append("count")

    # Insert CSS after outer-cards marker or before first class-gold-page rule
    needle = "/* CLASS_GOLD_OUTER_CARDS_v1 */"
    if needle in text:
        text = text.replace(needle, needle + CSS_BLOCK, 1)
        changed.append("css_after_outer")
    else:
        gold = "        .class-gold-page {"
        if gold in text:
            text = text.replace(gold, CSS_BLOCK + "\n" + gold, 1)
            changed.append("css_before_gold")
        else:
            raise SystemExit("ERROR no css insert point")

    # Title phrases on live sailor_spa strips
    old_ev = "Events featuring ' + classTitleLogo"
    new_ev = '<span class="class-gold-title-phrase">Events featuring</span> \' + classTitleLogo'
    old_cl = "Clubs sailing ' + classTitleLogo"
    new_cl = '<span class="class-gold-title-phrase">Clubs sailing</span> \' + classTitleLogo'
    if old_ev in text:
        text = text.replace(old_ev, new_ev, 1)
        changed.append("title_events")
    if old_cl in text:
        text = text.replace(old_cl, new_cl, 1)
        changed.append("title_clubs")

    if not changed:
        raise SystemExit("ERROR nothing changed")
    bak = Path(str(INDEX) + ".bak.class_gold_width_wrap")
    if not bak.exists():
        bak.write_text(INDEX.read_text(encoding="utf-8"), encoding="utf-8")
        print("BACKUP", bak)
    INDEX.write_text(text, encoding="utf-8")
    print("OK", changed, "size", INDEX.stat().st_size)


if __name__ == "__main__":
    main()
