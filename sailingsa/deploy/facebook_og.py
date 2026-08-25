"""Facebook Open Graph: 1200x630 PNG cards + head fragments. Used by live api.py patch."""
from __future__ import annotations

import hashlib
import html as html_module
import io
import os
import re
from typing import Optional
from urllib.parse import quote

OG_WIDTH = 1200
OG_HEIGHT = 630
OG_BRAND_BG = (0, 31, 63)  # #001f3f
OG_SAILOR_CIRCLE_RENDER = "circle_v1"  # bump when sailor OG crop changes
OG_SAILOR_CIRCLE_FRAC = 0.55  # circle diameter vs min(canvas w,h)
OG_SAILOR_DEFAULT_POSITION = (0.5, 0.28)  # matches DEV1_AVATAR_CROP default


def source_fingerprint(path: str) -> str:
    st = os.stat(path)
    raw = f"{os.path.abspath(path)}:{st.st_mtime_ns}:{st.st_size}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_og_image_url(base_url: str, page_type: str, entity_key: str, fingerprint: str) -> str:
    b = (base_url or "").rstrip("/")
    key = quote(str(entity_key or "site").strip("/") or "site", safe="")
    pt = quote(str(page_type or "home").strip(), safe="")
    return f"{b}/api/og/{pt}/{key}.png?v={fingerprint}"


def render_facebook_head(
    *,
    title: str,
    description: str,
    canonical_url: str,
    og_image_url: str = "",
    og_type: str = "website",
) -> str:
    t = html_module.escape(title or "SailingSA")
    d = html_module.escape(description or "")
    c = html_module.escape(canonical_url or "")
    ot = html_module.escape(og_type or "website")
    out = (
        f'<meta name="description" content="{d}">'
        f'<link rel="canonical" href="{c}">'
        f'<meta property="og:site_name" content="SailingSA">'
        f'<meta property="og:type" content="{ot}">'
        f'<meta property="og:title" content="{t}">'
        f'<meta property="og:description" content="{d}">'
        f'<meta property="og:url" content="{c}">'
    )
    if og_image_url:
        img = html_module.escape(og_image_url)
        out += (
            f'<meta property="og:image" content="{img}">'
            f'<meta property="og:image:width" content="{OG_WIDTH}">'
            f'<meta property="og:image:height" content="{OG_HEIGHT}">'
        )
    return out


def strip_facebook_meta(html: str) -> str:
    html = re.sub(r'<meta\s+property="og:[^"]+"\s+content="[^"]*"\s*/?\>', "", html, flags=re.I)
    html = re.sub(r'<meta\s+name="twitter:[^"]+"\s+content="[^"]*"\s*/?\>', "", html, flags=re.I)
    html = re.sub(
        r'<meta\s+name="description"\s+content="[^"]*"\s*/?>',
        "",
        html,
        count=1,
        flags=re.I,
    )
    html = re.sub(
        r'<link\s+rel="canonical"\s+href="[^"]*"\s*/?>',
        "",
        html,
        count=1,
        flags=re.I,
    )
    return html


def inject_facebook_head(html: str, head_fragment: str) -> str:
    html = strip_facebook_meta(html)
    if "</head>" in html.lower():
        return re.sub(r"</head>", head_fragment + "\n</head>", html, count=1, flags=re.I)
    return head_fragment + html


def url_to_local_path(
    url: str,
    *,
    static_dir: str,
    base_dir: str,
    club_logo_resolver,
) -> Optional[str]:
    if not url or not str(url).strip():
        return None
    u = str(url).split("?", 1)[0].strip()
    if not u:
        return None
    from urllib.parse import unquote

    u = unquote(u)
    if u.startswith("/api/club-logo/"):
        code = u.split("/api/club-logo/", 1)[-1].strip()
        if club_logo_resolver:
            return club_logo_resolver(code)
        return None
    if u.startswith("/artwork/"):
        rel = u.lstrip("/")
        for root in (base_dir, os.path.dirname(base_dir)):
            p = os.path.join(root, rel.replace("/", os.sep))
            if os.path.isfile(p):
                return p
        return None
    if u.startswith("/assets/"):
        rel = u.lstrip("/")
        p = os.path.join(static_dir, rel.replace("/", os.sep))
        if os.path.isfile(p):
            return p
        p2 = os.path.join(base_dir, rel.replace("/", os.sep))
        if os.path.isfile(p2):
            return p2
        return None
    if u.startswith("http://") or u.startswith("https://"):
        return None
    return None


