#!/usr/bin/env python3
"""GoWiFi-owned Openserve lines that also feed UISP.

Legal UPP customer names stay on the circuit. Display names are ours.
"""
from __future__ import annotations

INCOMING_FIBRE = {
    "B110033875": {
        "display_name": "GoWiFi · VK Pop",
        "role": "primary",
        "role_label": "Primary incoming fibre",
        "uisp_site": "VK Pop",
        "legal_name": "Kevin Weaving",
    },
    "B110034814": {
        "display_name": "GoWiFi · VK Pop",
        "role": "failover",
        "role_label": "Failover incoming fibre",
        "uisp_site": "VK Pop",
        "legal_name": "Kevin Weaving",
    },
}

ROLE_ORDER = {"primary": 0, "failover": 1}


def spec_for(service_number: str | None) -> dict | None:
    return INCOMING_FIBRE.get((service_number or "").strip())


def apply_site_line(row: dict) -> dict:
    spec = spec_for(row.get("service_number"))
    if not spec:
        return row
    row["legal_customer"] = row.get("customer")
    row["customer"] = spec["display_name"]
    row["incoming_role"] = spec["role"]
    row["incoming_label"] = spec["role_label"]
    row["uisp_site"] = spec["uisp_site"]
    row["appears_on"] = ["fibre", "uisp"]
    return row


def incoming_related_label(other: dict) -> str | None:
    if not other.get("incoming_label"):
        return None
    return f"{other['incoming_label']} {other['service_number']}"


def incoming_fibre_for_export(rows: list[dict]) -> list[dict]:
    chosen = [r for r in rows if r.get("incoming_role")]
    chosen.sort(
        key=lambda r: (ROLE_ORDER.get(r.get("incoming_role") or "", 9), r.get("service_number") or "")
    )
    return [
        {
            "service_number": r.get("service_number"),
            "customer": r.get("customer"),
            "legal_customer": r.get("legal_customer"),
            "incoming_role": r.get("incoming_role"),
            "incoming_label": r.get("incoming_label"),
            "uisp_site": r.get("uisp_site"),
            "product": r.get("product"),
            "speed": r.get("speed"),
            "line_status": r.get("line_status"),
            "address": r.get("address"),
            "appears_on": r.get("appears_on") or ["fibre", "uisp"],
        }
        for r in chosen
    ]


def self_test() -> int:
    failed = 0
    primary = apply_site_line(
        {"service_number": "B110033875", "customer": "Kevin Weaving", "speed": "500"}
    )
    failover = apply_site_line(
        {"service_number": "B110034814", "customer": "Kevin Weaving", "speed": "300"}
    )
    stranger = apply_site_line({"service_number": "B110047678", "customer": "HPP Control Rom"})
    if primary["customer"] != "GoWiFi · VK Pop" or primary["incoming_role"] != "primary":
        print("FAIL primary-alias", primary)
        failed += 1
    elif failover["incoming_role"] != "failover":
        print("FAIL failover-alias", failover)
        failed += 1
    elif stranger.get("incoming_role"):
        print("FAIL stranger-alias", stranger)
        failed += 1
    else:
        print("OK aliases")
    export = incoming_fibre_for_export([failover, primary])
    if [r["incoming_role"] for r in export] != ["primary", "failover"]:
        print("FAIL export-order", export)
        failed += 1
    elif incoming_related_label(failover) != "Failover incoming fibre B110034814":
        print("FAIL related", incoming_related_label(failover))
        failed += 1
    else:
        print("OK incoming-export")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
