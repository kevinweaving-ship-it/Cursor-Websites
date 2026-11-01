# SailingSA search intentions — research baseline (1 November 2026)

## Provenance
User-supplied candidate percentages attributed to Google; NOT externally verified. Do not present as actual search volumes, or tune rankings to these percentages without corroboration.

## Candidate list (preserve supplied order/values)
- Event 12.0%
- Results 10.0%
- Weather forecast 7.0%
- Wind forecast 6.5%
- Tide times 5.0%
- Class 4.5%
- Sailor name 4.0%
- Live tracking 4.0%
- Boat name 3.5%
- Charter boats 3.0%
- Sailing rules 2.5%
- Notice of Race 2.5%
- Sailing instructions 2.5%
- Notice to mariners 2.0%
- Marine chart 2.0%
- Sail No 1.5%
- Sail trim 1.5%
- Rig tension 1.5%
- Boat tuning guide 1.5%
- Knots guide 1.5%
- Navigation app 1.5%
- Marine GPS 1.0%
- Foul weather gear 1.0%
- Life jacket 1.0%
- Sailing boots 1.0%
- Sailing gloves 1.0%
- Blocks and shackles 1.0%
- Rope splicing 1.0%
- Anchor chain 0.8%
- VHF radio channels 0.8%
- AIS tracking 0.8%
- EPIRB registration 0.8%
- Marine battery 0.8%
- Outboard motor repair 0.8%
- Antifouling paint 0.8%
- Sail repair tape 0.8%
- Winch maintenance 0.5%
- Bimini top 0.5%
- Bilge pump 0.5%
- Marine toilet 0.5%
- Boat insurance 0.5%
- Sailing license 0.5%
- Marinas near me 0.5%
- Boat ramp 0.5%
- Mooring fees 0.5%
- Sailing club 0.5%
- Sailing school 0.5%
- Crew finder 0.5%
- Boat for sale 0.5%
- Yacht survey 0.3%

## Verified internal REA preliminary audit (2026-11-01)
- site_traffic_events: 419,546 rows from 2026-08-25 to 2026-11-01, contains heartbeats, scrolls and other interactions; NOT 419,546 searches.
- Last 90 days, is_bot=false: 26,029 click events.
- Last 30 days search-related click_text: Regatta 242, Sailors name 83, Sailor 75. These are click labels, NOT unique query volumes.
- traffic_events has only 22 historical rows and cannot support a full search-term report.
- Dedicated search query logging has not been verified. Avoid overclaiming.

## Search intent routing strategy
1. Native entity relevance: event, race results, class, club, sailor, boat, sail number, NOR, sailing instructions, live tracking. Use real database associations; support aliases / historic events.
2. Intent-aware suggestions: weather, wind, tides, rules, education, marine charts, navigational resources, equipment, boat services; link only to verified functioning relevant destinations. Do not fabricate SailingSA pages.
3. Relevance scoring should prioritize matching actual named entity and search intent, with query popularity learned from privacy-conscious aggregated on-site typed queries, successful result clicks, empty-result rates and reformulations, deduplicated sessions and bot exclusion.
4. UI contract: exactly one mixed search-results list, every result has a left logo/photo/icon (including fallback), no category selection required.
5. Do not mistake broad general recreational marine searches for Sailingsa's specific demand. Validate with Search Console for the actual property if available, analytics, server access logs and search interaction telemetry.
