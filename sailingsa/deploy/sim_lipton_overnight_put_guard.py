#!/usr/bin/env python3
"""Offline: harbour-close window is 17:00–10:00 unless a real gun race is on."""
from __future__ import annotations


def overnight(mins: int, *, gun: bool, phase: str, complete: bool, simulate: bool = False) -> bool:
    if simulate:
        return False
    if not (mins >= 17 * 60 or mins < 10 * 60):
        return False
    if gun and phase == "racing" and not complete:
        return False
    return True


def main() -> int:
    assert overnight(17 * 60, gun=False, phase="finished", complete=True) is True
    assert overnight(19 * 60, gun=False, phase="idle", complete=True) is True
    assert overnight(9 * 60 + 59, gun=False, phase="finished", complete=True) is True
    assert overnight(10 * 60, gun=False, phase="idle", complete=False) is False
    assert overnight(12 * 60, gun=False, phase="idle", complete=False) is False
    assert overnight(16 * 60 + 59, gun=False, phase="idle", complete=False) is False
    # Real race past 17:00 must not be killed.
    assert overnight(17 * 60 + 10, gun=True, phase="racing", complete=False) is False
    assert overnight(18 * 60, gun=True, phase="racing", complete=True) is True
    assert overnight(18 * 60, simulate=True, gun=False, phase="racing", complete=False) is False
    print("PASS overnight put guard window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
