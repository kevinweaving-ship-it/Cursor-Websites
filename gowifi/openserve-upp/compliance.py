#!/usr/bin/env python3
"""ICASA ECS/ECNS 2026 inspection checklist for GoWifi (Pty) Ltd.

Chris Erasmus (Western Cape) asked for the ECS/ECNS Compliance checklist
back. Forms and supporting documents go to EcsEcns.Compliance@icasa.org.za.
This module fills what we already know and leaves blanks we must not invent
(licence numbers, prior filings, FYE, type-approval certificates, GPS).
"""
from __future__ import annotations

from datetime import date

from company import COMPANY
from site_lines import INCOMING_FIBRE, incoming_fibre_for_export, apply_site_line, pop_cost

INSPECTOR = {
    "name": "Chris Erasmus",
    "title": "Technical Officer · Regions: Western Cape",
    "phone": "021 561 6815",
    "email": "cerasmus@icasa.org.za",
    "forms_email": "EcsEcns.Compliance@icasa.org.za",
    "office": (
        "Ground Floor, Knowledge Park III, Heron Crescent, Century City, Cape Town"
    ),
    "postal": "PostNet Suite #102, Private Bag X18, Milnerton, 7435",
}

CYCLE = "2026"
SOURCE = "Inspection form 2026.pdf · Chris Erasmus · Western Cape"


def _ready(item_id: str, ask: str, answer, note: str = "") -> dict:
    return {"id": item_id, "ask": ask, "answer": answer, "status": "ready", "note": note}


def _out(item_id: str, ask: str, answer=None, note: str = "") -> dict:
    return {
        "id": item_id,
        "ask": ask,
        "answer": answer,
        "status": "outstanding",
        "note": note,
    }


def _na(item_id: str, ask: str, note: str) -> dict:
    return {"id": item_id, "ask": ask, "answer": "N/A", "status": "n/a", "note": note}


def licensee() -> dict:
    lines = COMPANY["lines"]
    street = ", ".join(lines)
    return {
        "name": COMPANY["name"],
        "reg": COMPANY["reg"],
        "representative": COMPANY.get("representative") or "Kevin Weaving",
        "phone": COMPANY["phone"],
        "email": COMPANY["email"],
        "physical": street,
        "postal": COMPANY.get("postal") or street,
        "vat_registered": False,
    }


def network() -> dict:
    fibres = incoming_fibre_for_export(
        [
            apply_site_line({"service_number": sn, "customer": spec["legal_name"]})
            for sn, spec in INCOMING_FIBRE.items()
        ]
    )
    pop = pop_cost(fibres)
    return {
        "type": "Wireless last-mile (self-provide) + leased Openserve fibre backhaul",
        "self_provide": True,
        "lease_backhaul": True,
        "lease_from": "Openserve",
        "optic_fibre": True,
        "fibre_capacity": "Primary Webstream 500/250 + failover Office Connect 300/150",
        "fibre_lines": [
            {
                "service_number": r.get("service_number"),
                "role": r.get("incoming_label"),
                "sku": r.get("sku"),
                "speed": r.get("speed"),
                "cost": r.get("cost"),
            }
            for r in fibres
        ],
        "pop_cost": pop["cost"],
        "sites_owned": [
            {
                "name": "VK Pop",
                "address": "21 4th Avenue, Voelklip, Western Cape 7200",
                "gps": None,
            }
        ],
        "licence_exempt_spectrum": True,
        "wireless_coverage": True,
        "microwave_backhaul": None,
        "spectrum_licence": None,
    }


