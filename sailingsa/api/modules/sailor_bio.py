"""
Clean bio engine. Single entry: build_sailor_bio_from_db(sas_id).
Fetches facts from DB, ranks results, cleans event titles, builds narrative from
sentence variant arrays (deterministic by sas_id). Returns 90–130 word bio.
Not connected to the API.
"""

import os
import random
import re


def _event_tier(event_name: str) -> int:
    """0=national, 1=regional, 2=major, 3=club. Lower = more important."""
    if not event_name:
        return 3
    e = (event_name or "").lower()
    if "national" in e or "nationals" in e:
        return 0
    if "championship" in e or "regional" in e or "provincial" in e:
        return 1
    if "classic" in e or "charter" in e or "open" in e:
        return 2
    return 3


def _clean_event_title(title, year):
    if not title:
        return ""

    t = title

    # remove result-type words
    remove_words = [
        "Results",
        "results",
        "Fleet Final",
        "Final Results",
        "Overall",
        "Overall Results",
        "SA SAILING",
        "S.A. Sailing"
    ]

    for w in remove_words:
        t = t.replace(w, "")

    # remove duplicated years
    if year:
        t = t.replace(f"({year})", "")
        t = t.replace(str(year), "")

    # remove month leftovers
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for m in months:
        t = t.replace(m, "")

    # clean spacing
    t = " ".join(t.split()).strip()

    # title case then restore acronyms
    t = t.title()
    t = t.replace("Ilca", "ILCA")
    t = t.replace("Hyc", "HYC")
    t = t.replace("Tsc", "TSC")
    t = t.replace("Sa ", "SA ")
    t = t.replace("Genmac", "GENMAC")

    # rebuild title with year in front
    if year:
        t = f"{year} {t}"

    return t


def _normalize_class_name(cls: str) -> str:
    """Normalize for display: Ilca/ilca -> ILCA; Optimist, 420, Hobie, 29er."""
    if not cls or not isinstance(cls, str):
        return cls or ""
    s = cls.strip()
    s = re.sub(r"\bIlca\b", "ILCA", s)
    s = re.sub(r"\bilca\b", "ILCA", s)
    lower = s.lower()
    if "optimist" in lower:
        s = re.sub(r"(?i)\boptimist\b", "Optimist", s)
    if "hobie" in lower:
        s = re.sub(r"(?i)\bhobie\b", "Hobie", s)
    return s


