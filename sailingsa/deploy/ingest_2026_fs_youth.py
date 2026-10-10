#!/usr/bin/env python3
"""Parse 2026 FS Youth PDF, checksum scores, stamp SAS ID table names.

Does not change gold api.py. Never invents SAS IDs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # apply-from-json on live does not need pypdf
    PdfReader = None

RID = "2026-10-04-free-state-youth-provincial-champs"
EVENT_NAME = "2026-10-04 Free State Youth Provincial Champ"
SOURCE_URL = "https://www.sailing.org.za/file/6zubxvnhzmmmzy7p"
HOST_CLUB_ID = 85
HOST_CLUB_CODE = "LDYC"
HOST_CLUB_NAME = "Lake Deneys Yacht Club"
PROVINCE = "Free State"
START = "2026-10-03"
END = "2026-10-04"
AS_AT = "2026-10-04 17:30:00+02"
RESULT_STATUS = "Final"
LEFT_LOGO = "/artwork/Event Logo/Free-State-Youth-Provincial-Champs-2025.png?v=20261010fs26"
OPT_A_LOGO = "/artwork/Class Logo/Optimist-A-Class-Logo.png"
OPT_B_LOGO = "/artwork/Class Logo/Optimist-B-Class-Logo.png"
DAB_LOGO = "/artwork/Class Logo/Dabchick-Class-Logo.png"

# SAS ID table is name truth. None = review queue.
SAILORS = {
    "taylor milln": (20848, "Taylor Milln", "LDYC", 85),
    "luan bester": (20832, "Luan Bester", None, None),
    "matthew peake": (29339, "Matthew Peake", None, None),
    "james tanner": (17526, "James Tanner", None, None),
    "falken marschall": (23954, "Falken Marschall", None, None),
    "caroline peak": (29338, "Caroline Peake", None, None),
    "caroline peake": (29338, "Caroline Peake", None, None),
    "kayden gibbons": (20780, "Kayden Gibbons", None, None),
    "maximilian malan": (12878, "Maximilian Malan", None, None),
    "ethan biagio": (13961, "Ethan Biagio", None, None),
    "david smith": (27289, "David Smith", None, None),
    "angus poppmeier": (18076, "Angus Poppmeier", None, None),
    "megan stegen": (22702, "Megan Stegen", None, None),
    "matthew mcqueen": (22130, "Matthew McQueen", None, None),
    "wianro bester": (18628, "Wianro Bester", None, None),
    "mika malan": (12879, "Mika Malan", None, None),
    "michael mcqueen": (27561, "Michael McQueen", None, None),
    "reese mcculloch": (24737, "Reese McCulloch", "LDYC", 85),
    "sebastian marschall": (23953, "Sebastian Marschall", None, None),
    "anthony latsky": (24676, "Anthony Latsky", None, None),
    "riley doel": (22231, "Riley Doel", None, None),
    "ivan doncaster-tatnall": (29175, "Ivan Doncaster-Tatnall", None, None),
    "erin gibbons": (20779, "Erin Gibbons", None, None),
    "danny coetzer": (None, "Danny Coetzer", None, None),
    "ryan van der merwe": (None, "Ryan Van Der Merwe", None, None),
    "david riley": (None, "David Riley", None, None),
    "amelia henriques": (None, "Amelia Henriques", None, None),
}

CLUBS = {
    "ldyc": ("LDYC", 85),
    "vlc": ("VLC", 68),
    "dac": ("DAC", 52),
    "syc": ("SYC", 65),
    "byc": ("BYC", 86),
    "psc": ("PSC", 1),
}

FLEETS = [
    {
        "key": "optimist",
        "pdf_header": "Optimist",
        "class_original": "Optimist",
        "class_canonical": "Optimist A",
        "class_id": 62,
        "block_slug": "optimist-a",
        "fleet_label": "Optimist A",
        "entries": 7,
    },
    {
        "key": "dabchick",
        "pdf_header": "Dabchick",
        "class_original": "Dabchick",
        "class_canonical": "Dabchick",
        "class_id": 5,
        "block_slug": "dabchick",
        "fleet_label": "Dabchick",
        "entries": 13,
    },
    {
        "key": "optimist-b",
        "pdf_header": "Optimist B",
        "class_original": "Optimist B",
        "class_canonical": "Optimist B",
        "class_id": 63,
        "block_slug": "optimist-b",
        "fleet_label": "Optimist B",
        "entries": 6,
    },
]


def first_club(raw: str | None):
    if not raw:
        return None, None
    token = re.split(r"[\\s/]+", raw.strip())[0]
    return CLUBS.get(token.lower(), (token.upper(), None))


def norm_name(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip().lower())
    s = s.replace("van der merwe", "van der merwe")
    return s


def parse_num(tok: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)", tok)
    if not m:
        raise ValueError(f"no number in {tok!r}")
    return float(m.group(1))


def is_pen(tok: str) -> str | None:
    u = tok.upper()
    for code in ("DNC", "DNF", "DNS", "RET", "DSQ", "OCS"):
        if re.search(rf"\b{code}\b", u):
            return code
    return None


def format_score(val: float, code: str | None, discarded: bool) -> str:
    text = f"{val:.1f}" if code is None else f"{val:.1f} {code}"
    return f"({text})" if discarded else text


def assign_penalties(tokens: list[tuple[str, bool]], total: float, nett: float, default_pen: float):
    """Fill bare DNC/DNF so published total/nett checksum.

    DNC stays entries+1. Discard value is total-nett. DNF/RET take leftover.
    """
    disc_idx = [i for i, (_t, d) in enumerate(tokens) if d]
    if len(disc_idx) != 1:
        raise ValueError(f"need exactly one discard, got {disc_idx} in {tokens}")
    d_i = disc_idx[0]
    need_disc = total - nett

    values = [0.0] * 7
    flex = []
    for i, (tok, _d) in enumerate(tokens):
        code = is_pen(tok)
        if code is None or re.match(r"^\d", tok.strip()):
            values[i] = parse_num(tok)
        elif code == "DNC":
            values[i] = default_pen
        else:
            values[i] = default_pen
            if i != d_i:
                flex.append(i)
    values[d_i] = need_disc
    leftover = total - sum(values)
    if abs(leftover) > 0.01:
        if not flex:
            raise ValueError(f"cannot fit leftover {leftover} {tokens}")
        values[flex[0]] += leftover
    if abs(sum(values) - total) > 0.01:
        raise ValueError(f"total checksum fail {sum(values)} != {total} {tokens} {values}")
    if abs(total - values[d_i] - nett) > 0.01:
        raise ValueError(f"nett checksum fail disc={values[d_i]} total={total} nett={nett}")
    for v in values:
        if abs(v * 10 - round(v * 10)) > 0.01:
            raise ValueError(f"non .0 score {values} from {tokens}")

    out = {}
    for i, (tok, discarded) in enumerate(tokens):
        out[f"R{i+1}"] = format_score(values[i], is_pen(tok), discarded)
    return out


def split_fleets(text: str) -> dict[str, str]:
    # Optimist B header last so remaining Optimist is A-fleet only.
    parts = re.split(r"\n(?=Optimist B\n)", text, maxsplit=1)
    head, opt_b = (parts[0], parts[1]) if len(parts) == 2 else (text, "")
    parts = re.split(r"\n(?=Dabchick\n)", head, maxsplit=1)
    opt, dab = (parts[0], parts[1]) if len(parts) == 2 else (head, "")
    return {"optimist": opt, "dabchick": dab, "optimist-b": opt_b}


def extract_rows(section: str, entries: int) -> list[dict]:
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in section.splitlines()]
    rows = []
    for ln in lines:
        m = re.match(r"^(\d+)(?:st|nd|rd|th)\s+(.*)$", ln, re.I)
        if not m:
            continue
        rank = int(m.group(1))
        rest = m.group(2).strip()
        if rank == 6 and rest.startswith("1385 ") and "Caroline" in rest:
            # Sheet dropped club: sail stays, name is helm, scores shift right.
            rest = re.sub(r"^1385\s+Caroline\s+Peak\s+", "1385  Caroline Peak ", rest, count=1)
        rows.append({"rank": rank, "rest": rest})
    if len(rows) != entries:
        raise ValueError(f"expected {entries} rows, got {len(rows)}: {rows}")
    return rows


def parse_row(rest: str, rank: int) -> dict:
    toks = rest.split()
    if not toks:
        raise ValueError("empty row")
    sail = re.sub(r"^RSA", "", toks[0], flags=re.I)
    # scores start at first token that is number, (number, or penalty
    start = None
    for i, t in enumerate(toks[1:], start=1):
        if re.match(r"^\(?\d", t) or is_pen(t):
            start = i
            break
    if start is None:
        raise ValueError(f"no scores in {rest!r}")
    mid = toks[1:start]
    score_toks = toks[start:]
    joined = []
    i = 0
    while i < len(score_toks):
        if score_toks[i] == "(" and i + 1 < len(score_toks):
            joined.append("(" + score_toks[i + 1])
            i += 2
            continue
        joined.append(score_toks[i])
        i += 1
    score_toks = joined
    # last two numeric are total / nett
    if len(score_toks) < 3:
        raise ValueError(f"short scores {rest!r}")
    total = parse_num(score_toks[-2])
    nett = parse_num(score_toks[-1])
    race_raw = score_toks[:-2]
    # Amelia extra trailing DNC
    if rank == 6 and "Henriques" in rest and len(race_raw) == 8:
        race_raw = race_raw[:7]
    if len(race_raw) != 7:
        raise ValueError(f"need 7 races, got {race_raw} from {rest!r}")

    club_raw = None
    name_parts = mid
    if mid:
        first = mid[0]
        # first club code only when it looks like a club, not a person name
        if first.lower() in CLUBS or "/" in first:
            club_raw = first
            name_parts = mid[1:]
            # drop leftover club fragments like "AC" after VLC/AC
            while name_parts and (name_parts[0].lower() in {"ac", "/", "ldyc"} or name_parts[0] == "/"):
                name_parts = name_parts[1:]
    pdf_name = " ".join(name_parts).strip()
    return {
        "sail": sail,
        "club_raw": club_raw,
        "pdf_name": pdf_name,
        "race_raw": race_raw,
        "total": total,
        "nett": nett,
    }


def race_tokens(race_raw: list[str]) -> list[tuple[str, bool]]:
    out = []
    pending_open = False
    for t in race_raw:
        discarded = t.startswith("(") or pending_open
        if t.startswith("(") and not t.endswith(")"):
            pending_open = True
        if t.endswith(")"):
            pending_open = False
        clean = t.strip("()")
        # PDF had "( DNF)"
        clean = clean.strip()
        out.append((clean, discarded))
    if len(out) != 7:
        raise ValueError(f"tokenised {out}")
    return out


def build_entries(pdf_path: Path) -> list[dict]:
    text = PdfReader(str(pdf_path)).pages[0].extract_text() or ""
    sections = split_fleets(text)
    out = []
    for fleet in FLEETS:
        sec = sections[fleet["key"]]
        for raw in extract_rows(sec, fleet["entries"]):
            parsed = parse_row(raw["rest"], raw["rank"])
            key = norm_name(parsed["pdf_name"])
            if key not in SAILORS:
                raise ValueError(f"unmapped sailor {parsed['pdf_name']!r} ({key})")
            sas_id, helm_name, hist_club, hist_club_id = SAILORS[key]
            club, club_id = first_club(parsed["club_raw"])
            if not club:
                club, club_id = hist_club, hist_club_id
            tokens = race_tokens(parsed["race_raw"])
            default_pen = float(fleet["entries"] + 1)
            scores = assign_penalties(tokens, parsed["total"], parsed["nett"], default_pen)
            out.append(
                {
                    **fleet,
                    "rank": raw["rank"],
                    "sail": parsed["sail"],
                    "club": club,
                    "club_id": club_id,
                    "pdf_name": parsed["pdf_name"],
                    "helm_name": helm_name,
                    "sas_id": sas_id,
                    "scores": scores,
                    "total": parsed["total"],
                    "nett": parsed["nett"],
                }
            )
    return out


def print_report(rows: list[dict]) -> None:
    print(f"rows={len(rows)} checksum=OK")
    for r in rows:
        sid = r["sas_id"] if r["sas_id"] is not None else "NULL"
        print(
            f"{r['class_canonical']:11} {r['rank']:2} {r['sail']:8} {r['club'] or '-':4} "
            f"{r['helm_name']!s:24} sas={sid}  {r['nett']}/{r['total']}  {r['scores']}"
        )


def apply_live(rows: list[dict]) -> None:
    import psycopg2

    db = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
    conn = psycopg2.connect(db)
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO public.regattas (
          regatta_id, event_name, year, regatta_type,
          host_club_id, host_club_code, host_club_name, province_name,
          start_date, end_date, result_status, as_at_time,
          import_status, result_type, class_layout, event_scope,
          source_url, local_file_path, provenance_status, updated_at
        ) VALUES (
          %s, %s, 2026, 'PROVINCIAL',
          %s, %s, %s, %s,
          %s, %s, %s, %s,
          'manual', 'UNKNOWN', 'multi_class', 'PROVINCIAL',
          %s, %s, 'manual_sas_pdf', NOW()
        )
        ON CONFLICT (regatta_id) DO UPDATE SET
          event_name = EXCLUDED.event_name,
          start_date = EXCLUDED.start_date,
          end_date = EXCLUDED.end_date,
          result_status = EXCLUDED.result_status,
          as_at_time = EXCLUDED.as_at_time,
          host_club_id = EXCLUDED.host_club_id,
          host_club_code = EXCLUDED.host_club_code,
          source_url = EXCLUDED.source_url,
          updated_at = NOW()
        """,
        (
            RID,
            EVENT_NAME,
            HOST_CLUB_ID,
            HOST_CLUB_CODE,
            HOST_CLUB_NAME,
            PROVINCE,
            START,
            END,
            RESULT_STATUS,
            AS_AT,
            SOURCE_URL,
            "results/2026-10-04-free-state-youth-provincial-champs/6zubxvnhzmmmzy7p.pdf",
        ),
    )
    for fleet in FLEETS:
        bid = f"{RID}:{fleet['block_slug']}"
        cur.execute(
            """
            INSERT INTO public.regatta_blocks (
              block_id, regatta_id, class_original, class_canonical, class_id,
              fleet_label, races_sailed, discard_count, to_count,
              scoring_system, block_label_raw, entries_raced
            ) VALUES (
              %s, %s, %s, %s, %s,
              %s, 7, 1, 6,
              'Appendix A', %s, %s
            )
            ON CONFLICT (block_id) DO UPDATE SET
              class_canonical = EXCLUDED.class_canonical,
              class_id = EXCLUDED.class_id,
              fleet_label = EXCLUDED.fleet_label,
              races_sailed = 7,
              discard_count = 1,
              to_count = 6,
              entries_raced = EXCLUDED.entries_raced
            """,
            (
                bid,
                RID,
                fleet["class_original"],
                fleet["class_canonical"],
                fleet["class_id"],
                fleet["fleet_label"],
                fleet["class_canonical"],
                fleet["entries"],
            ),
        )
    cur.execute("DELETE FROM public.results WHERE regatta_id = %s", (RID,))
    for r in rows:
        bid = f"{RID}:{r['block_slug']}"
        cur.execute(
            """
            INSERT INTO public.results (
              regatta_id, block_id, rank, fleet_label,
              class_original, class_canonical, class_id,
              sail_number, club_raw, club_id,
              helm_name, helm_sa_sailing_id,
              races_sailed, discard_count, race_scores,
              total_points_raw, nett_points_raw,
              event_name, start_date, end_date,
              host_club_name, province_name,
              result_status, as_at_time, manually_parsed
            ) VALUES (
              %s, %s, %s, %s,
              %s, %s, %s,
              %s, %s, %s,
              %s, %s,
              7, 1, %s::jsonb,
              %s, %s,
              %s, %s, %s,
              %s, %s,
              %s, %s, TRUE
            )
            """,
            (
                RID,
                bid,
                r["rank"],
                r["fleet_label"],
                r["class_original"],
                r["class_canonical"],
                r["class_id"],
                r["sail"],
                r["club"],
                r["club_id"],
                r["helm_name"],
                r["sas_id"],
                json.dumps(r["scores"]),
                r["total"],
                r["nett"],
                EVENT_NAME,
                START,
                END,
                HOST_CLUB_NAME,
                PROVINCE,
                RESULT_STATUS,
                "2026-10-04 17:30",
            ),
        )
    conn.commit()
    cur.close()
    conn.close()
    _write_header_icons()
    _restore_event_logo()


