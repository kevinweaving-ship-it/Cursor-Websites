# Sailfish patents — full count vs “10+” claim

**Company:** 深圳旗鱼体育传播有限公司  
**Checked:** Google Patents assignee hits + company website marketing copy (`js/page.*.js`)  
**Date:** 2026-08-31  

---

## How the “>10 patents” claim reconciles

| Counting method | Count | Notes |
|---|---:|---|
| **Distinct patent families** (invention + utility) | **8** | Best technical count |
| **All CN publication numbers** (A + B + U) | **12** | This is how “more than 10” can be true |
| **Granted invention patents only** | **4** | B publications with grant |
| **What saill.cn itself advertises** | **2 inventions + 23 soft copyrights** | Marketing page (may be outdated) |

Their homepage literally says:

> **「2项发明专利、23项著作权」**  
> 专利号：`ZL 2019 1 0975113.6`、`ZL 2019 1 0989617.3`，**23项**国家认证计算机软件著作权。

Those ZLs map to:

| ZL (grant) | Application | CN pub |
|---|---|---|
| ZL 2019 1 0975113.6 | 201910975113.6 | **CN110750962B** |
| ZL 2019 1 0989617.3 | 201910989617.3 | **CN110738023B** |

Later filings (2021–2024 scoring / mark-rounding / Windwatcher / tracker hardware) appear on Google Patents under the same assignee but are **not** listed on that marketing blurb — so either the site is stale, or they only promote the two early weather grants.

**There is no separate Chinese class called “software patent.”**  
Software is usually protected as **计算机软件著作权 (soft著)**. Method inventions that implement software algorithms *are* invention patents (below). Soft著 ≠ patents.

---

## Complete patent family table

### Software-method inventions (algorithm / data / race logic)

| Patent family | What it covers | Status | Software? |
|---|---|---|---|
| **CN110738023A / CN110738023B** | Convert JSON weather grids → JPEG for smaller/faster/encryptable weather transmission | **Granted** (ZL201910989617.3) | Yes — method |
| **CN110750962A / CN110750962B** | GRIB weather pull/parse/merge → JSON for web/mobile race apps | **Granted** (ZL201910975113.6) | Yes — method |
| **CN113033968A / CN113033968B** | Sailing race performance evaluation — sailing / start / tacking scores from race CMS tracks | **Granted** | Yes — method |
| **CN114690225A / CN114690225B** | Automatic mark-rounding / pass detection from GPS traj + virtual course geometry | **Granted** | Yes — method |

### Hardware / instrument

| Patent family | What it covers | Status | Software? |
|---|---|---|---|
| **CN113588153A** | Marine true-wind instrument (Windwatcher class): wind sensor + GPS + 9-axis orientation + processor + comms | **Application / publication only** (no B found) | System (HW+SW) |
| **CN220137400U** | GPS positioning device & system (gyro, GPRS, offline store, SOS high-rate) | **Utility model granted** | Hardware |
| **CN220874872U** | GPS positioning equipment with protective / buffer structure | **Utility model granted** | Hardware |
| **CN220874741U** | Signal base station for positioning system (protective shell, status LEDs) | **Utility model granted** | Hardware |

### Publication-level checklist (12 docs)

1. CN110738023A  
2. CN110738023B ✅ granted  
3. CN110750962A  
4. CN110750962B ✅ granted  
5. CN113033968A  
6. CN113033968B ✅ granted  
7. CN113588153A (appl.)  
8. CN114690225A  
9. CN114690225B ✅ granted  
10. CN220137400U ✅ UM  
11. CN220874872U ✅ UM  
12. CN220874741U ✅ UM  

→ **12 publications = “more than 10 patents” if counting every CN number.**  
→ **8 families** if counting properly.  
→ **4 software-method invention families** granted.

---

## Software copyrights (软著) — claimed, titles not public

| Claim source | Count | Titles / certificate numbers |
|---|---:|---|
| saill.cn marketing | **23** | **Not published** on site; CN copyright portal needs exact 软著登字 / registration no. to look up |
| Open web / Baidu / copyright.com.cn scrape | 0 titles recovered | Soft著 announcements are not openly searchable by company name alone |

Likely soft著 cover products we already mapped in code/docs (names inferred, **not verified on certificates**):

- SF-Traj / 旗鱼轨迹 web  
- 赛事零距离 WeChat mini program  
- sf-admin 赛事管理  
- sf-training 训练管理  
- sailingrule / 帆船赛事信息平台  
- 云相册  
- 3D 全景客户端  
- device / protocol tooling  

Until Sailfish shares certificate numbers, treat **“23 soft著” as their claim only**.

---

## What was *not* found

- No additional assignee hits beyond the 8 families above (under this company name).  
- No patents under 王祥胜 or parent 海上轻骑 as assignee.  
- Do **not** mix in 广州市旗鱼软件科技 (12 patents / Sailfish OS) or 旗鱼点餐 — different companies.  
- CN103111065B sailing-track system is **广东省信息工程有限公司**, not Sailfish.

---

## Bottom line

- **If someone says “10+ patents”:** they are almost certainly counting **all CN publication numbers (12)** or mixing patents + soft著.  
- **Rigorous family count:** **8** (4 granted software-method inventions + 1 wind appl. + 3 hardware UMs).  
- **Software IP:** 4 granted **method patents** + claimed **23 soft copyrights** (titles undisclosed).  
- **Company’s own public boast:** only the **2** 2019 weather invention grants + **23** soft著.
