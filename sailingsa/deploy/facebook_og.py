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
OG_BRAND_BG = (0, 31, 63)  # legacy navy (sailor ring only)
OG_CANVAS_WHITE = (255, 255, 255)
OG_DUAL_BOX_RENDER = "dual_white_v6"  # bump when dual-logo layout changes; also busts FB path cache
OG_SAILOR_CIRCLE_RENDER = "circle_v1"
OG_SAILOR_CIRCLE_FRAC = 0.88  # circle vs right half of white box
OG_SAILOR_DEFAULT_POSITION = (0.5, 0.28)
OG_BOX_PAD = 40
OG_BOX_GAP = 36
OG_BOX_DIVIDER = (226, 232, 240)
OG_LOGO_TARGET_FRAC = 0.92  # both halves: logos fill this fraction of inner height
OG_TRIM_ALPHA = 12  # trim transparent padding before sizing

# Brand on white OG cards: full SAILING SA wordmark (Live SSOT).
# favicon / mark-on-color = dark header ONLY — never use on white OG canvas.
OG_BRAND_ASSET = "assets/logos/Live/logo-wordmark-on-white.png"
OG_ENTITY_FALLBACK_ASSET = "assets/logos/Live/logo-wordmark-on-white.png"

_BRAND_CANDIDATES = (
    OG_BRAND_ASSET,
    "assets/logos/sailingsa-logo.png",  # mark-on-white fallback only
)


def source_fingerprint(path: str) -> str:
    st = os.stat(path)
    raw = f"{os.path.abspath(path)}:{st.st_mtime_ns}:{st.st_size}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_og_image_url(base_url: str, page_type: str, entity_key: str, fingerprint: str) -> str:
    """Fingerprint is in the PATH (not ?v=) so Facebook cannot ignore cache-busting."""
    b = (base_url or "").rstrip("/")
    key = quote(str(entity_key or "site").strip("/") or "site", safe="")
    pt = quote(str(page_type or "home").strip(), safe="")
    fp = quote(str(fingerprint or "0").strip() or "0", safe="")
    return f"{b}/api/og/{pt}/{key}/{fp}.png"


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
            f'<meta property="og:image:secure_url" content="{img}">'
            f'<meta property="og:image:type" content="image/png">'
            f'<meta property="og:image:width" content="{OG_WIDTH}">'
            f'<meta property="og:image:height" content="{OG_HEIGHT}">'
            f'<meta name="twitter:card" content="summary_large_image">'
            f'<meta name="twitter:title" content="{t}">'
            f'<meta name="twitter:description" content="{d}">'
            f'<meta name="twitter:image" content="{img}">'
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
    """Insert OG tags immediately after <head> so crawlers see them before large CSS/JS."""
    html = strip_facebook_meta(html)
    frag = (head_fragment or "").strip()
    if not frag:
        return html
    m = re.search(r"<head[^>]*>", html, flags=re.I)
    if m:
        i = m.end()
        return html[:i] + "\n" + frag + "\n" + html[i:]
    if "</head>" in html.lower():
        return re.sub(r"</head>", frag + "\n</head>", html, count=1, flags=re.I)
    return frag + html


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
        # Prefer web root (STATIC_DIR), never api/artwork shadow copies first.
        roots: list[str] = []
        if static_dir:
            roots.append(os.path.abspath(static_dir))
        if base_dir:
            bd = os.path.abspath(base_dir)
            roots.append(os.path.dirname(bd))
            roots.append(bd)
        seen: set[str] = set()
        for root in roots:
            if not root or root in seen:
                continue
            seen.add(root)
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


def _web_root_from_source(source_path: str) -> Optional[str]:
    p = os.path.abspath(source_path)
    d = os.path.dirname(p)
    for _ in range(8):
        for rel in _BRAND_CANDIDATES:
            if os.path.isfile(os.path.join(d, rel)):
                return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def resolve_brand_favicon_path(source_path: str, static_dir: Optional[str] = None) -> Optional[str]:
    roots: list[str] = []
    if static_dir:
        roots.append(os.path.abspath(static_dir))
    root = _web_root_from_source(source_path)
    if root:
        roots.append(root)
    seen: set[str] = set()
    for base in roots:
        if base in seen:
            continue
        seen.add(base)
        for rel in _BRAND_CANDIDATES:
            p = os.path.join(base, rel.replace("/", os.sep))
            if os.path.isfile(p):
                return p
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
        raw = f"{base}:{OG_DUAL_BOX_RENDER}:{OG_SAILOR_CIRCLE_RENDER}:{px:.4f}:{py:.4f}"
    else:
        raw = f"{base}:{OG_DUAL_BOX_RENDER}:contain:{OG_LOGO_TARGET_FRAC:.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _trim_logo(img: "Image.Image") -> "Image.Image":
    """Remove transparent (or empty) margins so small marks scale up consistently."""
    from PIL import Image, ImageChops

    img = img.convert("RGBA")
    alpha = img.split()[3]
    bbox = alpha.point(lambda p: 255 if p > OG_TRIM_ALPHA else 0).getbbox()
    if bbox:
        return img.crop(bbox)
    flat = ImageChops.invert(ImageChops.difference(img, Image.new("RGBA", img.size, (255, 255, 255, 255))))
    bbox2 = flat.getbbox()
    if bbox2:
        return img.crop(bbox2)
    return img


