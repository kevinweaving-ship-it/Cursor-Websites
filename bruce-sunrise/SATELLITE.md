# Satellite vs Google — Vlycho quay

Google **Street View** is a road camera (four dates at this pin). Google **Maps / Earth** satellite is a **Maxar/Vantor mosaic**, not a yearly time-lapse. Other globes do **not** automatically have more **sharp** pictures of this quay. Some have **far more** pictures that are **too coarse** to name the hull.

Pin: **~38.6825°N, 20.6989°E** (same waterfront as Street View 105 Επαρ.Οδ. Λευκάδας–Βασιλικής).

## What actually has more photos per year than Google

| Source | How often over Vlycho | Resolution | Can it show a 20 m wooden trawler? | Cost |
| --- | --- | --- | --- | --- |
| **Sentinel-2** (Copernicus Browser) | **~144 unique days/year** 2019–2023; **~70–80** with cloud ≤20% (Element84 STAC, this pin) | 10 m | **Marginal.** The hull is ~2 pixels. Maybe “something on the wall” vs empty. **Cannot** ID Sunrise or a mooring ball. | Free |
| **Planet PlanetScope** | **Daily** land (clouds aside), 2016– | 3–5 m | **Yes as a boat-sized object** (~6–7 pixels). First cadence that can split April 2021 / 2022 / 2023. | Paid (Planet AI searches monthly mosaics; was free-to-try Nov 2026) |
| **Planet SkySat** | Sub-daily *if tasked* | 0.5 m | Yes, hull shape | Paid; **not** a full archive over this bay |
| **Sentinel-1** SAR | ~every 6–12 days, all weather | 10–20 m | Radar blob of a large hull, weak on wood | Free |
| **Landsat 8/9** | ~every 8–16 days | 15–30 m | No | Free |
| **Maxar / Vantor archive** (Earth Pro, ESRI Wayback, Discover) | **Tasked, not daily.** At this quay the Vivid mosaic used **three** 30 cm dates in 2017–2022 (below). | 0.3–0.5 m | **Yes** — same class as Google Earth | Viewers free; extra archive scenes paid |
| **Apple / Bing / Yandex** | Usually **one** current mosaic | ~0.3–0.5 m | One extra snapshot, not more per year | Free to view |
| **Hellenic Cadastre orthophotos** | 2007–09 and 2014–16 | 25–50 cm | Too early. Boat still in Scotland. | Free viewer |

**NASA Worldview / MODIS** is daily and useless here (250 m).

Openers:

