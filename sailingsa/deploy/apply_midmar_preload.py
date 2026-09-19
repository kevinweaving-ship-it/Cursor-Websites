#!/usr/bin/env python3
"""Preload Midmar Cup Hunter 19 entries with checksummed SAS IDs.

Live-only. Does not invent SAS IDs or sail/bow/boat numbers.

Hunter 19 gold columns (from existing results, read-only):
  class, sail_number, boat_name, helm, crew.
bow_no / hull_no / jib_no are unused on H19. Do not add a Fleet column;
class sailed is Hunter 19.
"""
from __future__ import annotations

import sys

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"
CLASS_NAME = "Hunter 19"
CLASS_ID = 209

# User-supplied names + spelling variants. Exact user spelling is first.
PEOPLE = {
    "paul": {
        "label": "Paul Changioun",
        "role": "helm",
        "variants": [("Paul", "Changioun"), ("Paul", "Changuion")],
    },
    "craig": {
        "label": "Craig Millar",
        "role": "helm",
        "variants": [("Craig", "Millar"), ("Craig", "Miller")],
    },
    "tony": {
        "label": "Tony Cockerill",
        "role": "helm",
        "variants": [("Tony", "Cockerill"), ("Anthony", "Cockerill")],
    },
    "megan": {
        "label": "Megan Guald",
        "role": "helm",
        "variants": [("Megan", "Guald"), ("Megan", "Gauld"), ("Megan", "Gould")],
    },
    "bryan": {
        "label": "Bryan Paxman",
        "role": "helm",
        "variants": [("Bryan", "Paxman"), ("Brian", "Paxman")],
    },
    "nick": {
        "label": "Nick Sommerville",
        "role": "helm",
        "variants": [
            ("Nick", "Sommerville"),
            ("Nick", "Somerville"),
            ("Nicholas", "Sommerville"),
            ("Nicholas", "Somerville"),
        ],
    },
    "luke": {
        "label": "Luke Wagner",
        "role": "helm",
        "variants": [("Luke", "Wagner")],
    },
    "gust": {
        "label": "Gust Funke",
        "role": "helm",
        "variants": [("Gust", "Funke"), ("Gustav", "Funke")],
    },
    "hayden": {
        "label": "Hayden Miller",
        "role": "helm_crew_boat",
        "variants": [("Hayden", "Miller")],
    },
    "tim": {
        "label": "Tim Weaving",
        "role": "crew",
        "variants": [("Tim", "Weaving"), ("Timothy", "Weaving")],
    },
    "howard": {
        "label": "Howard Leoto",
        "role": "crew2",
        "variants": [("Howard", "Leoto")],
    },
}

HELM_KEYS = ["paul", "craig", "tony", "megan", "bryan", "nick", "luke", "gust"]
CREW_BOAT = {"helm": "hayden", "crew": "tim", "crew2": "howard"}
# Only values the user supplied. Do not invent the rest.
KNOWN_SAILS = {"hayden": "403"}
KNOWN_BOATS = {"hayden": "Puffin"}


def table_cols(cur, table: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
        (table,),
    )
    return {r[0] for r in cur.fetchall()}


def sas_name_cols(cols: set[str]) -> tuple[str, str, str, str | None]:
    id_col = "sa_sailing_id" if "sa_sailing_id" in cols else "sas_id"
    fn_col = "first_name" if "first_name" in cols else "firstname"
    ln_col = "last_name" if "last_name" in cols else "surname"
    full_col = "full_name" if "full_name" in cols else None
    return id_col, fn_col, ln_col, full_col