def _ordinal(n: int) -> str:
    if n % 100 in (11, 12, 13):
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _fetch_facts(cur, sas_id: str) -> dict:
    """Fetch sailor facts from DB. regatta_count, race_count, top 3 classes, top 3 results (tier+rank+year)."""
    sid = str(sas_id).strip()
    if not sid:
        return {"name": "", "club": None, "province": None, "first_year": None, "regatta_count": None, "race_count": None, "classes_sailed": [], "best_results": [], "wins": 0, "podiums": 0, "national_wins": 0}

    # Name
    cur.execute("SELECT COALESCE(full_name, first_name || ' ' || COALESCE(last_name,'')) AS name FROM sas_id_personal WHERE sa_sailing_id::text = %s LIMIT 1", (sid,))
    row = cur.fetchone()
    name = (row.get("name") or "").strip() if row else ""
    if not name:
        cur.execute("SELECT COALESCE(helm_name, crew_name) AS name FROM results WHERE helm_sa_sailing_id::text = %s OR crew_sa_sailing_id::text = %s LIMIT 1", (sid, sid))
        row = cur.fetchone()
        name = (row.get("name") or "").strip() if row else ""

    # Club
    cur.execute("""
        SELECT COALESCE(c.club_abbrev, c.club_fullname, r.club_raw) AS club_name, r.club_id
        FROM results r LEFT JOIN clubs c ON c.club_id = r.club_id
        WHERE r.helm_sa_sailing_id::text = %s OR r.crew_sa_sailing_id::text = %s
        GROUP BY COALESCE(c.club_abbrev, c.club_fullname, r.club_raw), r.club_id
        ORDER BY COUNT(*) DESC LIMIT 1
    """, (sid, sid))
    crow = cur.fetchone() or {}
    club = (crow.get("club_name") or "").strip() or None
    club_id = crow.get("club_id")

    # Province (if clubs has province/region)
    province = None
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='clubs' AND column_name IN ('province','region')
        ORDER BY CASE WHEN column_name='province' THEN 0 ELSE 1 END LIMIT 1
    """)
    prow = cur.fetchone()
    col = (prow.get("column_name") or "") if prow else ""
    if col and club_id:
        try:
            cur.execute(f"SELECT {col} FROM clubs WHERE club_id = %s LIMIT 1", (club_id,))
            r = cur.fetchone()
            province = (r.get(col) or "").strip() or None
        except Exception:
            pass

    # Race count = same as sailor profile page (https://sailingsa.co.za/sailor/{slug}): sum over each result row of
    # COALESCE(NULLIF(races_sailed,0), count of R1,R2,... in race_scores). Regatta count and first_year unchanged.
    cur.execute("""
        WITH sailor_rows AS (
            SELECT res.regatta_id,
                   COALESCE(NULLIF(res.races_sailed, 0), (SELECT COUNT(*) FROM jsonb_object_keys(COALESCE(res.race_scores, '{}'::jsonb)) k WHERE k ~ '^R[0-9]'))::int AS race_entries
            FROM results res
            WHERE res.helm_sa_sailing_id::text = %s OR res.crew_sa_sailing_id::text = %s
        )
        SELECT
            (SELECT COUNT(DISTINCT regatta_id)::int FROM sailor_rows) AS regatta_count,
            (SELECT COALESCE(SUM(race_entries), 0)::int FROM sailor_rows) AS race_count,
            (SELECT MIN(EXTRACT(YEAR FROM COALESCE(r.end_date, r.start_date)))::int FROM results res2 LEFT JOIN regattas r ON r.regatta_id = res2.regatta_id WHERE res2.helm_sa_sailing_id::text = %s OR res2.crew_sa_sailing_id::text = %s) AS first_year
    """, (sid, sid, sid, sid))
    row = cur.fetchone() or {}
    regatta_count = row.get("regatta_count")
    race_count = row.get("race_count")
    first_year = row.get("first_year")

    # Earliest regatta date (for career sentence month/year)
    cur.execute("""
        SELECT MIN(COALESCE(reg.start_date, reg.end_date)) AS first_regatta_date
        FROM results res
        LEFT JOIN regattas reg ON reg.regatta_id = res.regatta_id
        WHERE res.helm_sa_sailing_id::text = %s OR res.crew_sa_sailing_id::text = %s
    """, (sid, sid))
    first_regatta_row = cur.fetchone() or {}
    first_regatta_date = first_regatta_row.get("first_regatta_date")

    # Top 3 classes by race count
    cur.execute("""
        SELECT c.class_name, COUNT(*) AS cnt
        FROM results res
        JOIN classes c ON c.class_id = res.class_id AND c.class_name IS NOT NULL AND TRIM(c.class_name) != '' AND c.class_name <> 'Unknown'
        WHERE (res.helm_sa_sailing_id::text = %s OR res.crew_sa_sailing_id::text = %s) AND res.raced = TRUE
        GROUP BY c.class_name ORDER BY COUNT(*) DESC
    """, (sid, sid))
    classes_sailed = [_normalize_class_name((r.get("class_name") or "").strip()) for r in (cur.fetchall() or []) if (r.get("class_name") or "").strip()][:3]

    # Podium results; rank by event tier + rank + year desc; take top 3; clean event titles
    cur.execute("""
        SELECT res.rank::int AS rank, reg.event_name, cls.class_name,
               EXTRACT(YEAR FROM COALESCE(reg.end_date, reg.start_date))::int AS year
        FROM results res
        JOIN regattas reg ON reg.regatta_id = res.regatta_id
        LEFT JOIN classes cls ON cls.class_id = res.class_id
        WHERE (res.helm_sa_sailing_id::text = %s OR res.crew_sa_sailing_id::text = %s)
          AND res.raced = TRUE AND res.rank IS NOT NULL AND res.rank BETWEEN 1 AND 3
          AND reg.event_name IS NOT NULL AND TRIM(reg.event_name) != ''
          AND cls.class_name IS NOT NULL AND TRIM(cls.class_name) != '' AND cls.class_name <> 'Unknown'
        ORDER BY res.rank ASC, COALESCE(reg.end_date, reg.start_date) DESC NULLS LAST
    """, (sid, sid))
    rows = cur.fetchall() or []
    wins = sum(1 for r in rows if r.get("rank") == 1)
    podiums = len(rows)
    national_wins = sum(1 for r in rows if r.get("rank") == 1 and _event_tier(r.get("event_name") or "") == 0)

    best_results = []
    for r in rows:
        best_results.append({
            "event_name": _clean_event_title(r.get("event_name") or "", r.get("year")),
            "class_name": _normalize_class_name((r.get("class_name") or "").strip()),
            "year": r.get("year"),
            "rank": r.get("rank"),
            "_tier": _event_tier(r.get("event_name") or ""),
        })
    best_results.sort(key=lambda x: (x["_tier"], x["rank"], -(x["year"] or 0)))
    for x in best_results:
        del x["_tier"]
    best_results = best_results[:3]

    return {
        "name": name,
        "club": club,
        "province": province,
        "first_year": first_year,
        "first_regatta_date": first_regatta_date,
        "regatta_count": regatta_count,
        "race_count": race_count,
        "classes_sailed": classes_sailed,
        "best_results": best_results,
        "wins": wins,
        "podiums": podiums,
        "national_wins": national_wins,
    }


def _build_narrative(facts: dict, sas_id: str) -> str:
    """Variant-based builder. Sentence 1 = full name; all later = first_name. Deterministic seed."""
    full_name = (facts.get("name") or "").strip()
    first_name = full_name.split()[0] if full_name else ""
    club = (facts.get("club") or "").strip() or ""
    province = (facts.get("province") or "").strip() or "the region"
    first_year = facts.get("first_year")
    first_regatta_date = facts.get("first_regatta_date")
    regatta_count = facts.get("regatta_count") or 0
    race_count = facts.get("race_count") or 0
    top_classes = facts.get("classes_sailed") or []
    best_results = facts.get("best_results") or []
    national_wins = facts.get("national_wins") or 0
    podiums = facts.get("podiums") or 0
    wins = facts.get("wins") or 0
    if national_wins and national_wins > 0:
        level = "elite"
    elif (podiums and podiums > 0) or (wins and wins > 0):
        level = "competitive"
    else:
        level = "developing"

    random.seed(hash(str(sas_id)) % (2**32))

    identity_pool = [
        "{full_name} sails out of {club} in the {province}.",
        "Sailing from {club}, {full_name} competes in the {province} dinghy circuit.",
        "A {province} sailor, {full_name} represents {club} in competitive dinghy racing.",
        "{full_name} represents {club} and races in the {province} sailing circuit.",
    ]

    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    month = ""
    year = first_year or ""
    if first_regatta_date:
        if hasattr(first_regatta_date, "month") and hasattr(first_regatta_date, "year"):
            month = month_names[first_regatta_date.month - 1] if 1 <= first_regatta_date.month <= 12 else ""
            year = first_regatta_date.year
        elif isinstance(first_regatta_date, str) and len(first_regatta_date) >= 7:
            parts = first_regatta_date[:10].split("-")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                try:
                    month = month_names[int(parts[1]) - 1]
                    year = int(parts[0])
                except (IndexError, ValueError):
                    pass

    career_pool = [
        "{first_name}'s earliest SailingSA result dates to {month} {year}. Since then {race_count} races across {regatta_count} regattas have been recorded.",
        "{first_name}'s competitive record on SailingSA begins in {month} {year}. Since then {race_count} races across {regatta_count} regattas have been completed.",
        "Since {month} {year}, {race_count} races across {regatta_count} regattas have been recorded for {first_name}."
    ]

    class1 = _normalize_class_name(top_classes[0]) if top_classes else "various classes"
    class2 = " and ".join(_normalize_class_name(c) for c in top_classes[1:]) if len(top_classes) > 1 else "other fleets"

    class_pool = [
        "{first_name}'s primary class has been {class1}, with additional appearances in {class2}.",
        "{first_name} competes mainly in the {class1} fleet, alongside races in {class2}.",
        "Most of {first_name}'s racing has been in {class1}, with additional starts in {class2}."
    ]

    # Deduplicate by event name so we don't show the same event twice
    event_names = [(r.get("event_name") or "").strip() for r in best_results if (r.get("event_name") or "").strip()]
    unique_events = []
    for e in event_names:
        if e not in unique_events:
            unique_events.append(e)
    unique_events = unique_events[:2]
    # Build highlights (event_name, class_name) for first 2 unique events
    highlights = []
    for ev in unique_events:
        for r in best_results:
            if (r.get("event_name") or "").strip() == ev:
                highlights.append({"event_name": ev, "class_name": (r.get("class_name") or "").strip()})
                break

    r0 = highlights[0] if highlights else {}
    r1 = highlights[1] if len(highlights) > 1 else r0
    e1 = (r0.get("event_name") or "").strip()
    c1 = _normalize_class_name((r0.get("class_name") or "").strip())
    e2 = (r1.get("event_name") or "").strip()
    c2 = _normalize_class_name((r1.get("class_name") or "").strip()) if r1 else c1
    if not e1:
        e1 = "SailingSA events"
    if not c1:
        c1 = "multiple fleets"
    if not e2:
        e2 = e1
    if not c2:
        c2 = c1
    phrase1 = f"winning the {e1} in the {c1} fleet"
    phrase2 = f"the {e2} in the {c2} fleet"

    highlight_pool = [
        f"Highlights include {phrase1}, along with {phrase2}.",
        f"Notable results include victory at the {e1} in the {c1} fleet and strong finishes at the {e2}.",
        f"{first_name}'s best results include {phrase1}, as well as the {e2} in the {c2} fleet.",
        f"Key performances include {phrase1}, along with the {e2} in the {c2} fleet.",
    ]

    closing_pool = [
        "{first_name} continues to compete regularly across provincial and national sailing events.",
        "{first_name} remains an active competitor in the Western Cape sailing circuit.",
        "{first_name} continues to build experience across competitive sailing regattas.",
        "{first_name} remains active in regional dinghy racing."
    ]

    s1 = random.choice(identity_pool).format(full_name=full_name, club=club, province=province)
    s2 = random.choice(career_pool).format(first_name=first_name, month=month, year=year, race_count=race_count, regatta_count=regatta_count) if (month or year) and regatta_count is not None and race_count is not None else f"{first_name} has sailed {race_count} races across {regatta_count} regattas in the SailingSA archive."
    s3 = random.choice(class_pool).format(first_name=first_name, class1=class1, class2=class2)
    s4 = random.choice(highlight_pool)
    s5 = random.choice(closing_pool).format(first_name=first_name)

    bio = " ".join([s1, s2, s3, s4, s5])
    word_count = len(bio.split())
    if word_count > 130:
        bio = " ".join(bio.split()[:130])
    return bio


def build_sailor_bio_from_db(sas_id: str) -> str:
    """
    1. Fetch sailor facts from DB
    2. Compute regatta_count and race_count
    3. Top 3 classes by race count
    4. Rank top 3 results by event tier + rank + year
    5. Clean event titles
    6. Generate narrative using sentence variant arrays
    7. Choose variants deterministically with random.seed(hash(sas_id))
    8. Return 90–130 word bio
    """
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise ValueError("DB_URL not set.")

    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        facts = _fetch_facts(cur, str(sas_id))
        return _build_narrative(facts, str(sas_id))
    finally:
        cur.close()
        conn.close()


def _resolve_sas_id_from_name(cur, full_name: str) -> str:
    """Resolve full name to sas_id for test mode."""
    cur.execute("""
        SELECT sa_sailing_id::text AS sid FROM sas_id_personal
        WHERE lower(trim(coalesce(full_name, first_name || ' ' || coalesce(last_name,'')))) = lower(trim(%s))
        LIMIT 1
    """, (full_name,))
    row = cur.fetchone()
    if row and row.get("sid"):
        return row["sid"]
    cur.execute("""
        SELECT COALESCE(helm_sa_sailing_id::text, crew_sa_sailing_id::text) AS sid FROM results
        WHERE lower(trim(coalesce(helm_name,''))) = lower(trim(%s)) OR lower(trim(coalesce(crew_name,''))) = lower(trim(%s))
        LIMIT 1
    """, (full_name, full_name))
    row = cur.fetchone()
    return (row.get("sid") or "") if row else ""


if __name__ == "__main__":
    import psycopg2
    import psycopg2.extras

    if not os.getenv("DB_URL"):
        raise SystemExit("DB_URL not set; set DB_URL to run test mode.")

    print("\n--- Sailor Bio Engine (test mode: real DB) ---\n")
    conn = psycopg2.connect(os.getenv("DB_URL"))
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for full_name in ["Timothy Weaving", "Joshua Keytel", "Gordon Guthrie", "Birgitta Weaving"]:
            sas_id = _resolve_sas_id_from_name(cur, full_name)
            if not sas_id:
                print(f"\n{full_name}\n{'-' * len(full_name)}\n(No sas_id found.)")
                continue
            bio = build_sailor_bio_from_db(sas_id)
            print(f"\n{full_name}")
            print("-" * len(full_name))
            print(bio)
    finally:
        cur.close()
        conn.close()
