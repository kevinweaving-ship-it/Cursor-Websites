#!/usr/bin/env python3
"""After 17:00 a completed unapplied race must still apply; after midnight skip."""
from __future__ import annotations


def apply_skip(mins: int, *, complete: bool, applied: bool, harbour: bool) -> bool:
    if not harbour:
        return False
    skip = True
    if mins >= 17 * 60 and complete and not applied:
        skip = False
    return skip


def main() -> int:
    assert apply_skip(2 * 60, complete=True, applied=False, harbour=True) is True
    assert apply_skip(9 * 60 + 59, complete=True, applied=False, harbour=True) is True
    assert apply_skip(17 * 60 + 10, complete=True, applied=False, harbour=True) is False
    assert apply_skip(18 * 60, complete=True, applied=True, harbour=True) is True
    assert apply_skip(17 * 60 + 10, complete=False, applied=False, harbour=True) is True
    assert apply_skip(12 * 60, complete=True, applied=False, harbour=False) is False
    print("PASS apply late-finish skip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
