#!/usr/bin/env python3
from pathlib import Path
P = Path("/var/www/sailingsa/sailingsa/backend/regatta_stored_pdf.py")
OLD = '''            "--no-pdf-header-footer",
            "--hide-scrollbars",
            "--run-all-compositor-stages-before-draw",
'''
NEW = '''            "--no-pdf-header-footer",
            "--hide-scrollbars",
            "--prefer-css-page-size",
            "--run-all-compositor-stages-before-draw",
'''
def main():
    t = P.read_text()
    if "--prefer-css-page-size" in t:
        print("already prefer-css-page-size")
        return 0
    if OLD not in t:
        raise SystemExit("chrome flags missing")
    P.write_text(t.replace(OLD, NEW, 1))
    print("PATCHED chrome flags")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
