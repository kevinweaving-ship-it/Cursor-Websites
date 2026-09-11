#!/usr/bin/env python3
"""Update ZVYC Cape Classic 2026 entry list from a Revolutionise attendees CSV.

Adds new helms into Extra / ILCA / Optimist. Creates 420 and Mirror fleets.
Puts Fireball and Sonnet together in the Open fleet.

Block IDs and fleet labels are derived from class (ILCA 4.7 → ilca-4.7-fleet).
Unknown CSV classes auto-create `{slug}-fleet` shells instead of aborting.

Usage (on live, with DB_URL):
  python3 update_zvyc_cape_classic_2026_entries.py --csv PATH [--apply]
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REGATTA_ID = "2026-09-13-zvyc-cape-classic"
SCORING = "Appendix A"
RACES_SAILED = 1
RACE_SCORES_R5 = {"R1": "", "R2": "", "R3": "", "R4": "", "R5": ""}
RACE_SCORES_R1 = {"R1": ""}
RACE_SCORES_R2 = {"R1": "", "R2": ""}

# Previous 2026 fleets (before this CSV): Extra, ILCA 4.7 / 6 / 7, Optimist A/B, Sonnet.
PREVIOUS_2026_CLASSES = {
    "Extra",
    "Ilca 4.7",
    "Ilca 6",
    "Ilca 7",
    "Optimist A",
    "Optimist B",
    "Sonnet",
}

MIXED_SUFFIXES = frozenset({"open", "overall", "fast", "slow"})


def class_slug(name: str) -> str:
    s = (name or "").strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9.-]", "", s)
    return s.strip("-")


def suffix_for_class(canonical: str, forced: str | None = None) -> str:
    """Public block tail: mixed shells keep open/fast/slow; one-design gets {slug}-fleet."""
    if forced:
        return forced
    slug = class_slug(canonical)
    if slug in MIXED_SUFFIXES:
        return slug
    return f"{slug}-fleet" if slug else "open"


CLASS_MAP = {
    "fireball": ("Fireball", "Fireball", 77, "open"),
    "ilca 7": ("ILCA 7", "Ilca 7", 46, "ilca-7-fleet"),
    "laser": ("Laser", "Ilca 7", 46, "ilca-7-fleet"),
    "ilca 6": ("ILCA 6", "Ilca 6", 45, "ilca-6-fleet"),
    "ilca": ("ILCA", "Ilca 6", 45, "ilca-6-fleet"),
    "ilca 4": ("Ilca 4.7", "Ilca 4.7", 8, "ilca-4.7-fleet"),  # CSV "ILCA 4" is not a class
    "ilca 4.7": ("Ilca 4.7", "Ilca 4.7", 8, "ilca-4.7-fleet"),
    "laser 4.7": ("Laser 4.7", "Ilca 4.7", 8, "ilca-4.7-fleet"),
    "sonnet": ("Sonnet", "Sonnet", 10, "open"),
    "optimist": ("Optimist", "Optimist A", 62, "optimist-a-fleet"),
    "optimist - a fleet": ("Optimist - A Fleet", "Optimist A", 62, "optimist-a-fleet"),
    "optimist fleet b": ("Optimist Fleet B", "Optimist B", 63, "optimist-a-fleet"),
    "extra": ("Extra", "Extra", 29, "extra-fleet"),
    "xtra": ("Xtra", "Extra", 29, "extra-fleet"),
    "420": ("420", "420", 7, "420-fleet"),
    "mirror": ("Mirror", "Mirror", 2, "mirror-fleet"),
}

BLOCKS = {
    "extra-fleet": {
        "class_original": "Extra",
        "class_canonical": "Extra",
        "fleet_label": "Extra",
        "class_id": 29,
        "race_scores": RACE_SCORES_R1,
    },
    "ilca-fleet": {
        "class_original": "ILCA",
        "class_canonical": "ILCA",
        "fleet_label": "ILCA",
        "class_id": None,
        "race_scores": RACE_SCORES_R5,
    },
    "ilca-4.7-fleet": {
        "class_original": "Ilca 4.7",
        "class_canonical": "Ilca 4.7",
        "fleet_label": "ILCA 4.7",
        "class_id": 8,
        "race_scores": RACE_SCORES_R5,
    },
    "ilca-6-fleet": {
        "class_original": "Ilca 6",
        "class_canonical": "Ilca 6",
        "fleet_label": "ILCA 6",
        "class_id": 45,
        "race_scores": RACE_SCORES_R5,
    },
    "ilca-7-fleet": {
        "class_original": "Ilca 7",
        "class_canonical": "Ilca 7",
        "fleet_label": "ILCA 7",
        "class_id": 46,
        "race_scores": RACE_SCORES_R5,
    },
    "optimist-a-fleet": {
        "class_original": "Optimist",
        "class_canonical": "Optimist",
        "fleet_label": "Optimist",
        "class_id": 1,
        "race_scores": RACE_SCORES_R5,
    },
    "420-fleet": {
        "class_original": "420",
        "class_canonical": "420",
        "fleet_label": "420",
        "class_id": 7,
        "race_scores": RACE_SCORES_R5,
    },
    "mirror-fleet": {
        "class_original": "Mirror",
        "class_canonical": "Mirror",
        "fleet_label": "Mirror",
        "class_id": 2,
        "race_scores": RACE_SCORES_R5,
    },
    "open": {
        "class_original": "OPEN",
        "class_canonical": "Open",
        "fleet_label": "Open",
        "class_id": 60,
        "race_scores": RACE_SCORES_R2,
    },
}

# CSV name (normalised) -> SAS match used for SA id / sail / club.
SAILOR_MATCH = {
    "ethan robbertze": {
        "helm_name": "Ethan Robbertze",
        "sa_id": 27710,
        "sail": "",
        "club": "ELYC",
        "club_id": 121,
    },
    "arthur peter wilson": {
        "helm_name": "Peter Wilson",
        "sa_id": 5141,
        "sail": "214130",
        "club": "ZVYC",
        "club_id": 3,
    },
    "blake madel": {
        "helm_name": "Blake Madel",
        "sa_id": 8680,
        "sail": "188566",
        "club": "ZVYC",
        "club_id": 3,
    },
    "sean kavanagh": {
        "helm_name": "Sean Kavanagh",
        "sa_id": 6804,
        "sail": "585",
        "club": "SBYC",
        "club_id": 17,
    },
    "liam geldenhuys": {
        "helm_name": "Liam Geldenhuys",
        "sa_id": 25653,
        "sail": "144",
        "club": "HYC",
        "club_id": 10,
    },
    "aaron ward": {
        "helm_name": "Aaron Ward",
        "sa_id": 12610,
        "sail": "188056",
        "club": "HMYC",
        "club_id": 98,
    },
    "kyo roberts": {
        "helm_name": "Kayo Roberts",
        "sa_id": 12516,
        "sail": "",
        "club": "IZI",
        "club_id": 28,
        # CSV "Laser"; no ILCA history. Parked in ILCA 7 for now (organizer).
        "class_override": ("Laser", "Ilca 7", 46, "ilca-7-fleet"),
        "note": "CSV Laser; no ILCA history — ILCA 7 for now.",
    },
    "simamkele mtshofeni": {
        "helm_name": "Simamkele Mtshofeni",
        "sa_id": 18908,
        "sail": "53007",
        "club": "IZI",
        "club_id": 28,
    },
    "athenkosi mahlumba": {
        "helm_name": "Athenkosi Mahluma",
        "sa_id": 12512,
        "sail": "53007",
        "club": "IZI",
        "club_id": 28,
    },
    "holden litsenborgh": {
        "helm_name": "Holden Van Litsenborgh",
        "sa_id": 28172,
        "sail": "54828",
        "club": "IZI",
        "club_id": 28,
    },
    "bradwin fritz": {
        "helm_name": "Bradwin Fritz",
        "sa_id": 28120,
        "sail": "54828",
        "club": "IZI",
        "club_id": 28,
    },
    "kimberly dube": {
        "helm_name": "Kimberly Dube",
        "sa_id": 29361,
        "sail": "54843",
        "club": "IZI",
        "club_id": 28,
    },
    "luke groenewaldt": {
        "helm_name": "Luke Groenewaldt",
        "sa_id": 28173,
        "sail": "70412",
        "club": "IZI",
        "club_id": 28,
    },
    "giovanni jansen": {
        "helm_name": "Giovanni Jansen",
        "sa_id": 28122,
        "sail": "69647",
        "club": "IZI",
        "club_id": 28,
    },
    "abdull alexander": {
        "helm_name": "Abdull Alexander",
        "sa_id": 23005,
        "sail": "1",
        "club": "ZVYC",
        "club_id": 3,
    },
    "renton geduld": {
        "helm_name": "Renton Geduld",
        "sa_id": 17517,
        "sail": "54808",
        "club": "ZVYC",
        "club_id": 3,
    },
    "amir yaghya": {
        "helm_name": "Amir Yaghya",
        "sa_id": 8382,
        "sail": "54808",
        "club": "ZVYC",
        "club_id": 3,
    },
    "jemayne wolmarans": {
        "helm_name": "Jemayne Wolmarans",
        "sa_id": 1521,
        "sail": "52997",
        "club": "ZVYC",
        "club_id": 3,
    },
    "nicholas breedt": {
        "helm_name": "Nicholas Breedt",
        "sa_id": 8893,
        "sail": "867",
        "club": "IYC",
        "club_id": 54,
    },
    "sebastian fourie": {
        "helm_name": "Sebastian Fourie",
        "sa_id": 25018,
        "sail": "6040",
        "club": "MAC",
        "club_id": 58,
    },
    "benjamin fourie": {
        "helm_name": "Benjamin Fourie",
        "sa_id": 25017,
        "sail": "1480",
        "club": "ZVYC",
        "club_id": 3,
    },
    "noah clulow": {
        "helm_name": "Noah Clulow",
        "sa_id": 15614,
        "sail": "144324",
        "club": "HMYC",
        "club_id": 98,
    },
    "aaron biagio": {
        "helm_name": "Aaron Biagio",
        "sa_id": 9393,
        "sail": "",
        "club": "RCYC",
        "club_id": 11,
    },
}

# Already on the 2026 list (CSV spelling -> existing helm).
ALREADY_ON_LIST = {
    "arran graham": "Arran Graham",
    "dylan le roux": "Dylan le Roux",
    "richard nankin": "Richard Nankin",
    "gordon guthrie": "Gordon Guthrie",
    "lele mseswa": "Bazolele Mseswa",
    "henning kock": "Henning Kock",
    "joshua keytel": "Joshua Keytel",
    "isabella keytel": "Isabella Keytel",
    "alistair keytel": "Alistair Keytel",
    "stephen du toit": "Stephen Du Toit",
    "alan keen": "Alan Keen",
    "jens dugas": "Jens Dugas",
    "jacques dugas": "Jacques Dugas",
    "rob foreman": "Robert Foreman",
    "alan gie": "Alan Gie",
    "eugene julius": "Eugene Julius",
    "robert wood": "Robert Wood",
    "alan everett": "Alan Everett",
    "theo scheder-bieschin": "Theodor Scheder-Bieschin",
    "andrew jones": "Andrew Jones",
    "jason deane": "Jason Deane",
    "david mair": "David Mair",
    "patrick jackson": "Patrick Jackson",
    "matthew starke": "Matthew Starke",
    "edison lu": "Edison Lu",
    "hanwen lu": "Hanwen Lu",
    "ian macrobert": "Ian MacRobert",
    "kevin foreman": "Kevin Foreman",
}


def norm_name(s: str) -> str:
    return " ".join((s or "").replace(",", " ").split()).strip().lower()


def block_id_for(suffix: str) -> str:
    return f"{REGATTA_ID}:{suffix}"


def load_csv(path: Path) -> list[dict]:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    rows = []
    with io.StringIO(raw.decode("utf-8-sig", errors="replace"), newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = (row.get("Attendee name") or "").strip()
            if not name or name.lower() in {"booking fee total", "total"}:
                continue
            rows.append(row)
    return rows


def map_class(raw_class: str) -> tuple[str, str, int | None, str]:
    key = " ".join((raw_class or "").split()).strip().lower()
    if key in CLASS_MAP:
        return CLASS_MAP[key]
    canonical = " ".join((raw_class or "").split()).strip()
    if not canonical:
        raise SystemExit(f"Unmapped class: {raw_class!r}")
    return canonical, canonical, None, suffix_for_class(canonical)


def connect():
    import psycopg2
    import psycopg2.extras

    url = os.getenv("DB_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("ERROR: DB_URL / DATABASE_URL not set")
    conn = psycopg2.connect(url)
    return conn, psycopg2.extras


def ensure_block(
    cur,
    suffix: str,
    *,
    orig: str | None = None,
    canonical: str | None = None,
    class_id: int | None = None,
    fleet_label: str | None = None,
) -> None:
    meta = BLOCKS.get(suffix) or {}
    orig = orig or meta.get("class_original") or canonical or suffix
    canonical = canonical or meta.get("class_canonical") or orig
    if class_id is None:
        class_id = meta.get("class_id")
    label = (fleet_label or meta.get("fleet_label") or canonical or "").strip() or None
    bid = block_id_for(suffix)
    cur.execute(
        "SELECT 1 FROM regatta_blocks WHERE block_id = %s",
        (bid,),
    )
    if cur.fetchone():
        cur.execute(
            """
            UPDATE regatta_blocks
            SET fleet_label = COALESCE(NULLIF(TRIM(fleet_label), ''), %s),
                block_label_raw = COALESCE(NULLIF(TRIM(block_label_raw), ''), %s),
                class_canonical = COALESCE(NULLIF(TRIM(class_canonical), ''), %s),
                class_original = COALESCE(NULLIF(TRIM(class_original), ''), %s)
            WHERE block_id = %s
            """,
            (label, label, canonical, orig, bid),
        )
        return
    cur.execute(
        """
        INSERT INTO regatta_blocks (
            block_id, regatta_id, class_original, class_canonical, fleet_label,
            races_sailed, discard_count, to_count, scoring_system, class_id,
            entries_raced, entries_closed, block_label_raw
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, 0, 1, %s, %s,
            0, false, %s
        )
        """,
        (
            bid,
            REGATTA_ID,
            orig,
            canonical,
            label,
            RACES_SAILED,
            SCORING,
            class_id,
            label,
        ),
    )
    print(f"Created block {bid}", file=sys.stderr)


def existing_keys(cur) -> tuple[set[str], set[int]]:
    cur.execute(
        """
        SELECT helm_name, helm_sa_sailing_id
        FROM results
        WHERE regatta_id = %s
        """,
        (REGATTA_ID,),
    )
    names = set()
    ids = set()
    for helm, sid in cur.fetchall():
        names.add(norm_name(helm or ""))
        if sid:
            ids.add(int(sid))
    # Nickname / spelling aliases already on the list.
    names.update(ALREADY_ON_LIST.keys())
    return names, ids


def rerank_fleets(cur) -> None:
    """ILCA: 4.7 then 6 then 7 then name. Others: helm name."""
    ilca_order = {"Ilca 4.7": 1, "Ilca 6": 2, "Ilca 7": 3}
    cur.execute(
        """
        SELECT result_id, block_id, class_canonical, helm_name
        FROM results
        WHERE regatta_id = %s
        """,
        (REGATTA_ID,),
    )
    rows = cur.fetchall()
    by_block: dict[str, list] = {}
    for result_id, bid, canonical, helm in rows:
        by_block.setdefault(bid, []).append((result_id, canonical or "", helm or ""))
    for bid, items in by_block.items():
        if bid.endswith(":ilca-fleet"):
            items.sort(key=lambda r: (ilca_order.get(r[1], 9), r[2].lower(), r[0]))
        elif bid.endswith(":open"):
            open_order = {"Fireball": 1, "Sonnet": 2}
            items.sort(key=lambda r: (open_order.get(r[1], 9), r[2].lower(), r[0]))
        else:
            items.sort(key=lambda r: (r[2].lower(), r[0]))
        for i, item in enumerate(items, start=1):
            cur.execute(
                "UPDATE results SET rank = %s WHERE result_id = %s",
                (i, item[0]),
            )
        suffix = bid.split(":", 1)[-1]
        fleet_label = BLOCKS.get(suffix, {}).get("fleet_label") or None
        if not fleet_label:
            sample_canonical = (items[0][1] if items else "") or suffix.replace("-", " ")
            fleet_label = sample_canonical
        if suffix == "ilca-fleet":
            fleet_label = "ILCA"
        cur.execute(
            """
            UPDATE results
            SET fleet_label = %s
            WHERE block_id = %s AND (fleet_label IS NULL OR fleet_label = '')
            """,
            (fleet_label, bid),
        )
        cur.execute(
            """
            UPDATE regatta_blocks
            SET entries_raced = %s
            WHERE block_id = %s
            """,
            (len(items), bid),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    attendees = load_csv(args.csv)
    print(
        "ILCA unspecified (CSV had no 4.7 / 6 / 7):\n"
        "  Jacques Dugas  CSV=ILCA   → ILCA 6 (23× ILCA 6, primary Ilca 6, age 17, sail 161599)\n"
        "  Jens Dugas     CSV=ILCA   → ILCA 4.7 (8× 4.7 vs 3× 6, age 15, last Cape Classic 4.7 sail 14;\n"
        "                              May 2026 ILCA Nationals was 6 / 171060 — confirm if stepping up)\n"
        "  Kayo Roberts   CSV=Laser  → ILCA 7 for now (no ILCA history; organizer call).\n",
        file=sys.stderr,
    )
    conn, extras = connect()
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f%z")

    new_class_report = []
    planned = []
    skipped = []
    unknown = []

    with conn:
        with conn.cursor() as cur:
            names, ids = existing_keys(cur)
            seen_this_csv = set()

            for row in attendees:
                csv_name = (row.get("Attendee name") or "").strip()
                raw_class = (row.get("Class of Boat") or "").strip()
                invoice = (row.get("Invoice reference") or "").strip()
                key = norm_name(csv_name)
                if key in seen_this_csv:
                    skipped.append((csv_name, raw_class, "duplicate in CSV", invoice))
                    continue
                seen_this_csv.add(key)

                orig, canonical, class_id, suffix = map_class(raw_class)
                match = SAILOR_MATCH.get(key)
                if key in ALREADY_ON_LIST or key in names or (match and match.get("sa_id") in ids):
                    skipped.append(
                        (csv_name, raw_class, f"already on list as {ALREADY_ON_LIST.get(key, csv_name)}", invoice)
                    )
                    continue
                if match is None:
                    unknown.append((csv_name, raw_class, invoice))
                    helm_name = csv_name
                    sa_id = None
                    sail = ""
                    club = ""
                    club_id = None
                    note = "no SAS match"
                else:
                    helm_name = match["helm_name"]
                    sa_id = match["sa_id"]
                    sail = match.get("sail") or ""
                    club = match.get("club") or ""
                    club_id = match.get("club_id")
                    note = match.get("note") or ""
                    if match.get("class_override"):
                        orig, canonical, class_id, suffix = match["class_override"]

                is_new_class = canonical not in PREVIOUS_2026_CLASSES
                needs_open = suffix == "open"
                planned.append(
                    {
                        "csv_name": csv_name,
                        "helm_name": helm_name,
                        "orig": orig,
                        "canonical": canonical,
                        "class_id": class_id,
                        "suffix": suffix,
                        "sa_id": sa_id,
                        "sail": sail,
                        "club": club,
                        "club_id": club_id,
                        "invoice": invoice,
                        "is_new_class": is_new_class,
                        "needs_open": needs_open,
                        "note": note,
                    }
                )
                if is_new_class:
                    new_class_report.append((canonical, orig, helm_name, needs_open))

            print("=== New classes vs previous 2026 list ===")
            print("Previous: Extra, ILCA 4.7 / ILCA 6 / ILCA 7, Optimist A / B, Sonnet")
            seen_new = {}
            for canonical, orig, helm, needs_open in new_class_report:
                seen_new.setdefault(canonical, {"orig": set(), "n": 0, "open": needs_open})
                seen_new[canonical]["orig"].add(orig)
                seen_new[canonical]["n"] += 1
            if not seen_new:
                print("None.")
            for canonical, info in sorted(seen_new.items()):
                flag = " → OPEN FLEET (not a Cape Classic class before)" if info["open"] else " → own fleet (standard Cape Classic class, first 2026 entries)"
                print(f"  {canonical} ({', '.join(sorted(info['orig']))}) x{info['n']}{flag}")

            print("\n=== Skip (already entered / CSV dup) ===")
            for item in skipped:
                print(f"  {item[0]} [{item[1]}] {item[2]} {item[3]}")

            print("\n=== Add ===")
            for p in planned:
                extra = f" | {p['note']}" if p["note"] else ""
                print(
                    f"  {p['helm_name']}  {p['canonical']}  sail={p['sail'] or '—'}  "
                    f"club={p['club'] or '—'}  sas={p['sa_id'] or '—'}  {p['invoice']}{extra}"
                )

            if unknown:
                print("\n=== Unmatched names ===")
                for item in unknown:
                    print(f"  {item}")

            if not args.apply:
                print("\nDry run. Pass --apply to write.", file=sys.stderr)
                return 0

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS results_bak_cape_classic_20260911 AS
                SELECT * FROM results WHERE FALSE
                """
            )
            cur.execute(
                """
                INSERT INTO results_bak_cape_classic_20260911
                SELECT * FROM results
                WHERE regatta_id = %s
                  AND NOT EXISTS (
                    SELECT 1 FROM results_bak_cape_classic_20260911 b
                    WHERE b.result_id = results.result_id
                  )
                """,
                (REGATTA_ID,),
            )

            # Generic CSV "ILCA" was previously dumped into ILCA 6.
            # Jens Dugas: age 15, 8× ILCA 4.7 vs 3× ILCA 6; last Cape Classic + WC Dinghy were 4.7 sail 14.
            # (May 2026 ILCA Nationals was ILCA 6 171060 — confirm if he is stepping up.)
            cur.execute(
                """
                UPDATE results
                SET class_canonical = 'Ilca 4.7',
                    class_id = 8,
                    sail_number = '14'
                WHERE regatta_id = %s
                  AND helm_sa_sailing_id = 13995
                  AND class_canonical ILIKE 'ilca%%'
                """,
                (REGATTA_ID,),
            )
            print(f"Corrected Jens Dugas ILCA → 4.7 ({cur.rowcount} row)", file=sys.stderr)

            # Existing Sonnets sit in :sonnet-fleet — fold them into Open with Fireball.
            ensure_block(cur, "open")
            open_bid = block_id_for("open")
            sonnet_bid = block_id_for("sonnet-fleet")
            cur.execute(
                """
                UPDATE results
                SET block_id = %s, fleet_label = 'Open'
                WHERE regatta_id = %s AND block_id = %s
                """,
                (open_bid, REGATTA_ID, sonnet_bid),
            )
            print(f"Moved {cur.rowcount} Sonnet row(s) into Open", file=sys.stderr)
            cur.execute(
                """
                DELETE FROM regatta_blocks
                WHERE block_id = %s
                  AND NOT EXISTS (SELECT 1 FROM results WHERE block_id = %s)
                """,
                (sonnet_bid, sonnet_bid),
            )

            for p in planned:
                ensure_block(
                    cur,
                    p["suffix"],
                    orig=p["orig"],
                    canonical=p["canonical"],
                    class_id=p["class_id"],
                    fleet_label=p["canonical"],
                )

            for p in planned:
                meta = BLOCKS.get(p["suffix"]) or {}
                bid = block_id_for(p["suffix"])
                race_scores = meta.get("race_scores") or RACE_SCORES_R5
                fleet_label = (meta.get("fleet_label") or p["canonical"] or "").strip() or None
                cur.execute(
                    """
                    INSERT INTO results (
                        regatta_id, block_id, rank,
                        fleet_label, class_original, class_canonical, class_id,
                        sail_number, club_raw, club_id,
                        helm_name, helm_sa_sailing_id,
                        races_sailed, discard_count, race_scores,
                        raced, result_status, as_at_time,
                        row_validation_status, manually_parsed, ranks_sailed
                    ) VALUES (
                        %s, %s, 0,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        0, 0, %s,
                        true, 'Provisional', %s,
                        'validated', false, 0
                    )
                    """,
                    (
                        REGATTA_ID,
                        bid,
                        fleet_label,
                        p["orig"],
                        p["canonical"],
                        p["class_id"],
                        p["sail"] or None,
                        p["club"] or None,
                        p["club_id"],
                        p["helm_name"],
                        p["sa_id"],
                        extras.Json(race_scores),
                        now,
                    ),
                )
            rerank_fleets(cur)

            cur.execute(
                """
                SELECT class_canonical, COUNT(*)
                FROM results
                WHERE regatta_id = %s
                GROUP BY 1
                ORDER BY 1
                """,
                (REGATTA_ID,),
            )
            print("\n=== Counts after apply ===")
            for canonical, n in cur.fetchall():
                print(f"  {canonical}: {n}")
            cur.execute(
                """
                SELECT block_id, class_canonical, entries_raced
                FROM regatta_blocks
                WHERE regatta_id = %s
                ORDER BY block_id
                """,
                (REGATTA_ID,),
            )
            print("\n=== Blocks ===")
            for bid, canonical, n in cur.fetchall():
                print(f"  {bid}  {canonical}  entries={n}")

            cur.execute(
                """
                SELECT class_canonical, helm_name, class_original, sail_number
                FROM results
                WHERE regatta_id = %s
                  AND (
                    class_canonical ILIKE 'ilca%%'
                    OR class_original ILIKE '%%laser%%'
                    OR class_original ILIKE '%%ilca%%'
                  )
                ORDER BY
                  CASE class_canonical
                    WHEN 'Ilca 4.7' THEN 1
                    WHEN 'Ilca 6' THEN 2
                    WHEN 'Ilca 7' THEN 3
                    ELSE 9
                  END,
                  helm_name
                """,
                (REGATTA_ID,),
            )
            ilca_rows = cur.fetchall()
            print("\n=== ILCA / Laser fleet ===")
            c = Counter(r[0] for r in ilca_rows)
            print(f"  Total: {len(ilca_rows)}")
            for k in ("Ilca 4.7", "Ilca 6", "Ilca 7"):
                print(f"  {k}: {c.get(k, 0)}")
            for canonical, helm, orig, sail in ilca_rows:
                print(f"    {canonical:8}  {helm:24}  csv={orig:12}  sail={sail or '—'}")

    print("Applied.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
