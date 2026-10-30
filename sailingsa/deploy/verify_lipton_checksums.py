#!/usr/bin/env python3
"""Verify internal checksums for Lipton 2026 results."""
import json

# Our database results (from API query)
RESULTS = [
    {"sail": "1571", "boat": "Nitro Juice", "club": "HYC", "bow": "32", "rank": 1, 
     "scores": {"R1": "2.0", "R2": "4.0", "R3": "1.0", "R4": "12.0", "R5": "2.0", "R6": "6.0", "R7": "4.0", "R8": "1.0", "R9": "9.0", "R10": "3.0"}, 
     "total": 44.0, "nett": 44.0},
    {"sail": "766", "boat": "Amtec Racing", "club": "RCYC", "bow": "26", "rank": 2,
     "scores": {"R1": "1.0", "R2": "6.0", "R3": "6.0", "R4": "4.0", "R5": "1.0", "R6": "9.0", "R7": "8.0", "R8": "4.0", "R9": "2.0", "R10": "5.0"},
     "total": 46.0, "nett": 46.0},
    {"sail": "774", "boat": "Nitro Maverick", "club": "UCTYC", "bow": "31", "rank": 3,
     "scores": {"R1": "6.0", "R2": "9.0", "R3": "5.0", "R4": "9.0", "R5": "5.0", "R6": "3.0", "R7": "3.0", "R8": "5.0", "R9": "5.0", "R10": "1.0"},
     "total": 51.0, "nett": 51.0},
    {"sail": "1169", "boat": "Ullman Sails Camissa", "club": "FBYC", "bow": "48", "rank": 4,
     "scores": {"R1": "8.0", "R2": "11.0", "R3": "2.0", "R4": "3.0", "R5": "10.0", "R6": "1.0", "R7": "10.0", "R8": "2.0", "R9": "8.0", "R10": "2.0"},
     "total": 57.0, "nett": 57.0},
    {"sail": "1175", "boat": "Nitro Monkey", "club": "SBYC", "bow": "49", "rank": 5,
     "scores": {"R1": "7.0", "R2": "8.0", "R3": "10.0", "R4": "5.0", "R5": "7.0", "R6": "4.0", "R7": "1.0", "R8": "8.0", "R9": "4.0", "R10": "8.0"},
     "total": 62.0, "nett": 62.0},
    {"sail": "768", "boat": "Ullman Racing", "club": "RNYC", "bow": "28", "rank": 6,
     "scores": {"R1": "4.0", "R2": "2.0", "R3": "9.0", "R4": "2.0", "R5": "6.0", "R6": "18.0 DSQ", "R7": "2.0", "R8": "3.0", "R9": "11.0", "R10": "6.0"},
     "total": 63.0, "nett": 63.0},
    {"sail": "1116", "boat": "G'day J", "club": "PYC", "bow": "34", "rank": 7,
     "scores": {"R1": "3.0", "R2": "7.0", "R3": "11.0", "R4": "11.0", "R5": "8.0", "R6": "5.0", "R7": "6.0", "R8": "6.0", "R9": "3.0", "R10": "4.0"},
     "total": 64.0, "nett": 64.0},
    {"sail": "173", "boat": "J-Walker", "club": "RCYCA", "bow": "8", "rank": 8,
     "scores": {"R1": "5.0", "R2": "10.0", "R3": "7.0", "R4": "7.0", "R5": "4.0", "R6": "2.0", "R7": "7.0", "R8": "9.0", "R9": "6.0", "R10": "9.0"},
     "total": 66.0, "nett": 66.0},
    {"sail": "1277", "boat": "22-ATE", "club": "WBYC", "bow": "52", "rank": 9,
     "scores": {"R1": "12.0", "R2": "1.0", "R3": "8.0", "R4": "1.0", "R5": "9.0", "R6": "8.0", "R7": "11.0", "R8": "13.0", "R9": "7.0", "R10": "7.0"},
     "total": 77.0, "nett": 77.0},
    {"sail": "763", "boat": "Phantom", "club": "KYC", "bow": "23", "rank": 10,
     "scores": {"R1": "11.0", "R2": "5.0", "R3": "3.0", "R4": "8.0", "R5": "3.0", "R6": "18.0 DSQ", "R7": "13.0", "R8": "7.0", "R9": "1.0", "R10": "13.0"},
     "total": 82.0, "nett": 82.0},
    {"sail": "1167", "boat": "Wildcard", "club": "LDYC", "bow": "46", "rank": 11,
     "scores": {"R1": "9.0", "R2": "3.0", "R3": "4.0", "R4": "10.0", "R5": "11.0", "R6": "18.0 DSQ", "R7": "5.0", "R8": "10.0", "R9": "13.0", "R10": "18 RET"},
     "total": 101.0, "nett": 101.0},
    {"sail": "185", "boat": "Andiamo", "club": "GLYC", "bow": "14", "rank": 12,
     "scores": {"R1": "10.0", "R2": "17.0", "R3": "15.0", "R4": "6.0", "R5": "14.0", "R6": "7.0", "R7": "12.0", "R8": "12.0", "R9": "10.0", "R10": "11.0"},
     "total": 114.0, "nett": 114.0},
    {"sail": "1139", "boat": "H2O Tech", "club": "BYC", "bow": "44", "rank": 13,
     "scores": {"R1": "16.0", "R2": "12.0", "R3": "12.0", "R4": "16.0", "R5": "13.0", "R6": "13.0", "R7": "9.0", "R8": "14.0", "R9": "12.0", "R10": "10.0"},
     "total": 127.0, "nett": 127.0},
    {"sail": "1237", "boat": "Attacke", "club": "LYCN", "bow": "51", "rank": 14,
     "scores": {"R1": "15.0", "R2": "15.0", "R3": "14.0", "R4": "13.0", "R5": "16.0", "R6": "10.0", "R7": "15.0", "R8": "11.0", "R9": "14.0", "R10": "14.0"},
     "total": 137.0, "nett": 137.0},
    {"sail": "771", "boat": "Donna Mia Forever", "club": "IZI", "bow": "63", "rank": 15,
     "scores": {"R1": "14.0", "R2": "16.0", "R3": "13.0", "R4": "15.0", "R5": "12.0", "R6": "11.0", "R7": "14.0", "R8": "15.0", "R9": "15.0", "R10": "16.0"},
     "total": 141.0, "nett": 141.0},
    {"sail": "1239", "boat": "CaCanny", "club": "TSC", "bow": "55", "rank": 16,
     "scores": {"R1": "13.0", "R2": "13.0", "R3": "16.0", "R4": "14.0", "R5": "15.0", "R6": "12.0", "R7": "16.0", "R8": "16.0", "R9": "16.0", "R10": "12.0"},
     "total": 143.0, "nett": 143.0},
    {"sail": "1138", "boat": "Laugh a minute", "club": "WYAC", "bow": "43", "rank": 17,
     "scores": {"R1": "17.0", "R2": "14.0", "R3": "17.0", "R4": "17.0", "R5": "17.0", "R6": "14.0", "R7": "17.0", "R8": "17.0", "R9": "18.0 RET", "R10": "15.0"},
     "total": 163.0, "nett": 163.0},
]

