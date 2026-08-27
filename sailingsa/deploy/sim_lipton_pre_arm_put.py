#!/usr/bin/env python3
"""10:00–12:00: leftover tracker T+ must not gun until race_armed."""
from __future__ import annotations


def pre_arm_block(mins: int, *, race_armed: bool = False, simulate: bool = False) -> bool:
    if simulate or race_armed:
        return False
    return 10 * 60 <= mins < 12 * 60


def put_blocked(mins: int, *, harbour: bool, **kwargs) -> bool:
    return harbour or pre_arm_block(mins, **kwargs)


def main() -> int:
    assert pre_arm_block(9 * 60 + 59) is False  # overnight harbour, not this guard
    assert pre_arm_block(10 * 60) is True
    assert pre_arm_block(11 * 60 + 59) is True
    assert pre_arm_block(12 * 60) is False
    assert pre_arm_block(10 * 60, race_armed=True) is False
    assert pre_arm_block(11 * 60, simulate=True) is False
    assert put_blocked(2 * 60, harbour=True) is True
    assert put_blocked(10 * 60, harbour=False) is True
    assert put_blocked(12 * 60, harbour=False, race_armed=True) is False
    assert put_blocked(12 * 60, harbour=False) is False

    def leftover_active(mins, *, has_gun, phase, complete, simulate=False):
        race_active = has_gun and phase == "racing" and not complete
        if race_active and not simulate and mins < 12 * 60:
            race_active = False
        return race_active

    assert leftover_active(10 * 60, has_gun=True, phase="racing", complete=False) is False
    assert leftover_active(11 * 60 + 59, has_gun=True, phase="racing", complete=False) is False
    assert leftover_active(12 * 60, has_gun=True, phase="racing", complete=False) is True
    assert leftover_active(10 * 60, has_gun=True, phase="racing", complete=False, simulate=True) is True

    print("PASS pre-arm put block")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
