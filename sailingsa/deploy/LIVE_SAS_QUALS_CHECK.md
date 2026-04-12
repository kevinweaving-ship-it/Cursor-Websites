# Live SAS ID / quals check

**Run date:** 2026-03-07 (from live DB).

## Counts (live)

| What | Count |
|------|-------|
| **sas_id_personal** (all SAS IDs we know) | 28,423 |
| **Have ≥1 qual in member_roles** | 183 |
| **In sas_id_personal but NO quals in our table** | 28,240 |

## Our quals table (roles)

We have **27** role codes in `roles`; **223** rows in `member_roles` (person_key + role_code).

| role_code | role_label |
|-----------|------------|
| ASST_COACH | Assistant Race Coach |
| RACE_COACH | Race Coach |
| COACH_DEV | Race Coach Developer |
| SENIOR_COACH | Senior Race Coach |
| ASSIST_INSTR | Assistant Instructor |
| INSTR_DINGHY | Instructor (Dinghy/Multihull) |
| INSTR_KEEL | Instructor (Keelboat) |
| SENIOR_INSTR | Senior Instructor |
| JUDGE_CLUB | Judge (Club) |
| JUDGE_DIST | Judge (District) |
| JUDGE_INT | Judge (International IJ) |
| JUDGE_NAT | Judge (National NJ) |
| JUDGE_REG | Judge (Regional) |
| UMPIRE_NAT | Umpire (National) |
| RTP_AUTH | Return to Play Authorisation |
| RO_ASST | Race Officer (Assistant) |
| RO_CLUB | Race Officer (Club/District) |
| RO_FAC | Race Officer (Facilitator) |
| RO_NAT | Race Officer (National) |
| RO_REG | Race Officer (Regional) |
| NAT_SE_SAF | National Senior Safety Officer |
| VSO | SA Sailing Vessel Safety Officer |
| SBI | Safety Boat Instructor |
| SBO | Safety Boat Operator |
| APPT_EXAM | Appointed Examiner |
| NAT_SE_EXAM | National Senior Examiner |
| SAMSA_SURV | SAMSA Vessel Surveyor |

## SAS IDs that already have quals in our table (183)

These are the SAS IDs that have at least one row in `member_roles` (so we already have some quals for them):

```
100, 10434, 1090, 1134, 1136, 1154, 119, 11901, 1198, 1202, 121, 1232, 1249, 1250, 1270, 1278, 1313, 1324, 133, 1330, 1366, 1385, 1387, 1401, 1422, 143, 1433, 1439, 1457, 14573, 1481, 1482, 1485, 1491, 1492, 1505, 1533, 1545, 1563, 157, 1574, 158, 1590, 1631, 1641, 165, 1655, 1658, 1661, 1663, 1672, 1675, 1685, 1687, 1691, 1695, 1698, 1699, 1710, 17137, 172, 1738, 1744, 1763, 1766, 185, 18643, 188, 1894, 1905, 19093, 1927, 1928, 1929, 195, 196, 197, 19804, 2030, 2073, 2132, 2167, 221, 2252, 2267, 2278, 228, 2281, 2319, 236, 2380, 241, 2551, 2561, 25675, 2583, 2616, 27, 28, 3165, 3217, 324, 33, 3360, 339, 3440, 354, 355, 363, 3752, 380, 384, 385, 395, 410, 444, 445, 45, 4684, 475, 499, 5003, 502, 504, 505, 5083, 5173, 518, 520, 5201, 534, 546, 549, 555, 56, 58, 59, 5913, 600, 61, 615, 6193, 6511, 656, 658, 6581, 659, 66, 672, 6811, 694, 695, 709, 711, 723, 725, 7280, 732, 7349, 735, 756, 80, 81, 8518, 8778, 888, 8936, 90, 9013, 9250, 9277, 9358, 9384, 9418, 9482, 9507, 9508, 9509, 9510, 9654, 9693, 9804, 99
```

## Finding “new” quals (SAS ID has a qual we don’t have)

- **“New qual”** = a (SAS ID, accreditation) pair that exists at SAS (e.g. from [accreditation finder](https://www.sailing.org.za/accreditation-finder/)) but we **don’t** have that combination in `member_roles` (or that role in `roles`).
- To list those SAS IDs you need an **external list** of (SAS ID, qualification), e.g.:
  - Export from SAS accreditation finder, or  
  - A scrape/API that returns who has which accreditation.
- Then: for each (sas_id, qual) in that list, check if we have a matching `person_key` (= `SAS:<sas_id>`) and `role_code` in `member_roles`; if not, that sas_id is “has new qual not in our table”.

**Re-run counts on live (read-only):**

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 'psql postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master -c "
SELECT (SELECT COUNT(*) FROM sas_id_personal) AS sas_id_personal,
       (SELECT COUNT(*) FROM member_roles) AS member_roles,
       (SELECT COUNT(DISTINCT TRIM(REPLACE(person_key, '\''SAS:'\'', '\'''\''))) FROM member_roles WHERE person_key LIKE '\''SAS:%'\'') AS sas_ids_with_quals;
"'
```