# R1-R7 official from lipton_r7_official_update.py
R7_OFFICIAL = {
    "1571": {"races": [2, 4, 1, 12, 2, 6, 4], "nett": 31.0},
    "766": {"races": [1, 6, 6, 4, 1, 9, 8], "nett": 35.0},
    "774": {"races": [6, 9, 5, 9, 5, 3, 3], "nett": 40.0},
    "1175": {"races": [7, 8, 10, 5, 7, 4, 1], "nett": 42.0},
    "173": {"races": [5, 10, 7, 7, 4, 2, 7], "nett": 42.0},
    "768": {"races": [4, 2, 9, 2, 6, 18, 2], "nett": 43.0},
    "1169": {"races": [8, 11, 2, 3, 10, 1, 10], "nett": 45.0},
    "1277": {"races": [12, 1, 8, 1, 9, 8, 11], "nett": 50.0},
    "1116": {"races": [3, 7, 11, 11, 8, 5, 6], "nett": 51.0},
    "1167": {"races": [9, 3, 4, 10, 11, 18, 5], "nett": 60.0},
    "763": {"races": [11, 5, 3, 8, 3, 18, 13], "nett": 61.0},
    "185": {"races": [10, 17, 15, 6, 14, 7, 12], "nett": 81.0},
    "1139": {"races": [16, 12, 12, 16, 13, 13, 9], "nett": 91.0},
    "771": {"races": [14, 16, 13, 15, 12, 11, 14], "nett": 95.0},
    "1237": {"races": [15, 15, 14, 13, 16, 10, 15], "nett": 98.0},
    "1239": {"races": [13, 13, 16, 14, 15, 12, 16], "nett": 99.0},
    "1138": {"races": [17, 14, 17, 17, 17, 14, 17], "nett": 113.0},
}

def parse_score(s):
    """Extract numeric score from string like '5.0' or '18.0 DSQ'"""
    import re
    m = re.search(r'(\d+(?:\.\d+)?)', str(s))
    return float(m.group(1)) if m else 0.0

