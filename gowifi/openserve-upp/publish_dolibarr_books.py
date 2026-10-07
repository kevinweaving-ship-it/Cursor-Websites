#!/usr/bin/env python3
"""Publish Dolibarr 22-client books to /dash/dolibarr-books.json only.

The live dash client cards in accounts.json were reconciled over days of
statement work. This script must never overlay billed / paid / due /
advance / balance_label / paid_up onto those cards. Unused historic
receipts stay on the statement as Paid Up — they are not dash credits.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("/home/user-data/www/default/dash/dolibarr-books.json")
DOLIBARR_URL = "/dash/clients.html"


def _sql(query: str) -> list[list[str]]:
    raw = subprocess.check_output(
        ["mysql", "--protocol=socket", "-u", "root", "-N", "-e", query],
        text=True,
    )
    rows = []
    for line in raw.splitlines():
        if line.strip():
            rows.append(line.split("\t"))
    return rows


def _money(value) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _label(remain: float) -> str:
    if remain > 0.004:
        return f"Due {remain:,.2f}"
    return "Paid Up"


def load_books() -> dict[str, dict]:
    rows = _sql(
        """
        SELECT s.nom,
               ROUND(SUM(f.total_ttc),2) billed,
               ROUND(COALESCE(SUM(pf.paid),0),2) allocated
        FROM dolibarr.llx_societe s
        JOIN dolibarr.llx_facture f
          ON f.fk_soc=s.rowid AND f.type=0 AND f.fk_statut IN (1,2)
        LEFT JOIN (
          SELECT fk_facture, SUM(amount) paid
          FROM dolibarr.llx_paiement_facture
          GROUP BY fk_facture
        ) pf ON pf.fk_facture=f.rowid
        GROUP BY s.rowid
        """
    )
    books: dict[str, dict] = {}
    for name, billed, allocated in rows:
        billed_f = _money(billed)
        remain = round(billed_f - _money(allocated), 2)
        books[name] = {
            "name": name,
            "billed": billed_f,
            "remain": remain,
            "advance": 0.0,
        }
    for name, amount in _sql(
        """
        SELECT s.nom, ROUND(d.amount_ttc,2)
        FROM dolibarr.llx_societe_remise_except d
        JOIN dolibarr.llx_societe s ON s.rowid=d.fk_soc
        WHERE d.fk_facture IS NULL
        """
    ):
        rec = books.setdefault(
            name, {"name": name, "billed": 0.0, "remain": 0.0, "advance": 0.0}
        )
        rec["advance"] = round(rec["advance"] + _money(amount), 2)
    for rec in books.values():
        rec["due"] = rec["remain"] if rec["remain"] > 0.004 else 0.0
        rec["paid"] = round(rec["billed"] - rec["due"], 2)
        rec["ar"] = rec["due"]
        rec["paid_up"] = rec["due"] <= 0.004
        rec["balance_label"] = _label(rec["remain"])
    return books


def totals(books: dict[str, dict]) -> dict:
    billed = round(sum(r["billed"] for r in books.values()), 2)
    ar = round(sum(r["ar"] for r in books.values()), 2)
    advances = round(sum(r["advance"] for r in books.values()), 2)
    paid = round(billed - ar, 2)
    return {
        "source": "dolibarr",
        "url": DOLIBARR_URL,
        "clients": len(books),
        "billed": billed,
        "paid": paid,
        "ar": ar,
        "advances": advances,
        "net": round(ar - advances, 2),
        "as_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> int:
    books = load_books()
    if len(books) != 22:
        raise SystemExit(f"expected 22 Dolibarr clients, got {len(books)}")
    summary = totals(books)
    if abs(summary["billed"] - 321557.76) > 0.02:
        raise SystemExit(f"billed mismatch {summary['billed']}")
    if abs(summary["ar"] - 8903.50) > 0.02:
        raise SystemExit(f"ar mismatch {summary['ar']}")
    if abs(summary["advances"] - 5000.65) > 0.02:
        raise SystemExit(f"advances mismatch {summary['advances']}")

    pack = {
        "books": summary,
        "clients": list(books.values()),
    }
    OUT.write_text(json.dumps(pack, indent=2) + "\n")
    OUT.chmod(0o644)

    print(
        "dolibarr-books",
        f"clients={summary['clients']}",
        f"billed={summary['billed']:.2f}",
        f"paid={summary['paid']:.2f}",
        f"ar={summary['ar']:.2f}",
        f"advances={summary['advances']:.2f}",
        f"net={summary['net']:.2f}",
        "accounts.json=untouched",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