def lookup_person(cur, person: dict, id_col: str, fn_col: str, ln_col: str, full_col: str | None) -> dict:
    """Return unique SAS match or a failure reason. Never invent an ID."""
    found: dict[str, dict] = {}
    probes = []
    for fn, ln in person["variants"]:
        cur.execute(
            f"""
            SELECT {id_col}::text, {fn_col}, {ln_col}
                   {(", " + full_col) if full_col else ""}
            FROM sas_id_personal
            WHERE {fn_col} ILIKE %s AND {ln_col} ILIKE %s
            ORDER BY {id_col}
            """,
            (fn, ln),
        )
        rows = cur.fetchall()
        probes.append((f"{fn} {ln}", rows))
        for row in rows:
            sid = str(row[0]).strip()
            if sid:
                found[sid] = {
                    "sid": sid,
                    "first": row[1],
                    "last": row[2],
                    "full": row[3] if full_col and len(row) > 3 else f"{row[1]} {row[2]}",
                    "via": f"{fn} {ln}",
                }
    # Prefer the exact user-typed first+last if that variant is unique.
    exact_fn, exact_ln = person["variants"][0]
    exact_ids = {
        sid
        for sid, rec in found.items()
        if rec["via"].lower() == f"{exact_fn} {exact_ln}".lower()
    }
    if len(exact_ids) == 1:
        sid = next(iter(exact_ids))
        rec = found[sid]
        return {"ok": True, "sid": int(sid), "name": rec["full"], "via": rec["via"], "probes": probes}
    if len(found) == 1:
        rec = next(iter(found.values()))
        return {"ok": True, "sid": int(rec["sid"]), "name": rec["full"], "via": rec["via"], "probes": probes}
    if not found:
        return {"ok": False, "reason": "missing", "probes": probes}
    return {
        "ok": False,
        "reason": "ambiguous",
        "ids": found,
        "probes": probes,
    }


def club_for_sas(cur, sid: int) -> tuple[str | None, int | None]:
    cur.execute(
        """
        SELECT r.club_id, COALESCE(NULLIF(TRIM(c.club_abbrev), ''), NULLIF(TRIM(r.club_raw), ''))
        FROM results r
        LEFT JOIN clubs c ON c.club_id = r.club_id
        WHERE r.helm_sa_sailing_id = %s
          AND (r.club_id IS NOT NULL OR NULLIF(TRIM(r.club_raw), '') IS NOT NULL)
        ORDER BY r.result_id DESC
        LIMIT 1
        """,
        (sid,),
    )
    row = cur.fetchone()
    if row:
        return (row[1], row[0])
    return (None, None)