def items() -> list[dict]:
    who = licensee()
    net = network()
    return [
        _ready("LI1", "Name of Licensee", who["name"], f"CIPC {who['reg']}"),
        _out(
            "LI2",
            "Type and number of Licenses",
            None,
            "Chris treats us as ECS/ECNS. Confirm Class vs Individual from the licence copies. Do not tick I-ECS / I-ECNS without those copies.",
        ),
        _out(
            "LI3",
            "Licence Numbers",
            None,
            "Need the C-ECS / C-ECNS (or I-) numbers off the licence documents. Not on the box.",
        ),
        _ready("LI4", "Physical Address", who["physical"]),
        _out(
            "LI5",
            "Has above address changed",
            None,
            "Current letterhead is 21 4th Avenue, Voelklip. Confirm against the address on the licence.",
        ),
        _out("LI6", "Did Licensee Notify ICASA of address change", None, "Only if LI5 is yes."),
        _ready("LI7", "Postal Address", who["postal"], "Same as physical until a PO Box is given."),
        _out("LI8", "Has postal address changed", None, "Confirm against the licence."),
        _out("LI9", "Did Licensee Notify ICASA of postal change", None, "Only if LI8 is yes."),
        _out(
            "LI10",
            "Has contact details changed",
            None,
            f"Current: {who['representative']} · {who['phone']} · {who['email']}. Confirm against ICASA's file.",
        ),
        _out(
            "LI11",
            "Did shareholding on the Licence change",
            None,
            "Books have loan accounts Kevin Weaving 33% and Walter Esterhuizen 33%. That is not the licence share register. Need the CIPC / licence shareholding.",
        ),
        _ready(
            "LI12",
            "Is Licensee operational",
            "Yes",
            "Live wireless and fibre clients. VK Pop incoming fibre active.",
        ),
        _out(
            "LI13",
            "If yes, commencement date",
            "On or after 27 Jul 2020",
            "First FNB on the books 27 Jul 2020. Confirm the licence commencement / first service date.",
        ),
        _na("LI14", "If not operational, did licensee apply for extension", "We are operational."),
        _na("LI15", "If yes, when was request for extension made", "We are operational."),
        _out(
            "CS1",
            "Compliance submissions & reporting",
            None,
            "Need the pack already sent (if any) vs still outstanding. Chris asked for this checklist for tracking.",
        ),
        _out(
            "CS2",
            "Licensee Financial Year End",
            None,
            "Not on the box. Licence-fee and USAF due dates are FYE + 6 months.",
        ),
        _out(
            "CS3",
            "Did licensee submit the following",
            None,
            "Tick each form below only from filed copies or ICASA receipts.",
        ),
        _out("CS4", "Annual Financial Statements", None, "Send with the forms pack when the accountant has them."),
        _out(
            "CS5",
            "Pay Annual Licence Fees (service licence)",
            None,
            "General licence fee on licensed-service turnover. Due FYE + 6 months.",
        ),
        _out(
            "CS6",
            "Contribute / Pay USAF",
            None,
            "0.2% of annual turnover unless a deduction applies. Due FYE + 6 months.",
        ),
        _out(
            "CS7",
            "Form 1: Standard Terms & Conditions",
            None,
            "Annual. ICASA year — due 31 March.",
        ),
        _out(
            "CS8",
            "Submit Annual Licence Fees & USAF Calculation",
            None,
            "Form 2 / calculation with the payments. FYE + 6 months.",
        ),
        _out(
            "CS9",
            "Form 3: Universal Service & Access Obligations",
            None,
            "Only if the licence has a USAO. Else file a nil / N/A once we have the licence.",
        ),
        _out(
            "CS10",
            "Form 4: e-rate",
            None,
            "Only if we give e-rate to schools. Else a nil return. Due 31 Mar / 30 Sep.",
        ),
        _out(
            "CS11",
            "Form 5: Tariff",
            None,
            "Retail card is on the dash (no VAT). File 30 Apr / 31 Oct once FYE is known.",
        ),
        _out(
            "CS12",
            "Form 6A: Electronic Communications (sectoral planning)",
            None,
            "Quarterly: 31 Jan, 30 Apr, 31 Jul, 31 Oct.",
        ),
        _out(
            "CS13",
            "Form 7A: Code of Conduct for ECS & ECNS",
            None,
            "Twice a year: FYE and FYE + 6 months.",
        ),
        _out(
            "CS14",
            "Form 12A: ECN/S Complaints Reporting",
            None,
            "Twice a year: FYE + 1 month and FYE + 7 months. Nil if no complaints.",
        ),
        _ready("LN1", "Type of network operated", net["type"]),
        _ready("LN2", "Does Licensee self provide", "Yes", "Wireless last-mile on UISP."),
        _ready("LN3", "Does Licensee lease backhaul", "Yes"),
        _ready("LN4", "From whom does Licensee lease backhaul", net["lease_from"]),
        _out(
            "LN5",
            "Lease backhaul from Other",
            "Openserve Webstream + Office Connect at VK Pop",
            "Primary B110033875 500/250, failover B110034814 300/150.",
        ),
        _out(
            "LN6",
            "Did Licensee sign a Lease agreement",
            "Yes — Openserve UPP",
            "Attach the Openserve / UPP agreement if ICASA wants LN7.",
        ),
        _out(
            "LN7",
            "Agreement submitted to ICASA",
            None,
            "Attach the Openserve agreement with the forms pack unless already on file.",
        ),
        _ready("LN8", "Does Licensee use Optic Fibre", "Yes", net["fibre_capacity"]),
        _ready(
            "LN9",
            "What is the capacity",
            net["fibre_capacity"],
            f"Monthly Openserve cost R{net['pop_cost']:.2f} incl VAT we pay. Cost of wireless, not a client.",
        ),
        _out(
            "LN10",
            "Does licensee use Microwave for backhaul",
            None,
            "Incoming at VK Pop is fibre. Confirm no microwave hops on UISP.",
        ),
        _out(
            "LN11",
            "Does licensee have Spectrum License for microwave",
            None,
            "Only if LN10 is yes.",
        ),
        _out("LN12", "Provide microwave licence nr", None, "Only if LN11 is yes."),
        _ready(
            "LN13",
            "Does Licensee use Licence Exempt Spectrum",
            "Yes",
            "Wi-Fi last-mile (typically 2.4 / 5 GHz). Confirm bands from UISP.",
        ),
        _ready("LN14", "Does licensee use Spectrum for wireless coverage", "Yes"),
        _out(
            "LN15",
            "Does licensee have Spectrum licence for above",
            None,
            "Exempt use does not need a spectrum licence. If any licensed band is in use, put the number here.",
        ),
        _out("LN16", "Provide spectrum licence nr", None, "Only if LN15 is a licensed band."),
        _out(
            "LN17",
            "Number of Sites / Base stations / Wireless Access Points",
            "At least 1 owned site: VK Pop",
            "Count the rest from UISP (sites, sectors, WAPs).",
        ),
        _ready(
            "LN18",
            "If Licensee does not own any Sites, who owns",
            "We own / operate VK Pop at 21 4th Avenue, Voelklip",
        ),
        _out(
            "LN19",
            "Provide GPS coordinates for sites owned by Licensee",
            None,
            "Need GPS for VK Pop (and any other owned site).",
        ),
        _out("LN20", "GPS Coordinates", None, "Outstanding — do not guess."),
        _ready(
            "TA1",
            "Does licensee have transmitting and receiving electronic equipment",
            "Yes",
            "UISP radios at VK Pop and client CPEs.",
        ),
        _out(
            "TA2",
            "Was equipment type approved by ICASA",
            None,
            "Need the TA certificates for each radio / CPE model.",
        ),
        _out("TA3", "State date of approval", None, "From the TA certificates."),
        _out("TA4", "Provide approval", None, "Attach TA certificates to the forms pack."),
        _out(
            "S1",
            "Spectrum Fees",
            None,
            "Only if we hold a spectrum licence. Exempt Wi-Fi has no annual spectrum fee.",
        ),
        _out("S2", "Did licensee pay spectrum fees", None, "Only if S1 applies."),
        _out(
            "S3",
            "Does licensee comply with spectrum terms & condition",
            None,
            "Yes for exempt use once we confirm bands. Licensed spectrum needs the licence conditions.",
        ),
    ]


