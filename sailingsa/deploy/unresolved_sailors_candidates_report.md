# Unresolved sailors: match run report

## 1. Top 20 unresolved (with class + regatta_id context)

| helm_name | sail_number | cnt | classes | regattas |
|-----------|-------------|-----|---------|----------|
| Pavle Kostov | 3165 | 3 | Cape 31 | 316-2025-gimco-c31-overall, 320-2025-mykonos-..., 321-2025-mykonos-... |
| Scato Deursen | 191070 | 2 | Ilca 6 | 193-2024-hyc-cape-classic, 310-2025-hyc-cape-classic-ilca-6-results |
| Frederik Brandis | 4862 | 2 | Cape 31 | 320-2025-mykonos-..., 321-2025-mykonos-... |
| Alex Garoufalias | 201 | 1 | Hunter | 330-2025-hunter-mpumalanga-regionals |
| Aston Kallaway | 191033 | 1 | Ilca 6 | 377-2025-hyc-sa-youth-nationals |
| Athenkosi MAHLUMBA | 70842 | 1 | Mirror | 337-2025-mirror-worlds-results |
| Ash | 60382 | 1 | Hobie 14 | 375-2025-ec-champs |
| ... (full 20 from query) | | | | |

---

## 2. Match order used

1. **sas_id_personal.primary_sailno** = sail_number  
2. **LOWER(full_name) LIKE** LOWER('%helm_name%')  
3. **Prior results:** same sail_number already has valid helm_sa_sailing_id  

---

## 3. Applied (single clear match only)

| helm_name | sail_number | sa_id | source |
|-----------|-------------|-------|--------|
| Dave Clair | 2343 | 674 | prior_results |
| JJ Fourie | 4387 | 7610 | prior_results |
| Matthew Inglis | 151449 | 9716 | prior_results |
| Michelle Behrmann | 12671 | 90 | prior_results |

**4 rows updated.**

---

## 4. Left in queue with candidate list (multiple candidates)

| helm_name | sail_number | n_candidates | sa_ids (candidates) |
|-----------|-------------|--------------|----------------------|
| Giovanni Jansen | 69647 | 2 | 2725, 21500 |
| Shaun Preez | 160028 | 2 | 3487, 13995 |
| Keira Fairbank | 33 | 3 | 3477, 13488, 15704 |
| Dylan Stevens | 4 | 6 | 312, 459, 1521, 6497, 10816, 19469 |

---

## 5. Left in queue with no candidates

No match from primary_sailno, full_name LIKE, or prior results:

- Pavle Kostov 3165  
- Scato Deursen 191070  
- Frederik Brandis 4862  
- Alex Garoufalias 201  
- Aston Kallaway 191033  
- Athenkosi MAHLUMBA 70842  
- Ash 60382  
- Athi Vena 11  
- Aydin OHara 188568  
- Bao-Sheng Chiu R 1069  
- Blake Roodt (blank sail)  
- Blokkies Loubser 4642  
- Brenna Kieser 1360  
- Brunello Ramplin 54806  
- Cassiopia 2927  
- Buys JP 160086  
- Cath Vise 25  
- Cayllum EDWARDS 69647  
- Charlie Lorentz 582  
- Athi Mahlumba 70842  
- (and any others in top 20 not listed above)

Resolve manually or add to sailor_helm_aliases when confirmed.
