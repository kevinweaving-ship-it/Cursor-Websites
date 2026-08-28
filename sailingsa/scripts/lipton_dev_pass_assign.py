#!/usr/bin/env python3
"""Assign mark passes using fleet time windows.

Sequential "next mark after last hit" mis-labels backmarkers: a late buoy visit
gets stuck as L1-4 when it was really L2-4 / L3-1. Fix: seed passes from the
fleet pack, then for each boat pick the unused rounding nearest the fleet
median time for that pass (same mark), with increasing times only.
"""
from __future__ import annotations

from statistics import median

from lipton_mark_rounding import COURSE_PASSES


def _first_cand(cands: dict, sail: str, mark: str, after: int, before: int):
    return next((c for c in cands[sail].get(str(mark), []) if after < c["ts"] < before), None)


def _commit(mark_passes: list, summary: list | None, spec_id: str, lap: int, mark: int, ranked: list):
    ranked = sorted(ranked, key=lambda r: r["ts_ms"])
    mark_passes.append(
        {
            "id": spec_id,
            "label": f"M{mark}",
            "lap": lap,
            "mark": int(mark),
            "boats": ranked,
        }
    )
    if summary is not None and ranked:
        summary.append({"id": spec_id, "n": len(ranked), "first": ranked[0]["boat"]})


def sequential_seed_passes(
    cands: dict,
    *,
    gun: int,
    finish_ts: dict,
    last_finish: int,
    use_wl: bool,
    min_fleet: int,
) -> list[dict]:
    """Majority-fleet sequential pack — seeds which passes exist and rough times."""
    boat_by = list(cands)
    last_ts = {sail: gun + 60_000 for sail in boat_by}
    mark_passes: list[dict] = []
    summary: list[dict] = []

    if use_wl:
        for lap in (1, 2, 3):
            weather, nxts = [], {}
            for sail in boat_by:
                fin = finish_ts.get(sail, last_finish) - 80_000
                c = _first_cand(cands, sail, "1", last_ts[sail] + 2_000, fin)
                if not c:
                    continue
                weather.append({"boat": sail, "ts_ms": int(c["ts"])})
                nxts[sail] = c["ts"]
            if len(weather) < min_fleet:
                break
            for sail, ts in nxts.items():
                last_ts[sail] = ts
            _commit(mark_passes, summary, f"L{lap}-1", lap, 1, weather)
            leeward, nxts = [], {}
            for sail in boat_by:
                fin = finish_ts.get(sail, last_finish) - 80_000
                opts = []
                for mark in ("3", "4"):
                    c = _first_cand(cands, sail, mark, last_ts[sail] + 2_000, fin)
                    if c:
                        opts.append(c)
                if not opts:
                    continue
                c = min(opts, key=lambda x: x["ts"])
                leeward.append({"boat": sail, "ts_ms": int(c["ts"])})
                nxts[sail] = c["ts"]
            if len(leeward) < min_fleet:
                break
            for sail, ts in nxts.items():
                last_ts[sail] = ts
            _commit(mark_passes, summary, f"L{lap}-3", lap, 3, leeward)
    else:
        for spec in COURSE_PASSES:
            ranked, nxts = [], {}
            for sail in boat_by:
                fin = finish_ts.get(sail, last_finish)
                cutoff = fin - 80_000 if spec["mark"] == "4" else fin
                nxt = _first_cand(cands, sail, spec["mark"], last_ts[sail] + 2_000, cutoff)
                if not nxt:
                    continue
                ranked.append({"boat": sail, "ts_ms": int(nxt["ts"])})
                nxts[sail] = nxt["ts"]
            if len(ranked) < min_fleet:
                continue
            for sail, ts in nxts.items():
                last_ts[sail] = ts
            _commit(mark_passes, summary, spec["id"], spec["lap"], int(spec["mark"]), ranked)
    return mark_passes


