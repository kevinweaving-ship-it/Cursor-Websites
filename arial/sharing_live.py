"""Sharing-worker health: meter is live even if ingest persist is behind."""
from __future__ import annotations

from typing import Any


def health_says_live(health: dict[str, Any] | None) -> bool:
    if not isinstance(health, dict):
        return False
    if health.get("meterStale") is True:
        return False
    if health.get("meterOnline") is False:
        return False
    if health.get("mqttConnected") is False:
        return False
    return bool(health.get("meterOnline") or health.get("ok"))