def _fit_contain(
    img: "Image.Image",
    box_w: int,
    box_h: int,
    *,
    allow_upscale: bool = True,
) -> tuple["Image.Image", int, int]:
    from PIL import Image

    sw, sh = img.size
    scale = min(box_w / max(sw, 1), box_h / max(sh, 1))
    if not allow_upscale:
        scale = min(scale, 1.0)
    nw = max(1, int(round(sw * scale)))
    nh = max(1, int(round(sh * scale)))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    return resized, (box_w - nw) // 2, (box_h - nh) // 2


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


def render_og_dual_white_box_png(
    entity_source_path: str,
    brand_source_path: Optional[str] = None,
    *,
    right_mode: str = "contain",
    object_position: tuple[float, float] = OG_SAILOR_DEFAULT_POSITION,
) -> bytes:
    """White 1200x630 OG card: SailingSA favicon/logo left, entity logo right (same box)."""
    from PIL import Image, ImageDraw

    brand_path = brand_source_path or resolve_brand_favicon_path(entity_source_path)
    if not brand_path or not os.path.isfile(brand_path):
        raise FileNotFoundError("SailingSA brand favicon/logo not found for OG card")

    canvas = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), OG_CANVAS_WHITE)
    draw = ImageDraw.Draw(canvas)

    inner_w = OG_WIDTH - (2 * OG_BOX_PAD)
    inner_h = OG_HEIGHT - (2 * OG_BOX_PAD)
    half_w = max(1, (inner_w - OG_BOX_GAP) // 2)
    left_x = OG_BOX_PAD
    right_x = OG_BOX_PAD + half_w + OG_BOX_GAP
    top_y = OG_BOX_PAD

    divider_x = OG_BOX_PAD + half_w + (OG_BOX_GAP // 2)
    draw.line(
        [(divider_x, top_y + 24), (divider_x, top_y + inner_h - 24)],
        fill=OG_BOX_DIVIDER,
        width=2,
    )

    brand = Image.open(brand_path).convert("RGBA")
    entity = Image.open(entity_source_path).convert("RGBA")

    target_h = max(1, int(inner_h * OG_LOGO_TARGET_FRAC))
    target_w = half_w

    b_img, bx, by = _fit_contain(brand, target_w, target_h, allow_upscale=True)
    canvas.paste(b_img, (left_x + bx, top_y + by), b_img)

    # Match entity visual weight to rendered brand height (not full box height).
    match_h = max(1, b_img.height)
    match_w = target_w

    if right_mode == "circle":
        diam = max(1, int(min(match_w, match_h) * OG_SAILOR_CIRCLE_FRAC))
        entity_body = _trim_logo(entity)
        square = _cover_crop_square(entity_body, diam, object_position[0], object_position[1])
        circle = _circle_mask_image(square, diam)
        rx = right_x + (half_w - diam) // 2
        ry = top_y + (inner_h - diam) // 2
        canvas.paste(circle, (rx, ry), circle)
    else:
        entity_body = _trim_logo(entity)
        e_img, ex, ey = _fit_contain(entity_body, match_w, match_h, allow_upscale=True)
        canvas.paste(e_img, (right_x + ex, top_y + ey), e_img)

    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()


def render_og_sailor_avatar_png(
    source_path: str,
    object_position: tuple[float, float] = OG_SAILOR_DEFAULT_POSITION,
    brand_source_path: Optional[str] = None,
) -> bytes:
    return render_og_dual_white_box_png(
        source_path,
        brand_source_path,
        right_mode="circle",
        object_position=object_position,
    )


def render_og_logo_png(
    source_path: str,
    brand_source_path: Optional[str] = None,
) -> bytes:
    return render_og_dual_white_box_png(
        source_path,
        brand_source_path,
        right_mode="contain",
    )


def cache_og_png(
    cache_dir: str,
    page_type: str,
    entity_key: str,
    source_path: str,
    title: Optional[str] = None,
    object_position: Optional[tuple[float, float]] = None,
    static_dir: Optional[str] = None,
) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    fp = og_cache_fingerprint(source_path, page_type, object_position)
    safe_key = re.sub(r"[^\w\-]+", "_", str(entity_key or "site"))[:120]
    out_path = os.path.join(cache_dir, f"{page_type}_{safe_key}_{fp}.png")
    if not os.path.isfile(out_path):
        brand = resolve_brand_favicon_path(source_path, static_dir)
        if (page_type or "").strip().lower() == "sailor":
            pos = object_position or OG_SAILOR_DEFAULT_POSITION
            data = render_og_sailor_avatar_png(source_path, pos, brand)
        else:
            data = render_og_logo_png(source_path, brand)
        with open(out_path, "wb") as f:
            f.write(data)
    return out_path