def _robust_median(times: list[int]) -> int:
    """Median of the middle half — backmarker outliers must not pull the window."""
    if not times:
        return 0
    s = sorted(times)
    if len(s) < 4:
        return int(median(s))
    lo = len(s) // 4
    hi = max(lo + 1, (3 * len(s) + 3) // 4)
    return int(median(s[lo:hi]))


def _mark_options(mark: int, use_wl: bool) -> list[str]:
    if use_wl and int(mark) == 3:
        return ["3", "4"]
    return [str(mark)]


def realign_passes_to_fleet_windows(
    cands: dict,
    seed_passes: list[dict],
    *,
    gun: int,
    finish_ts: dict,
    last_finish: int,
    use_wl: bool,
    window_before_ms: int = 10 * 60_000,
    window_after_ms: int = 40 * 60_000,
    max_skew_ms: int = 20 * 60_000,
) -> list[dict]:
    """Reassign every boat to each seeded pass by fleet-median time + same mark.

    A hit 30 minutes late is not kept on an early pass label — it stays free for
    the later lap pass whose fleet window it actually matches (FBYC R2 case).
    """
    boat_by = list(cands)
    last_ts = {sail: gun + 60_000 for sail in boat_by}
    used_ts: dict[str, set[int]] = {sail: set() for sail in boat_by}
    out: list[dict] = []

    seed_meds = []
    for p in seed_passes:
        times = [int(b["ts_ms"]) for b in (p.get("boats") or []) if b.get("ts_ms") is not None]
        seed_meds.append(_robust_median(times) if times else gun)

    for i, seed in enumerate(seed_passes):
        med = seed_meds[i]
        next_med = seed_meds[i + 1] if i + 1 < len(seed_meds) else None
        win_lo = med - window_before_ms
        win_hi = med + window_after_ms
        if next_med is not None:
            # Don't steal the next lap's cluster.
            win_hi = min(win_hi, (med + next_med) // 2 + 60_000)
        marks = _mark_options(int(seed["mark"]), use_wl)
        ranked = []
        nxts = {}
        for sail in boat_by:
            fin = finish_ts.get(sail, last_finish) - 80_000
            opts = []
            for mk in marks:
                for c in cands[sail].get(mk, []) or []:
                    ts = int(c["ts"])
                    if ts in used_ts[sail]:
                        continue
                    # Allow same-second gate (M3 then M4): only require non-decreasing time.
                    if not (last_ts[sail] <= ts < fin):
                        continue
                    opts.append(c)
            if not opts:
                continue
            in_win = [c for c in opts if win_lo <= c["ts"] <= win_hi]
            pool = in_win
            if not pool:
                # Allow closest overall only if still near the fleet median.
                closest = min(opts, key=lambda c: abs(c["ts"] - med))
                if abs(closest["ts"] - med) <= max_skew_ms:
                    pool = [closest]
            if not pool:
                continue
            pick = min(pool, key=lambda c: abs(c["ts"] - med))
            # Reject if still absurdly far from fleet (keeps late hit for later pass).
            if abs(pick["ts"] - med) > max_skew_ms and not in_win:
                continue
            if in_win and abs(pick["ts"] - med) > window_after_ms:
                continue
            ranked.append({"boat": sail, "ts_ms": int(pick["ts"])})
            nxts[sail] = int(pick["ts"])
            used_ts[sail].add(int(pick["ts"]))
        if len(ranked) < max(8, (len(boat_by) + 1) // 2):
            # Keep seed pass if realign too sparse (shouldn't drop a sailed mark).
            ranked = [{"boat": b["boat"], "ts_ms": int(b["ts_ms"])} for b in seed.get("boats") or []]
            for b in ranked:
                last_ts[b["boat"]] = max(last_ts.get(b["boat"], gun), b["ts_ms"])
                used_ts[b["boat"]].add(b["ts_ms"])
        else:
            for sail, ts in nxts.items():
                last_ts[sail] = ts
        _commit(out, None, seed["id"], int(seed["lap"]), int(seed["mark"]), ranked)
    return out


def pack_passes_with_fleet_windows(
    cands: dict,
    *,
    gun: int,
    finish_ts: dict,
    last_finish: int,
    use_wl: bool,
    min_fleet: int | None = None,
) -> list[dict]:
    boat_n = len(cands)
    if min_fleet is None:
        min_fleet = max(12, (boat_n * 3 + 3) // 4) if boat_n else 8
    seed = sequential_seed_passes(
        cands,
        gun=gun,
        finish_ts=finish_ts,
        last_finish=last_finish,
        use_wl=use_wl,
        min_fleet=min_fleet,
    )
    if not seed:
        return []
    return realign_passes_to_fleet_windows(
        cands,
        seed,
        gun=gun,
        finish_ts=finish_ts,
        last_finish=last_finish,
        use_wl=use_wl,
    )
