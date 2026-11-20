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

If that Oct 2022 read holds, the **wall** arrival tightens to **after 21 Oct 2022 and by May 2023**. That **raises April 2023** for the mole tow and **weakens April 2021 / April 2022 as wall dates** (she would already have been sitting there by the Oct 2022 mosaic). She can still have been on a **ball** in 2021–22; these tiles show balls in the bay but no obvious 20 m hull on the frames checked.

## What to open next

1. **Planet monthly mosaics** for April 2021, April 2022, April 2023, and Oct 2022–May 2023 — only dataset with both cadence and 3 m.
2. **Copernicus Browser** Sentinel-2 true-colour, cloud-filtered, 2021–May 2023 — cheap “is the wall occupied” blob check; do not treat a 2-pixel blob as ID.
3. **Maxar Discover** for any extra 30 cm scene between Oct 2022 and May 2023 (Earth/ESRI may have skipped it).
4. Earth Pro slider on the **basin**, not only the road.
