#!/usr/bin/env python3
"""Verify lipton-dev-series-scores.json matches Lipton 2026 overall after 10 races PDF."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SERIES_PATH = Path(__file__).resolve().parents[1] / "sailingsa/frontend/js/lipton-dev-series-scores.json"

# Totals from Lipton Cup 2026 Overall results after 10 races PDF
PDF_TOTALS = {
    "HYC": 44.0,
    "RCYC": 46.0,
    "UCTYC": 51.0,
    "FBYC": 57.0,
    "SBYC": 62.0,
    "RNYC": 63.0,
    "PYC": 64.0,
    "RCYC Academy": 66.0,
    "WBYC": 77.0,
    "KYC": 82.0,
    "LDYC": 101.0,
    "GLYC": 114.0,
    "BYC": 127.0,
    "LYC": 137.0,
    "IZIVUNGUVUNGU": 141.0,
    "TSC": 143.0,
    "WYAC": 163.0,
}

PDF_CODES = {
    ("RNYC", 6): "DSQ",
    ("KYC", 6): "DSQ",
    ("LDYC", 6): "DSQ",
    ("WYAC", 9): "RET",
    ("LDYC", 10): "RET",
}


def canonical_matrix(data: dict) -> str:
    lines = []
    for boat in sorted(data["boats"].keys()):
        row = data["boats"][boat]
        pts = [str(row["points"][str(i)]) for i in range(1, 11)]
        codes = [row.get("codes", {}).get(str(i), "") for i in range(1, 11)]
        lines.append(f"{boat}|{','.join(pts)}|{','.join(codes)}")
    return "\n".join(lines)


def main() -> int:
    data = json.loads(SERIES_PATH.read_text(encoding="utf-8"))
    errors = []

    matrix = canonical_matrix(data)
    matrix_sha = hashlib.sha256(matrix.encode()).hexdigest()
    expected_sha = (data.get("checksum") or {}).get("matrix_sha256")
    if expected_sha and matrix_sha != expected_sha:
        errors.append(f"matrix_sha256 mismatch: got {matrix_sha}, expected {expected_sha}")

    dsq_r6 = sorted(
        b for b, row in data.get("boats", {}).items() if row.get("codes", {}).get("6") == "DSQ"
    )
    if dsq_r6 != ["KYC", "LDYC", "RNYC"]:
        errors.append(f"R6 DSQ boats {dsq_r6!r} != ['KYC', 'LDYC', 'RNYC']")

    for boat, exp in PDF_TOTALS.items():
        pts = data["boats"].get(boat, {}).get("points", {})
        total = sum(float(pts[str(i)]) for i in range(1, 11))
        if abs(total - exp) > 0.001:
            errors.append(f"{boat} total {total} != PDF {exp}")

    for (boat, rn), code in PDF_CODES.items():
        got = data["boats"].get(boat, {}).get("codes", {}).get(str(rn))
        if got != code:
            errors.append(f"{boat} R{rn} code {got!r} != PDF {code!r}")

    for n in (6, 7, 10):
        key = str(n)
        rows = []
        for boat in data["boats"]:
            total = sum(float(data["boats"][boat]["points"][str(i)]) for i in range(1, int(n) + 1))
            rows.append((total, boat))
        rows.sort()
        ranked = [{"rank": i + 1, "boat": b, "nett": t} for i, (t, b) in enumerate(rows)]
        exp = data.get("overall_after", {}).get(key) or data.get("overall_after", {}).get(int(n))
        if exp:
            for i, row in enumerate(exp):
                if ranked[i]["boat"] != row["boat"] or abs(ranked[i]["nett"] - row["nett"]) > 0.001:
                    errors.append(f"overall_after {n} rank {i+1}: calc {ranked[i]} != stored {row}")

    if errors:
        print("FAIL", SERIES_PATH)
        for e in errors:
            print(" ", e)
        return 1

    print("OK", SERIES_PATH)
    print("  matrix_sha256", matrix_sha)
    print("  R6 DSQ", dsq_r6)
    print("  boats", len(data["boats"]), "races 10 entries", data.get("entries"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
