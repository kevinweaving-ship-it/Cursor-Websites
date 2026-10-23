"""Render the WhatsApp alert graphics (all-graphic cards, no text rows).

WhatsApp shows a link-preview card at roughly 1.91:1 and crops anything taller, so both cards are
rendered at 720x377 (1.91:1) and nothing important sits near the edges.

main card : site | date | time  /  door+lock Area STATE | user | source  /  power  /  4 stills  /  "tap this card to REPLAY"
live card : smaller blue LIVE action card (separate message under the main card).
"""
import base64
import io
import json
import os
import time
import ssl
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CAMS = [("garage", "Garage"), ("workshop", "Workshop"), ("pool", "Pool"), ("driveway", "Driveway")]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
W, H, PAD, GAP = 720, 377, 12, 6
STATE_COLOUR = {"disarmed": "#15803d", "armed": "#1d4ed8", "alarm": "#dc2626"}
_emoji_cache = {}


SNAP_AGES = {}   # cam -> seconds old, filled by fetch_snaps (0 = live frame)


def _get_json(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout, context=ssl.create_default_context()) as r:
        return json.loads(r.read())


def fetch_snaps(url, timeout=6, wait_fresh_s=5, stale_ok_s=1800):
    """Camera stills for the card. The snapshot files are only refreshed while the streams are warm, so: ping /warm,
    give the producers up to wait_fresh_s to deliver a live frame for all four cams, then fill any gap with the newest
    still up to stale_ok_s old (age recorded in SNAP_AGES and stamped on the tile). Never a black box if any frame exists."""
    SNAP_AGES.clear()
    base = url.split("/snaps.json", 1)[0]
    try:
        _get_json(base + "/warm", 3)
    except Exception:  # noqa: BLE001
        pass
    d, deadline = {}, time.time() + wait_fresh_s
    while True:
        try:
            d = _get_json(url + ("&" if "?" in url else "?") + "max_age=15", timeout) or {}
        except Exception:  # noqa: BLE001
            d = {}
        if len([k for k in d if not k.startswith("_")]) >= 4 or time.time() >= deadline:
            break
        time.sleep(1)
    fresh = {k: v for k, v in d.items() if not k.startswith("_")}
    ages = dict(d.get("_age_s") or {})
    if len(fresh) < 4:
        try:
            old = _get_json(url + ("&" if "?" in url else "?") + "max_age=%d" % stale_ok_s, timeout) or {}
        except Exception:  # noqa: BLE001
            old = {}
        for k, v in old.items():
            if k.startswith("_") or k in fresh:
                continue
            fresh[k] = v
            ages[k] = (old.get("_age_s") or {}).get(k, stale_ok_s)
    out = {}
    for k, v in fresh.items():
        try:
            out[k] = Image.open(io.BytesIO(base64.b64decode(v.split(",", 1)[1]))).convert("RGB")
            SNAP_AGES[k] = int(ages.get(k, 0))
        except Exception:  # noqa: BLE001
            pass
    return out


def _font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_B if bold else FONT, size)
    except OSError:
        return ImageFont.load_default()


def _emoji_font(ch, size):
    """Colour emoji as RGBA (Noto Color Emoji is a 109px bitmap font; render there, then scale)."""
    key = (ch, size)
    if key in _emoji_cache:
        return _emoji_cache[key]
    try:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox() or (0, 0, 1, 1))
        im.thumbnail((size, size), Image.LANCZOS)
    except Exception:  # noqa: BLE001
        im = Image.new("RGBA", (size, size), (148, 163, 184, 255))
    _emoji_cache[key] = im
    return im


def _icon_dir() -> str:
    """Sailing cards used Tabler outline SVGs. Aerialnet does not have /var/www/sailingsa."""
    here = Path(__file__).resolve().parent
    extra = (os.getenv("WA_CARD_ICON_DIR") or "").strip()
    cands = [
        here / "icons" / "tabler" / "outline",
        Path("/opt/arial-whatsapp-poc/icons/tabler/outline"),
        Path("/var/www/sailingsa/assets/icons/tabler/outline"),
        Path("/home/user-data/www/aerialnet.co.za/assets/icons/tabler/outline"),
    ]
    if extra:
        cands.insert(0, Path(extra))
    for p in cands:
        try:
            if p.is_dir() and (p / "map-pin.svg").is_file():
                return str(p) + "/"
        except OSError:
            continue
    return str(cands[0]) + "/"


