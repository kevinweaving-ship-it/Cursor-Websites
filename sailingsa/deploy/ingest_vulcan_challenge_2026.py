#!/usr/bin/env python3
"""Ingest VULCAN Challenge 2026 final results as ToT - Custom time scores.

Parent URL: /regatta/2026-09-13-vulcan-challenge
Child fleets: Hobie Fleet, Hunter 19 Fleet, Keelboat Fleet.
Scoring is time-on-time (ToT - Custom), not Appendix A / Low Point.
Never put the scoring system in fleet_label or block_label_raw — sailed line only.
"""
import json
import psycopg2

RID = "2026-09-13-vulcan-challenge"
AS_AT = "2026-09-14 19:40:10+02"
STATUS = "Provisional"

HOBIE = "2026-09-13-vulcan-challenge:01-hobie"
HUNTER = "2026-09-13-vulcan-challenge:02-hunter-19"
KEEL = "2026-09-13-vulcan-challenge:03-keelboats"

# rank, boat, sail, class, helm, crew, division, tot, start, finish, elapsed, corrected, delta, pts, code
HOBIE_ROWS = [
    (1, "Hobie 1", "90687", "Hobie 16", "Graham Offord", None, "H16", "0.8210", "11:46:00", "13:39:00", "01:53:00", "01:32:46", "00:00:00", 1.0, None),
    (2, "Orbree", "112487", "Hobie 16", "Robert Obree", None, "H16", "0.8210", "11:46:00", "13:47:02", "02:01:02", "01:39:22", "00:06:36", 2.0, None),
    (3, "Hobie 2", "91000", "Hobie 16", "Andrew Walker", None, "H16", "0.8210", "11:46:00", "14:02:29", "02:16:29", "01:52:03", "00:19:17", 3.0, None),
    (4, "Splitwise", "90107", "Hobie 16", "Paco Mendes", None, "H16", "0.8210", "11:46:00", "14:42:48", "02:56:48", "02:25:09", "00:52:23", 4.0, None),
]

HUNTER_ROWS = [
    (1, "Bleau", "263", "Hunter 19", "Paul Tomes", "Mary-Clare Tomes", "Non Spin", "0.9750", "11:56:00", "14:45:00", "02:49:00", "02:44:46", "00:00:00", 1.0, None),
    (2, "Take 3", "754", "Hunter 19", "Robert Dove", "Brian Langham", "Non Spin", "0.9750", "11:56:00", "14:45:15", "02:49:15", "02:45:01", "00:00:15", 2.0, None),
    (3, "Bad News", "256", "Hunter 19", "Martin Wesermann", "Andrew Mandy", "Non Spin", "0.9750", "11:56:00", "14:45:55", "02:49:55", "02:45:40", "00:00:54", 3.0, None),
    (4, "Charlie", "773", "Hunter 19", "Robert Fine", "Paul Pearce", "Spin", "1.0000", "11:56:00", "14:45:10", "02:49:10", "02:49:10", "00:04:24", 4.0, None),
    (5, "Sea Nile", "405", "Hunter 19", "Paul Moxley", "Mark Preen", "Spin", "1.0000", "11:56:00", "14:45:46", "02:49:46", "02:49:46", "00:05:00", 5.0, None),
    (6, "Solenta", "403", "Hunter 19", "Hayden Miller", "Timothy Weaving", "Non Spin", "0.9750", "11:56:00", "14:50:36", "02:54:36", "02:50:14", "00:05:28", 6.0, None),
    (7, "Artemis", "007", "Hunter 19", "Howard Donnelly", "Jendo Ocenasek", "Spin", "1.0000", "11:56:00", "14:48:01", "02:52:01", "02:52:01", "00:07:15", 7.0, None),
    (8, "Luca", "727", "Hunter 19", "Kris Jarzebowski", "Jamie Jarzebowski", "Non Spin", "0.9750", "11:56:00", "14:57:47", "03:01:47", "02:57:14", "00:12:28", 8.0, None),
    (9, "Buboo", "401", "Hunter 19", "Dion de Gruchy", "David Eccles", "Spin", "1.0000", "11:56:00", "14:57:52", "03:01:52", "03:01:52", "00:17:06", 9.0, None),
    (10, "Nemo", "145", "Hunter 19", "Andy Le May", "Lucy Jamieson", "Non Spin", "0.9750", "11:56:00", None, None, None, None, 11.0, "RET"),
]