- [Copernicus Browser](https://browser.dataspace.copernicus.eu/) — Sentinel-2 / Sentinel-1, this pin
- [ESRI World Imagery Wayback](https://livingatlas.arcgis.com/wayback/) — click the point; use **capture** date (`SRC_DATE`), not the publication title
- [Maxar Discover](https://discover.maxar.com) — full catalog (browse; download is paid)
- Google Earth Pro historical slider — **same Maxar diet** as Wayback, not a denser archive

## High-res dates that actually exist at this quay (ESRI metadata)

Wayback publication titles are **not** capture dates. Identify on the point, 21 Nov 2026:

| Capture (`SRC_DATE`) | Sensor | In the basemap until | Use for this case |
| --- | --- | --- | --- |
| 22 May 2017 | Maxar 0.31 m | Dec 2018 – Dec 2021 publications | Too early (still Scapa / France) |
| **2 Aug 2020** | Maxar 0.31 m | Apr 2022 – Feb 2023 publications | **Three days before** last public Port Vauban page (5 Aug 2020) |
| **21 Oct 2022** | Maxar 0.31 m | Apr 2023 – at least Aug 2024 | After Hermanus Apr 2022; before Street View May 2023 |
| **28 Aug 2025** | Vantor Vivid 0.34 m | Current ESRI / Google mosaic | After both empty auctions; wreck still there |

That is **not** “more photos per year than Google.” It is the **same sparse commercial stack**, with two dates Google Earth may or may not have on the slider: **2 Aug 2020** and **21 Oct 2022**.

## What the tiles show (supported, not a closed hull ID)

Crops in [`photos/`](photos/).

| Date | File | Read |
| --- | --- | --- |
| 2 Aug 2020 | [`wayback-vlycho-20200802-z17-quay.jpg`](photos/wayback-vlycho-20200802-z17-quay.jpg) | Town quay and near-shore balls: ordinary small white boats. **No** isolated 20 m workboat at the later wreck berth. Matches Antibes that week. |
| 21 Oct 2022 | [`wayback-vlycho-20221021-quay.jpg`](photos/wayback-vlycho-20221021-quay.jpg), [`…-quay-north.jpg`](photos/wayback-vlycho-20221021-quay-north.jpg) | Same wall packed with **white yachts**. **No** lone pale hull with a boom. |
| 28 Aug 2025 | [`wayback-vlycho-20250828-wreck.jpg`](photos/wayback-vlycho-20250828-wreck.jpg), [`…-z17-wreck.jpg`](photos/wayback-vlycho-20250828-z17-wreck.jpg) | **One** large pale hull at that wall, **boom** in the water. Matches the listed wreck. |

If that Oct 2022 read holds, the **wall** arrival tightens to **after 21 Oct 2022 and by May 2023**. That **raises April 2023** for the mole tow and **weakens April 2021 / April 2022 as wall dates**.

## Bay / mooring buoys — looked, not found

Family: she sat on a **ball in the bay**, then was moved to the pier. The Maxar mosaics cover the **whole inner bay** (village quay, laid moorings, south shallows, north toward Vliho Yacht Club / Geni). Capture date is the same on the water as on the wall.

Yellow bar on the crops is **20 m** (Sunrise’s recorded length) at that zoom.

| Date | File | What is in the bay | 20 m wooden trawler on a buoy? |
| --- | --- | --- | --- |
| **2 Aug 2020** | [`bay-20200802-moorings-20m.jpg`](photos/bay-20200802-moorings-20m.jpg), [`bay-20200802-z17.jpg`](photos/bay-20200802-z17.jpg) | Yacht-sized boats on balls. Empty south shallows. | **No.** She was still advertised at Port Vauban. |
| **21 Oct 2022** | [`bay-20221021-moorings-20m.jpg`](photos/bay-20221021-moorings-20m.jpg), [`bay-20221021-z18-wide.jpg`](photos/bay-20221021-z18-wide.jpg) | Same mooring field, still yacht-sized. North pontoons: ordinary yachts. No hull matching the later wreck’s length. | **No.** Not on a ball, not on the pier. |
| **28 Aug 2025** | [`bay-20250828-moorings-20m.jpg`](photos/bay-20250828-moorings-20m.jpg), [`bay-20250828-z18.jpg`](photos/bay-20250828-z18.jpg) | Wreck **on the pier** with a boom. Balls still yacht-sized. | **No** — she is already at the wall. |

There is **no public 30 cm frame of Sunrise on a Vlycho buoy**. The ball period, if it happened, sits in the **Maxar gap after 2 Aug 2020 and before 21 Oct 2022** (or she was not in this bay on those two days). iLefkada’s “more than two years in the bay” by 18 Dec 2023 would need her here from ~Dec 2021 — **that is not visible on 21 Oct 2022**. Tag: **supported absence on these mosaics**, not a proof she never used a ball.

**Planet monthly mosaics (21 Nov 2026, low–moderate, not an ID):** first ~15–20 m **candidate** in the inner bay **Dec 2020**; later flags Feb/May 2021, Feb/Apr 2022; last mooring-style flag **Jan 2023**; jetty brightens **May–Jun 2023** (Street View already has her on the wall in **May 2023**). Oct 2022 **not flagged**, agrees Maxar. Full log and the “not flagged ≠ absent” caveat: [`PLANET.md`](PLANET.md).

Nydri harbour and other Lefkada inlets were **not** searched.

## Other maps tried for the buoy years (2021–early 2023)

Working assumption from family/locals: she **was** on a ball in this bay, then dragged to the pier. Google/ESRI simply have **no sharp photo of that stretch**.

| Map | Result |
| --- | --- |
| **Copernicus VHR 2021** (EU 2 m mosaic, veg season 2020–22) | **Free, looked.** Land and the quay strip are there; **the mooring field is blanked** (NoData). It is a land-cover product. Cannot see a buoy. Crop: [`bay-vhr2021-quay-water-masked.jpg`](photos/bay-vhr2021-quay-water-masked.jpg). |
| **Copernicus VHR 2018** | Same water cut-out. Too early anyway (still Scotland/France). |
| **Sentinel-2** | Plenty of dates, **10 m**. A 20 m hull is two pixels. Cannot honestly ID a buoyed trawler. |
| **Planet PlanetScope** | **Daily, 3 m.** Right resolution for a boat-sized object. **Planet AI monthly mosaics run 21 Nov 2026** — filed in [`PLANET.md`](PLANET.md). Auto-flags are **candidates, not IDs**. The screener **missed** the known wreck on the wall for most of 2023–25. |
| **Maxar / Airbus archive** (Discover, SkyWatch) | May have extra 30 cm days that never made it into Google/ESRI. Paid browse/order. |
| **AIS / MarineTraffic** | No public hit on **POL000AYP**. An abandoned boat often has the transponder off. |
| **Apple / Bing / Cadastre** | One mosaic, or too early. Not a 2021–22 time series. |

## What to open next

1. **Planet monthly mosaics already run.** Do **not** re-run the 65-month auto-screener (it missed the known wreck). Next: **daily** PlanetScope **Apr–Jun 2023** (wall week) and **Nov–Dec 2020** (first-candidate week), or SkySat / leftover Maxar 30 cm. Log: [`PLANET.md`](PLANET.md). Prompts below still work if you open a **daily** scene, not another monthly mosaic.

**Prompt 1 — lock the wreck (size and place)**

> Vlycho / Vliho, Lefkada, Greece. Concrete village quay at about 38.6825 N, 20.6989 E (road 105 Επαρ.Οδ. Λευκάδας–Βασιλικής). From May 2023 a ~20 m / 70 ft cream wooden motor vessel, converted trawler, sits against that wall, still floating. By late 2024 / 2025 it is listing with a boom. That hull is MV SUNRISE. Show the pier on PlanetScope. Measure its length on the image. That size is the target. Ignore the small white yachts.

**Prompt 2 — find that same hull on a buoy, then the drag to the pier**

> Same vessel, same size as the wreck you just measured. Search only Vlycho inner bay, water east of that quay (about 38.6815–38.686 N, 20.6995–20.705 E). Monthly mosaics August 2020 to May 2023. Find the first month that oblong sits on a mooring buoy, the last month it is still on a buoy, and the first month it is against the pier. Show a before/after: buoy position → pier position. She was not on this quay in May 2019 and not in this bay on Maxar 2 Aug 2020 (still in France). Maxar 21 Oct 2022 did not show a 20 m hull here — check whether Planet disagrees.

A hit: same ~20 m oblong on the balls for months, then on the wall. Small yachts on buoys are not her. One cloudy month is not a move.
2. **Copernicus Browser** Sentinel-2 true-colour, cloud-filtered, 2021–May 2023 — blob check only; 10 m cannot ID a buoyed hull.
3. **Maxar Discover** for any extra 30 cm scene Aug 2020–May 2023 that the Vivid mosaic skipped.
4. Nydri / other Lefkada inlets — not searched.
