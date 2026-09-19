#!/usr/bin/env python3
"""Temp grey Hunter boat names for the 4 Midmar rows that had no name.

Only write a name when historical Hunter results have one. Do not invent.
442 has no Hunter history — leave blank.

Sources (Hunter 19 only, excluding this event):
  2013 Paul Changuion SAS 1218 → Essex Girl (3 Nationals; his only named 2013).
  741 Paige Smith → Bueno Vento (2023 + 2026 Nationals). Not Sheba: that name
      is already on Midmar 748, and 741 also raced as Sheba in 2024.
  40 Penny Macpherson → Odin's Eye (2021–23 Odins Eye + 2025 Odin's Eye).
      Scout is the other 2024 name; latest Nationals spelling used.
  442 Daniela Cantarelli → no Hunter boat_name anywhere. Skip.
"""
import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
FLAG = "boat_name_temp"

# result_id → temp name. Only empty boat_name rows.
TEMP = {
    21209: "Essex Girl",  # Paul 2013
    21212: "Bueno Vento",  # Paige 741
    21218: "Odin's Eye",  # Penny 40
}


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT result_id, helm_name, helm_sa_sailing_id, sail_number,
               boat_name, validation_flag, entry_id
        FROM results
        WHERE regatta_id=%s
        ORDER BY COALESCE(rank,99999), result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    print("===== BEFORE =====")
    for r in rows:
        empty = not (r["boat_name"] or "").strip()
        mark = "MISSING" if empty else "HAS"
        print(mark, dict(r))

    applied = []
    skipped = []
    for r in rows:
        rid = r["result_id"]
        current = (r["boat_name"] or "").strip()
        if rid in TEMP:
            if current:
                skipped.append((rid, r["helm_name"], "already", current))
                continue
            name = TEMP[rid]
            flag = r["validation_flag"]
            if flag and flag != FLAG:
                skipped.append((rid, r["helm_name"], "flag_kept", flag))
                cur.execute(
                    "UPDATE results SET boat_name=%s WHERE result_id=%s AND regatta_id=%s",
                    (name, rid, RID),
                )
            else:
                cur.execute(
                    """
                    UPDATE results
                    SET boat_name=%s, validation_flag=%s
                    WHERE result_id=%s AND regatta_id=%s
                    """,
                    (name, FLAG, rid, RID),
                )
            if r["entry_id"]:
                cur.execute(
                    """
                    UPDATE entries
                    SET boat_name=%s
                    WHERE entry_id=%s AND regatta_id=%s
                      AND (boat_name IS NULL OR TRIM(boat_name)='')
                    """,
                    (name, r["entry_id"], RID),
                )
            else:
                cur.execute(
                    """
                    UPDATE entries
                    SET boat_name=%s
                    WHERE regatta_id=%s
                      AND TRIM(sail_number::text)=%s
                      AND (boat_name IS NULL OR TRIM(boat_name)='')
                    """,
                    (name, RID, str(r["sail_number"] or "").strip()),
                )
            applied.append((rid, r["helm_name"], r["sail_number"], name))
        elif not current:
            skipped.append((rid, r["helm_name"], r["sail_number"], "no_history"))

    conn.commit()

    cur.execute(
        """
        SELECT result_id, helm_name, sail_number, boat_name, validation_flag
        FROM results
        WHERE regatta_id=%s
        ORDER BY COALESCE(rank,99999), result_id
        """,
        (RID,),
    )
    print("===== AFTER =====")
    for r in cur.fetchall():
        print(dict(r))
    print("APPLIED", applied)
    print("SKIPPED", skipped)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
