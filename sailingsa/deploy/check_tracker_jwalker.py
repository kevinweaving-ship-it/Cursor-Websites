#!/usr/bin/env python3
"""Check tracker finish positions for J-Walker (RCYC Academy)."""
import json

with open("/root/lipton-vakaros-archive/lipton_vakaros_summary.json") as f:
    d = json.load(f)

print("J-Walker (RCYC Academy) - GPS Tracker Finish Positions:")
print("=" * 60)

for race in d.get("races", []):
    rn = race.get("race_number")
    finishes = race.get("finish_order", [])
    
    # Find RCYC Academy position
    for i, fin in enumerate(finishes, 1):
        if fin.get("sail_number") == "RCYC Academy":
            print(f"  Race {rn:>2}: Finished {i}th (GPS position)")
            break
    else:
        if finishes:
            print(f"  Race {rn:>2}: Not found in finish order")
        else:
            print(f"  Race {rn:>2}: No finish data (race may have been abandoned)")
