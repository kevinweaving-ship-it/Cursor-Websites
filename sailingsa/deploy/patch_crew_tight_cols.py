#!/usr/bin/env python3
"""Surgical live api.py: class sheet loads crew2/crew3; shrink wasted column width."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def _sub(text: str, old: str, new: str, expect: int, label: str) -> str:
    n = text.count(old)
    if n != expect:
        raise SystemExit(f"FAIL {label}: expected {expect} got {n}")
    return text.replace(old, new)


def main() -> None:
    text = API.read_text(encoding="utf-8")
    if "# SHEET_CREW2_TIGHT" in text:
        print("already patched")
        return

    text = _sub(
        text,
        "                       res.rank, res.sail_number, res.helm_name, res.crew_name,\n"
        "                       res.boat_name, res.jib_no, res.bow_no, res.hull_no,\n"
        "                       res.hull_colour,\n"
        "                       res.club_raw,\n",
        "                       res.rank, res.sail_number, res.helm_name, res.crew_name,\n"
        "                       res.crew2_name, res.crew3_name,\n"
        "                       res.boat_name, res.jib_no, res.bow_no, res.hull_no,\n"
        "                       res.hull_colour,\n"
        "                       res.club_raw,\n",
        1,
        "class SELECT names",
    )
    text = _sub(
        text,
        "                       res.helm_sa_sailing_id, res.crew_sa_sailing_id,\n"
        "                       res.total_points_raw, res.nett_points_raw, res.race_scores, res.raced,\n"
        "                       res.start_time, res.finish_time, res.duration_time, res.corrected_time, res.delta_time,\n",
        "                       res.helm_sa_sailing_id, res.crew_sa_sailing_id,\n"
        "                       res.crew2_sa_sailing_id, res.crew3_sa_sailing_id,\n"
        "                       res.total_points_raw, res.nett_points_raw, res.race_scores, res.raced,\n"
        "                       res.start_time, res.finish_time, res.duration_time, res.corrected_time, res.delta_time,\n",
        1,
        "class SELECT sas ids",
    )
    text = _sub(
        text,
        "            sas_ids = set()\n"
        "            for r in raw:\n"
        "                h, c = r.get(\"helm_sa_sailing_id\"), r.get(\"crew_sa_sailing_id\")\n"
        "                if h is not None and str(h).strip().isdigit():\n"
        "                    sas_ids.add(str(h).strip())\n"
        "                if c is not None and str(c).strip().isdigit():\n"
        "                    sas_ids.add(str(c).strip())\n",
        "            sas_ids = set()\n"
        "            for r in raw:\n"
        "                for _sidk in (\"helm_sa_sailing_id\", \"crew_sa_sailing_id\",\n"
        "                              \"crew2_sa_sailing_id\", \"crew3_sa_sailing_id\"):\n"
        "                    _sidv = r.get(_sidk)\n"
        "                    if _sidv is not None and str(_sidv).strip().isdigit():\n"
        "                        sas_ids.add(str(_sidv).strip())\n",
        1,
        "class sas_ids loop",
    )

    slug_insert = (
        "        crew2_name = r.get(\"crew2_name\")\n"
        "        crew2_sas_id = str(r.get(\"crew2_sa_sailing_id\") or \"\") if r.get(\"crew2_sa_sailing_id\") is not None else \"\"\n"
        "        crew2_slug = slug_map.get(crew2_sas_id) if (crew2_sas_id and crew2_sas_id.isdigit()) else None\n"
        "        crew3_name = r.get(\"crew3_name\")\n"
        "        crew3_sas_id = str(r.get(\"crew3_sa_sailing_id\") or \"\") if r.get(\"crew3_sa_sailing_id\") is not None else \"\"\n"
        "        crew3_slug = slug_map.get(crew3_sas_id) if (crew3_sas_id and crew3_sas_id.isdigit()) else None\n"
    )
    dict_extra = (
        "            \"crew2_name\": crew2_name,\n"
        "            \"crew2_slug\": crew2_slug,\n"
        "            \"crew2_sa_sailing_id\": r.get(\"crew2_sa_sailing_id\"),\n"
        "            \"crew3_name\": crew3_name,\n"
        "            \"crew3_slug\": crew3_slug,\n"
        "            \"crew3_sa_sailing_id\": r.get(\"crew3_sa_sailing_id\"),\n"
    )
    text = _sub(
        text,
        "        if not crew_slug and _result_row_identity_pending_crew(r):\n"
        "            crew_slug = _identity_pending_name_slug(crew_name)\n"
        "        by_block[bid][\"rows\"].append({\n"
        "            \"result_id\": r.get(\"result_id\"),\n"
        "            \"rank\": r.get(\"rank\"),\n"
        "            \"sail_number\": r.get(\"sail_number\"),\n"
        "            \"helm_name\": helm_name,\n"
        "            \"helm_slug\": helm_slug,\n"
        "            \"helm_sa_sailing_id\": r.get(\"helm_sa_sailing_id\"),\n"
        "            \"helm_profile_from_name_only\": bool(helm_slug and r.get(\"helm_sa_sailing_id\") is None),\n"
        "            \"crew_name\": crew_name,\n"
        "            \"crew_slug\": crew_slug,\n"
        "            \"crew_sa_sailing_id\": r.get(\"crew_sa_sailing_id\"),\n"
        "            \"crew_profile_from_name_only\": bool(crew_slug and r.get(\"crew_sa_sailing_id\") is None),\n"
        "            \"crew_list\": crew_by_result.get(r.get(\"result_id\"), []),\n",
        "        if not crew_slug and _result_row_identity_pending_crew(r):\n"
        "            crew_slug = _identity_pending_name_slug(crew_name)\n"
        + slug_insert
        + "        by_block[bid][\"rows\"].append({\n"
        "            \"result_id\": r.get(\"result_id\"),\n"
        "            \"rank\": r.get(\"rank\"),\n"
        "            \"sail_number\": r.get(\"sail_number\"),\n"
        "            \"helm_name\": helm_name,\n"
        "            \"helm_slug\": helm_slug,\n"
        "            \"helm_sa_sailing_id\": r.get(\"helm_sa_sailing_id\"),\n"
        "            \"helm_profile_from_name_only\": bool(helm_slug and r.get(\"helm_sa_sailing_id\") is None),\n"
        "            \"crew_name\": crew_name,\n"
        "            \"crew_slug\": crew_slug,\n"
        "            \"crew_sa_sailing_id\": r.get(\"crew_sa_sailing_id\"),\n"
        "            \"crew_profile_from_name_only\": bool(crew_slug and r.get(\"crew_sa_sailing_id\") is None),\n"
        + dict_extra
        + "            \"crew_list\": crew_by_result.get(r.get(\"result_id\"), []),\n",
        1,
        "class row dict",
    )

    text = _sub(
        text,
        "        if (row.get(\"crew_name\") or \"\").strip():\n"
        "            return True\n",
        "        if any((row.get(k) or \"\").strip() for k in (\"crew_name\", \"crew2_name\", \"crew3_name\")):\n"
        "            return True\n",
        1,
        "_row_has_crew",
    )
    text = _sub(
        text,
        "th,td{border:1px solid #1d294d;padding:8px;text-align:center;line-height:1.35;overflow:visible}",
        "th,td{border:1px solid #1d294d;padding:6px 4px;text-align:center;line-height:1.35;overflow:visible;white-space:nowrap;width:1%;vertical-align:middle}",
        1,
        "td padding",
    )
    text = _sub(
        text,
        ".fleet-section .table-wrapper table.fleet-results-table th.wc-meta-col,.fleet-section .table-wrapper table.fleet-results-table td.wc-meta-col{width:max-content;max-width:12rem}",
        ".fleet-section .table-wrapper table.fleet-results-table th.wc-meta-col,.fleet-section .table-wrapper table.fleet-results-table td.wc-meta-col{width:1%;max-width:none;white-space:nowrap}",
        1,
        "wc-meta width",
    )
    text = _sub(
        text,
        ".fleet-section .table-wrapper table.fleet-results-table .class-col,.fleet-section .table-wrapper table.fleet-results-table .club-col,.fleet-section .table-wrapper table.fleet-results-table .sail-col{white-space:nowrap}",
        ".fleet-section .table-wrapper table.fleet-results-table .class-col,.fleet-section .table-wrapper table.fleet-results-table .club-col,.fleet-section .table-wrapper table.fleet-results-table .sail-col{width:1%;white-space:nowrap}",
        1,
        "club/sail width",
    )

    needle = "def _get_regatta_class_page_data"
    i = text.find(needle)
    if i < 0:
        raise SystemExit("FAIL class page fn missing")
    text = text[:i] + "# SHEET_CREW2_TIGHT\n" + text[i:]
    API.write_text(text, encoding="utf-8")
    print("patched", API, "bytes", len(text))


if __name__ == "__main__":
    main()
