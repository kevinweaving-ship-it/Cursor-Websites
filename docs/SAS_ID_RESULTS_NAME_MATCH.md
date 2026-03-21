# SAS ID / Results name match (SA ID match)

**Goal:** Result names (helm_name, crew_name, etc.) must align with the canonical name in `sas_id_personal` for that SA ID so that:
- All results show on the sailor profile (match by SA ID; display uses canonical name).
- Name-based fallback and display are consistent.

**When you refer to this README:** Run the fix (migration below), then re-run resource test if needed.

---

## Audit list (Result name vs sas_id_personal vs SA ID)

| Result name | sas_id_personal (canonical) | SA ID |
|-------------|----------------------------|-------|
| Andrew Lawson | Andrew Lawson | 14729 |
| Aston Kallaway | Ashton Kallaway | 26085 |
| Athi Vena | Athenkosi Vena | 1481 |
| Bastian Taylor | Bastien Taylor | 26382 |
| Bella Keytel | Isabella Keytel | 10148 |
| Callum Edwards / Cayllum Edwards | Caylem Edwards | 21500 |
| Charlie Lorentz | Charles Lorentz | 15472 |
| Charlie Schultz | Charles Schultz | 27542 |
| Chris Oloff | Christian Oloff | 9305 |
| Dave Clair | David St Clair | 27416 |
| Dave Hood | David Hood | 27699 |
| Dylan Hall | Dylan Hall | 12583 |
| Dylan Stevens | Dyllan Stevens | 15804 |
| Erin Smith | Erin Smith | 16826 |
| Fateer Yon | Fatier Yon | 10166 |
| Haley Rae | Hayley Rae | 15738 |
| Hannah Sasman | Hannah Maria Sasman | 9670 |
| Harrison Hudson | Harrison Hudson | 22172 |
| Harry Schultz | Harold Schultz | 23152 |
| Jack Cumming | Jack Cumming | 13487 |
| James Rae | James Rae | 15737 |
| Jan Berg | Jan Van Den Berg | 16969 |
| Jaun Viljoen | Jan Viljoen | 10154 |
| Jordan Dyk | Jordan van Dyk | 15110 |
| Josh Keytel | Joshua Keytel | 13522 |
| Josh Nankin | Joshua Nankin | 8704 |
| Keyruren MAHARAJ | Keyuren Maharaj | 8628 |
| Lana Plessis | Lana du Plessis | 18500 |
| Lihle Matomela | Kamvaelihle Matomela | 23596 |
| Maksimilian Strydom-Micic | Maksi Strydom-Micic | 27806 |
| Mark Bosch | Mark Van Den Bosch | 9442 |
| Marshall Oosthuysen | Marshall Gutsche Oosthuysen | 3505 |
| Matthew Starke | Matthew Starke | 26883 |
| Max Celliers | Max Celliers | 9172 |
| Mickylo Nel | Michael Nel | 13571 |
| Mikaeel Parker | Michael Parker | 21006 |
| Mike Hayton | Michael Hayton | 2350 |
| Mike Peper | Michael Peper | 4947 |
| Mike Robinson | Michael Robinson | 17703 |
| Morne Harding | Mornay Harding | 3985 |
| Neil van Schalkwyk | Neil Schalkwyk | 10341 |
| Neill Cameron | Neil Cameron | 13768 |
| Nick Chapman | Nicholas Chapman | 374 |
| Patrick Kessel | Patrick Kessel | 8697 |
| Peet Merwe | Petrus van der Merwe | 26237 |
| Pete Wilson | Peter Wilson | 5141 |
| Polia van der Westhuizen | Polla Van Der Westhuizen | 14609 |
| Rob Savage | Robin Savage | 540 |
| Sean Kavanagh | Sean Kavanagh | 6804 |
| Shaun Preez | Shaun Du Preez | 3487 |
| Stevie Rumpf | Stefan Rumpf | 26353 |
| Tehilah Plessis | Tehilah du Plessis | 18501 |
| Thinus Groenewald | Marthinus Groenewald | 686 |
| Thomas Slater | Thomas Slater | 6583 |
| Wali Crawford | Walter Crawford | 3351 |
| Wayne Smith | Wayne Smith | 3372 |
| Zubhair Davids | Zubair Davids | 10167 |

(Canonical name = `COALESCE(TRIM(full_name), TRIM(first_name || ' ' || COALESCE(last_name, '')))` from `sas_id_personal`.)

---

## Fix (run once)

**Migration:** Sync all result names from `sas_id_personal` by SA ID so every row where `helm_sa_sailing_id` / `crew_sa_sailing_id` / etc. is set gets the canonical name.

```bash
psql "$DB_URL" -f database/migrations/126_sync_results_names_from_sas_id_personal.sql
```

Or from project root with `.env` loaded:

```bash
source .env  # or export DB_URL=...
psql "$DB_URL" -f database/migrations/126_sync_results_names_from_sas_id_personal.sql
```

This updates:
- `results.helm_name` where `helm_sa_sailing_id` matches a row in `sas_id_personal`
- `results.crew_name` where `crew_sa_sailing_id` matches
- `results.crew2_name` where `crew2_sa_sailing_id` matches (if column exists)
- `results.crew3_name` where `crew3_sa_sailing_id` matches (if column exists)

No manual per-person updates needed; the migration uses the live canonical name from `sas_id_personal` for each SA ID.

If the migration fails on `crew2_sa_sailing_id` or `crew3_sa_sailing_id` (e.g. "column does not exist"), edit `126_sync_results_names_from_sas_id_personal.sql` and comment out the two UPDATE blocks for crew2 and crew3, then re-run.

---

## After the fix

- Profiles: All results for a sailor are found by SA ID (and name fallback still works; names now match).
- Re-run resource test if you want to confirm: `python3 scripts/resource_test_standings_and_profile.py`
