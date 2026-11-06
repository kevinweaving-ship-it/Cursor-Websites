#!/usr/bin/env python3
"""Known sailing sponsors: slug, match terms, public details.

Headline (main) = brand appears in the event title.
Tier 2 = supporting sponsor found later via web/Google, name not in the title.
"""
from __future__ import annotations

import re

# Longer match keys first when scanning titles.
SPONSOR_DISPLAY = {
    "north sails": "North Sails",
    "ullman sails": "Ullman Sails",
    "macs shipping": "MACS Shipping",
    "southern wind": "Southern Wind",
    "laser performance": "Laser Performance",
    "uk sailmakers": "UK Sailmakers",
    "genmac": "Genmac",
    "intasure": "Intasure",
    "sailworld": "Sailworld",
    "quantum": "Quantum",
    "harken": "Harken",
    "musto": "Musto",
    "zhik": "Zhik",
    "ullman": "Ullman Sails",
    "nitro": "Nitro",
    "cell c": "Cell C",
    "cell-c": "Cell C",
    "h2o": "H2O",
    "h20": "H2O",
    "h₂o": "H2O",
    "amtec": "AMTEC",
    "seaport supply": "Seaport Supply",
    "seaport": "Seaport Supply",
    "jonsson": "Jonsson",
    "jonsson workwear": "Jonsson Workwear",
    "aquelle": "aQuellé",
    "a quelle": "aQuellé",
    "blue bay lodge": "Blue Bay Lodge",
    "southern ropes": "Southern Ropes",
    "ropeworx": "RopeWorx",
    "stp-intasure": "STP-Intasure",
    "stp intasure": "STP-Intasure",
    "viking": "Viking",
    "albion": "Albion",
    "miller gold": "Miller Gold & Co",
    "miller gold & co": "Miller Gold & Co",
    "msc": "MSC",
    "shane's gaul": "Shane's Gaul",
    "shane gaul": "Shane's Gaul",
}

