#!/usr/bin/env python3
"""Extract an ANZAM SHRS final standings table and verify its scoring checksum."""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from bs4 import BeautifulSoup


HEADER = ["Place", "Sail No", "Skipper", "Nat", "Total", "Disc", "Final"]
SCORE = re.compile(r"(?:(?P<code>[A-Z]+)\s+)?(?P<points>\d+(?:\.\d+)?)")
PLACE = re.compile(r"([A-Z])\s+(\d+)")
COLOUR = re.compile(r"\.([\w-]+)\s*\{[^}]*background-color\s*:\s*(#[\da-f]{6})", re.I)


def parse(raw):
    html = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode()
    doc = BeautifulSoup(html, "html.parser")
    colours = {name: colour.upper() for name, colour in COLOUR.findall(html)}
    race_columns = []
    fleets = []
    seen = set()
    for tr in doc.find_all("tr"):
        cells = tr.find_all(["td", "th"], recursive=False)
        text = [cell.get_text(" ", strip=True) for cell in cells]
        if len(text) < len(HEADER):
            continue
        if text[:len(HEADER)] == HEADER:
            labels = text[len(HEADER):]
            if (race_columns and race_columns != labels) or not labels or any(
                not re.fullmatch(r"[QF]\d+", label) for label in labels
            ) or len(labels) != len(set(labels)):
                raise ValueError("Inconsistent qualifying/finals columns")
            race_columns = labels
            continue
        if not text[0] and text[2].endswith(" FLEET"):
            fleets.append({"label": text[2].title(), "rows": []})
            continue
        if not race_columns or not fleets or not text[0]:
            continue
        place = PLACE.fullmatch(text[0])
        if not place or len(text) != len(HEADER) + len(race_columns):
            raise ValueError(f"Unexpected standings row: {text[:3]}")
        prefix, rank = place.groups()
        fleet = fleets[-1]
        if prefix != fleet["label"][0] or int(rank) != len(fleet["rows"]) + 1:
            raise ValueError(f"Unexpected place {text[0]} in {fleet['label']}")
        nationality, sail_number = text[1].split()
        skipper = text[2].removeprefix("&nbsp").lstrip("\xa0 ")
        identity = nationality, sail_number
        if identity in seen or not skipper:
            raise ValueError(f"Duplicate sail identity or blank skipper: {text[:3]}")
        seen.add(identity)
        total, discards, nett = map(Decimal, text[4:7])
        actual_total = actual_discards = Decimal(0)
        scores = {}
        for label, cell, value in zip(race_columns, cells[len(HEADER):], text[len(HEADER):]):
            if not value:
                scores[label] = None
                continue
            match = SCORE.fullmatch(value)
            if not match:
                raise ValueError(f"Invalid score {value!r} at {text[0]} {label}")
            points = Decimal(match["points"])
            discarded = any(colours.get(name) == "#FFFFB8" for name in cell.get("class", []))
            actual_total += points
            if discarded:
                actual_discards += points
            scores[label] = {"points": str(points), "code": match["code"], "discarded": discarded}
        if (actual_total, actual_discards, total - discards) != (total, discards, nett):
            raise ValueError(
                f"Scoring checksum failed for {fleet['label']} {text[0]}: "
                f"calculated total/discards {actual_total}/{actual_discards}, "
                f"published {total}/{discards}/{nett}"
            )
        fleet["rows"].append({
            "place": text[0], "rank": int(rank), "nationality": nationality,
            "sail_number": sail_number, "skipper": skipper, "scores": scores,
            "total": str(total), "discards": str(discards), "nett": str(nett),
        })
    if not fleets or any(not fleet["rows"] for fleet in fleets):
        raise ValueError("No complete fleet ladders found")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "race_columns": race_columns, "fleets": fleets}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("sheet", type=Path)
    print(json.dumps(parse(cli.parse_args().sheet.read_bytes()), ensure_ascii=False, indent=2))
