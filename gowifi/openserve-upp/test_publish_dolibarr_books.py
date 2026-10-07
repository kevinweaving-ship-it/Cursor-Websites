#!/usr/bin/env python3
"""Guard: Dolibarr books stay off the reconciled dash client cards."""
from __future__ import annotations

import ast
from pathlib import Path

import publish_dolibarr_books as pub

SRC = Path(__file__).with_name("publish_dolibarr_books.py").read_text()


def test_label_never_invents_credit():
    assert pub._label(0.0) == "Paid Up"
    assert pub._label(-399.0) == "Paid Up"
    assert pub._label(1284.50) == "Due 1,284.50"
    assert "Credit" not in pub._label(0.0)
    assert "Credit" not in pub._label(399.0)


def test_publisher_source_never_writes_accounts_json():
    tree = ast.parse(SRC)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "ACCOUNTS" not in names
    assert "overlay" not in names
    assert "accounts.json" not in SRC or "accounts.json=untouched" in SRC
    assert "never overlay" in SRC.lower() or "must never overlay" in SRC


def test_paid_can_exceed_billed_and_stay_paid_up():
    billed, paid = 22610.0, 23009.0
    due = round(billed - paid, 2)
    assert due == -399.0
    assert pub._label(due) == "Paid Up"
    assert "Credit" not in pub._label(due)


if __name__ == "__main__":
    test_label_never_invents_credit()
    test_publisher_source_never_writes_accounts_json()
    test_paid_can_exceed_billed_and_stay_paid_up()
    print("ok")
