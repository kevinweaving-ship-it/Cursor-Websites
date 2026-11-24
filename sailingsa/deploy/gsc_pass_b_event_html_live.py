#!/usr/bin/env python3
"""Surgical Pass B patch for live /var/www/sailingsa/api/api.py.

Stops fabricated 17:30 as_at, adds truthful title/meta/H1/JSON-LD/footer.
Does not touch pool/DB helpers, sitemap, housekeeping, or WhatsApp.
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "GSC_PASS_B_EVENT_HTML_v1"

HELPER = r'''
def _pass_b_named_event_series(regatta_id: str, event_name: str):
    """Existing /events-logos catalogue only. No new series table."""
    label, href, prev = "", "", []
    try:
        from events_logos_gallery import _canon_series_key, _series_key_from_regatta_name

        idx = _catalogue_event_index()
        key = _canon_series_key(_series_key_from_regatta_name(event_name, regatta_id))
        row = idx.get(key) if key else None
        href = _catalogue_event_href_for_row(row) or ""
        label = str((row or {}).get("label") or "").strip()
        slug = str((row or {}).get("slug") or "").strip()
        if slug:
            try:
                d = _events_logos_gallery_deps()
                elg = d.pop("elg")
                full = elg.row_by_slug(slug, **d) or {}
                label = str(full.get("label") or label).strip()
                href = str(full.get("url") or href).strip()
                for r in full.get("regattas") or []:
                    if isinstance(r, dict) and r.get("url") and r.get("year"):
                        prev.append({"url": r["url"], "year": r["year"]})
            except Exception:
                pass
    except Exception:
        return "", "", []
    return label, href, prev


def _pass_b_class_names_from_fleets(fleets) -> list:
    out, seen = [], set()
    for f in fleets or []:
        if not isinstance(f, dict):
            continue
        cn = str(f.get("class_name") or f.get("name") or f.get("fleet_name") or "").strip()
        key = cn.lower()
        if not cn or key in seen or key in {"fleet", "overall"}:
            continue
        seen.add(key)
        out.append(cn)
    return out


def _pass_b_build_page_bits(
    *,
    display_name,
    canonical_url,
    start_d,
    end_d,
    result_status,
    as_at_time,
    fleets,
    host_club_text,
    host_club_slug,
    host_club_province,
    regatta_id,
    formatted_results_line,
):
    from sailingsa.backend.event_page_seo import build_regatta_pass_b

    base = _canonical_base_url()
    series_name, series_href, prev = _pass_b_named_event_series(str(regatta_id), display_name)
    venue = ""
    try:
        place, _co = _regatta_venue_cohost(str(regatta_id))
        venue = (place or "").strip()
    except Exception:
        venue = ""
    as_at_display = ""
    if as_at_time is not None:
        try:
            if hasattr(as_at_time, "strftime"):
                as_at_display = as_at_time.strftime("%d %B %Y at %H:%M")
            else:
                as_at_display = str(as_at_time)[:16]
        except Exception:
            as_at_display = ""
    host_href = f"/club/{host_club_slug}" if host_club_slug else ""
    image_url = f"{base.rstrip('/')}/api/og/regatta/{regatta_id}.png"
    return build_regatta_pass_b(
        display_name=display_name,
        canonical_url=canonical_url,
        base_url=base,
        start_date=start_d,
        end_date=end_d,
        result_status=result_status,
        as_at_time=as_at_time,
        fleets=fleets,
        host_club=host_club_text or "",
        host_club_href=host_href,
        province=host_club_province or "",
        venue=venue,
        class_names=_pass_b_class_names_from_fleets(fleets),
        series_name=series_name,
        series_href=series_href,
        previous_editions=prev,
        formatted_results_line=formatted_results_line or "",
        as_at_display=as_at_display,
        image_url=image_url,
    )

'''


def patch(text: str) -> str:
    text = text.replace(
        '\'<div class="regatta-name-view"><h1 class="regatta-name" id="regattaNameView">\' + escaped_view + "</div></div>"',
        '\'<div class="regatta-name-view"><h1 class="regatta-name" id="regattaNameView">\' + escaped_view + "</h1></div>"',
        1,
    )
    if MARKER in text and "Do not invent end-date 17:30" in text:
        return text

    old_resolve = '''    """Snapshot time ladder: keep recorded as_at; else matched calendar event last day @ 17:30; else regatta end/start."""
    if as_at_time:
        return as_at_time'''
    new_resolve = '''    """Recorded snapshot only. Do not invent end-date 17:30. GSC_PASS_B_EVENT_HTML_v1."""
    if as_at_time:
        return as_at_time
    return None
    if False:  # noqa: historical 17:30 ladder disabled — kept so later lines stay dead
        return as_at_time'''
    if old_resolve not in text:
        raise SystemExit("resolve docstring anchor missing")
    text = text.replace(old_resolve, new_resolve, 1)

    # Make the rest of the old ladder unreachable is not enough — early return None
    # already exits. Leave remaining code in place to avoid a huge delete.

    old_fmt = '''    if not as_at_time:
        from sailingsa.backend.regatta_status_line import resolve_status_as_at
        _dt = resolve_status_as_at(None, end_date=end_date, start_date=start_date)
        if _dt:
            return _with_as_at(_dt.strftime("%d %B %Y at %H:%M"))
        return f"Results are {escaped_word} (snapshot time not recorded)"'''
    new_fmt = '''    if not as_at_time:
        return f"Results are {escaped_word} (snapshot time not recorded)"'''
    if old_fmt not in text:
        raise SystemExit("format fallback anchor missing")
    text = text.replace(old_fmt, new_fmt, 1)

    old_css = '    ".regatta-name{font-size:24px;font-weight:bold;color:#1a2750;margin-bottom:8px}"'
    new_css = (
        old_css
        + '\n    "h1.regatta-name{margin:0 0 8px;padding:0}"\n'
        + '    ".regatta-event-context{margin:1.5rem 1rem 0;padding:0.75rem 0 0;border-top:1px solid #e0e0e0;font-size:0.85rem;color:#444;line-height:1.45;text-align:left}"\n'
        + '    ".regatta-event-context p{margin:0 0 0.35rem}"\n'
        + '    ".regatta-event-context a{color:#1a2750}"'
    )
    if old_css not in text:
        raise SystemExit("css anchor missing")
    text = text.replace(old_css, new_css, 1)

    text = text.replace(
        '<div class="regatta-name-view"><div class="regatta-name" id="regattaNameView">\' + escaped_view + "</div></div>"',
        '<div class="regatta-name-view"><h1 class="regatta-name" id="regattaNameView">\' + escaped_view + "</h1></div>"',
        1,
    )
    text = text.replace(
        '<div class="regatta-name-view"><h1 class="regatta-name" id="regattaNameView">\' + escaped_view + "</div></div>"',
        '<div class="regatta-name-view"><h1 class="regatta-name" id="regattaNameView">\' + escaped_view + "</h1></div>"',
        1,
    )
    text = text.replace(
        'f\'<div class="regatta-name">{escaped_title}</div>\'',
        'f\'<h1 class="regatta-name">{escaped_title}</h1>\'',
    )

    if "def _pass_b_build_page_bits(" not in text:
        anchor = "def serve_regatta_standalone(slug: str, request: Request):"
        if anchor not in text:
            raise SystemExit("standalone anchor missing")
        text = text.replace(anchor, HELPER + "\n" + anchor, 1)

    old_status = '''        status_word = _gold_status_word_if_results((result_status or "Final").strip() or "Final", fleets)
        status_line_text = _format_regatta_status_line(
            status_word, as_at_time, str(regatta_id), end_date=end_d, start_date=start_d
        )
        _pdf_sl = _regatta_pdf_status_line_override(str(regatta_id))
        if _pdf_sl:
            status_line_text = html_module.escape(_pdf_sl)
            if _regatta_is_lipton_challenge(str(regatta_id)):
                status_line_text = _regatta_lipton_status_line_html(status_line_text)'''
    new_status = '''        status_word = _gold_status_word_if_results((result_status or "Final").strip() or "Final", fleets)
        status_line_text = _format_regatta_status_line(
            status_word, as_at_time, str(regatta_id), end_date=end_d, start_date=start_d
        )
        _pdf_sl = _regatta_pdf_status_line_override(str(regatta_id))
        if _pdf_sl:
            status_line_text = html_module.escape(_pdf_sl)
            if _regatta_is_lipton_challenge(str(regatta_id)):
                status_line_text = _regatta_lipton_status_line_html(status_line_text)
        _pass_b = None
        try:
            _pass_b = _pass_b_build_page_bits(
                display_name=display_name,
                canonical_url=canonical_url,
                start_d=start_d,
                end_d=end_d,
                result_status=result_status,
                as_at_time=as_at_time,
                fleets=fleets,
                host_club_text=host_club_text if False else "",
                host_club_slug=None,
                host_club_province=host_club_province,
                regatta_id=str(regatta_id),
                formatted_results_line=status_line_text,
            )
        except Exception as _pass_b_err:
            print(f"[pass_b] early { _pass_b_err }", flush=True)
            _pass_b = None'''
    if old_status not in text:
        raise SystemExit("status-line anchor missing")
    text = text.replace(old_status, new_status, 1)

    # Rebuild pass_b after host_club_text/slug are known
    old_host_done = '''        esc_host = html_module.escape(host_club_text)
        host_club_html = ('''
    new_host_done = '''        if True:
            try:
                _pass_b = _pass_b_build_page_bits(
                    display_name=display_name,
                    canonical_url=canonical_url,
                    start_d=start_d,
                    end_d=end_d,
                    result_status=result_status,
                    as_at_time=as_at_time,
                    fleets=fleets,
                    host_club_text=host_club_text,
                    host_club_slug=host_club_slug,
                    host_club_province=host_club_province,
                    regatta_id=str(regatta_id),
                    formatted_results_line=status_line_text,
                )
                if _pass_b and not _pdf_sl:
                    status_line_text = _pass_b.get("status_visible") or status_line_text
            except Exception as _pass_b_err:
                print(f"[pass_b] bits { _pass_b_err }", flush=True)
        esc_host = html_module.escape(host_club_text)
        host_club_html = ('''
    if old_host_done not in text:
        raise SystemExit("host_club_html anchor missing")
    text = text.replace(old_host_done, new_host_done, 1)

    old_json = '''        # SportsEvent JSON-LD: startDate required (ISO 8601 YYYY-MM-DD); rest for rich result eligibility
        start_iso = _iso_date(start_d)
        json_ld = {
            "@context": "https://schema.org",
            "@type": "SportsEvent",
            "name": ev_name or event_name,
            "sport": "Sailing",
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        }
        if start_iso:
            json_ld["startDate"] = start_iso
        end_iso = _iso_date(end_d)
        if end_iso:
            json_ld["endDate"] = end_iso
        description = ev_name or event_name or ""
        if description:
            json_ld["description"] = description
        organizer_name = host_club_text or "SailingSA"
        json_ld["organizer"] = {"@type": "Organization", "name": organizer_name}
        if host_club_text:
            address = {"@type": "PostalAddress", "addressCountry": "ZA"}
            if host_club_province:
                address["addressLocality"] = host_club_province
            json_ld["location"] = {
                "@type": "Place",
                "name": host_club_text,
                "address": address,
            }'''
    new_json = '''        # SportsEvent JSON-LD: startDate required (ISO 8601 YYYY-MM-DD); rest for rich result eligibility
        start_iso = _iso_date(start_d)
        json_ld = {
            "@context": "https://schema.org",
            "@type": "SportsEvent",
            "name": ev_name or event_name,
            "sport": "Sailing",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        }
        if _pass_b and _pass_b.get("schema_event_status"):
            json_ld["eventStatus"] = _pass_b["schema_event_status"]
        if start_iso:
            json_ld["startDate"] = start_iso
        end_iso = _iso_date(end_d)
        if end_iso:
            json_ld["endDate"] = end_iso
        description = (_pass_b or {}).get("description") or ev_name or event_name or ""
        if description:
            json_ld["description"] = description
        organizer_name = host_club_text or "SailingSA"
        json_ld["organizer"] = {"@type": "Organization", "name": organizer_name}
        if host_club_text:
            address = {"@type": "PostalAddress", "addressCountry": "ZA"}
            if host_club_province:
                address["addressLocality"] = host_club_province
            json_ld["location"] = {
                "@type": "Place",
                "name": host_club_text,
                "address": address,
            }
        _pass_b_ld_html = (_pass_b or {}).get("json_ld_html") or ""'''
    if old_json not in text:
        raise SystemExit("json-ld anchor missing")
    text = text.replace(old_json, new_json, 1)

    old_footer = '''            '<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year-sa-footer"></span></footer>' '''
    new_footer = '''            + ((_pass_b or {}).get("footer_html") or "") +
            '<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year-sa-footer"></span></footer>' '''
    # page_inner concatenates footer as a string literal in a paren list
    old_page_footer = '''            f"{mm_card_script}{sa_toolbar_script}{wc_club_edit_script}{entry_script}{live_board_script}"
            '<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year-sa-footer"></span></footer>' '''.rstrip()
    new_page_footer = '''            f"{mm_card_script}{sa_toolbar_script}{wc_club_edit_script}{entry_script}{live_board_script}"
            + ((_pass_b or {}).get("footer_html") or "") +
            '<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year-sa-footer"></span></footer>' '''.rstrip()
    if old_page_footer not in text:
        raise SystemExit("page footer anchor missing")
    text = text.replace(old_page_footer, new_page_footer, 1)

    old_lipton_title = '''            _fb_lipton_head = _fb_og_head_for(
                "regatta",
                str(canonical_slug),
                f"{escaped_title} | SailingSA",
                f"Regatta results: {escaped_title}.",
                canonical_url,
                source_url=_fb_og_regatta_left_url(str(regatta_id), ev_name or event_name),
            )
            extra_head = (
                f"<script type=\\"application/ld+json\\">{json.dumps(json_ld)}</script>"
                f"<style>{_RESULT_SHEET_CSS}</style>"
            )
            resp = _html_with_gold_header(f"{escaped_title} | SailingSA", page_inner, extra_head)'''
    new_lipton_title = '''            _p_title = ((_pass_b or {}).get("title") or (escaped_title + " | SailingSA"))
            _p_desc = ((_pass_b or {}).get("description") or ("Regatta results: " + escaped_title + "."))
            _fb_lipton_head = _fb_og_head_for(
                "regatta",
                str(canonical_slug),
                _p_title,
                _p_desc,
                canonical_url,
                source_url=_fb_og_regatta_left_url(str(regatta_id), ev_name or event_name),
            )
            extra_head = (
                ((_pass_b or {}).get("json_ld_html") or f"<script type=\\"application/ld+json\\">{json.dumps(json_ld)}</script>")
                + f"<style>{_RESULT_SHEET_CSS}</style>"
            )
            resp = _html_with_gold_header(_p_title, page_inner, extra_head)'''
    if old_lipton_title not in text:
        raise SystemExit("lipton title anchor missing")
    text = text.replace(old_lipton_title, new_lipton_title, 1)

    old_doc = '''        doc = (
            "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><title>"
            f"{escaped_title} | SailingSA</title>"
            f"<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">"
            + _fb_og_head_for("regatta", str(canonical_slug), f"{escaped_title} | SailingSA", f"Regatta results: {escaped_title}.", canonical_url, source_url=_fb_og_regatta_left_url(str(regatta_id), ev_name or event_name))
            + "<link rel=\\"icon\\" href=\\"/favicon.ico\\" sizes=\\"any\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"16x16\\" href=\\"/favicon-16.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"32x32\\" href=\\"/favicon-32.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"48x48\\" href=\\"/favicon-48.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"192x192\\" href=\\"/favicon-192.png\\"><link rel=\\"apple-touch-icon\\" href=\\"/apple-touch-icon.png\\">"
            "<link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"192x192\\" href=\\"/favicon-192.png\\">"
            f"<script type=\\"application/ld+json\\">{json.dumps(json_ld)}</script>"
            f"<style>{_RESULT_SHEET_CSS}</style></head><body>"
            f"{page_inner}"
            "</body></html>"
        )'''
    new_doc = '''        _p_title = ((_pass_b or {}).get("title") or (f"{escaped_title} | SailingSA"))
        _p_desc = ((_pass_b or {}).get("description") or (f"Regatta results: {escaped_title}."))
        _p_ld = ((_pass_b or {}).get("json_ld_html") or f"<script type=\\"application/ld+json\\">{json.dumps(json_ld)}</script>")
        doc = (
            "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><title>"
            f"{html_module.escape(_p_title)}</title>"
            f"<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">"
            + _fb_og_head_for("regatta", str(canonical_slug), _p_title, _p_desc, canonical_url, source_url=_fb_og_regatta_left_url(str(regatta_id), ev_name or event_name))
            + "<link rel=\\"icon\\" href=\\"/favicon.ico\\" sizes=\\"any\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"16x16\\" href=\\"/favicon-16.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"32x32\\" href=\\"/favicon-32.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"48x48\\" href=\\"/favicon-48.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"192x192\\" href=\\"/favicon-192.png\\"><link rel=\\"apple-touch-icon\\" href=\\"/apple-touch-icon.png\\">"
            "<link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"192x192\\" href=\\"/favicon-192.png\\">"
            f"{_p_ld}"
            f"<style>{_RESULT_SHEET_CSS}</style></head><body>"
            f"{page_inner}"
            "</body></html>"
        )'''
    if old_doc not in text:
        raise SystemExit("doc title anchor missing")
    text = text.replace(old_doc, new_doc, 1)

    # Drop the broken early pass_b that runs before host is known
    text = text.replace(
        '''        _pass_b = None
        try:
            _pass_b = _pass_b_build_page_bits(
                display_name=display_name,
                canonical_url=canonical_url,
                start_d=start_d,
                end_d=end_d,
                result_status=result_status,
                as_at_time=as_at_time,
                fleets=fleets,
                host_club_text=host_club_text if False else "",
                host_club_slug=None,
                host_club_province=host_club_province,
                regatta_id=str(regatta_id),
                formatted_results_line=status_line_text,
            )
        except Exception as _pass_b_err:
            print(f"[pass_b] early { _pass_b_err }", flush=True)
            _pass_b = None
''',
        "        _pass_b = None\n",
        1,
    )
    return text


def main() -> int:
    api_path = API
    if len(sys.argv) > 1:
        api_path = Path(sys.argv[1])
    if not api_path.is_file():
        print("missing", api_path)
        return 2
    raw = api_path.read_text(encoding="utf-8")
    new = patch(raw)
    if new == raw:
        print("no changes")
        return 0
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = api_path.with_name(api_path.name + f".{stamp}.passb.bak")
    shutil.copy2(api_path, bak)
    tmp = api_path.with_suffix(api_path.suffix + ".passb.tmp")
    tmp.write_text(new, encoding="utf-8")
    import py_compile

    py_compile.compile(str(tmp), doraise=True)
    tmp.replace(api_path)
    print("patched", api_path, "backup", bak, "bytes", len(new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