ICON_DIR = _icon_dir()
_icon_cache: dict = {}
# emoji -> (tabler icon, colour) so the card uses the same line icons as the web pages
EMOJI_ICON = {"\U0001F4CD": ("map-pin", "#1e293b"), "\U0001F4C5": ("calendar", "#1e293b"), "\U0001F552": ("clock", "#1e293b"),
              "\U0001F6AA": ("door", "#1e293b"), "\U0001F513": ("lock-open", "#15803d"), "\U0001F512": ("lock", "#1d4ed8"), "\U0001F6A8": ("bell-ringing", "#dc2626"),
              "\U0001F464": ("user", "#1e293b"), "\U0001F4E1": ("device-mobile", "#1e293b"), "\u26A1": ("bolt", "#b45309"),
              "\u2705": ("circle-check", "#15803d"), "\u274C": ("circle-x", "#dc2626"), "\u2753": ("help-circle", "#64748b"),
              "\U0001F449": ("hand-click", "#ffffff"), "\U0001F534": ("circle", "#dc2626")}


def svg_icon(name, size, colour):
    """Tabler outline SVG rendered to an RGBA bitmap via rsvg-convert (stroke recoloured); cached per name/size/colour."""
    key = (name, size, colour)
    if key in _icon_cache:
        return _icon_cache[key]
    import subprocess
    try:
        svg = open(ICON_DIR + name + ".svg", encoding="utf-8").read().replace('stroke="currentColor"', f'stroke="{colour}"')
        png = subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size)], input=svg.encode(), capture_output=True, timeout=10, check=True).stdout
        im = Image.open(io.BytesIO(png)).convert("RGBA")
    except Exception:  # noqa: BLE001
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    _icon_cache[key] = im
    return im


def emoji(ch, size):
    """Icon for an emoji code point: Tabler line icon where mapped, else the colour-emoji font."""
    if ch in EMOJI_ICON:
        name, col = EMOJI_ICON[ch]
        return svg_icon(name, size, col)
    return _emoji_font(ch, size)