def og_cache_fingerprint(
    source_path: str,
    page_type: str,
    object_position: Optional[tuple[float, float]] = None,
) -> str:
    base = source_fingerprint(source_path)
    pt = (page_type or "").strip().lower()
    if pt == "sailor":
        px, py = object_position or OG_SAILOR_DEFAULT_POSITION
        raw = f"{base}:{OG_SAILOR_CIRCLE_RENDER}:{px:.4f}:{py:.4f}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    return base


def _cover_crop_square(
    img: "Image.Image",
    size: int,
    pos_x: float = 0.5,
    pos_y: float = 0.28,
) -> "Image.Image":
    from PIL import Image

    sw, sh = img.size
    scale = max(size / max(sw, 1), size / max(sh, 1))
    nw = max(1, int(round(sw * scale)))
    nh = max(1, int(round(sh * scale)))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    center_x = pos_x * nw
    center_y = pos_y * nh
    left = int(round(center_x - size / 2))
    top = int(round(center_y - size / 2))
    left = max(0, min(left, nw - size))
    top = max(0, min(top, nh - size))
    return resized.crop((left, top, left + size, top + size))


def _circle_mask_image(img: "Image.Image", size: int) -> "Image.Image":
    from PIL import Image, ImageDraw

    img = img.convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def render_og_sailor_avatar_png(
    source_path: str,
    object_position: tuple[float, float] = OG_SAILOR_DEFAULT_POSITION,
) -> bytes:
    """1200x630 card with centred circular avatar (same crop idiom as /sailor/ page)."""
    from PIL import Image, ImageDraw

    src = Image.open(source_path).convert("RGBA")
    canvas = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), OG_BRAND_BG)
    diam = max(1, int(min(OG_WIDTH, OG_HEIGHT) * OG_SAILOR_CIRCLE_FRAC))
    square = _cover_crop_square(src, diam, object_position[0], object_position[1])
    circle = _circle_mask_image(square, diam)
    x = (OG_WIDTH - diam) // 2
    y = (OG_HEIGHT - diam) // 2
    draw = ImageDraw.Draw(canvas)
    ring = max(3, diam // 90)
    draw.ellipse(
        (x - ring, y - ring, x + diam + ring, y + diam + ring),
        outline=(255, 255, 255),
        width=ring,
    )
    canvas.paste(circle, (x, y), circle)
    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()


def render_og_card_png(source_path: str, title: Optional[str] = None) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    src = Image.open(source_path).convert("RGBA")
    canvas = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), OG_BRAND_BG)
    sw, sh = src.size
    max_w = int(OG_WIDTH * 0.72)
    max_h = int(OG_HEIGHT * 0.62)
    scale = min(max_w / max(sw, 1), max_h / max(sh, 1), 1.0)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    logo = src.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (OG_WIDTH - nw) // 2
    y = (OG_HEIGHT - nh) // 2
    if title:
        y = int(OG_HEIGHT * 0.12)
    canvas.paste(logo, (x, y + (0 if not title else 40)), logo)
    if title:
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        except Exception:
            font = ImageFont.load_default()
        tw = draw.textlength(title, font=font)
        draw.text(((OG_WIDTH - tw) / 2, 28), title[:80], fill=(255, 255, 255), font=font)
    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()


def cache_og_png(
    cache_dir: str,
    page_type: str,
    entity_key: str,
    source_path: str,
    title: Optional[str] = None,
    object_position: Optional[tuple[float, float]] = None,
) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    fp = og_cache_fingerprint(source_path, page_type, object_position)
    safe_key = re.sub(r"[^\w\-]+", "_", str(entity_key or "site"))[:120]
    out_path = os.path.join(cache_dir, f"{page_type}_{safe_key}_{fp}.png")
    if not os.path.isfile(out_path):
        if (page_type or "").strip().lower() == "sailor":
            pos = object_position or OG_SAILOR_DEFAULT_POSITION
            data = render_og_sailor_avatar_png(source_path, pos)
        else:
            data = render_og_card_png(source_path, title=title)
        with open(out_path, "wb") as f:
            f.write(data)
    return out_path
