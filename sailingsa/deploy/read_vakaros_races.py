#!/usr/bin/env python3
"""Read vakaros regatta races finish order data."""
import json

with open("/root/lipton-vakaros-archive/lipton_vakaros_summary.json") as f:
    d = json.load(f)

for race in d.get("races", []):
    rn = race.get("race_number")
    finishes = race.get("finish_order", [])
    print(f"Race {rn}:")
    for i, fin in enumerate(finishes[:17], 1):
        print(f"  {i}. {fin.get('sail_number')}")
    print()
