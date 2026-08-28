#!/usr/bin/env python3
"""Keelboat result columns when boats have names. Does not replace whole api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

MARKER = "keelboat = bool(show_boat)"

OLD_HEAD = '''    show_boat = _optional_col_visible("boat_name", has_boat_name)
    show_jib = _optional_col_visible("jib", has_jib_no)
    show_bow = _optional_col_visible("bow", has_bow_no)
    show_hull = _optional_col_visible("hull", has_hull_no)
    show_crew_col = _optional_col_visible("crew", has_crew)
    show_races = bool(race_columns)

    thead = ""
    if _pref_on("rank"):
        thead += '<th class="rank-col">Rank</th>'
    if _pref_on("fleet"):
        thead += "<th>Fleet</th>"
    if _pref_on("class"):
        thead += "<th>Class</th>"
    if _pref_on("sail_no"):
        thead += '<th class="sail-col">Sail No</th>'
    if show_boat:
        thead += "<th>Boat Name</th>"
    if show_jib:
        thead += "<th>Jib No</th>"
    if show_bow:
        thead += "<th>Bow No</th>"
    if show_hull:
        thead += "<th>Hull No</th>"
    if _pref_on("club"):
        thead += '<th class="club-col">Club</th>'
    if _pref_on("helm"):
        thead += '<th class="helm-col">Helm</th>'
    if show_crew_col:
        thead += "<th>Crew</th>"
    if show_races:
        for rc in race_columns:
            thead += f"<th>{html_module.escape(rc)}</th>"
    if _pref_on("total"):
        thead += "<th>Total</th>"
    if _pref_on("nett"):
        thead += '<th class="nett-col">Nett</th>'
'''

NEW_HEAD = '''    show_boat = _optional_col_visible("boat_name", has_boat_name)
    show_jib = _optional_col_visible("jib", has_jib_no)
    show_bow = _optional_col_visible("bow", has_bow_no)
    show_hull = _optional_col_visible("hull", has_hull_no)
    show_crew_col = _optional_col_visible("crew", has_crew)
    show_races = bool(race_columns)
    # Keelboat (boats have names): Rank, Bow, Boat name, Club, Nett, last race → R1, Sail no, Helm, Crew
    keelboat = bool(show_boat)
    if keelboat and race_columns:
        race_columns = list(reversed(race_columns))

    if keelboat:
        ordered = []
        if _pref_on("rank"):
            ordered.append("rank")
        if show_bow:
            ordered.append("bow")
        if show_boat:
            ordered.append("boat")
        if _pref_on("club"):
            ordered.append("club")
        if _pref_on("nett"):
            ordered.append("nett")
        if show_races:
            ordered.append("races")
        if _pref_on("sail_no"):
            ordered.append("sail")
        if _pref_on("helm"):
            ordered.append("helm")
        if show_crew_col:
            ordered.append("crew")
    else:
        ordered = []
        if _pref_on("rank"):
            ordered.append("rank")
        if _pref_on("fleet"):
            ordered.append("fleet")
        if _pref_on("class"):
            ordered.append("class")
        if _pref_on("sail_no"):
            ordered.append("sail")
        if show_boat:
            ordered.append("boat")
        if show_jib:
            ordered.append("jib")
        if show_bow:
            ordered.append("bow")
        if show_hull:
            ordered.append("hull")
        if _pref_on("club"):
            ordered.append("club")
        if _pref_on("helm"):
            ordered.append("helm")
        if show_crew_col:
            ordered.append("crew")
        if show_races:
            ordered.append("races")
        if _pref_on("total"):
            ordered.append("total")
        if _pref_on("nett"):
            ordered.append("nett")

    thead = ""
    for col in ordered:
        if col == "rank":
            thead += '<th class="rank-col">Rank</th>'
        elif col == "fleet":
            thead += "<th>Fleet</th>"
        elif col == "class":
            thead += "<th>Class</th>"
        elif col == "sail":
            thead += '<th class="sail-col">Sail No</th>'
        elif col == "boat":
            thead += "<th>Boat Name</th>"
        elif col == "jib":
            thead += "<th>Jib No</th>"
        elif col == "bow":
            thead += "<th>Bow</th>" if keelboat else "<th>Bow No</th>"
        elif col == "hull":
            thead += "<th>Hull No</th>"
        elif col == "club":
            thead += '<th class="club-col">Club</th>'
        elif col == "helm":
            thead += '<th class="helm-col">Helm</th>'
        elif col == "crew":
            thead += "<th>Crew</th>"
        elif col == "races":
            for rc in race_columns:
                thead += f"<th>{html_module.escape(rc)}</th>"
        elif col == "total":
            thead += "<th>Total</th>"
        elif col == "nett":
            thead += '<th class="nett-col">Nett</th>'
'''

OLD_ROW = '''        row_html = f'<tr class="{row_classes}">'
        if _pref_on("rank"):
            row_html += f'<td class="rank-col">{_wc_cell(html_module.escape(rank_str), rank_plain, "rank", None, 8)}</td>'
        if _pref_on("fleet"):
            row_html += f"<td>{fleet_str}</td>"
        if _pref_on("class"):
            row_html += f"<td>{_wc_cell(class_str, class_name_raw, 'class_name', None, 64, 'class', class_xin)}</td>"
        if _pref_on("sail_no"):
            row_html += f'<td class="sail-col">{_wc_cell(sail_str, sail_raw, "sail_number", None, 32)}</td>'
        if show_boat:
            bn = str(r.get("boat_name") or "")
            row_html += f'<td>{_wc_cell(html_module.escape(bn), bn, "boat_name", None, 120)}</td>'
        if show_jib:
            jv = str(r.get("jib_no") or "")
            row_html += f'<td>{_wc_cell(html_module.escape(jv), jv, "jib_no", None, 32)}</td>'
        if show_bow:
            bv = str(r.get("bow_no") or "")
            row_html += f'<td>{_wc_cell(html_module.escape(bv), bv, "bow_no", None, 32)}</td>'
        if show_hull:
            hv = str(r.get("hull_no") or "")
            row_html += f'<td>{_wc_cell(html_module.escape(hv), hv, "hull_no", None, 32)}</td>'
        if _pref_on("club"):
            row_html += f'<td class="club-col">{_wc_cell(club_link_html, club_raw, "club_code", None, 32, "club", club_xin)}</td>'
        if _pref_on("helm"):
            row_html += f'<td class="helm-col">{_wc_cell(helm_str, helm_raw or "", "helm_name", None, 120, "helm", helm_xin)}</td>'
        if show_crew_col:
            row_html += f"<td>{_wc_cell(crew_str, crew_raw_for_edit, 'crew_name', None, 160, 'crew', crew_xin)}</td>"
        if show_races:
            for rkey in race_columns:
                score = (race_scores.get(rkey) or "").strip()
                is_discarded = score.startswith("(") and score.endswith(")")
                has_penalty = bool(re.search(r"\\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\\b", score, re.I)) if score else False
                cell_class = "code" if has_penalty else ("disc" if is_discarded else ("score-counts" if score else ""))
                row_html += f'<td class="{cell_class}">{_wc_cell(html_module.escape(score), score, None, rkey, 48)}</td>'
        if _pref_on("total"):
            row_html += f'<td class="{strike_class}">{_wc_cell(total_str, total_plain, "total_points_raw", None, 24)}</td>'
        if _pref_on("nett"):
            row_html += f'<td class="nett-col {strike_class}">{_wc_cell(nett_str, nett_plain, "nett_points_raw", None, 24)}</td>'
        row_html += "</tr>"
'''

NEW_ROW = '''        row_html = f'<tr class="{row_classes}">'
        for col in ordered:
            if col == "rank":
                row_html += f'<td class="rank-col">{_wc_cell(html_module.escape(rank_str), rank_plain, "rank", None, 8)}</td>'
            elif col == "fleet":
                row_html += f"<td>{fleet_str}</td>"
            elif col == "class":
                row_html += f"<td>{_wc_cell(class_str, class_name_raw, 'class_name', None, 64, 'class', class_xin)}</td>"
            elif col == "sail":
                row_html += f'<td class="sail-col">{_wc_cell(sail_str, sail_raw, "sail_number", None, 32)}</td>'
            elif col == "boat":
                bn = str(r.get("boat_name") or "")
                row_html += f'<td>{_wc_cell(html_module.escape(bn), bn, "boat_name", None, 120)}</td>'
            elif col == "jib":
                jv = str(r.get("jib_no") or "")
                row_html += f'<td>{_wc_cell(html_module.escape(jv), jv, "jib_no", None, 32)}</td>'
            elif col == "bow":
                bv = str(r.get("bow_no") or "")
                row_html += f'<td>{_wc_cell(html_module.escape(bv), bv, "bow_no", None, 32)}</td>'
            elif col == "hull":
                hv = str(r.get("hull_no") or "")
                row_html += f'<td>{_wc_cell(html_module.escape(hv), hv, "hull_no", None, 32)}</td>'
            elif col == "club":
                row_html += f'<td class="club-col">{_wc_cell(club_link_html, club_raw, "club_code", None, 32, "club", club_xin)}</td>'
            elif col == "helm":
                row_html += f'<td class="helm-col">{_wc_cell(helm_str, helm_raw or "", "helm_name", None, 120, "helm", helm_xin)}</td>'
            elif col == "crew":
                row_html += f"<td>{_wc_cell(crew_str, crew_raw_for_edit, 'crew_name', None, 160, 'crew', crew_xin)}</td>"
            elif col == "races":
                for rkey in race_columns:
                    score = (race_scores.get(rkey) or "").strip()
                    is_discarded = score.startswith("(") and score.endswith(")")
                    has_penalty = bool(re.search(r"\\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\\b", score, re.I)) if score else False
                    cell_class = "code" if has_penalty else ("disc" if is_discarded else ("score-counts" if score else ""))
                    row_html += f'<td class="{cell_class}">{_wc_cell(html_module.escape(score), score, None, rkey, 48)}</td>'
            elif col == "total":
                row_html += f'<td class="{strike_class}">{_wc_cell(total_str, total_plain, "total_points_raw", None, 24)}</td>'
            elif col == "nett":
                row_html += f'<td class="nett-col {strike_class}">{_wc_cell(nett_str, nett_plain, "nett_points_raw", None, 24)}</td>'
        row_html += "</tr>"
'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("keelboat columns already patched")
        return 0
    if OLD_HEAD not in text:
        print("ERROR: thead block not found on live api.py")
        return 1
    if OLD_ROW not in text:
        print("ERROR: row block not found on live api.py")
        return 1
    text = text.replace(OLD_HEAD, NEW_HEAD, 1)
    text = text.replace(OLD_ROW, NEW_ROW, 1)
    if MARKER not in text:
        print("ERROR: patch did not apply")
        return 1
    API.write_text(text, encoding="utf-8")
    print("patched keelboat column order")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