def routing() -> dict:
    return {
        "checklist_to": INSPECTOR["email"],
        "checklist_to_name": INSPECTOR["name"],
        "forms_to": INSPECTOR["forms_email"],
        "note": (
            "Return this completed checklist to Chris Erasmus. "
            "Send Compliance Forms and supporting documents to "
            f"{INSPECTOR['forms_email']}."
        ),
    }


def cover_mail() -> dict:
    who = licensee()
    return {
        "to": INSPECTOR["email"],
        "cc": INSPECTOR["forms_email"],
        "subject": f"{who['name']} — ECS/ECNS compliance checklist {CYCLE}",
        "body": (
            f"Good day {INSPECTOR['name'].split()[0]}\n\n"
            f"Please find the ECS/ECNS compliance checklist for {who['name']} "
            f"({who['reg']}).\n\n"
            "Company details on our letterhead:\n"
            f"  {who['name']}\n"
            f"  {who['physical']}\n"
            f"  {who['representative']} · {who['phone']} · {who['email']}\n\n"
            "We are operational. Incoming fibre at VK Pop is Openserve Webstream "
            "500/250 (primary) and Office Connect 300/150 (failover). Wireless "
            "last-mile is self-provided. Those two fibres are backhaul cost, "
            "not clients.\n\n"
            "Licence numbers, financial year-end, prior form filings, type-approval "
            "certificates and site GPS are still being pulled from the licence "
            "file and will follow with the forms pack to "
            f"{INSPECTOR['forms_email']}.\n\n"
            "Regards\n"
            f"{who['representative']}\n"
            f"{who['name']}\n"
            f"{who['phone']}\n"
        ),
    }


