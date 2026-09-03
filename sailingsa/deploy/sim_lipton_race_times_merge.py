#!/usr/bin/env python3
"""R6 pending rows must merge with finished R4/R5, not be dropped."""
from __future__ import annotations


def rt_has_fin(rows) -> bool:
    return isinstance(rows, list) and any(
        isinstance(r, dict) and (r.get("place") is not None or r.get("finish_ms") is not None)
        for r in rows
    )


def merge_race_times(prev_rt, cur_rt):
    if not prev_rt:
        return dict(cur_rt or {})
    merged = dict(prev_rt)
    for k, rows in (cur_rt or {}).items():
        if rt_has_fin(rows) or not rt_has_fin(merged.get(k)):
            merged[k] = rows
    return merged


def main() -> int:
    prev = {
        "R4": [{"bow": "26", "place": 4, "finish_ms": 100, "boat_name": "Amtec Racing"}],
        "R5": [{"bow": "26", "place": 1, "finish_ms": 80, "boat_name": "Amtec Racing"}],
    }
    r6_pending = {"R6": [{"bow": "26", "boat_name": "VAKAROS Amtec"}]}
    out = merge_race_times(prev, r6_pending)
    assert set(out) == {"R4", "R5", "R6"}
    assert out["R5"][0]["place"] == 1
    assert out["R6"][0]["boat_name"] == "VAKAROS Amtec"
    assert out["R6"][0].get("place") is None

    # Empty incoming must not wipe finished races.
    out2 = merge_race_times(prev, {})
    assert set(out2) == {"R4", "R5"}
    assert out2["R5"][0]["place"] == 1

    # Empty R5 incoming must not clobber finished R5.
    out3 = merge_race_times(prev, {"R5": []})
    assert out3["R5"][0]["place"] == 1

    # Finished R6 replaces pending and keeps R4/R5.
    out4 = merge_race_times(out, {"R6": [{"bow": "26", "place": 2, "finish_ms": 90}]})
    assert out4["R6"][0]["place"] == 2
    assert out4["R4"][0]["place"] == 4

    # Old bug: no incoming finishes → keep prev only, drop R6.
    old_dropped = prev  # what live did when has_fin was false
    assert "R6" not in old_dropped

    print("PASS race_times merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
