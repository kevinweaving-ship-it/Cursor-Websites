"""Midmar Cup landing-card history row: small cup left, history text right."""

MIDMAR_CUP_RID = "2026-09-19-hmyc-midmar-cup"
MIDMAR_CUP_IMG_SRC = "/artwork/Event Logo/Midmar-Cup.jpg"
MIDMAR_CUP_EVENT_IMG_SRC = "/artwork/Event Logo/Midmar-Cup-Event.jpg"

MIDMAR_CUP_CSS = """
.landing-event-card-story-wrap--with-cup {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 10px;
}
.landing-event-card-story-wrap--with-cup .sa-home-regatta-children-head {
    flex: 1 1 auto;
    min-width: 0;
}
.temp-landing-hero-image .landing-event-cup-img,
.temp-landing-secondary-image .landing-event-cup-img,
#landing-event-hero-2 .landing-event-cup-img,
.landing-event-cup-img {
    display: block !important;
    width: auto !important;
    height: 72px !important;
    max-width: 52px !important;
    max-height: 72px !important;
    object-fit: contain !important;
    margin: 4px 0 4px 8px !important;
    float: none !important;
    background: transparent;
    flex: 0 0 auto;
}
.landing-event-card--live:has(a[href*="hmyc-midmar-cup"]) .landing-event-card-count {
    animation: midmar-live-invert 2.8s ease-in-out infinite alternate;
}
@keyframes midmar-live-invert {
    from {
        background: #fff1e6;
        border-color: #f5ac86;
        color: #9a3412;
    }
    to {
        background: #9a3412;
        border-color: #9a3412;
        color: #fff1e6;
    }
}
@media (prefers-reduced-motion: reduce) {
    .landing-event-card--live:has(a[href*="hmyc-midmar-cup"]) .landing-event-card-count {
        animation: none;
    }
}
"""


def is_midmar_cup_card(url_or_id: str) -> bool:
    return MIDMAR_CUP_RID in str(url_or_id or "")


def midmar_event_mm_videos() -> list:
    """Seed MM reels payload for the Midmar event URL. More clips can be appended later."""
    return [
        {
            "id": "midmar-cup-1",
            "kind": "photo",
            "title": "Midmar Cup",
            "thumb": MIDMAR_CUP_EVENT_IMG_SRC,
            "play_url": MIDMAR_CUP_EVENT_IMG_SRC,
            "aspect": "3 / 4",
        }
    ]


def midmar_cup_img_html() -> str:
    return (
        f'<img class="landing-event-cup-img" src="{MIDMAR_CUP_IMG_SRC}" '
        f'alt="Midmar Cup" width="52" height="78" loading="lazy" decoding="async">'
    )


def wrap_story_html(story: str, url_or_id: str = "") -> str:
    """Story/history block. Midmar gets the cup image on the left."""
    story = (story or "").strip()
    if not story:
        return ""
    wrap_mod = ""
    cup = ""
    if is_midmar_cup_card(url_or_id):
        wrap_mod = " landing-event-card-story-wrap--with-cup"
        cup = midmar_cup_img_html()
    return (
        f'<div class="sa-home-regatta-children landing-event-card-story-wrap{wrap_mod}">'
        f"{cup}"
        f'<div class="sa-home-regatta-children-head">'
        f'<p class="landing-event-card-story">{story}</p>'
        f"</div></div>"
    )
