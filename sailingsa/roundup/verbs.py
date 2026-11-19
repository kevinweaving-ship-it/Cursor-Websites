"""R4 status-aware verbs and margin language."""

from __future__ import annotations


def status_verb(status: str) -> str:
    mapping = {
        "provisional": "leads",
        "partial": "leads",
        "final": "won",
        "series_final": "won",
        "under_review": "results under review",
        "awaiting": "awaiting results",
        "unknown": "recorded",
    }
    return mapping.get(status, "recorded")


def dominated(winner: dict, runner_up: dict | None, races_sailed: int | None) -> bool:
    if not runner_up or winner.get("nett") is None or runner_up.get("nett") is None:
        return False
    try:
        margin = float(runner_up["nett"]) - float(winner["nett"])
        winner_nett = float(winner["nett"])
    except (TypeError, ValueError):
        return False
    wide = margin >= 5 or (winner_nett > 0 and margin >= 0.2 * winner_nett)
    if not wide:
        return False
    wins = int(winner.get("win_count") or 0)
    if not races_sailed:
        return False
    return wins >= 0.4 * races_sailed


def result_phrase(status: str, winner: dict | None, runner_up: dict | None, races_sailed: int | None) -> str:
    if status == "under_review":
        return "results under review"
    if status == "awaiting":
        return "awaiting results"
    if not winner:
        return status_verb(status)
    if runner_up and winner.get("nett") is not None and runner_up.get("nett") is not None:
        try:
            if float(winner["nett"]) == float(runner_up["nett"]):
                return "on countback"
        except (TypeError, ValueError):
            pass
    if races_sailed and winner.get("win_count") == races_sailed:
        return "swept"
    if dominated(winner, runner_up, races_sailed):
        return "dominated"
    return status_verb(status)