def _row(d, im, x, y, items, font, colour="#1e293b"):
    """items: list of (emoji_str|None, text, colour|None). Returns end x."""
    for em, text, col in items:
        if em:
            for ch in em.split(" "):
                e = emoji(ch, font.size + 4)
                im.paste(e, (x, y + (font.size + 4 - e.height) // 2 - 1), e)
                x += e.width + 4
            x += 2
        if text:
            d.text((x, y), text, font=font, fill=col or colour)
            x += int(d.textlength(text, font=font)) + 10
    return x


def _sep(d, x, y, h):
    d.line((x, y + 4, x, y + h - 4), fill="#cbd5e1", width=2)
    return x + 12


def _fit(d, text, font, max_w):
    while text and d.textlength(text, font=font) > max_w:
        text = text[:-2] + "\u2026"
    return text


def render_main(site, date, time_, area, state, user, via, power_ok, snaps):
    """Square 720x720 card; everything inside a centred safe area so the phone's centre-crop of the preview
    (WhatsApp iOS shows link previews as a square crop) never cuts content."""
    st = (state or "").upper()
    kind = "alarm" if "ALARM" in st or "PANIC" in st or "FIRE" in st else "armed" if st == "ARMED" else "disarmed" if st == "DISARMED" else "other"
    sc = STATE_COLOUR.get(kind, "#334155")
    SZ, S = 720, 56                      # canvas, safe margin
    L, R = S, SZ - S                     # safe x-range (608 px wide)
    ROW_H, G = 46, 6
    im = Image.new("RGB", (SZ, SZ), "#ffffff")
    d = ImageDraw.Draw(im)
    f = _font(22, True)
    maxw = R - L
    # row 1: site | date | time
    y = S
    d.rounded_rectangle((L, y, R, y + ROW_H), 9, fill="#eef2f7")
    x = _row(d, im, L + 10, y + 10, [("\U0001F4CD", _fit(d, site, f, 200), "#111827")], f)
    x = _sep(d, x, y, ROW_H)
    x = _row(d, im, x, y + 10, [("\U0001F4C5", date, "#111827")], f)
    x = _sep(d, x, y, ROW_H)
    _row(d, im, x, y + 10, [("\U0001F552", time_, "#111827")], f)
    # row 2: event
    y += ROW_H + G
    d.rounded_rectangle((L, y, R, y + ROW_H), 9, fill={"alarm": "#fee2e2", "armed": "#dbeafe", "disarmed": "#dcfce7"}.get(kind, "#f1f5f9"))
    lock = "\U0001F6A8" if kind == "alarm" else "\U0001F512" if kind == "armed" else "\U0001F513"
    x = _row(d, im, L + 10, y + 10, [("\U0001F6AA " + lock, _fit(d, f"{area} ", f, 220), "#111827")], f)
    x = _row(d, im, x - 10, y + 10, [(None, st, sc)], f)
    if user:
        x = _sep(d, x, y, ROW_H)
        x = _row(d, im, x, y + 10, [("\U0001F464", _fit(d, user, f, 130), "#111827")], f)
    if via and d.textlength(via, font=f) + x + 50 < R:
        x = _sep(d, x, y, ROW_H)
        _row(d, im, x, y + 10, [("\U0001F4E1", via, "#111827")], f)
    # row 3: power
    y += ROW_H + G
    ok = power_ok
    d.rounded_rectangle((L, y, R, y + ROW_H), 9, fill="#f1f5f9" if ok is None else "#dcfce7" if ok else "#fee2e2")
    ptxt = "Power unknown" if ok is None else "Power OK" if ok else "A/C FAILURE \u00b7 alarm on battery"
    _row(d, im, L + 10, y + 10, [("\u26A1 " + ("\u2753" if ok is None else "\u2705" if ok else "\u274C"), ptxt, "#111827" if ok else "#b91c1c")], f)
    # 2x2 stills
    y += ROW_H + G + 2
    tw_ = (maxw - G) // 2
    th_ = tw_ * 9 // 16
    for i, (cam, label) in enumerate(CAMS):
        cx = L + (i % 2) * (tw_ + G)
        cy = y + (i // 2) * (th_ + G)
        tile = snaps.get(cam)
        if tile is not None:
            im.paste(tile.resize((tw_, th_)), (cx, cy))
        else:
            d.rectangle((cx, cy, cx + tw_, cy + th_), fill="#111827")
            d.text((cx + tw_ // 2, cy + th_ // 2), "no image", font=_font(15), fill="#9ca3af", anchor="mm")
        lf = _font(15, True)
        lw = d.textlength(label, font=lf)
        d.rounded_rectangle((cx + 6, cy + 6, cx + 6 + lw + 12, cy + 28), 4, fill="#000000")
        d.text((cx + 12, cy + 9), label, font=lf, fill="#ffffff")
        age = SNAP_AGES.get(cam, 0)
        if tile is not None and age > 20:
            at = ("%d min ago" % max(1, round(age / 60))) if age < 3600 else ("%dh ago" % (age // 3600))
            af = _font(13, True)
            aw = d.textlength(at, font=af)
            d.rounded_rectangle((cx + tw_ - aw - 18, cy + th_ - 24, cx + tw_ - 6, cy + th_ - 6), 4, fill="#7c2d12")
            d.text((cx + tw_ - aw - 12, cy + th_ - 22), at, font=af, fill="#ffffff")
    # footer: click target
    fy = y + 2 * th_ + G + G + 2
    fh = min(56, SZ - S - fy)
    d.rounded_rectangle((L, fy, R, fy + fh), 9, fill="#0f2747")
    ff = _font(24, True)
    text = "TAP CARD TO REPLAY  \u22125s / +15s"
    e = emoji("\U0001F449", ff.size + 6)
    total = e.width + 10 + d.textlength(text, font=ff)
    x = int((SZ - total) // 2)
    im.paste(e, (x, fy + (fh - e.height) // 2), e)
    d.text((x + e.width + 10, fy + fh // 2), text, font=ff, fill="#ffffff", anchor="lm")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=84, optimize=True)
    return buf.getvalue()


def render_live(site):
    im = Image.new("RGB", (W, H), "#1d6fe0")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((PAD, PAD, W - PAD, H - PAD), 16, fill="#1a5fc4", outline="#60a5fa", width=3)
    f = _font(64, True)
    e = emoji("\U0001F534", 68)
    tw = d.textlength("LIVE", font=f)
    x = int((W - (e.width + 22 + tw)) // 2)
    im.paste(e, (x, 100), e)
    d.text((x + e.width + 22, 92), "LIVE", font=f, fill="#ffffff")
    d.text((W // 2, 226), f"View all 4 cameras live \u00b7 {site}", font=_font(24), fill="#dbeafe", anchor="mm")
    d.text((W // 2, 280), "\u261B  TAP THIS CARD FOR LIVE", font=_font(22, True), fill="#ffffff", anchor="mm")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()


def thumb(jpeg_bytes, size=320):
    im = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    im.thumbnail((size, size))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70)
    return buf.getvalue()


if __name__ == "__main__":
    import sys
    snaps = fetch_snaps(sys.argv[1] if len(sys.argv) > 1 else "https://aerialnet.co.za/voelklip/hik/snaps.json")
    m = render_main("Vo\u00eblklip", "05 Sep 26", "18:21", "Garage", "DISARMED", "Kevin", "Remote", True, snaps)
    open("/tmp/card_main.jpg", "wb").write(m)
    open("/tmp/card_live.jpg", "wb").write(render_live("Vo\u00eblklip"))
    print("snaps", sorted(snaps), "main", len(m))
