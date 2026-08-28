#!/usr/bin/env python3
"""Keelboat result columns when boats have names. Surgical live api.py patch only."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "keelboat = bool(show_boat)"

INSERT_SHOW_RACES = (
    "    show_races = bool(race_columns)\n"
    "\n"
    "    # Windsurfer / custom race headers:"
)
INSERT_SHOW_RACES_NEW = (
    "    show_races = bool(race_columns)\n"
    "    # Keelboat (boats have names): Rank, Bow, Boat name, Club, Nett, last race → R1, Sail no, Helm, Crew\n"
    "    keelboat = bool(show_boat)\n"
    "    if keelboat and race_columns:\n"
    "        race_columns = list(reversed(race_columns))\n"
    "\n"
    "    # Windsurfer / custom race headers:"
)

THEAD_TAIL = (
    "    if _pref_on(\"nett\"):\n"
    "        thead += '<th class=\"nett-col\">Nett</th>'\n"
    "\n"
    "    late_part = \"\""
)
THEAD_TAIL_NEW = r'''    if _pref_on("nett"):
        thead += '<th class="nett-col">Nett</th>'
    if keelboat:
        # Rebuild header: Rank / Bow / Boat name / Club / Nett / Rn…R1 / Sail no / Helm / Crew
        _ths = []
        _i = 0
        while True:
            _s = thead.find("<th", _i)
            if _s < 0:
                break
            _e = thead.find("</th>", _s)
            if _e < 0:
                break
            _ths.append(thead[_s:_e + 5])
            _i = _e + 5
        _by = {}
        _races = []
        for _th in _ths:
            _low = _th.lower()
            if 'class="rank-col"' in _th:
                _by["rank"] = _th
            elif "boat name" in _low:
                _by["boat"] = _th
            elif 'class="club-col"' in _th:
                _by["club"] = _th
            elif 'class="nett-col"' in _th:
                _by["nett"] = _th
            elif 'class="sail-col"' in _th:
                _by["sail"] = _th
            elif 'class="helm-col"' in _th:
                _by["helm"] = _th
            elif 'class="crew-col"' in _th:
                _by["crew"] = _th
            elif 'class="race-col"' in _th:
                _races.append(_th)
            elif ">bow" in _low:
                _by["bow"] = _th.replace("Bow No", "Bow")
        thead = "".join(_by[k] for k in ("rank", "bow", "boat", "club", "nett") if k in _by)
        thead += "".join(_races)
        thead += "".join(_by[k] for k in ("sail", "helm", "crew") if k in _by)

    late_part = ""'''

ROW_START = '        row_html = f\'<tr class="{row_classes}"{_tr_extra}>\''
ROW_END = '        row_html += "</tr>"'

JOIN_ROW = '''        _kb_order = ("rank", "bow", "boat", "club", "nett", "races", "sail", "helm", "crew")
        _dg_order = (
            "rank", "fleet", "class", "bow", "sail", "nat", "boat", "jib", "hull",
            "club", "category", "gender", "helm", "crew", "races", "pcs", "total", "disc", "nett",
        )
        for _k in (_kb_order if keelboat else _dg_order):
            row_html += _cells.get(_k, "")
        row_html += "</tr>"'''


def _patch_row_block(block: str) -> str:
    """Convert sequential row_html += cells into named _cells then join in order."""
    if "_cells = {}" in block:
        return block
    block = block.replace(
        ROW_START,
        ROW_START + "\n        _cells = {}",
        1,
    )
    # Rank (three assignments) — unique by following snippet
    block = block.replace(
        """            if wc_sa_fleet_edit and is_wc_fleet_sheet and result_id_row is not None:
                row_html += (
                    f'<td class="rank-col rank-col--with-del">'
                    f"{_del_btn}"
                    f'<button type="button" class="wc-rank-menu-hit wc-rank-menu-hit--active" '""",
        """            if wc_sa_fleet_edit and is_wc_fleet_sheet and result_id_row is not None:
                _cells["rank"] = (
                    f'<td class="rank-col rank-col--with-del">'
                    f"{_del_btn}"
                    f'<button type="button" class="wc-rank-menu-hit wc-rank-menu-hit--active" '""",
        1,
    )
    block = block.replace(
        """            elif sa_fleet_ops and result_id_row is not None:
                row_html += (
                    f'<td class="rank-col rank-col--with-del">'
                    f"{_del_btn}"
                    f"{html_module.escape(rank_str)}"
                    f"</td>"
                )
            else:
                row_html += f'<td class="rank-col">{html_module.escape(rank_str)}</td>'""",
        """            elif sa_fleet_ops and result_id_row is not None:
                _cells["rank"] = (
                    f'<td class="rank-col rank-col--with-del">'
                    f"{_del_btn}"
                    f"{html_module.escape(rank_str)}"
                    f"</td>"
                )
            else:
                _cells["rank"] = f'<td class="rank-col">{html_module.escape(rank_str)}</td>'""",
        1,
    )
    pairs = [
        (
            '            row_html += f\'<td class="fleet-col">{fleet_str}</td>\'',
            '            _cells["fleet"] = f\'<td class="fleet-col">{fleet_str}</td>\'',
        ),
        (
            """                row_html += (
                    f'<td class="class-col">'
                    f'<div class="wc-class-col-sa">'""",
            """                _cells["class"] = (
                    f'<td class="class-col">'
                    f'<div class="wc-class-col-sa">'""",
        ),
        (
            '                row_html += f\'<td class="class-col">{class_cell}</td>\'',
            '                _cells["class"] = f\'<td class="class-col">{class_cell}</td>\'',
        ),
        (
            '            row_html += f\'<td class="wc-meta-col">{_wc_cell(bow_disp, bv, "bow_no", None, 32)}</td>\'',
            '            _cells["bow"] = f\'<td class="wc-meta-col">{_wc_cell(bow_disp, bv, "bow_no", None, 32)}</td>\'',
        ),
        (
            '            row_html += f\'<td class="sail-col">{_wc_cell(sail_link_html, sail_raw, "sail_number", None, 32)}</td>\'',
            '            _cells["sail"] = f\'<td class="sail-col">{_wc_cell(sail_link_html, sail_raw, "sail_number", None, 32)}</td>\'',
        ),
        (
            '            row_html += f\'<td class="nat-col">{_nationality_flag_cell_html(r.get("nationality"))}</td>\'',
            '            _cells["nat"] = f\'<td class="nat-col">{_nationality_flag_cell_html(r.get("nationality"))}</td>\'',
        ),
        (
            '            row_html += f\'<td class="wc-meta-col">{_wc_cell(bn_html, bn_edit, "boat_name", None, 120)}</td>\'',
            '            _cells["boat"] = f\'<td class="wc-meta-col">{_wc_cell(bn_html, bn_edit, "boat_name", None, 120)}</td>\'',
        ),
        (
            '            row_html += f\'<td class="wc-meta-col">{_wc_cell(html_module.escape(jv), jv, "jib_no", None, 32)}</td>\'',
            '            _cells["jib"] = f\'<td class="wc-meta-col">{_wc_cell(html_module.escape(jv), jv, "jib_no", None, 32)}</td>\'',
        ),
        (
            '            row_html += f\'<td class="wc-meta-col">{_wc_cell(html_module.escape(hv), hv, "hull_no", None, 32)}</td>\'',
            '            _cells["hull"] = f\'<td class="wc-meta-col">{_wc_cell(html_module.escape(hv), hv, "hull_no", None, 32)}</td>\'',
        ),
        (
            '            row_html += f\'<td class="club-col">{_wc_cell(club_disp, club_raw, "club_code", None, 32, "club", club_xin)}</td>\'',
            '            _cells["club"] = f\'<td class="club-col">{_wc_cell(club_disp, club_raw, "club_code", None, 32, "club", club_xin)}</td>\'',
        ),
        (
            '            row_html += f\'<td class="wc-meta-col">{age_html}</td>\'',
            '            _cells["category"] = f\'<td class="wc-meta-col">{age_html}</td>\'',
        ),
        (
            '            row_html += f\'<td class="wc-meta-col">{html_module.escape(gv)}</td>\'',
            '            _cells["gender"] = f\'<td class="wc-meta-col">{html_module.escape(gv)}</td>\'',
        ),
        (
            '            row_html += f\'<td class="helm-col">{_wc_cell(helm_str, helm_raw or "", "helm_name", None, 120, "helm", helm_xin)}</td>\'',
            '            _cells["helm"] = f\'<td class="helm-col">{_wc_cell(helm_str, helm_raw or "", "helm_name", None, 120, "helm", helm_xin)}</td>\'',
        ),
        (
            '            row_html += f\'<td class="crew-col">{_wc_cell(crew_str, crew_raw_for_edit, "crew_name", None, 160, "crew", crew_xin)}</td>\'',
            '            _cells["crew"] = f\'<td class="crew-col">{_wc_cell(crew_str, crew_raw_for_edit, "crew_name", None, 160, "crew", crew_xin)}</td>\'',
        ),
        (
            '                    row_html += f\'<td class="{rc_cls}" data-race-key="{_rk_attr}">{_wc_cell(inner, score, None, rkey, 48)}</td>\'',
            '                    _cells["races"] = _cells.get("races", "") + f\'<td class="{rc_cls}" data-race-key="{_rk_attr}">{_wc_cell(inner, score, None, rkey, 48)}</td>\'',
        ),
        (
            '                    row_html += f\'<td class="{rc_cls}" data-race-key="{_rk_attr}"{_style}>{_inner}</td>\'',
            '                    _cells["races"] = _cells.get("races", "") + f\'<td class="{rc_cls}" data-race-key="{_rk_attr}"{_style}>{_inner}</td>\'',
        ),
        (
            '                row_html += f\'<td class="wc-meta-col">{tcf_disp}</td>\'',
            '                _cells["pcs"] = _cells.get("pcs", "") + f\'<td class="wc-meta-col">{tcf_disp}</td>\'',
        ),
        (
            '                row_html += f\'<td class="wc-meta-col">{st_disp}</td>\'',
            '                _cells["pcs"] = _cells.get("pcs", "") + f\'<td class="wc-meta-col">{st_disp}</td>\'',
        ),
        (
            '                row_html += f\'<td class="wc-meta-col">{ft_disp}</td>\'',
            '                _cells["pcs"] = _cells.get("pcs", "") + f\'<td class="wc-meta-col">{ft_disp}</td>\'',
        ),
        (
            '                row_html += f\'<td class="wc-meta-col">{el_disp}</td>\'',
            '                _cells["pcs"] = _cells.get("pcs", "") + f\'<td class="wc-meta-col">{el_disp}</td>\'',
        ),
        (
            '                row_html += f\'<td class="wc-meta-col">{co_disp}</td>\'',
            '                _cells["pcs"] = _cells.get("pcs", "") + f\'<td class="wc-meta-col">{co_disp}</td>\'',
        ),
        (
            '                row_html += f\'<td class="wc-meta-col">{de_disp}</td>\'',
            '                _cells["pcs"] = _cells.get("pcs", "") + f\'<td class="wc-meta-col">{de_disp}</td>\'',
        ),
        (
            '                row_html += f\'<td class="wc-meta-col">{aph_disp}</td>\'',
            '                _cells["pcs"] = _cells.get("pcs", "") + f\'<td class="wc-meta-col">{aph_disp}</td>\'',
        ),
        (
            '            row_html += f\'<td class="wc-meta-col">{hc_disp}</td>\'',
            '            _cells["pcs"] = f\'<td class="wc-meta-col">{hc_disp}</td>\'',
        ),
        (
            '            row_html += f\'<td class="total-col {strike_class}">{_wc_cell(total_str, total_plain, "total_points_raw", None, 24)}</td>\'',
            '            _cells["total"] = f\'<td class="total-col {strike_class}">{_wc_cell(total_str, total_plain, "total_points_raw", None, 24)}</td>\'',
        ),
        (
            '            row_html += f\'<td class="disc-col {strike_class}">{disc_str}</td>\'',
            '            _cells["disc"] = f\'<td class="disc-col {strike_class}">{disc_str}</td>\'',
        ),
        (
            '            row_html += f\'<td class="nett-col {strike_class}">{_wc_cell(nett_str, nett_plain, "nett_points_raw", None, 24)}</td>\'',
            '            _cells["nett"] = f\'<td class="nett-col {strike_class}">{_wc_cell(nett_str, nett_plain, "nett_points_raw", None, 24)}</td>\'',
        ),
    ]
    for old, new in pairs:
        if old not in block:
            raise SystemExit("ERROR: row snippet not found:\n" + old[:120])
        block = block.replace(old, new, 1)
    leftover = [ln for ln in block.splitlines() if "row_html +=" in ln and "</tr>" not in ln]
    if leftover:
        raise SystemExit("ERROR: leftover row_html += : " + leftover[0])
    block = block.replace(ROW_END, JOIN_ROW, 1)
    return block


def apply_text(text: str) -> str:
    if MARKER in text and "_kb_order" in text:
        print("keelboat columns already patched")
        return text
    if INSERT_SHOW_RACES not in text:
        raise SystemExit("ERROR: show_races / Windsurfer block not found")
    if INSERT_SHOW_RACES.count("show_races = bool(race_columns)") > 0:
        pass
    text = text.replace(INSERT_SHOW_RACES, INSERT_SHOW_RACES_NEW, 1)
    if THEAD_TAIL not in text:
        raise SystemExit("ERROR: thead nett / late_part block not found")
    text = text.replace(THEAD_TAIL, THEAD_TAIL_NEW, 1)
    start = text.find(ROW_START)
    if start < 0:
        raise SystemExit("ERROR: row_html start not found")
    end = text.find(ROW_END, start)
    if end < 0:
        raise SystemExit("ERROR: row_html end not found")
    old_block = text[start : end + len(ROW_END)]
    new_block = _patch_row_block(old_block)
    text = text[:start] + new_block + text[end + len(ROW_END) :]
    if MARKER not in text or "_kb_order" not in text:
        raise SystemExit("ERROR: patch did not apply")
    fn0 = text.find("def _render_result_sheet_fleet")
    fn1 = text.find("def _render_fleet_section_html_for_block")
    fn_src = text[fn0:fn1] if fn0 >= 0 and fn1 > fn0 else text
    leftover = [
        ln
        for ln in fn_src.splitlines()
        if "row_html +=" in ln and "_cells.get" not in ln and "</tr>" not in ln
    ]
    if leftover:
        raise SystemExit("ERROR: leftover row_html += in function: " + leftover[0])
    return text


def main() -> int:
    api = API
    if not api.exists():
        # Local dry-run on dumped function
        api = Path("/tmp/live_render_result_sheet_fleet.py")
        text = api.read_text(encoding="utf-8")
        text = apply_text(text)
        api.write_text(text, encoding="utf-8")
        print("dry-run patched", api)
        return 0
    text = api.read_text(encoding="utf-8")
    new = apply_text(text)
    if new is text or new == text:
        return 0
    api.write_text(new, encoding="utf-8")
    print("patched keelboat column order on live api.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