def apply() -> int:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    print("===== SCHEMA =====")
    result_cols = table_cols(cur, "results")
    entry_cols = table_cols(cur, "entries")
    sas_cols = table_cols(cur, "sas_id_personal")
    print("results", sorted(result_cols))
    print("entries", sorted(entry_cols))
    print("has bow_no", "bow_no" in result_cols)
    print("has hull_no", "hull_no" in result_cols)
    print("has boat_number", "boat_number" in result_cols)
    print("has crew2", "crew2_name" in result_cols)
    print("has fleet_label", "fleet_label" in result_cols)

    id_col, fn_col, ln_col, full_col = sas_name_cols(sas_cols)
    print("sas id/fn/ln/full", id_col, fn_col, ln_col, full_col)

    cur.execute(
        "SELECT regatta_id, event_name, fleet_classes, result_status FROM regattas WHERE regatta_id=%s",
        (RID,),
    )
    print("regatta", cur.fetchone())
    cur.execute(
        "SELECT block_id, class_canonical, class_id, fleet_label FROM regatta_blocks WHERE regatta_id=%s",
        (RID,),
    )
    print("blocks", cur.fetchall())

    print("\n===== SAS CHECKSUM =====")
    resolved = {}
    failed = {}
    for key, person in PEOPLE.items():
        rec = lookup_person(cur, person, id_col, fn_col, ln_col, full_col)
        if rec["ok"]:
            resolved[key] = rec
            print(f"OK {person['label']}: SAS {rec['sid']} name={rec['name']!r} via={rec['via']}")
        else:
            failed[key] = rec
            print(f"FAIL {person['label']}: {rec['reason']} probes={rec['probes']}")

    if failed:
        print("\nREFUSING to invent SAS IDs for:", ", ".join(PEOPLE[k]["label"] for k in failed))

    # Unique-ID collision check across the accepted set.
    sid_owners: dict[int, list[str]] = {}
    for key, rec in resolved.items():
        sid_owners.setdefault(rec["sid"], []).append(key)
    collisions = {sid: keys for sid, keys in sid_owners.items() if len(keys) > 1}
    if collisions:
        print("COLLISION same SAS ID mapped to multiple people:", collisions)
        for keys in collisions.values():
            for key in keys:
                failed[key] = {"ok": False, "reason": "collision"}
                resolved.pop(key, None)

    boats = []
    for key in HELM_KEYS:
        rec = resolved.get(key)
        if not rec:
            print(f"SKIP boat helm={PEOPLE[key]['label']} (no unique SAS ID)")
            continue
        club_raw, club_id = club_for_sas(cur, rec["sid"])
        boats.append(
            {
                "helm_name": rec["name"],
                "helm_sid": rec["sid"],
                "crew_name": None,
                "crew_sid": None,
                "crew2_name": None,
                "crew2_sid": None,
                "club_raw": club_raw,
                "club_id": club_id,
                "sail_number": KNOWN_SAILS.get(key),
                "boat_name": KNOWN_BOATS.get(key),
            }
        )

    helm = resolved.get(CREW_BOAT["helm"])
    crew = resolved.get(CREW_BOAT["crew"])
    crew2 = resolved.get(CREW_BOAT["crew2"])
    if helm and crew and crew2:
        club_raw, club_id = club_for_sas(cur, helm["sid"])
        boats.append(
            {
                "helm_name": helm["name"],
                "helm_sid": helm["sid"],
                "crew_name": f"{crew['name']}, {crew2['name']}",
                "crew_sid": crew["sid"],
                "crew2_name": crew2["name"],
                "crew2_sid": crew2["sid"],
                "club_raw": club_raw,
                "club_id": club_id,
                "sail_number": KNOWN_SAILS.get("hayden"),
                "boat_name": KNOWN_BOATS.get("hayden"),
            }
        )
    else:
        missing = [
            PEOPLE[CREW_BOAT[role]]["label"]
            for role, rec in (("helm", helm), ("crew", crew), ("crew2", crew2))
            if not rec
        ]
        print("SKIP 3-up boat; missing unique SAS:", ", ".join(missing))

    if not boats:
        print("NO_BOATS")
        cur.close()
        conn.close()
        return 1

    # Match other H19 blocks: class = Hunter 19, fleet_label left unset (no Fleet column).
    cur.execute(
        """
        UPDATE regatta_blocks
        SET class_original = %s,
            class_canonical = %s,
            class_id = %s,
            fleet_label = NULL,
            entries_raced = %s
        WHERE block_id = %s
        """,
        (CLASS_NAME, CLASS_NAME, CLASS_ID, len(boats), BLOCK),
    )
    print("BLOCK_UPDATE", cur.rowcount)

    cur.execute("SELECT result_id, helm_name, helm_sa_sailing_id FROM results WHERE regatta_id=%s", (RID,))
    existing = cur.fetchall()
    print("EXISTING_RESULTS", existing)

    has_boat_name = "boat_name" in result_cols
    has_crew2 = "crew2_name" in result_cols and "crew2_sa_sailing_id" in result_cols
    has_class_id = "class_id" in result_cols
    has_raced = "raced" in result_cols
    has_result_status = "result_status" in result_cols

    inserted = 0
    updated = 0
    for boat in boats:
        cur.execute(
            """
            SELECT result_id FROM results
            WHERE regatta_id = %s AND helm_sa_sailing_id = %s
            ORDER BY result_id
            LIMIT 1
            """,
            (RID, boat["helm_sid"]),
        )
        row = cur.fetchone()
        sets = {
            "block_id": BLOCK,
            "class_original": CLASS_NAME,
            "class_canonical": CLASS_NAME,
            "helm_name": boat["helm_name"],
            "helm_sa_sailing_id": boat["helm_sid"],
            "crew_name": boat["crew_name"],
            "crew_sa_sailing_id": boat["crew_sid"],
            "sail_number": boat.get("sail_number"),
            "club_raw": boat["club_raw"],
            "club_id": boat["club_id"],
            "races_sailed": 0,
            "discard_count": 0,
            "race_scores": psycopg2.extras.Json({}),
        }
        # Internal class sailed only — do not add a Fleet column.
        if "fleet_label" in result_cols:
            sets["fleet_label"] = CLASS_NAME
        if has_class_id:
            sets["class_id"] = CLASS_ID
        if has_boat_name:
            sets["boat_name"] = boat.get("boat_name")
        if has_crew2:
            sets["crew2_name"] = boat["crew2_name"]
            sets["crew2_sa_sailing_id"] = boat["crew2_sid"]
        if has_raced:
            sets["raced"] = True
        if has_result_status:
            sets["result_status"] = "Provisional"

        if row:
            result_id = row[0]
            # Do not blank sail / boat name if a later pass already filled them.
            for col in ("sail_number", "boat_name"):
                if col in sets and sets[col] is None:
                    sets.pop(col)
            assignments = []
            vals = []
            for col, val in sets.items():
                assignments.append(f"{col} = %s")
                vals.append(val)
            vals.append(result_id)
            cur.execute(
                f"UPDATE results SET {', '.join(assignments)} WHERE result_id = %s",
                vals,
            )
            updated += 1
            print(f"UPDATE result_id={result_id} helm={boat['helm_name']} sas={boat['helm_sid']}")
        else:
            cols = ["regatta_id"] + list(sets.keys())
            vals = [RID] + list(sets.values())
            placeholders = ", ".join(["%s"] * len(vals))
            cur.execute(
                f"INSERT INTO results ({', '.join(cols)}) VALUES ({placeholders})",
                vals,
            )
            inserted += 1
            print(f"INSERT helm={boat['helm_name']} sas={boat['helm_sid']} crew={boat['crew_name']}")

        if "regatta_id" in entry_cols and "helm_sas_id" in entry_cols:
            cur.execute(
                "SELECT entry_id FROM entries WHERE regatta_id=%s AND helm_sas_id=%s LIMIT 1",
                (RID, str(boat["helm_sid"])),
            )
            existing_entry = cur.fetchone()
            if existing_entry:
                eupd = []
                evals = []
                if boat.get("sail_number") and "sail_number" in entry_cols:
                    eupd.append("sail_number=%s")
                    evals.append(boat["sail_number"])
                if boat.get("boat_name") and "boat_name" in entry_cols:
                    eupd.append("boat_name=%s")
                    evals.append(boat["boat_name"])
                if eupd:
                    evals.append(existing_entry[0])
                    cur.execute(
                        f"UPDATE entries SET {', '.join(eupd)} WHERE entry_id=%s",
                        evals,
                    )
            elif not existing_entry:
                ecols = ["regatta_id", "block_id", "helm_sas_id"]
                evals = [RID, BLOCK, str(boat["helm_sid"])]
                if "crew_sas_id" in entry_cols and boat["crew_sid"]:
                    ecols.append("crew_sas_id")
                    evals.append(str(boat["crew_sid"]))
                if "club_code" in entry_cols and boat["club_raw"]:
                    ecols.append("club_code")
                    evals.append(boat["club_raw"])
                if "sail_number" in entry_cols:
                    ecols.append("sail_number")
                    evals.append(boat.get("sail_number"))
                if "boat_name" in entry_cols:
                    ecols.append("boat_name")
                    evals.append(boat.get("boat_name"))
                if "verified" in entry_cols:
                    ecols.append("verified")
                    evals.append(True)
                cur.execute(
                    f"INSERT INTO entries ({', '.join(ecols)}) VALUES ({', '.join(['%s'] * len(evals))})",
                    evals,
                )

    dump_cols = [
        c
        for c in (
            "result_id",
            "helm_name",
            "helm_sa_sailing_id",
            "crew_name",
            "crew_sa_sailing_id",
            "crew2_name",
            "crew2_sa_sailing_id",
            "class_canonical",
            "fleet_label",
            "sail_number",
            "boat_name",
            "bow_no",
            "hull_no",
            "boat_number",
        )
        if c in result_cols
    ]
    cur.execute(
        f"SELECT {', '.join(dump_cols)} FROM results WHERE regatta_id = %s ORDER BY result_id",
        (RID,),
    )
    print("\n===== PRELOAD ROWS =====")
    for r in cur.fetchall():
        print(r)
    print(f"INSERTED={inserted} UPDATED={updated} BOATS={len(boats)} FAILED={list(failed)}")

    conn.commit()
    cur.close()
    conn.close()
    return 0 if boats and not failed else (0 if boats else 1)


if __name__ == "__main__":
    sys.exit(apply())
