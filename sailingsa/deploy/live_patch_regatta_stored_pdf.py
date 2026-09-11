#!/usr/bin/env python3
"""Wire server-made /regatta results.pdf routes on live api.py (surgical)."""

from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")

PDF_ROUTES = '''
@app.get("/regatta/{slug}/results.pdf")
@app.head("/regatta/{slug}/results.pdf")
def _regatta_parent_results_pdf(slug: str, download: int = 0):
    return _serve_regatta_stored_pdf(slug, None, bool(download))


@app.get("/regatta/{slug}/class-{class_slug}/results.pdf")
@app.head("/regatta/{slug}/class-{class_slug}/results.pdf")
def _regatta_child_results_pdf(slug: str, class_slug: str, download: int = 0):
    return _serve_regatta_stored_pdf(slug, class_slug, bool(download))


'''

HELPER = '''

def _schedule_regatta_pdf_rebuild(slug: str) -> None:
    rid = str(slug or "").strip()
    if not rid:
        return
    threading.Thread(target=_rebuild_regatta_stored_pdfs, args=(rid,), daemon=True).start()


def _rebuild_regatta_stored_pdfs(slug: str):
    from sailingsa.backend.regatta_stored_pdf import write_event_pdfs

    rid = str(slug or "").strip()
    if not rid:
        return None
    data = _get_regatta_full_page_data(rid)
    if not data:
        return None
    ev_name = data[0] if data else rid
    fleets = data[4] if len(data) > 4 else []
    result_status = data[5] if len(data) > 5 else "Final"
    as_at_time = data[6] if len(data) > 6 else None
    host_abbrev = data[8] if len(data) > 8 else ""
    host_full = data[9] if len(data) > 9 else ""
    host_legacy = data[1] if len(data) > 1 else ""
    host = _format_regatta_host_display(host_abbrev, host_full, host_legacy or "")
    status_line = _format_regatta_status_line((result_status or "Final").strip() or "Final", as_at_time)
    left_logo = ""
    right_logo = ""
    try:
        lu, ru = _wc_regatta_header_icon_urls(rid)
        left_logo = lu or _regatta_named_event_logo_url(rid, ev_name or "") or ""
        right_logo = ru or ""
    except Exception:
        pass
    fleet_jobs = []
    for f in fleets or []:
        html = _render_result_sheet_fleet(f, wc_sa_fleet_edit=False)
        fleet_jobs.append(
            {
                "class_slug": (f.get("class_slug") or "").strip(),
                "html": html,
                "n_rows": len(f.get("rows") or []),
            }
        )
    return write_event_pdfs(
        slug=rid,
        event_name=(ev_name or rid).strip() or rid,
        host=host,
        status_line=status_line,
        sheet_url="https://sailingsa.co.za/regatta/" + rid,
        fleets=fleet_jobs,
        left_logo=left_logo,
        right_logo=right_logo,
    )


def _serve_regatta_stored_pdf(slug: str, class_slug, download: bool):
    from sailingsa.backend.regatta_stored_pdf import pdf_abs_path, pdf_download_name
    from fastapi.responses import FileResponse

    rid = str(slug or "").strip()
    cslug = (class_slug or "").strip() or None
    if not rid:
        raise HTTPException(status_code=404, detail="PDF not found")
    path = pdf_abs_path(rid, cslug)
    if not path.is_file() or path.stat().st_size < 500:
        try:
            _rebuild_regatta_stored_pdfs(rid)
        except Exception as exc:
            print(f"[regatta-pdf] rebuild {rid}: {exc}", flush=True)
        path = pdf_abs_path(rid, cslug)
    if not path.is_file() or path.stat().st_size < 500:
        raise HTTPException(status_code=404, detail="PDF not found")
    fn = pdf_download_name(rid, cslug)
    disp = "attachment" if download else "inline"
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disp}; filename="{fn}"',
            "Cache-Control": "public, max-age=60",
        },
    )


'''


def main() -> None:
    text = LIVE_API.read_text(encoding="utf-8")
    if '@app.get("/regatta/{slug}/results.pdf")' not in text:
        anchor = '@app.get("/regatta/{slug}/class-{class_slug}")'
        if anchor not in text:
            raise SystemExit("missing class-{class_slug} route anchor")
        text = text.replace(anchor, PDF_ROUTES + anchor, 1)
    if "def _rebuild_regatta_stored_pdfs" not in text:
        helper_end = (
            "    from sailingsa.backend.regatta_print_compact_css import print_share_bar_html\n"
            "\n"
            "    return print_share_bar_html()\n"
        )
        if helper_end not in text:
            raise SystemExit("print helper end not found")
        text = text.replace(helper_end, helper_end + HELPER, 1)
    if "_schedule_regatta_pdf_rebuild(str(regatta_id))" not in text:
        old_commit = (
            "        conn.commit()\n"
            "    out_row = _fetch_regatta_result_row_by_id(result_id)\n"
        )
        new_commit = (
            "        conn.commit()\n"
            "    if regatta_id:\n"
            "        _schedule_regatta_pdf_rebuild(str(regatta_id))\n"
            "    out_row = _fetch_regatta_result_row_by_id(result_id)\n"
        )
        if old_commit not in text:
            raise SystemExit("patch_result commit anchor not found")
        text = text.replace(old_commit, new_commit, 1)
        if "regatta_id = None\n    with psycopg2.connect(DB_URL) as conn:" not in text:
            text = text.replace(
                "def patch_result(request: Request, result_id: int, p: ResultPatch):\n"
                "    _require_super_admin(request)\n"
                "    with psycopg2.connect(DB_URL) as conn:\n",
                "def patch_result(request: Request, result_id: int, p: ResultPatch):\n"
                "    _require_super_admin(request)\n"
                "    regatta_id = None\n"
                "    with psycopg2.connect(DB_URL) as conn:\n",
                1,
            )
        race_old = (
            "            _ensure_snapshot_integrity(conn, regatta_id)\n"
            "            conn.commit()\n"
            "            \n"
            "            # Return updated result data\n"
        )
        race_new = (
            "            _ensure_snapshot_integrity(conn, regatta_id)\n"
            "            conn.commit()\n"
            "            _schedule_regatta_pdf_rebuild(str(regatta_id))\n"
            "            \n"
            "            # Return updated result data\n"
        )
        if race_old in text:
            text = text.replace(race_old, race_new, 1)
    LIVE_API.write_text(text, encoding="utf-8")
    print("wired stored results.pdf routes + save rebuild")


if __name__ == "__main__":
    main()
