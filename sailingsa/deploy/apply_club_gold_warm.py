#!/usr/bin/env python3
"""Wipe stale club HTML and warm every slug to gold HMYC cards. Keep ZVYC story headers."""
from pathlib import Path
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DISK = Path("/var/tmp/sailingsa_club_pages")
SLUG_FILE = Path("/tmp/club_gold_slugs.txt")
HDRS = {"Host": "sailingsa.co.za", "X-Forwarded-Proto": "https"}
KNOWN = """
1bss abyc ayc bishops bryc bsc byc china cryc dac drsc dut dyc edyc elyc
epbc fhyc fbyc gbyc ghs gmbc glyc grsc gyc hbyc hmyc hsc hyc isc iyc izi
jyc-zim khp ksyc kyc lasa ldyc ltwc lyc lycn mac mbsc mbyc moz mryc myc
nrsc nsa pbyc perbc pnyc poyc psc pyc rcyc rcyca rnyc ryc sac sacs sbyc
spyc syc tac tcc tsa tsc tuks tyc uct ukzn usyc vca vlc vsc vyc wbyc wits
wyac zvsc zyc zvyc
""".split()

def collect_slugs() -> list[str]:
    slugs = set(KNOWN)
    if SLUG_FILE.exists():
        slugs.update(x.strip() for x in SLUG_FILE.read_text().split() if x.strip())
    if DISK.exists():
        for p in DISK.glob("*.html"):
            name = p.name[:-5]
            if "." in name:
                name = name.split(".")[0]
            if name and name not in ("none", "unassigned", "unk"):
                slugs.add(name)
    slugs.discard("none")
    slugs.discard("unassigned")
    slugs.discard("unk")
    out = sorted(slugs)
    SLUG_FILE.write_text("\n".join(out) + "\n")
    return out

def wipe() -> int:
    n = 0
    if not DISK.exists():
        return 0
    for p in DISK.glob("*.html"):
        try:
            p.unlink()
            n += 1
        except OSError as e:
            print("UNLINK_ERR", p.name, e)
    return n

def grab(slug: str) -> tuple[str, int, str]:
    req = urllib.request.Request(
        "http://127.0.0.1:8000/club/%s?cb=goldall1" % slug, headers=HDRS
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read().decode("utf-8", "replace")
            return slug, r.status, body
    except Exception as e:
        return slug, 0, str(e)

def markers(h: str) -> dict:
    return {
        "cards": h.count("sa-home-regatta-card"),
        "stack": h.count("club-home-cards-stack"),
        "toggle": h.count("club-list-expand-btn"),
        "slot": h.count("club-home-sailor-slot"),
        "table": h.count("club-upcoming-table"),
        "hosted": h.count("Events hosted"),
        "classes": h.count("Classes sailed"),
        "story": h.count("club-story-header"),
        "weather": h.lower().count("weather"),
        "len": len(h),
    }

def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    slugs = collect_slugs()
    print("SLUGS", len(slugs))

    if mode in ("wipe", "all"):
        n = wipe()
        print("WIPED", n)

    if mode == "wipe":
        return 0

    t0 = time.time()
    gold = old = err = 0
    rows = []
    workers = 3
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(grab, s): s for s in slugs}
        for fut in as_completed(futs):
            slug, code, body = fut.result()
            if code != 200 or "<html" not in body.lower():
                err += 1
                print("ERR", slug, code, body[:80].replace("\n", " "))
                continue
            m = markers(body)
            is_gold = m["stack"] > 0 and m["table"] == 0
            if is_gold:
                gold += 1
            else:
                old += 1
            flag = "GOLD" if is_gold else "OLD"
            print(
                f"{flag} {slug:12} cards={m['cards']:3} tog={m['toggle']:2} "
                f"slot={m['slot']:3} tbl={m['table']} hosted={m['hosted']} "
                f"classes={m['classes']} story={m['story']} wx={m['weather']} len={m['len']}"
            )
            rows.append((slug, m, flag))

    print("DONE gold", gold, "old", old, "err", err, "sec", int(time.time() - t0))

    zv = next((r for r in rows if r[0] == "zvyc"), None)
    if zv:
        m, flag = zv[1], zv[2]
        print(
            "ZVYC_EXTRAS", flag,
            "hosted", m["hosted"],
            "classes", m["classes"],
            "story", m["story"],
            "wx", m["weather"],
        )
        if flag != "GOLD" or m["hosted"] < 1 or m["classes"] < 1 or m["story"] < 1:
            print("ZVYC_EXTRAS_FAIL")
            return 2
        print("ZVYC_EXTRAS_OK")
    else:
        print("ZVYC_MISSING")
        return 2

    hm = next((r for r in rows if r[0] == "hmyc"), None)
    if not hm or hm[2] != "GOLD":
        print("HMYC_GOLD_FAIL")
        return 3

    if old:
        print("STILL_OLD", [r[0] for r in rows if r[2] == "OLD"])
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