# slug -> public profile (website / about). JSON/DB can override.
CATALOG: list[dict] = [
    {
        "slug": "ullman",
        "aliases": ["ullman-sails"],
        "display_name": "Ullman Sails",
        "short_name": "Ullman",
        "logo_path": "/artwork/Sponsor Logo/Ullman-Sails.png",
        "website_url": "https://ullmansails.com/lofts/south-africa/",
        "about_text": "Ullman Sails Cape Town loft. Title sponsor of the Ullman Sails Women's Series at Royal Cape Yacht Club.",
        "match_terms": ["ullman sails", "ullman"],
        "tier": "headline",
        "city": "Cape Town",
        "country": "South Africa",
    },
    {
        "slug": "north-sails",
        "aliases": ["northsails", "north"],
        "display_name": "North Sails",
        "short_name": "North",
        "logo_path": "/artwork/Sponsor Logo/North-Sails.png",
        "website_url": "https://www.northsails.com/sailing/en/locations/capetown-south-africa-2",
        "about_text": "North Sails is a global sailmaker with a Cape Town loft. Appears on South African championships and series including the North Sails J22 Championships.",
        "match_terms": ["north sails"],
        "tier": "headline",
        "city": "Cape Town",
        "country": "South Africa",
    },
    {
        "slug": "nitro",
        "aliases": ["nitro-sails", "team-nitro", "nitro-sailing-team"],
        "display_name": "Nitro",
        "short_name": "Nitro",
        "logo_path": "/artwork/Sponsor Logo/Nitro.png",
        "website_url": "https://www.facebook.com/NitroSailingTeam",
        "about_text": "NITRO Sailing Team is a Cape Town based team of sailors racing on Nitro Yachts. Live like there is no tomorrow!",
        "match_terms": ["nitro", "nitro sailing", "nitro sailing team", "nitro yachts"],
        "tier": "headline",
        "city": "Cape Town",
        "country": "South Africa",
    },
    {
        "slug": "cell-c",
        "aliases": ["cellc", "cell"],
        "display_name": "Cell C",
        "short_name": "Cell C",
        "logo_path": "/artwork/Sponsor Logo/Cell-C.png",
        "website_url": "https://www.cellc.co.za/",
        "about_text": "Cell C — branded racing entry appearing on South African J22 campaigns (boat name Cell C).",
        "match_terms": ["cell c", "cell-c"],
        "tier": "headline",
        "country": "South Africa",
    },
    {
        "slug": "h2o",
        "aliases": ["h20", "bwt", "h2o-international", "bwt-south-africa"],
        "display_name": "H2O",
        "short_name": "H2O",
        "logo_path": "/artwork/Sponsor Logo/H2O.png",
        "website_url": "https://bwtshop.co.za/",
        "about_text": (
            "Established in 1994 as H2O International South Africa, we are without a doubt the industry "
            "leading force in water purification on the African continent. Today, we are known as BWT "
            "and with a team of passionate Head office staff and franchisees. BWT has a proven track "
            "record for many years of unmatched expertise and product range stretching not only "
            "throughout South Africa, but also into Namibia, Botswana, Mozambique and Nigeria."
        ),
        "match_terms": ["h2o", "h20", "bwt", "h2o international"],
        "tier": "headline",
        "country": "South Africa",
    },
    {
        "slug": "amtec",
        "aliases": ["amtec-racing", "applied-mineral-technologies"],
        "display_name": "AMTEC",
        "short_name": "AMTEC",
        "logo_path": "/artwork/Sponsor Logo/AMTEC.png",
        "website_url": "https://amtec.co.za/",
        "about_text": (
            "Founded in 2000, AMTEC has grown into a trusted leader in construction and engineering "
            "services for the mining, materials handling, heavy industrial, water treatment and paper "
            "& pulp sectors across Southern Africa. Proudly Level 1 B-BBEE certified, AMTEC is a "
            "people-first, purpose-driven company."
        ),
        "match_terms": ["amtec", "amtec racing"],
        "tier": "headline",
        "country": "South Africa",
        "city": "eMalahleni",
        "province": "Mpumalanga",
    },
    {
        "slug": "genmac",
        "aliases": ["genmac-international"],
        "display_name": "Genmac",
        "short_name": "Genmac",
        "website_url": "https://www.genih.com/",
        "logo_path": "/artwork/Sponsor Logo/Genmac.png",
        "tier": "headline",
        "about_text": "Genmac International Holdings (GIH) is a consulting engineering firm. Title sponsor of the 2023 SA Sailing Youth Nationals at Henley Midmar Yacht Club.",
        "match_terms": ["genmac"],
        "country": "South Africa",
    },
    {
        "slug": "intasure",
        "aliases": ["stp-intasure", "stpintasure", "stp"],
        "display_name": "Intasure",
        "short_name": "Intasure",
        "logo_path": "/artwork/Sponsor Logo/Intasure.png",
        "website_url": "https://www.intasure.com/",
        "about_text": "South African insurance (incl. STP-Intasure branding). Headline on FBYC Intasure Spring Regatta and SASWC Intasure Interschools; 2nd-tier on Western Cape Dinghy Championships 2026.",
        "match_terms": ["intasure", "stp-intasure", "stp intasure"],
        "tier": "headline",
        "country": "South Africa",
    },
    {
        "slug": "macs-shipping",
        "aliases": ["macs"],
        "display_name": "MACS Shipping",
        "short_name": "MACS",
        "website_url": "https://www.macship.com/",
        "logo_path": "/artwork/Sponsor Logo/MACS-Shipping.svg",
        "about_text": "MACS Shipping. Title sponsor of ZVYC club championships in years the brand appeared on the event name.",
        "match_terms": ["macs shipping"],
        "tier": "headline",
        "country": "South Africa",
    },
    {
        "slug": "zhik",
        "aliases": [],
        "display_name": "Zhik",
        "short_name": "Zhik",
        "logo_path": "/artwork/Sponsor Logo/Zhik.png",
        "website_url": "https://www.zhik.com/",
        "about_text": "Zhik makes sailing apparel and equipment. Title sponsor of the Zhik Double Handed Series.",
        "match_terms": ["zhik"],
        "tier": "headline",
    },
    {
        "slug": "southern-wind",
        "aliases": ["southernwind"],
        "display_name": "Southern Wind",
        "short_name": "Southern Wind",
        "logo_path": "/artwork/Sponsor Logo/Southern-Wind.png",
        "website_url": "https://www.southernwind.com/",
        "about_text": "Southern Wind Shipyard, Cape Town. Named on the Southern Wind WC/EC Hobie 16 Provincial Championships.",
        "match_terms": ["southern wind"],
        "tier": "headline",
        "city": "Cape Town",
        "country": "South Africa",
    },
    {
        "slug": "seaport-supply",
        "aliases": ["seaport"],
        "display_name": "Seaport Supply",
        "short_name": "Seaport",
        "logo_path": "/artwork/Sponsor Logo/Seaport-Supply.png",
        "website_url": "https://seaportsupply.co.za/",
        "about_text": "Cape Town marine equipment distributor. Title sponsor of the Seaport Supply West Coast Offshore.",
        "match_terms": ["seaport supply", "seaport"],
        "tier": "headline",
        "city": "Cape Town",
        "country": "South Africa",
    },
    {
        "slug": "shanes-gaul",
        "aliases": ["shane-gaul", "gaul"],
        "display_name": "Shane's Gaul",
        "short_name": "Shane's Gaul",
        "website_url": "https://www.sailing.org.za/",
        "about_text": "Shane's Gaul Regatta is the yearly GBYC named event. Calendar titles sometimes shorten it to Gaul Regatta.",
        "logo_path": "/artwork/Sponsor Logo/Shanes-Gaul.png",
        "match_terms": ["shane's gaul", "shane gaul", "gaul regatta", "gbyc gaul"],
        "tier": "headline",
        "country": "South Africa",
    },
    {
        "slug": "msc",
        "aliases": ["msc-cruises"],
        "display_name": "MSC",
        "short_name": "MSC",
        "logo_path": "/artwork/Sponsor Logo/MSC.png",
        "website_url": "https://www.msc.com/",
        "about_text": "MSC. Named on MSC Week and the MSC Commodore's Cup.",
        "match_terms": ["msc week", "msc commodore", "msc dinghy"],
        "tier": "headline",
    },
    {
        "slug": "jonsson",
        "aliases": ["pyc-jonsson"],
        "display_name": "Jonsson Workwear",
        "short_name": "Jonsson",
        "logo_path": "/artwork/Sponsor Logo/Jonsson-Workwear.png",
        "website_url": "https://www.jonssonworkwear.com/",
        "about_text": "Title name on the PYC Jonsson Cup, a yearly Point Yacht Club event.",
        "match_terms": ["jonsson cup", "jonsson"],
        "tier": "headline",
        "city": "Durban",
        "country": "South Africa",
    },
    {
        "slug": "miller-gold",
        "aliases": ["miller-gold-and-co", "miller-gold-co", "mgandco"],
        "display_name": "Miller Gold & Co",
        "short_name": "Miller Gold",
        "logo_path": "/artwork/Sponsor Logo/Miller-Gold.png",
        "website_url": "https://mgandco.co.za/",
        "about_text": "Miller Gold & Co (Miller Gold House (Pty) Ltd) was established in 1992 by Sindy Miller, a GIA and Jewellery Council SA jewellery professional with 34 years' industry experience. The house specialises in premium new and pre-owned jewellery, vintage and antique jewellery, natural diamonds, gemstones, watches, Krugerrands, engagement rings, valuations and bespoke / design-a-ring work. Every showcased piece is specifically selected for uniqueness, quality and authenticity. Pre-owned jewellery and gold coins are authenticated by expert gemologists. Miller Gold is FICA registered and FICA compliant. Headline sponsor of the 2026 TSC 420 Nationals.",
        "match_terms": ["miller gold", "miller gold & co", "miller gold and co"],
        "tier": "headline",
        "city": "Cape Town",
        "country": "South Africa",
    },
    {
        "slug": "albion",
        "aliases": ["albion-press", "albion-supply-chain"],
        "display_name": "Albion",
        "short_name": "Albion",
        "logo_path": "/artwork/Sponsor Logo/Albion.png",
        "about_text": "Albion Supply Chain Management, a division of Albion Press. 2nd-tier sponsor of Western Cape Dinghy Championships 2026 (SBYC).",
        "match_terms": ["albion supply", "albion press"],
        "tier": "tier2",
        "country": "South Africa",
    },
    {
        "slug": "aquelle",
        "aliases": ["a-quelle"],
        "display_name": "aQuellé",
        "short_name": "aQuellé",
        "logo_path": "/artwork/Sponsor Logo/aQuelle.svg",
        "website_url": "https://www.aquelle.co.za/",
        "about_text": "South African bottled water brand. 2nd-tier sponsor of Western Cape Dinghy Championships 2026 (SBYC).",
        "match_terms": ["aquelle", "a quelle"],
        "tier": "tier2",
        "country": "South Africa",
    },
    {
        "slug": "blue-bay-lodge",
        "aliases": ["blue-bay"],
        "display_name": "Blue Bay Lodge & Resort",
        "short_name": "Blue Bay Lodge",
        "logo_path": "/artwork/Sponsor Logo/Blue-Bay-Lodge.png",
        "website_url": "https://www.bluebaylodge.co.za/",
        "about_text": "Saldanha lodge and resort. 2nd-tier sponsor and launch venue partner for Western Cape Dinghy Championships 2026.",
        "match_terms": ["blue bay lodge"],
        "tier": "tier2",
        "city": "Saldanha",
        "country": "South Africa",
    },
    {
        "slug": "brights",
        "aliases": ["brights-hardware"],
        "display_name": "Brights Hardware",
        "short_name": "Brights",
        "logo_path": "/artwork/Sponsor Logo/Brights.jpg",
        "about_text": "Brights Hardware Store. 2nd-tier sponsor of Western Cape Dinghy Championships 2026 (SBYC).",
        "match_terms": ["brights hardware"],
        "tier": "tier2",
        "country": "South Africa",
    },
    {
        "slug": "cam-ra",
        "aliases": ["camra", "cam-ra-productions"],
        "display_name": "CaM-Ra Productions",
        "short_name": "CaM-Ra",
        "logo_path": "/artwork/Sponsor Logo/Cam-Ra.jpeg",
        "about_text": "CaM-Ra Productions. 2nd-tier media sponsor of Western Cape Dinghy Championships 2026 (SBYC).",
        "match_terms": ["cam-ra", "cam ra productions"],
        "tier": "tier2",
        "country": "South Africa",
    },
    {
        "slug": "central-boating",
        "aliases": [],
        "display_name": "Central Boating",
        "short_name": "Central Boating",
        "logo_path": "/artwork/Sponsor Logo/Central-Boating.jpeg",
        "about_text": "Central Boating. 2nd-tier sponsor of Western Cape Dinghy Championships 2026 (SBYC).",
        "match_terms": ["central boating"],
        "tier": "tier2",
        "country": "South Africa",
    },
    {
        "slug": "ropeworx",
        "aliases": ["rope-worx"],
        "display_name": "RopeWorx",
        "short_name": "RopeWorx",
        "logo_path": "/artwork/Sponsor Logo/RopeWorx.png",
        "website_url": "https://ropeworx.co.za/",
        "about_text": "RopeWorx. 2nd-tier sponsor of Western Cape Dinghy Championships 2026 (SBYC).",
        "match_terms": ["ropeworx"],
        "tier": "tier2",
        "country": "South Africa",
    },
    {
        "slug": "saldanha-bay-hotel",
        "aliases": ["sbh"],
        "display_name": "Saldanha Bay Hotel",
        "short_name": "Saldanha Bay Hotel",
        "logo_path": "/artwork/Sponsor Logo/Saldanha-Bay-Hotel.png",
        "about_text": "Saldanha Bay Hotel. 2nd-tier sponsor of Western Cape Dinghy Championships 2026 (SBYC).",
        "match_terms": ["saldanha bay hotel"],
        "tier": "tier2",
        "city": "Saldanha",
        "country": "South Africa",
    },
    {
        "slug": "southern-ropes",
        "aliases": [],
        "display_name": "Southern Ropes",
        "short_name": "Southern Ropes",
        "logo_path": "/artwork/Sponsor Logo/Southern-Ropes.svg",
        "website_url": "https://www.southernropes.com/",
        "about_text": "Southern Ropes. 2nd-tier sponsor of Western Cape Dinghy Championships 2026 (SBYC).",
        "match_terms": ["southern ropes"],
        "tier": "tier2",
        "country": "South Africa",
    },
    {
        "slug": "viking",
        "aliases": ["viking-life-saving"],
        "display_name": "Viking Life-Saving Equipment",
        "short_name": "Viking",
        "logo_path": "/artwork/Sponsor Logo/Viking.svg",
        "website_url": "https://www.viking-life.com/",
        "about_text": "Viking Life-Saving Equipment. 2nd-tier sponsor of Western Cape Dinghy Championships 2026 (SBYC).",
        "match_terms": ["viking life-saving", "viking life saving"],
        "tier": "tier2",
    },
]


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return s or "sponsor"


def catalog_by_slug() -> dict[str, dict]:
    out = {}
    for item in CATALOG:
        slug = (item.get("slug") or "").strip().lower()
        if slug:
            out[slug] = dict(item)
    return out


def alias_to_slug() -> dict[str, str]:
    out = {}
    for item in CATALOG:
        slug = (item.get("slug") or "").strip().lower()
        if not slug:
            continue
        out[slug] = slug
        for a in item.get("aliases") or []:
            a = (a or "").strip().lower().strip("/")
            if a:
                out[a] = slug
    return out


def extract_sponsor(original_name: str) -> str:
    s = (original_name or "").lower().replace("&amp;", "&")
    for key in sorted(SPONSOR_DISPLAY.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", s):
            return SPONSOR_DISPLAY[key]
    return ""


def slug_for_display_name(display: str) -> str:
    want = (display or "").strip().lower()
    for item in CATALOG:
        if (item.get("display_name") or "").strip().lower() == want:
            return item["slug"]
    return _slugify(display)