def _write_header_icons() -> None:
    # Gold default: left = prior-year event logo; host mark comes from
    # /api/club-logo/{host} via host_club_id. Never put raw Club Logo PNG in right.
    entry = {
        "left": LEFT_LOGO,
        "fleet_logos": {
            "optimist-a": OPT_A_LOGO,
            "dabchick": DAB_LOGO,
            "optimist-b": OPT_B_LOGO,
        },
    }
    paths = [
        Path("/var/www/sailingsa/data/wc_regatta_header_icons.json"),
        Path("/var/www/sailingsa/static/data/wc_regatta_header_icons.json"),
        Path("/var/www/sailingsa/wc_regatta_header_icons.json"),
    ]
    for p in paths:
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        data[RID] = entry
        p.write_text(json.dumps(data, indent=2) + "\n")
        print("header_icons", p)


def _restore_event_logo() -> None:
    name = "Free-State-Youth-Provincial-Champs-2025.png"
    bundle = Path(__file__).resolve().parent / name
    src = bundle if bundle.exists() else Path("/var/www/sailingsa/api/artwork/Event Logo") / name
    if not src.exists():
        return
    data = src.read_bytes()
    for dest in (
        Path("/var/www/sailingsa/artwork/Event Logo") / name,
        Path("/var/www/sailingsa/api/artwork/Event Logo") / name,
    ):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        print("event_logo", dest)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    write_json = Path("/tmp/fs-youth-2026/parsed.json")
    json_in = Path(args[0]) if args and args[0].endswith(".json") else None
    pdf = Path(args[0]) if args and not str(args[0]).endswith(".json") else Path("/tmp/fs-youth-2026/2026-FS_Youth.pdf")
    if json_in and json_in.exists():
        rows = json.loads(json_in.read_text())
    else:
        rows = build_entries(pdf)
        write_json.parent.mkdir(parents=True, exist_ok=True)
        write_json.write_text(json.dumps(rows, indent=2) + "\n")
        print("wrote", write_json)
    print_report(rows)
    unmatched = [r for r in rows if r["sas_id"] is None]
    print(f"unmatched_review_queue={len(unmatched)} {[r['helm_name'] for r in unmatched]}")
    if apply:
        apply_live(rows)
        print("APPLIED", RID)


if __name__ == "__main__":
    main()