def _counts(rows: list[dict]) -> dict:
    out = {"ready": 0, "outstanding": 0, "n/a": 0}
    for row in rows:
        out[row["status"]] = out.get(row["status"], 0) + 1
    out["total"] = len(rows)
    return out


def for_export(as_at: date | None = None) -> dict:
    as_at = as_at or date.today()
    rows = items()
    counts = _counts(rows)
    return {
        "as_at": as_at.isoformat(),
        "cycle": CYCLE,
        "source": SOURCE,
        "inspector": INSPECTOR,
        "licensee": licensee(),
        "network": network(),
        "routing": routing(),
        "cover_mail": cover_mail(),
        "counts": counts,
        "items": rows,
        "note": (
            "Do not invent licence numbers or tick forms as filed. "
            "Ready answers can go on Chris's checklist now. Outstanding "
            "items block a signed return."
        ),
    }


def self_test() -> int:
    failed = 0
    pack = for_export(date(2026, 10, 5))
    ids = [r["id"] for r in pack["items"]]
    if pack["licensee"]["name"] != "GoWifi (Pty) Ltd":
        print("FAIL licensee", pack["licensee"])
        failed += 1
    elif "LI3" not in ids or "CS7" not in ids or "LN9" not in ids:
        print("FAIL form-ids", ids)
        failed += 1
    elif pack["routing"]["checklist_to"] != "cerasmus@icasa.org.za":
        print("FAIL routing", pack["routing"])
        failed += 1
    elif pack["routing"]["forms_to"] != "EcsEcns.Compliance@icasa.org.za":
        print("FAIL forms-to", pack["routing"])
        failed += 1
    else:
        print("OK icasa-routing")
    li3 = next(r for r in pack["items"] if r["id"] == "LI3")
    li12 = next(r for r in pack["items"] if r["id"] == "LI12")
    ln8 = next(r for r in pack["items"] if r["id"] == "LN8")
    if li3["status"] != "outstanding" or li3["answer"] is not None:
        print("FAIL no-invented-licence", li3)
        failed += 1
    elif li12["answer"] != "Yes" or ln8["answer"] != "Yes":
        print("FAIL operational-fibre", li12, ln8)
        failed += 1
    elif pack["counts"]["outstanding"] < 1 or pack["counts"]["ready"] < 1:
        print("FAIL counts", pack["counts"])
        failed += 1
    elif "B110033875" not in str(pack["network"]["fibre_lines"]):
        print("FAIL pop-on-network", pack["network"])
        failed += 1
    else:
        print("OK icasa-checklist")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
