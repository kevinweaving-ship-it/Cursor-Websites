#!/usr/bin/env python3
"""Infer cancel / redo / move / cease from orders. Do not ask."""
from __future__ import annotations

import re

DROP = {"new", "the", "and"}
SYNONYM = {"rom": "room"}
TOWN = {
    "western",
    "cape",
    "hermanus",
    "onrus",
    "river",
    "voelklip",
    "sandbaai",
    "vermont",
    "noordhoek",
}


def tidy_customer(name: str | None) -> str:
    text = re.sub(r"\s+", " ", (name or "").strip())
    if not text:
        return "—"
    text = re.sub(r"\bRom\b", "Room", text, flags=re.I)
    text = re.sub(r"\s+New$", "", text, flags=re.I)
    return text


def name_tokens(name: str | None) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    out = []
    for word in words:
        word = SYNONYM.get(word, word)
        if word not in DROP:
            out.append(word)
    return out


def name_key(name: str | None) -> str:
    return " ".join(name_tokens(name)[:3])


def _lev(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _close_word(a: str, b: str) -> bool:
    if a == b:
        return True
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True
    return min(len(a), len(b)) >= 6 and _lev(a, b) <= 1


def names_match(a: str | None, b: str | None) -> bool:
    if name_key(a) and name_key(a) == name_key(b):
        return True
    left, right = name_tokens(a), name_tokens(b)
    if len(left) >= 2 and len(right) >= 2 and left[-1] == right[-1]:
        return _close_word(left[0], right[0])
    return False


def addr_key(addr: str | None) -> str:
    words = [w for w in re.findall(r"[a-z0-9]+", (addr or "").lower()) if w not in TOWN]
    return " ".join(words)


def addrs_differ(a: str | None, b: str | None) -> bool:
    left, right = addr_key(a), addr_key(b)
    if not left or not right:
        return False
    return left != right


def short_addr(addr: str | None) -> str:
    parts = [p.strip() for p in re.sub(r"\s+", " ", (addr or "").strip()).split(",") if p.strip()]
    for part in parts:
        if re.search(r"\b(rd|st|av|ave|dr|ln|cl|ct|street|road)\b", part, re.I):
            return part[:48]
    return parts[0][:48] if parts else ""


def was_live_client(row: dict) -> bool:
    if row.get("never_installed"):
        return False
    return bool(row.get("installed") or row.get("joined") or row.get("activated"))


def _peer(peers: list[dict], row: dict, want: str) -> dict | None:
    for other in peers or []:
        if other.get("service_number") == row.get("service_number"):
            continue
        if want == "replacement" and row.get("line_status") == "cancelled" and other.get(
            "line_status"
        ) in {"active", "suspended"}:
            return other
        if want == "prior" and row.get("line_status") in {"active", "suspended"} and other.get(
            "line_status"
        ) == "cancelled":
            return other
    return None


def classify(row: dict, peers: list[dict] | None = None) -> dict:
    """redo = address/order error, then the next order is the install (same client).
    move = was a live client, cancelled, later new order at another house.
    cease = cancelled, no later order from us (end of account).
    live = current line, not a cancel story.
    """
    peers = peers or []
    replacement = _peer(peers, row, "replacement")
    prior = _peer(peers, row, "prior")
    status = row.get("line_status")

    if status == "cancelled" and replacement:
        if was_live_client(row) and addrs_differ(row.get("address"), replacement.get("address")):
            kind = "move"
        elif was_live_client(row):
            kind = "reorder"
        else:
            kind = "redo"
        return _pack(kind, row, peer=replacement, prior=None)
    if status == "cancelled":
        return _pack("cease", row, peer=None, prior=None)
    if prior:
        if not was_live_client(prior):
            return _pack("redo", row, peer=None, prior=prior)
        if addrs_differ(prior.get("address"), row.get("address")):
            return _pack("move", row, peer=None, prior=prior)
        return _pack("live", row, peer=None, prior=prior)
    return _pack("live", row, peer=None, prior=None)


def _pack(kind: str, row: dict, peer: dict | None, prior: dict | None) -> dict:
    return {
        "kind": kind,
        "peer": peer,
        "prior": prior,
        "related_label": related_label(kind, row, peer, prior),
        "headline": headline(kind, row, peer, prior),
    }


def related_label(kind: str, row: dict, peer: dict | None, prior: dict | None) -> str | None:
    other = peer or prior
    if not other:
        if kind == "cease":
            return "no new order · end of account"
        return None
    sn = other.get("service_number") or "—"
    there = short_addr(other.get("address"))
    if kind == "redo":
        if row.get("line_status") == "cancelled":
            extra = f" at {there}" if there else ""
            return f"address error · same client re-ordered as {sn}{extra}"
        return f"this is the install · same client after address error {sn}"
    if kind == "move":
        if row.get("line_status") == "cancelled":
            extra = f" at {there}" if there else ""
            return f"moved house · new order {sn}{extra}"
        here = short_addr(row.get("address"))
        extra = f" at {here}" if here else ""
        return f"new house{extra} after {sn} cancelled"
    if kind == "reorder":
        return f"same house re-order {sn}"
    return None


def headline(kind: str, row: dict, peer: dict | None, prior: dict | None) -> str:
    other = peer or prior
    if kind == "redo" and row.get("never_installed"):
        here = short_addr(row.get("address"))
        bits = ["Never installed", f"address was wrong{f' ({here})' if here else ''}"]
        if other:
            extra = f"same client re-ordered as {other.get('service_number')}"
            there = short_addr(other.get("address"))
            if there:
                extra += f" at {there}"
            extra += " · that order is the install"
            if other.get("installed_label") and other["installed_label"] != "—":
                extra += f" ({other['installed_label']}"
                if other.get("delay_label") and other["delay_label"] not in {"—", "0 days"}:
                    extra += f", {other['delay_label']} delay"
                extra += ")"
            bits.append(extra)
        if row.get("cancelled_label"):
            bits.append(f"Cancelled {row['cancelled_label']}")
        return " · ".join(bits)
    if kind == "redo":
        sn = (prior or {}).get("service_number") or "—"
        return f"Same client · this is the install after the wrong-address order {sn} was cancelled"
    if kind == "move" and row.get("line_status") == "cancelled":
        bits = []
        if row.get("months_label") and row["months_label"] != "—":
            bits.append(f"Was a client {row['months_label']}")
        here = short_addr(row.get("address"))
        if here:
            bits.append(f"at {here}")
        bits.append("cancelled")
        if other:
            extra = f"new order {other.get('service_number')}"
            there = short_addr(other.get("address"))
            if there:
                extra += f" at {there}"
            extra += " · new house, not a redo of the first install"
            bits.append(extra)
        return " · ".join(bits)
    if kind == "move":
        sn = (prior or {}).get("service_number") or "—"
        here = short_addr(row.get("address"))
        extra = f" at {here}" if here else ""
        return f"New house{extra} · same client after {sn} was cancelled · not a redo"
    if kind == "cease":
        bits = []
        if row.get("never_installed"):
            bits.append("Never installed")
            reason = row.get("cancel_reason") or ""
            if "unverified" in reason:
                note = row.get("ua_note")
                bits.append("unverified address" + (f" ({note})" if note else ""))
            if "handover" in reason:
                bits.append("then cancelled before Openserve handover")
            elif reason and "unverified" not in reason:
                bits.append(reason)
        elif row.get("months_label") and row["months_label"] != "—":
            bits.append(f"Was a client {row['months_label']}")
        if row.get("cancelled_label"):
            bits.append(f"Cancelled {row['cancelled_label']}")
        else:
            bits.append("cancelled")
        bits.append("no new order · end of account")
        return " · ".join(bits)
    return ""


def cluster_by_client(rows: list[dict]) -> list[list[dict]]:
    groups: list[list[dict]] = []
    for row in rows:
        for group in groups:
            if names_match(group[0].get("customer"), row.get("customer")):
                group.append(row)
                break
        else:
            groups.append([row])
    return groups


def same_house_reorder_bit(cancelled_product: str | None) -> str:
    prod = (cancelled_product or "order").replace("OPENSERVE ", "").title()
    return f"Same address · earlier {prod} order cancelled · this order is the install"


def self_test() -> int:
    failed = 0

    def check(name, got, want):
        nonlocal failed
        if got != want:
            print(f"FAIL {name}: {got!r} != {want!r}")
            failed += 1
        else:
            print("OK", name)

    check("hpp-name", names_match("HPP  Control Rom", "HPP  Control Room New"), True)
    check("aman-name", names_match("Aman  Breedt", "Aman Breedt"), True)
    check("collette-name", names_match("Collette Brink", "Colllette  Brink"), True)
    check("breedt-not-same", names_match("Herman Breedt", "Aman Breedt"), False)
    check("addr-mussel", addrs_differ("3 MUSSEL RD HERMANUS", "10323 MUSSEL RD HERMANUS"), True)
    check("addr-same", addrs_differ("3 JAN VAN RIEBEECK CT SANDBAAI", "3 JAN VAN RIEBEECK CT SANDBAAI ONRUS"), False)

    hpp_old = {
        "service_number": "B110047675",
        "customer": "HPP Control Room",
        "address": "3 MUSSEL RD HERMANUS HERMANUS, WESTERN CAPE",
        "line_status": "cancelled",
        "never_installed": True,
        "cancelled_label": "22 Sep 2025",
    }
    hpp_new = {
        "service_number": "B110047678",
        "customer": "HPP Control Room",
        "address": "10323 MUSSEL RD HERMANUS HERMANUS, WESTERN CAPE",
        "line_status": "active",
        "never_installed": False,
        "installed": "2025-10-08",
        "installed_label": "08 Oct 2025",
        "delay_label": "19 days",
    }
    redo_old = classify(hpp_old, [hpp_new])
    redo_new = classify(hpp_new, [hpp_old])
    check("hpp-old-kind", redo_old["kind"], "redo")
    check("hpp-new-kind", redo_new["kind"], "redo")
    check("hpp-not-move", "moved" in (redo_old["headline"] + redo_new["headline"]).lower(), False)
    check("hpp-is-install", "that order is the install" in redo_old["headline"], True)

    aljo = {
        "service_number": "B110040916",
        "customer": "Aljo van Vreden",
        "address": "17A TURTLE CL,VERMONT,ONRUS RIVER",
        "line_status": "cancelled",
        "never_installed": False,
        "installed": "2025-08-03",
        "joined": "2025-08-03",
        "months_label": "1 yr 2 mo",
    }
    cease = classify(aljo, [])
    check("aljo-kind", cease["kind"], "cease")
    check("aljo-end", "end of account" in cease["headline"], True)
    check("aljo-no-new", "no new order" in cease["headline"], True)

    herman = {
        "service_number": "B110039414",
        "customer": "Herman Breedt",
        "address": "7 PATERSON ST HERMANUS",
        "line_status": "cancelled",
        "never_installed": False,
        "installed": "2025-01-29",
        "joined": "2025-01-29",
        "months_label": "1 yr 8 mo",
    }
    check("herman-kind", classify(herman, [])["kind"], "cease")

    moved_old = {
        "service_number": "B1",
        "customer": "Pat Client",
        "address": "10 OLD RD HERMANUS",
        "line_status": "cancelled",
        "never_installed": False,
        "installed": "2024-01-01",
        "joined": "2024-01-01",
        "months_label": "8 mo",
    }
    moved_new = {
        "service_number": "B2",
        "customer": "Pat Client",
        "address": "99 NEW ST VOELKLIP",
        "line_status": "active",
        "never_installed": False,
        "installed": "2025-06-01",
        "joined": "2025-06-01",
    }
    move_old = classify(moved_old, [moved_new])
    move_new = classify(moved_new, [moved_old])
    check("move-old-kind", move_old["kind"], "move")
    check("move-new-kind", move_new["kind"], "move")
    check("move-not-redo", "wrong-address" in move_old["headline"] or "address was wrong" in move_old["headline"], False)
    check("move-says-house", "new house" in move_old["headline"], True)

    check("tidy-hpp", tidy_customer("HPP  Control Rom"), "HPP Control Room")
    check("tidy-hpp-new", tidy_customer("HPP  Control Room New"), "HPP Control Room")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
