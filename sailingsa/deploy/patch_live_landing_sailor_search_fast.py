#!/usr/bin/env python3
"""After typing stops: names first, then a real /dev-1 card for every on-screen match.

Do not fetch cards while typing. Abort in-flight /dev-1 on each keystroke.
Marker: LANDING_SAILOR_SEARCH_VISIBLE_CARDS_v7
"""
from __future__ import annotations

from pathlib import Path

HTMLS = [
    Path("/var/www/sailingsa/blank.html"),
    Path("/var/www/sailingsa/index.html"),
]
MARKER = "LANDING_SAILOR_SEARCH_VISIBLE_CARDS_v7"

VISIBLE_CARDS = """                        if (window.__ssaSailorCardIO) {
                            try { window.__ssaSailorCardIO.disconnect(); } catch (_) {}
                            window.__ssaSailorCardIO = null;
                        }
                        /* """ + MARKER + """ every on-screen match gets a real /dev-1 card */
                        var cardQ = [];
                        var cardBusy = 0;
                        var cardMax = 2;
                        function pumpCards() {
                            if (gen !== (window.__sailorSearchGen || 0)) return;
                            while (cardBusy < cardMax && cardQ.length) {
                                var it = cardQ.shift();
                                cardBusy += 1;
                                Promise.resolve(fetchOne(it)).then(function() {
                                    cardBusy -= 1;
                                    pumpCards();
                                }, function() {
                                    cardBusy -= 1;
                                    pumpCards();
                                });
                            }
                        }
                        function enqueueCard(item) {
                            if (!item || item.wrap.getAttribute('data-card-queued') === '1') return;
                            item.wrap.setAttribute('data-card-queued', '1');
                            cardQ.push(item);
                            pumpCards();
                        }
                        if (typeof IntersectionObserver === 'function') {
                            var io = new IntersectionObserver(function(entries) {
                                if (gen !== (window.__sailorSearchGen || 0)) return;
                                entries.forEach(function(en) {
                                    if (!en.isIntersecting) return;
                                    io.unobserve(en.target);
                                    var item = null;
                                    for (var si = 0; si < slots.length; si++) {
                                        if (slots[si].wrap === en.target) { item = slots[si]; break; }
                                    }
                                    if (item) enqueueCard(item);
                                });
                            }, { root: null, rootMargin: '100px 0px', threshold: 0.01 });
                            window.__ssaSailorCardIO = io;
                            for (var so = 0; so < slots.length; so++) io.observe(slots[so].wrap);
                        } else {
                            for (var sf = 0; sf < slots.length; sf++) enqueueCard(slots[sf]);
                        }
                        return Promise.resolve();
"""

OLD_TOP1_A = """                        if (window.__ssaSailorCardIO) {
                            try { window.__ssaSailorCardIO.disconnect(); } catch (_) {}
                            window.__ssaSailorCardIO = null;
                        }
                        /* LANDING_SAILOR_SEARCH_TOP1_AFTER_IDLE_v6 only #1 card after typing stops */
                        return slots[0] ? fetchOne(slots[0]) : Promise.resolve();"""

OLD_TOP1_B = """                        if (window.__ssaSailorCardIO) {
                            try { window.__ssaSailorCardIO.disconnect(); } catch (_) {}
                            window.__ssaSailorCardIO = null;
                        }
                        // After typing has stopped: only the current #1 (best match). Do not pre-build the rest.
                        return slots[0] ? fetchOne(slots[0]) : Promise.resolve();"""


def patch_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    if MARKER in text and "enqueueCard" in text:
        print("HTML", path, "already v7")
        return
    if OLD_TOP1_A in text:
        text = text.replace(OLD_TOP1_A, VISIBLE_CARDS, 1)
    elif OLD_TOP1_B in text:
        text = text.replace(OLD_TOP1_B, VISIBLE_CARDS, 1)
    else:
        raise SystemExit(f"top-1 block missing {path}")
    if "/dev-1?embed=1" not in text:
        raise SystemExit(f"dev-1 missing {path}")
    if MARKER not in text:
        raise SystemExit(f"v7 marker missing {path}")
    if text == orig:
        raise SystemExit(f"no html changes {path}")
    path.write_text(text, encoding="utf-8")
    print("HTML", path, "ok")


def main() -> int:
    for p in HTMLS:
        if p.is_file():
            patch_html(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
