# Unresolved sailors — batch 2 (OFFSET 20 LIMIT 50)

## Summary

| Metric | Value |
|--------|--------|
| **Rows checked** | 50 |
| **Rows auto-matched (single-match UPDATEs)** | 4 |
| **Remaining queue (result rows)** | 115 |
| **Remaining queue (distinct helm_name, sail_number)** | 111 |

Goal: reduce queue to &lt;80 before historical scrape. Run further batches (next OFFSET/LIMIT) to continue.

---

## Match logic (same as batch 1)

1. `sas_id_personal.primary_sailno` = sail_number  
2. `LOWER(full_name) LIKE LOWER('%' || helm_name || '%')`  
3. Prior results: same sail_number already has valid `helm_sa_sailing_id`  
Auto-UPDATE only when exactly one distinct `sa_id` per (helm_name, sail_number).

---

## Applied (single clear match) — this run: 4

| helm_name | sail_number | sa_id |
|-----------|-------------|-------|
| Chris Oloff | 909 | 9305 |
| Hennie Lachlan | 1435 | 27610 |
| Sebelo MPUNGUSO | 66853 | 21107 |
| WHO YOU | 60888 | 21546 |

---

## Remaining in queue with multiple candidates

| helm_name | sail_number | n_candidates | sa_ids (candidates) |
|-----------|-------------|--------------|----------------------|
| Cayllum EDWARDS | 69647 | 2 | 2725, 21500 |
| Charlie Lorentz | 582 | 2 | 2690, 15472 |
| Haitham Hawkins-Badat | 1410 | 2 | 15510, 21701 |
| Max Lorentz | 582 | 2 | 2690, 15472 |
| Morne Harding | 9 | 2 | 1221, 2637 |
| Athenkosi MAHLUMBA | 70842 | 3 | 12512, 18908, 22842 |
| Athi Mahlumba | 70842 | 3 | 12512, 18908, 22842 |
| Sibulele Tyla | 69925 | 3 | 1491, 12516, 21491 |
| Simamkele Mtshofeni | 70842 | 3 | 12512, 18908, 22842 |
| Lorelei Deursen | 8 | 4 | 12516, 18979, 19214, 27830 |
| Athi Vena | 11 | 5 | 3711, 6497, 12509, 12661, 13516 |
| Stephan Buys | 2 | 5 | 3985, 6992, 8549, 12494, 20794 |
| Olwam Ngqukye | 7 | 8 | 1521, 2725, 4986, 10166, 10366, 14707, 21489, 22841 |
| Morgan | 7621 | 32 | (32 ids — resolve manually) |
| Graham | Black | 99 | (99 ids — resolve manually) |
| Reg | (blank) | 152 | (152 ids — resolve manually) |

---

## Remaining with no candidates (this batch slice)

No match from primary_sailno, full_name LIKE, or prior results. Resolve manually or add to `sailor_helm_aliases` when confirmed.

| helm_name | sail_number |
|-----------|-------------|
| Andre Scholtz | 1642 |
| Brunello Ramplin | 54806 |
| Dave Hood | 75128 |
| David MEEHAN | 69536 |
| Erhardt Joubert | 4848 |
| H Westhuizen | 2941 |
| Hamill Declan | 1576690lJ |
| Hamill Ivan | 157669 |
| Irfaan Boyce | 189 |
| JP Buys | 1351 |
| James KOMWEIBEL | 70812 |
| Jan Berg | 4698 |
| Jessica Brick | 2646 |
| Keyruren MAHARAJ | 24142 |
| Lesley Rostek | NAM4 |
| Lodewyk Viljoen | 5396 |
| Mayreesh Williams | 7041 |
| Mike Peper | 1967 |
| Muhaimeen Thompson | 561 |
| Neill Cameron | (blank) |
| Paul Thomson | 10625 |
| Peet Merwe | 2013 |
| Quinton Pretorious | 60432 |
| Rob Hamill | 142925NZ |
| Robin Aproskie | 36480 |
| Stevie Rumpf | 60395 |
| Suleiman Almaro | 532 |
| Thomas Atwood | 54568 |
| Van JB | 64600 |
| Wally Maritz | 65 |
