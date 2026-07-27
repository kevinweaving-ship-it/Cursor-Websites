# 47 results with club_raw that don’t resolve to a club

**Why:** `club_raw` is set on the result row but does not match any row in `clubs` (by `club_abbrev` or `club_fullname`) or in `club_aliases` (by `alias`). So `club_id` stays NULL and sailor “most-sailed club” can’t use these rows.

**Fix:** Add each value as a club in `clubs`, or add it as an alias in `club_aliases` pointing to an existing club. Then re-run `ensure_sailor_club_from_results.py` on the cloud.

---

## Full list (result_id, regatta, class, club_raw, helm, crew)

| result_id | regatta / event | year | class | club_raw | helm_name | crew_name |
|-----------|-----------------|------|-------|----------|-----------|-----------|
| 2514 | Hermanus Cape Classic 2024 | 2024 | Ilca 6 | BISHOPS | Lukas Drimie | |
| 2531 | Hermanus Cape Classic 2024 | 2024 | 420 | BISHOPS | Jack Stewart | Marshall Oosthuysen |
| 4170 | ZVYC Interschools | 2025 | Optimist C | Bergvliet High School | Michelle Behrmann | |
| 2723 | 2023 MSC Dinghy Classes & Hobi | 2023 | Hobie 16 | FHBSC | Caroline Hutchison | Claire Heginbotham |
| 4159 | ZVYC Interschools | 2025 | Optimist A | Fish Hoek Primary | Ben Madel | |
| 3964 | SA Youth Nationals Dec 2025 | 2025 | Dabchick | GYLC | Isabella Watson | |
| 3992 | SA Youth Nationals Dec 2025 | 2025 | Ilca 4.7 | GYLC | Jean Buys | |
| 4086 | SA Youth Nationals Dec 2025 | 2025 | Optimist A | GYLC | Arthur Finn Watson | |
| 4157 | ZVYC Interschools | 2025 | Ilca 4.7 | Herzlia Highlands | Edison Lu | |
| 4168 | ZVYC Interschools | 2025 | Optimist C | Kirstenhof Primary | Oliver Rawden | |
| 4038 | SA Youth Nationals Dec 2025 | 2025 | Ilca 6 | MSBC | Rainier Lambrecht | |
| 4047 | SA Youth Nationals Dec 2025 | 2025 | Mirror | MSC Izi | Simankele Mtshofeni | Jansen, Giovanni |
| 4050 | SA Youth Nationals Dec 2025 | 2025 | Mirror | MSC Izi | Kayo Roberts | Cayllum Edwards |
| 4051 | SA Youth Nationals Dec 2025 | 2025 | Mirror | MSC Izi | Holden Litsenborgh | Jayden Arendse |
| 4053 | SA Youth Nationals Dec 2025 | 2025 | Mirror | MSC Izi | Aiden Edwards | Luke Groenewald |
| 4056 | SA Youth Nationals Dec 2025 | 2025 | Mirror | MSC Izi | Hayden Phillanda | Abrahams, Shamier |
| 2528 | Hermanus Cape Classic 2024 | 2024 | Fireball | Maties | Thomas Ochabski | Kerry Obchabski |
| 4163 | ZVYC Interschools | 2025 | Optimist A | Michael Oak Waldorf | Michael Hartnack | |
| 4161 | ZVYC Interschools | 2025 | Optimist A | Parklands College | Benjamin Fourie | |
| 4166 | ZVYC Interschools | 2025 | Optimist C | Parklands College | Bao-Sheng Chiu | |
| 4172 | ZVYC Interschools | 2025 | Optimist C | Parklands College | Bao-Cheng Chiu | |
| 4174 | ZVYC Interschools | 2025 | Optimist B | Parklands College | Sebastian Fourie | |
| 2062 | SA Sailing Youth Nationals - I | 2025 | Ilca 4.7 | RBYC | Dillon Wrethman | |
| 4114 | SA Youth Nationals Dec 2025 | 2025 | Optimist B | RSA | Takunda Joshua Tekwe | |
| 4088 | SA Youth Nationals Dec 2025 | 2025 | Optimist A | Red House | Ruan Labuschagne | |
| 4155 | ZVYC Interschools | 2025 | Dabchick | Rustenburg | Faith Lyons | |
| 4150 | ZVYC Interschools | 2025 | Dabchick | SACS High School | Thomas Henshilwood | |
| 4151 | ZVYC Interschools | 2025 | Dabchick | SACS High School | Joshua Nankin | |
| 4153 | ZVYC Interschools | 2025 | Dabchick | SACS High School | Jack Cumming | |
| 4154 | ZVYC Interschools | 2025 | Ilca 6 | SACS High School | Josh Keytel | |
| 4158 | ZVYC Interschools | 2025 | Optimist A | SACS Jnr | Ben Henshilwood | |
| 4160 | ZVYC Interschools | 2025 | Optimist A | SACS Jnr | Harold Schultz | |
| 4162 | ZVYC Interschools | 2025 | Optimist A | SACS Jnr | Benjamin Hudson | |
| 4164 | ZVYC Interschools | 2025 | Optimist A | SACS Jnr | Harrison Hudson | |
| 4169 | ZVYC Interschools | 2025 | Optimist C | SACS Jnr | Mikaeel Parker | |
| 2701 | 2023 MSC Dinghy Classes & Hobi | 2023 | Extra | SAS | Nicholas Breedt | |
| 2722 | 2023 MSC Dinghy Classes & Hobi | 2023 | Hobie 16 | SAS | Andrew Lawson | Michael Lawson |
| 4167 | ZVYC Interschools | 2025 | Optimist C | Springfield | Brenna Kieser | |
| 4171 | ZVYC Interschools | 2025 | Optimist C | Sweet Valley Primary | Matthew Starke | |
| 4173 | ZVYC Interschools | 2025 | Optimist B | Sweet Valley Primary | Cameron Starke | |
| 2483 | ZVYC Southern Charter Classic | 2024 | Mirror | TBA | Van JB | TBA |
| 3766 | TSC CAPE CLASSIC Dec 2025 | 2025 | Topaz | TSA | Stephan Buys | Michael Buys |
| 2726 | 2023 MSC Dinghy Classes & Hobi | 2023 | Hobie 16 | UCYC | Lee Gibbs | Reece McMinn |
| 4152 | ZVYC Interschools | 2025 | Ilca 6 | Westerford | Jacques Dugas x | |
| 4156 | ZVYC Interschools | 2025 | Ilca 4.7 | Westerford | Jens Dugas | |
| 4149 | ZVYC Interschools | 2025 | Ilca 6 | Wynberg Boys High | Blake Madel | |
| 2440 | ZVYC Southern Charter Classic | 2024 | 420 | ZVYCS | Jemayne Wolmarans | Sulieman Almano |

---

## Distinct club_raw values to add (as club or alias)

These 27 strings are what appear in the 47 rows. Add each to `clubs` (if it’s a real club/school) or to `club_aliases` (e.g. alias → existing club).

- BISHOPS  
- Bergvliet High School  
- FHBSC  
- Fish Hoek Primary  
- GYLC  
- Herzlia Highlands  
- Kirstenhof Primary  
- MSBC  
- MSC Izi  
- Maties  
- Michael Oak Waldorf  
- Parklands College  
- RBYC  
- RSA  
- Red House  
- Rustenburg  
- SACS High School  
- SACS Jnr  
- SAS  
- Springfield  
- Sweet Valley Primary  
- TBA  
- TSA  
- UCYC  
- Westerford  
- Wynberg Boys High  
- ZVYCS  

**Notes:**  
- **TBA** = “to be announced”; you may leave it unresolved or add an alias to a generic “TBA” club if you have one.  
- **SAS** = likely “SA Sailing” or similar; **RSA** = country; **TSA** = possibly “TSC” or another club. Map to the correct club and add alias if needed.