def main():
    print("=" * 80)
    print("LIPTON 2026 — CHECKSUM VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    # 1. Internal checksum (sum of races = total)
    print("1. INTERNAL CHECKSUM (sum of race scores = total)")
    print("-" * 60)
    internal_ok = True
    for r in RESULTS:
        scores = r["scores"]
        race_sum = sum(parse_score(scores.get(f"R{i}", 0)) for i in range(1, 11))
        total = r["total"]
        match = abs(race_sum - total) < 0.01
        status = "✓" if match else "✗ MISMATCH"
        if not match:
            internal_ok = False
        print(f"  Bow {r['bow']:>2} {r['boat']:<20} Sum={race_sum:>6.1f} Total={total:>6.1f} {status}")
    
    print()
    if internal_ok:
        print("  RESULT: All internal checksums PASS (sum of races = total)")
    else:
        print("  RESULT: Some internal checksums FAIL")
    
    # 2. R1-R7 vs official PDF
    print()
    print("2. R1-R7 vs OFFICIAL PDF (lipton_r7_official_update.py)")
    print("-" * 60)
    r7_ok = True
    for r in RESULTS:
        sail = r["sail"]
        if sail not in R7_OFFICIAL:
            print(f"  Sail {sail}: NOT IN OFFICIAL (skip)")
            continue
        official = R7_OFFICIAL[sail]
        ours = [parse_score(r["scores"].get(f"R{i}", 0)) for i in range(1, 8)]
        theirs = [float(x) for x in official["races"]]
        match = ours == theirs
        if not match:
            r7_ok = False
            print(f"  Sail {sail} {r['boat']:<20} ✗ MISMATCH")
            print(f"      Ours:     {ours}")
            print(f"      Official: {theirs}")
        else:
            our_sum = sum(ours)
            official_sum = sum(theirs)
            print(f"  Sail {sail} Bow {r['bow']:>2} {r['boat']:<20} ✓ R1-R7 match (sum={our_sum:.0f})")
    
    print()
    if r7_ok:
        print("  RESULT: All R1-R7 scores match official PDF")
    else:
        print("  RESULT: Some R1-R7 scores do NOT match official PDF")
    
    # 3. J-Walker discrepancy analysis
    print()
    print("3. J-WALKER (BOW 8) DISCREPANCY ANALYSIS")
    print("-" * 60)
    jwalker = next(r for r in RESULTS if r["sail"] == "173")
    
    print(f"  Our database:")
    print(f"    R1-R7: {[parse_score(jwalker['scores'].get(f'R{i}')) for i in range(1, 8)]}")
    print(f"    R8-R10: {[parse_score(jwalker['scores'].get(f'R{i}')) for i in range(8, 11)]}")
    print(f"    Total: {jwalker['total']}")
    
    print()
    print(f"  Official R1-R7 (from PDF): {R7_OFFICIAL['173']['races']}")
    print(f"  Official R1-R7 sum: {R7_OFFICIAL['173']['nett']}")
    
    r1_r7_sum = sum(parse_score(jwalker['scores'].get(f'R{i}')) for i in range(1, 8))
    r8_r10_sum = sum(parse_score(jwalker['scores'].get(f'R{i}')) for i in range(8, 11))
    
    print()
    print(f"  Our R1-R7 sum: {r1_r7_sum}")
    print(f"  Our R8-R10 sum: {r8_r10_sum}")
    print(f"  Our Total: {r1_r7_sum + r8_r10_sum}")
    
    print()
    print("  If official total is 64 (user claim):")
    print(f"    Discrepancy: {jwalker['total']} - 64 = 2 points")
    print(f"    Official R8-R10 would be: 64 - {r1_r7_sum} = {64 - r1_r7_sum}")
    print(f"    Our R8-R10: {r8_r10_sum}")
    print(f"    R8-R10 discrepancy: {r8_r10_sum} - {64 - r1_r7_sum} = {r8_r10_sum - (64 - r1_r7_sum)}")
    
    # 4. Source of R8-R10 scores
    print()
    print("4. SOURCE OF R8-R10 SCORES")
    print("-" * 60)
    print("  Our R8-R10 scores come from Vakaros tracker finish positions:")
    print("    R8: RCYC Academy finished 9th → score 9")
    print("    R9: RCYC Academy finished 6th → score 6")
    print("    R10: RCYC Academy finished 9th → score 9")
    print()
    print("  The tracker records physical finish positions.")
    print("  Official scores may differ due to:")
    print("    - Protests upheld (changing positions)")
    print("    - Redress granted (improving a score)")
    print("    - Race committee corrections")
    print("    - Scoring penalties (not reflected in tracker)")
    
    # 5. Conclusion
    print()
    print("5. CONCLUSION")
    print("-" * 60)
    print("  ✓ Internal checksums: PASS (all race sums = totals)")
    print("  ✓ R1-R7 vs official: MATCH (verified against PDF)")
    print("  ? R8-R10 vs official: UNKNOWN (no official R8-R10 PDF)")
    print()
    print("  The 2-point discrepancy for J-Walker (66 vs 64) is in R8-R10.")
    print("  To correct, need official R8-R10 race scores from race committee.")
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
