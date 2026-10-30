# Events vs landing regatta list — comparison

Source: live `/events` embedded JSON vs `/api/regattas/with-counts` (landing search/list).

## Counts
- Landing regatta parents: **372**
- `/events` cards: **1155**
- Direct `regatta_id` link: **259**
- Regattas with no events `regatta_id`: **113**
  - Fuzzy match to an unlinked event (should link): **17** (2024+: **2**)
  - No matching event row at all: **96** (2024+: **39**)
- Past events unlinked: **678**
- Past with `result_yes`: **438**
- Suspect wrong links (low name overlap): **133**

## ILCA KZN 2026
- Present on `/events` **Past**, linked to `2026-08-10-ilca-kzn-regional-championships`, has results.
- laser.org “Closed / Not available” is their entry page status — not missing from our events list.

## 2024+ regattas with no events match
- `2026-03-25-hbyc-hunter-19-summer-26-saturdays` — 2026 HBYC - Hunter 19 - ☀ 26 Saturdays (2026-03-25)
- `2026-03-25-hbyc-hunter-19-summer-26-tuesdays` — 2026 HBYC - Hunter 19 - ☀ 26 Tuesdays (2026-03-25)
- `2026-03-29-eden-inter-schools-primary` — 2026 Eden Inter Schools Primary (2026-03-28)
- `2026-03-29-hbyc-hunter-19-2026-leopard-challenge-leg-1` — 2026 HBYC - Hunter 19 - 2026 Leopard Challenge Leg 1 (2026-03-29)
- `2026-07-19-hbyc-hunter-19-winter-26-saturdays` — 2026 HBYC - Hunter 19 - Winter 26 Saturdays (2026-07-19)
- `2025-03-23-hbyc-hunter-19-summer-25-saturdays` — 2025 HBYC - Hunter 19 - ☀ 25 Saturdays (2025-03-23)
- `2025-03-26-hbyc-hunter-19-summer-25-tuesdays` — 2025 HBYC - Hunter 19 - ☀ 25 Tuesdays (2025-03-26)
- `2025-05-11-mpumalanga-regionals-df95` — 2025-05-11 DF95 Mpumalanga Champ (2025-05-11)
- `2025-09-21-hbyc-hunter-19-winter-25-saturdays` — 2025 HBYC - Hunter 19 - Winter 25 Saturdays (2025-09-21)
- `2025-11-26-hbyc-hunter-19-summer-26-weekdays` — 2025 HBYC - Hunter 19 - ☀ 26 Weekdays (2025-11-26)
- `2025-12-12-tuesday-blown-out-thursdays` — 2025 Tuesday Blown Out Thursdays (2025-12-12)
- `2025-12-31-wc-extra-regionals` — 2025-12-31 WC Extra Regionals (2025-12-31)
- `2024-01-28-ec-df95-regionals` — 2024-01-28 EC DF95 Regionals (2024-01-26)
- `2024-01-28-king-of-vaal` — 2024-01-28 King of the Vaal (2024-01-28)
- `2024-02-17-mykonos-offshore` — 2024-02-17 Mykonos Offshore (2024-02-16)
- `2024-02-24-hmyc-6hr-race` — 2024-02-24 Henley Midmar Yacht Club 6&9 Hour (2024-02-24)
- `2024-03-03-admirals-regatta-orc` — 2024-03-03 Admirals Regatta ORC (2024-03-03)
- `2024-03-11-hbyc-hunter-19-summer-24-saturdays` — 2024 HBYC - Hunter 19 - ☀ 24 Saturdays (2024-03-11)
- `2024-03-14-hbyc-hunter-19-summer-24-weekdays` — 2024 HBYC - Hunter 19 - ☀ 24 Weekdays (2024-03-14)
- `2024-03-24-hunter19-kzn-regionals` — 2024-03-24 Hunter 19 KZN Regionals (2024-03-24)
- `2024-04-01-mirror-nationals` — 2024-04-01 Mirror Nationals (2024-03-29)
- `2024-04-01-wc-dinghy-champs-2-ilca-finn-505-regionals` — 2024-04-01 WC Dinghy Champs (2024-04-01)
- `2024-04-14-hmyc-autumn-series` — 2024-04-14 HMYC Autumn Series (2024-04-14)
- `2024-04-21-hmyc-memorial-series` — 2024-04-21 HMYC Memorial Series (2024-04-21)
- `2024-05-05-zyc-club-fun-race` — 2024-05-05 ZYC Club Fun Race (2024-05-05)
- `2024-07-07-hmyc-club-championships-243` — 2024-07-07 HMYC Club Class Champs (2024-07-07)
- `2024-08-11-j22-nationals` — 2024-08-11 J22 National Champs (2024-08-09)
- `2024-08-17-triple-crown-1-24-25` — 2024-08-17 Triple Crown (2024-08-17)
- `2024-09-01-hbyc-hunter-19-winter-24` — 2024 HBYC - Hunter 19 - Winter 24 (2024-09-01)
- `2024-09-07-triple-crown-2-24-25` — 2024 Triple Crown (2024-09-07)
- `2024-09-08-optimist-gp-provincials` — 2024-09-08 Optimist GP Provincials (2024-09-08)
- `2024-09-23-505` — 2024-09-23 505 SAS National Champs (2024-09-21)
- `2024-10-26-triple-crown-24-25-triple-crown-3-24-25` — 2024-10-26 Triple Crown (2024-10-26)
- `2024-11-17-triple-crown-24-25-triple-crown-4-24-25` — 2024-11-17 Triple Crown (2024-11-17)
- `2024-11-19-flying-fifteen-national-championships` — 2024-11-19 Flying Fifteen National Champs (2024-11-19)
- `2024-11-19-soling-national-championships` — 2024-11-19 Soling National Champs (2024-11-19)
- `2024-12-17-hobie-16-nationals` — 2024-12-17 Hobie 16 Nationals (2024-12-17)
- `2024-12-31-halcat-mpumalanga-regionals` — 2024-12-31 Halcat Mpumalanga Regionals (2024-12-31)
- `2024-12-31-stadt-23-nationals` — 2024-12-31 Stadt 23 Nationals (2024-12-31)

