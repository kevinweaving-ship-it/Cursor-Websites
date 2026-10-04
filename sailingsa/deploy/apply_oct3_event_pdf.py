#!/usr/bin/env python3
"""Event URL Print/Share must open the same results.pdf as /regatta/."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/regatta-pdf-share.js")
CSS = Path("/var/www/sailingsa/sailingsa/backend/regatta_print_compact_css.py")

OLD_SHEET = """    if (p.indexOf("/regatta/") === 0) {
      return "https://sailingsa.co.za" + p.replace(/\\/+$/, "");
    }"""
NEW_SHEET = """    if (p.indexOf("/regatta/") === 0 || p.indexOf("/event/") === 0) {
      return "https://sailingsa.co.za" + p.replace(/\\/+$/, "");
    }"""

OLD_PDFPATH = """    if (p.indexOf("/regatta/") !== 0) return "";"""
NEW_PDFPATH = """    if (p.indexOf("/regatta/") !== 0 && p.indexOf("/event/") !== 0) return "";"""

OLD_FB = (
    "        \"if(p.indexOf('/regatta/')===0)window.open(p+'/results.pdf','_blank');})()\"\n"
)
NEW_FB = (
    "        \"if(p.indexOf('/regatta/')===0||p.indexOf('/event/')===0)"
    "window.open(p+'/results.pdf','_blank');})()\"\n"
)

OLD_VER = 'PDF_SHARE_JS_SRC = "/js/regatta-pdf-share.js?v=20260919print9"'
NEW_VER = 'PDF_SHARE_JS_SRC = "/js/regatta-pdf-share.js?v=20261004eventpdf"'

OLD_ROUTE = '''@app.get("/regatta/{slug}/results.pdf")
@app.head("/regatta/{slug}/results.pdf")
def _regatta_parent_results_pdf(slug: str, download: int = 0):
    return _serve_regatta_stored_pdf(slug, None, bool(download))
'''
NEW_ROUTE = OLD_ROUTE + '''

@app.get("/event/{slug}/results.pdf")
@app.head("/event/{slug}/results.pdf")
def _event_parent_results_pdf(slug: str, download: int = 0):
    return _serve_regatta_stored_pdf(slug, None, bool(download))
'''

OLD_RID = """    rid = str(slug or "").strip()
    cslug = (class_slug or "").strip() or None"""
NEW_RID = """    rid = str(slug or "").strip()
    try:
        rid = str(_resolve_regatta_id_alias(rid) or rid).strip()
    except Exception:
        pass
    cslug = (class_slug or "").strip() or None"""


def main() -> None:
    js = JS.read_text()
    if OLD_SHEET not in js:
        if "/event/" in js and "pdfPath" in js:
            print("JS_SHEET_ALREADY")
        else:
            print("JS_SHEET_MARK")
            print(repr(js[js.find("function sheetUrl") : js.find("function sheetUrl") + 420]))
            raise SystemExit(2)
    else:
        js = js.replace(OLD_SHEET, NEW_SHEET, 1)
        print("JS_SHEET_OK")
    if OLD_PDFPATH in js:
        js = js.replace(OLD_PDFPATH, NEW_PDFPATH, 1)
        print("JS_PDFPATH_OK")
    elif NEW_PDFPATH in js:
        print("JS_PDFPATH_ALREADY")
    else:
        print("JS_PDFPATH_MARK")
        raise SystemExit(3)
    JS.write_text(js)

    css = CSS.read_text()
    if OLD_FB in css:
        css = css.replace(OLD_FB, NEW_FB, 1)
        print("CSS_FB_OK")
    elif "/event/" in css and "results.pdf" in css:
        print("CSS_FB_ALREADY")
    else:
        print("CSS_FB_MARK")
        i = css.find("fallback =")
        print(repr(css[i : i + 280]))
        raise SystemExit(4)
    if OLD_VER in css:
        css = css.replace(OLD_VER, NEW_VER, 1)
        print("CSS_VER_OK")
    elif NEW_VER in css:
        print("CSS_VER_ALREADY")
    else:
        print("CSS_VER_SKIP")
    CSS.write_text(css)

    api = API.read_text()
    if "@app.get(\"/event/{slug}/results.pdf\")" in api:
        print("API_ROUTE_ALREADY")
    elif OLD_ROUTE not in api:
        print("API_ROUTE_MARK")
        raise SystemExit(5)
    else:
        api = api.replace(OLD_ROUTE, NEW_ROUTE, 1)
        print("API_ROUTE_OK")
    if OLD_RID in api:
        api = api.replace(OLD_RID, NEW_RID, 1)
        print("API_ALIAS_OK")
    elif "_resolve_regatta_id_alias(rid)" in api[api.find("def _serve_regatta_stored_pdf") : api.find("def _serve_regatta_stored_pdf") + 400]:
        print("API_ALIAS_ALREADY")
    else:
        print("API_ALIAS_MARK")
        raise SystemExit(6)
    API.write_text(api)

    print("JS_HAS_EVENT", "/event/" in JS.read_text())
    print("CSS_HAS_EVENT", "/event/" in CSS.read_text())
    print("API_HAS_EVENT_PDF", '@app.get("/event/{slug}/results.pdf")' in API.read_text())
    print("API_HAS_ALIAS", "_resolve_regatta_id_alias(rid)" in API.read_text())


if __name__ == "__main__":
    main()
