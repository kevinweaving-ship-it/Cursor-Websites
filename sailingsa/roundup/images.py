"""R9 image fallback: scored photo → club/class logo → designed text card. No grey box."""

from __future__ import annotations

from pathlib import Path

from sailingsa.roundup.ingest import LIVE_ORIGIN, absolute_media_url

LOGO_HINTS = ("logo", "artwork/club", "artwork/class", "artwork/event", "artwork/sponsor")
OG_HINTS = ("/api/og/", "og-card", "og_card")
LIVE_MEDIA = {
    "2026-10-24-vyc-tour-de-vlei": f"{LIVE_ORIGIN}/sailing-roundup/issues/2026-10-26/media/2026-10-24-vyc-tour-de-vlei-hero.png",
    "2026-10-24-ullman-sails-womens-series-day-2": f"{LIVE_ORIGIN}/sailing-roundup/issues/2026-10-26/media/2026-10-24-ullman-sails-womens-series-day-2-hero.jpg",
    "2026-df95-global-championship": f"{LIVE_ORIGIN}/sailing-roundup/issues/2026-10-26/media/df95-global-2026.png",
}


def classify_page_image(url: str) -> str:
    low = (url or "").lower()
    if any(h in low for h in OG_HINTS):
        return "og"
    if any(h in low for h in LOGO_HINTS):
        return "logo"
    return "photo"


def pick_image(sheet: dict) -> dict:
    """Stay on the live hero slot. Prefer the existing issue media, then logos, then a text card."""
    event_id = sheet["event_id"]
    if event_id in LIVE_MEDIA:
        return {
            "role": "hero",
            "src": LIVE_MEDIA[event_id],
            "fallback": False,
            "credit": "SailingSA" if "df95" not in event_id else "Australian Radio Yachting Association",
            "kind": "photo",
        }
    logos = []
    for raw in sheet.get("page_images") or []:
        url = absolute_media_url(raw)
        kind = classify_page_image(url or "")
        if kind == "logo" and "sailingsa-logo" not in (url or "").lower():
            logos.append(url)
    if logos:
        return {
            "role": "hero",
            "src": logos[0],
            "fallback": True,
            "credit": sheet.get("club") or "SailingSA",
            "kind": "logo",
        }
    return {
        "role": "hero",
        "src": "",
        "fallback": True,
        "credit": "",
        "kind": "text_card",
        "text": sheet.get("name") or "Weekly Roundup",
    }


def write_text_card(path: Path, title: str) -> None:
    """Designed navy 16:9 card so the live hero slot is never a grey Image box."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        _write_svg(path.with_suffix(".svg"), title)
        return
    img = Image.new("RGB", (1170, 658), "#001f3f")
    draw = ImageDraw.Draw(img)
    draw.rectangle((24, 24, 1146, 634), outline="#e5c394", width=2)
    font = ImageFont.load_default()
    draw.text((48, 80), "WEEKLY ROUNDUP", fill="#e5c394", font=font)
    draw.text((48, 280), title[:48], fill="#f4eee4", font=font)
    img.save(path, "PNG")


def _write_svg(path: Path, title: str) -> None:
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="1170" height="658" viewBox="0 0 1170 658">
<rect width="1170" height="658" fill="#001f3f"/>
<rect x="24" y="24" width="1122" height="610" fill="none" stroke="#e5c394" stroke-width="2"/>
<text x="48" y="80" fill="#e5c394" font-family="Arial,sans-serif" font-size="18">WEEKLY ROUNDUP</text>
<text x="48" y="300" fill="#f4eee4" font-family="Georgia,serif" font-size="36">{title}</text>
</svg>
""",
        encoding="utf-8",
    )