KEEL_ROWS = [
    (1, "JML3", "SA600", "L26", "Scott Macfarlane", None, "Non Spin", "0.8955", "11:51:00", "14:45:18", "02:54:18", "02:36:05", "00:00:00", 1.0, None),
    (2, "Ocean Optimist", "SA3141", "Beneteau Class 35", "Greg Townes", None, "Spin", "1.0526", "11:51:00", "14:47:43", "02:56:43", "03:06:01", "00:29:56", 2.0, None),
    (3, "Catalyst", "SA2186", "Sadler 32", "Greg Francois", None, "Non Spin", "0.8275", "11:51:00", None, None, None, None, 4.0, "RET"),
]


def r1_score(pts, code):
    if code:
        return {"R1": f"{pts:.1f} {code}"}
    return {"R1": f"{pts:.1f}"}


def main():
    conn = psycopg2.connect("postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master")
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE public.regattas
        SET scoring_system = 'ToT - Custom',
            scoring_mode = 'pcs_timed',
            result_status = %s,
            as_at_time = %s,
            class_layout = 'multi'
        WHERE regatta_id = %s
        """,
        (STATUS, AS_AT, RID),
    )

    cur.execute("DELETE FROM public.results WHERE regatta_id = %s", (RID,))
    cur.execute("DELETE FROM public.regatta_blocks WHERE regatta_id = %s", (RID,))

    blocks = [
        (HOBIE, "Hobie 16", "Hobie 16", "Hobie Fleet", 4),
        (HUNTER, "Hunter 19", "Hunter 19", "Hunter 19 Fleet", 10),
        (KEEL, "Keelboat", "", "Keelboat Fleet", 3),
    ]
    for bid, c_orig, c_can, fleet, entries in blocks:
        cur.execute(
            """
            INSERT INTO public.regatta_blocks (
                block_id, regatta_id, class_original, class_canonical, fleet_label,
                races_sailed, discard_count, to_count, scoring_system, rating_system,
                block_label_raw, entries_raced
            ) VALUES (
                %s, %s, %s, %s, %s,
                1, 0, 1, 'ToT - Custom', 'ToT',
                %s, %s
            )
            """,
            (bid, RID, c_orig, c_can, fleet, fleet, entries),
        )

    def insert_rows(bid, fleet, rows):
        for rank, boat, sail, cls, helm, crew, _div, tot, start, finish, elapsed, corrected, delta, pts, code in rows:
            cur.execute(
                """
                INSERT INTO public.results (
                    regatta_id, block_id, fleet_label, class_original,
                    rank, boat_name, sail_number, helm_name, crew_name,
                    handicap, start_time, finish_time, duration_time, corrected_time, delta_time,
                    race_scores, total_points_raw, nett_points_raw,
                    races_sailed, discard_count, ranks_sailed, raced,
                    result_status, as_at_time, event_name, start_date, end_date,
                    manually_parsed
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s::jsonb, %s, %s,
                    1, 0, 1, %s,
                    %s, %s, '2026 VULCAN Challenge', '2026-09-13', '2026-09-13',
                    true
                )
                """,
                (
                    RID, bid, fleet, cls,
                    rank, boat, sail, helm, crew,
                    tot, start, finish, elapsed, corrected, delta,
                    json.dumps(r1_score(pts, code)), pts, pts,
                    False if code == "RET" else True,
                    STATUS, AS_AT,
                ),
            )

    insert_rows(HOBIE, "Hobie Fleet", HOBIE_ROWS)
    insert_rows(HUNTER, "Hunter 19 Fleet", HUNTER_ROWS)
    insert_rows(KEEL, "Keelboat Fleet", KEEL_ROWS)

    conn.commit()
    cur.close()
    conn.close()
    # SAS IDs: never leave PDF names unmatched. Same-dir matcher.
    import importlib.util
    from pathlib import Path

    match_path = Path(__file__).with_name("match_vulcan_sailors_sas.py")
    spec = importlib.util.spec_from_file_location("match_vulcan_sailors_sas", match_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()
    print("OK: ToT - Custom results loaded")


if __name__ == "__main__":
    main()