## 2024+ should-link (event exists, regatta_id null)
- [0.60] `2025-01-27-hmyc-grand-slam` ↔ SAS 2025 HMYC GRAND SLAM (2025-01-25)
- [0.78] `2024-05-25-ullman-sails-womens-series-1` ↔ 2024 Ullman Sails Women's Series — Day 1 (2024-05-25)

## Suspect wrong links
- [0.00] `2019-04-30-hobie-16-national-championships` / REG `2019 Hobie 16 National Champs` ← EVT `2019 Hobie16 Nationals` (past)
- [0.00] `2021-09-26-j22-south-african-national-championships` / REG `2021 J/22 South African National Champs` ← EVT `DAC Keelboat  Week` (past)
- [0.00] `2021-12-21-sa-youth-nationals-championship` / REG `2021 Youth Nationals Champ` ← EVT `2021 YNats - Results` (past)
- [0.00] `2022-06-19-pyc-grand-slam` / REG `2022 PYC Grand Slam` ← EVT `SASKZN Grandslam Regatta - Point Yacht Club` (past)
- [0.00] `2023-05-02-cats-monohull-ec-regionals` / REG `2023 Cats & Monohull EC Regionals` ← EVT `Eastern Cape Dinghy Provincial Championships` (past)
- [0.00] `2025-02-02-gimco-mirror` / REG `2025 Gimco Mirror` ← EVT `Hunter 19 Mpumalanga Championship 2025` (past)
- [0.00] `2025-02-02-gimco-mirror` / REG `2025 Gimco Mirror` ← EVT `Mykonos Offshore 2025` (past)
- [0.00] `2025-03-23-hunter-nationals` / REG `2025 Hunter Nationals` ← EVT `National Race Officers Workshop` (past)
- [0.00] `2025-04-19-mirror-worlds` / REG `2025-04-19 Marriott IMCA World Champs` ← EVT `2025 Mirror Worlds` (past)
- [0.00] `2025-04-28-h16-provincials` / REG `2025-04-28 Southern Wind WC/EC Hobie 16 Provincial Champs` ← EVT `2025 H16 PROVINCIALS PROVISIONAL` (past)
- [0.00] `2025-09-27-hobie16-nationals` / REG `2025-09-27 Hobie16 Nationals` ← EVT `Hobie Robberg Regatta` (past)
- [0.00] `2025-09-28-finn-nationals` / REG `2025 Finn Nationals` ← EVT `2025 29er SA Sailing National Championship` (past)
- [0.00] `2025-09-28-finn-nationals` / REG `2025 Finn Nationals` ← EVT `National Race Officers Workshop` (past)
- [0.00] `2025-09-28-finn-nationals` / REG `2025 Finn Nationals` ← EVT `National Umpire Seminar` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 DART 18 OPEN KZN REGIONAL CHAMPIONSHIPS` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 Dragonflite 95 Radio Championships` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 HUNTER KZN REGIONAL CHAMPIONSHIPS` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 Halcat National Championship` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 KZN Dabchick` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 Optimist &amp; Dabchick Regional Championship` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 SA Sailing FS AGM` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 SA Sailing GP AGM` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 SA Sailing KZN AGM` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 SA Sailing NR AGM` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 SA Sailing National AGM` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `2025 Youth Sailing World Championships` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `Boskop Open Regatta 2025` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `Shane&#039;s Gaul Regatta 2025` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `The Canyon Cup 2025 ORC DH Nationals` (past)
- [0.00] `2025-10-19-eastern-cape-champs-monohull` / REG `2025 Eastern Cape Champs Monohull` ← EVT `TuziTekwini Ocean Race 2025` (past)
