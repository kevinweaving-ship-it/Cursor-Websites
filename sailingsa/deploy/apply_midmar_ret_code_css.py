#!/usr/bin/env python3
"""Show Appendix A points above RET/DNC codes in fleet score cells."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
OLD = ".code{color:#c62828;font-weight:bold}"
NEW = ".code{color:#c62828;font-weight:bold;white-space:pre-line;line-height:1.15}"


def main() -> None:
    text = API.read_text()
    n = text.count(OLD)
    if n:
        API.write_text(text.replace(OLD, NEW))
        print("CSS_OK", n)
        return
    if NEW in text:
        print("CSS_ALREADY")
        return
    raise SystemExit("CSS_ANCHOR_MISSING")


if __name__ == "__main__":
    main()
