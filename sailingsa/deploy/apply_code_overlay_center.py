#!/usr/bin/env python3
"""Keep compact row height. Overlay code: centre under score, lift off bottom."""
from pathlib import Path
import shutil
import time

SRC = Path("/var/www/sailingsa/sailingsa/backend/regatta_print_compact_css.py")

OLD = """/* Race codes (DNC etc): centred under the score, slightly off the cell bottom. */
.fleet-results-table.rs-compact-row-logos td.race-col {
  position: relative !important;
  text-align: center !important;
}
.fleet-results-table.rs-compact-row-logos td.race-col span.code {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: 100% !important;
}
.fleet-results-table.rs-compact-row-logos .wc-score {
  font-size: 1em !important;
  font-weight: 600 !important;
  display: block !important;
  text-align: center !important;
  position: static !important;
  width: 100% !important;
}
.fleet-results-table.rs-compact-row-logos .wc-code,
.fleet-results-table.rs-compact-row-logos span.code .wc-code,
.fleet-results-table.rs-compact-row-logos span.disc .wc-code {
  font-size: 33% !important;
  font-weight: 700 !important;
  position: static !important;
  display: block !important;
  text-align: center !important;
  width: 100% !important;
  right: auto !important;
  left: auto !important;
  bottom: auto !important;
  top: auto !important;
  margin: 1px 0 3px !important;
  line-height: 1 !important;
  vertical-align: baseline !important;
  letter-spacing: 0.02em !important;
  opacity: 1 !important;
}"""

NEW = """/* Race codes stay overlaid (no extra row height). Centre under score; lift off bottom. */
.fleet-results-table.rs-compact-row-logos td.race-col {
  position: relative !important;
}
.fleet-results-table.rs-compact-row-logos .wc-score {
  font-size: 1em !important;
  font-weight: 600 !important;
}
.fleet-results-table.rs-compact-row-logos .wc-code,
.fleet-results-table.rs-compact-row-logos span.code .wc-code,
.fleet-results-table.rs-compact-row-logos span.disc .wc-code {
  font-size: 33% !important;
  font-weight: 700 !important;
  position: absolute !important;
  left: 50% !important;
  right: auto !important;
  top: auto !important;
  bottom: 4px !important;
  transform: translateX(-50%) !important;
  margin: 0 !important;
  line-height: 1 !important;
  vertical-align: baseline !important;
  letter-spacing: 0.02em !important;
  opacity: 1 !important;
  width: auto !important;
  text-align: center !important;
}"""

OLD_PRINT = """  .fleet-results-table .wc-code,
  .fleet-results-table.rs-compact-row-logos .wc-code {
    font-size: 33% !important;
    font-weight: 700 !important;
    position: static !important;
    display: block !important;
    text-align: center !important;
    width: 100% !important;
    right: auto !important;
    left: auto !important;
    bottom: auto !important;
    margin: 1px 0 2px !important;
    line-height: 1 !important;
    vertical-align: baseline !important;"""

NEW_PRINT = """  .fleet-results-table .wc-code,
  .fleet-results-table.rs-compact-row-logos .wc-code {
    font-size: 33% !important;
    font-weight: 700 !important;
    position: absolute !important;
    left: 50% !important;
    right: auto !important;
    bottom: 3px !important;
    transform: translateX(-50%) !important;
    margin: 0 !important;
    line-height: 1 !important;
    vertical-align: baseline !important;"""


def main() -> None:
    text = SRC.read_text()
    if "lift off bottom" in text and "transform: translateX(-50%)" in text and "position: absolute !important" in text:
        if "display: flex !important" not in text.split("Race codes")[1][:800]:
            print("ALREADY_PATCHED")
            return
    if OLD not in text:
        raise SystemExit("SCREEN_CSS_MISSING")
    text = text.replace(OLD, NEW, 1)
    n = 0
    if OLD_PRINT in text:
        text = text.replace(OLD_PRINT, NEW_PRINT)
        n = 1
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = SRC.with_name(f"regatta_print_compact_css.py.bak.{ts}")
    shutil.copy2(SRC, bak)
    SRC.write_text(text)
    print("BACKUP", bak, "PRINT", n, "PATCHED")


if __name__ == "__main__":
    main()
