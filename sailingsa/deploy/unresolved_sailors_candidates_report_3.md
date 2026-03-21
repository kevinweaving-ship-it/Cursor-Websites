# Unresolved sailors — batch 3 (OFFSET 70 LIMIT 50)

## Summary

| Metric | Value |
|--------|--------|
| **Rows checked** | 50 |
| **Rows auto-matched (single-match UPDATEs)** | 10 |
| **Remaining queue (result rows)** | 105 |
| **Remaining queue (distinct helm_name, sail_number)** | 101 |

Goal: drive queue below ~70. Run further batches (e.g. OFFSET 120 LIMIT 50) to continue.

---

## Match logic

1. sail_number → `sas_id_personal.primary_sailno`  
2. helm_name → `LOWER(full_name) LIKE LOWER('%' || helm_name || '%')`  
3. Prior results: same sail_number already has valid `helm_sa_sailing_id`  
Auto-update only when exactly one distinct `sa_id` per (helm_name, sail_number).

---

## Applied (single clear match) — 10

| helm_name | sail_number | sa_id |
|-----------|-------------|-------|
| Aili-May | 420 | 27701 |
| Aston Kallaway | 191033 | 13808 |
| Cassiopia | 2927 | 15570 |
| Harry Schultz | 1308 | 27542 |
| Kay-Lynn | 160132 | 10159 |
| Lorelai Deursen | 1316 | 27986 |
| Mason Guthrie | 1311 | 27155 |
| Tom Henshilwood | 3457 | 9612 |
| Vermaak Duran | 571 | 3711 |
| Wali Crawford | 195 | 3351 |

---

## Remaining in queue with multiple candidates

| helm_name | sail_number | n_candidates | note |
|-----------|-------------|--------------|------|
| Lana Plessis | 70122 | 2 | 18500, 19581 |
| Muhaimeen Thompson | 5309 | 2 | 17516, 18306 |
| Rex Anderson | 15 | 3 | 9461, 12006, 14234 |
| Unam Aviwe | 69488 | 3 | 10167, 18908, 24612 |
| Lawrie | 2468 | 4 | 4518, 6236, 6257, 22801 |
| Tom Henshilwood | 570 | 4 | 355, 4986, 9612, 19765 |
| Who are you? | 52998 | 4 | 2990, 6903, 7516, 12516 |
| Ryan Pentolfe | 5 | 7 | (7 ids) |
| Dillon | (blank) | 8 | (8 ids) |
| Max | 582 | 51 | (51 ids — resolve manually) |
| Shaun | 4998 | 56 | (56 ids — resolve manually) |
| Ash | 60382 | 164 | (164 ids — resolve manually) |
| William | 922 | 168 | (168 ids — resolve manually) |

---

## Remaining with no candidates (this batch slice)

| helm_name | sail_number |
|-----------|-------------|
| Alex Garoufalias | 201 |
| Blake Roodt | (blank) |
| Blokkies Loubser | 4642 |
| Ernst Eugester | 2964 |
| Friso Deursen | 23524 |
| H Plessis | 3171 |
| Holden Litsenborgh | 64600 |
| Lionel Hewitt | 37101 |
| Maksimilian Strydom-Micic | 1092 |
| Nick Chapman | 1921 |
| Oliver Voigt | 90121 |
| Phillip Nyamakura | 2986 |
| Reinder Groenewald | SA4524 |
| Ryan Pentolfe | (blank) |
| Tara WILSON | 70595 |
| Tehilah Plessis | 70416 |
| Wallly Maritz | 65 |
| Yestin Hudley | 54901 |

Resolve manually or add to `sailor_helm_aliases` when confirmed.
