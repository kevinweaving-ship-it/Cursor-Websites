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
        "sku": "OWS500M",
        "cost_of": "wireless",
    },
    "B110034814": {
        "display_name": "GoWiFi · VK Pop",
        "role": "failover",
        "role_label": "Failover incoming fibre",
        "uisp_site": "VK Pop",
        "legal_name": "Kevin Weaving",
        "sku": "OOCF300M",
        "cost_of": "wireless",
    },
}

ROLE_ORDER = {"primary": 0, "failover": 1}


def spec_for(service_number: str | None) -> dict | None:
    return INCOMING_FIBRE.get((service_number or "").strip())


def is_incoming(service_number: str | None = None, row: dict | None = None) -> bool:
    if row and row.get("incoming_role"):
        return True
    return spec_for(service_number or (row or {}).get("service_number")) is not None


def apply_site_line(row: dict) -> dict:
    spec = spec_for(row.get("service_number"))
    if not spec:
        return row
    row["legal_customer"] = row.get("customer")
    row["customer"] = spec["display_name"]
    row["incoming_role"] = spec["role"]
    row["incoming_label"] = spec["role_label"]
    row["uisp_site"] = spec["uisp_site"]
    row["sku"] = spec.get("sku")
    row["cost_of"] = spec.get("cost_of")
    row["appears_on"] = ["pop", "uisp"]
    row["not_a_client"] = True
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
    out = []
    for r in chosen:
        pkg = None
        try:
            from packages import by_sku

            pkg = by_sku(r.get("sku"))
        except Exception:
            pkg = None
        out.append(
            {
                "service_number": r.get("service_number"),
                "customer": r.get("customer"),
                "legal_customer": r.get("legal_customer"),
                "incoming_role": r.get("incoming_role"),
                "incoming_label": r.get("incoming_label"),
                "uisp_site": r.get("uisp_site"),
                "product": r.get("product"),
                "speed": r.get("speed") or (pkg or {}).get("speed"),
                "line_status": r.get("line_status"),
                "address": r.get("address"),
                "appears_on": r.get("appears_on") or ["pop", "uisp"],
                "not_a_client": True,
                "cost_of": r.get("cost_of") or "wireless",
                "sku": r.get("sku"),
                "cost": (pkg or {}).get("cost"),
                "retail": None,
                "story_label": r.get("story_label"),
                "change_bits": r.get("change_bits"),
                "months": r.get("months"),
                "months_label": r.get("months_label"),
                "joined": r.get("joined"),
                "joined_label": r.get("joined_label"),
                "installed": r.get("installed"),
                "installed_label": r.get("installed_label"),
                "activated": r.get("activated"),
                "activated_label": r.get("activated_label"),
                "ordered": r.get("ordered"),
                "ordered_label": r.get("ordered_label"),
                "delay_days": r.get("delay_days"),
                "delay_label": r.get("delay_label"),
                "access_status": r.get("access_status"),
                "partner_status": r.get("partner_status"),
                "fibre_fetched_at": r.get("fibre_fetched_at"),
            }
        )
    return out


def pop_cost(rows: list[dict] | None = None, billed_wireless: float | None = None) -> dict:
    """Monthly cost of the POP lines — recovered from wireless income."""
    lines = rows if rows is not None else incoming_fibre_for_export(
        [apply_site_line({"service_number": sn, "customer": spec["legal_name"]}) for sn, spec in INCOMING_FIBRE.items()]
    )
    cost = round(sum(float(r.get("cost") or 0) for r in lines), 2)
    billed = None if billed_wireless is None else round(float(billed_wireless or 0), 2)
    cover = None if billed is None else round(billed - cost, 2)
    return {
        "cost": cost,
        "lines": len(lines),
        "cost_of": "wireless",
        "billed_wireless": billed,
        "cover": cover,
        "note": (
            "VK Pop incoming fibre is not a client. All info lives on the POP card. "
            "These lines are the backhaul cost that wireless income has to cover."
        ),
    }


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
    elif not primary.get("not_a_client") or primary.get("cost_of") != "wireless":
        print("FAIL not-a-client", primary)
        failed += 1
    elif is_incoming("B110033875") is False or is_incoming("B110047678"):
        print("FAIL is-incoming")
        failed += 1
    else:
        print("OK aliases")
    export = incoming_fibre_for_export([failover, primary])
    ows500 = ooc300 = None
    try:
        from packages import by_sku

        ows500 = by_sku("OWS500M")
        ooc300 = by_sku("OOCF300M")
    except Exception as exc:
        print("FAIL packages", exc)
        failed += 1
    pop = pop_cost(export, billed_wireless=4000)
    want = round(float((ows500 or {}).get("cost") or 0) + float((ooc300 or {}).get("cost") or 0), 2)
    if [r["incoming_role"] for r in export] != ["primary", "failover"]:
        print("FAIL export-order", export)
        failed += 1
    elif incoming_related_label(failover) != "Failover incoming fibre B110034814":
        print("FAIL related", incoming_related_label(failover))
        failed += 1
    elif not export[0].get("not_a_client") or export[0].get("retail") is not None:
        print("FAIL export-not-client", export[0])
        failed += 1
    elif export[0].get("cost") != (ows500 or {}).get("cost"):
        print("FAIL export-cost", export[0], ows500)
        failed += 1
    elif pop["cost"] != want or pop["lines"] != 2 or pop["cost_of"] != "wireless":
        print("FAIL pop-cost", pop, want)
        failed += 1
    elif pop["billed_wireless"] != 4000 or pop["cover"] != round(4000 - want, 2):
        print("FAIL pop-cover", pop, want)
        failed += 1
    else:
        print("OK incoming-export")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
