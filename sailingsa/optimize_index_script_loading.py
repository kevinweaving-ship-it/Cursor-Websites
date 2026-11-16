#!/usr/bin/env python3
"""Make homepage scripts non-blocking for first paint.

Live and local index.html ship many render-blocking <script src> tags. Mobile often
feels fine because the large immutable bundles are already cached; a cold Mac
Chrome load pays the full download + main-thread parse cost before the body fills.

This transform:
  1) Moves early <head> scripts to after stylesheet links (CSS discovered first).
  2) Adds defer to body/external <script src> tags (keeps document order).
  3) Optionally extracts large trailing inline <script> blocks to hashed files
     with defer so fat source index.html matches the live thin-HTML behaviour.

Head scripts stay synchronous (canonical redirects / layout attribute).
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

SCRIPT_OPEN_RE = re.compile(r"<script(\b[^>]*)>", re.I)
SCRIPT_BLOCK_RE = re.compile(r"<script(\b[^>]*)>(.*?)</script>", re.I | re.S)
HEAD_RE = re.compile(r"(<head\b[^>]*>)(.*?)(</head>)", re.I | re.S)
STYLESHEET_RE = re.compile(
    r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>', re.I
)


def _is_json_ld(attrs: str) -> bool:
    return "application/ld+json" in (attrs or "").lower()


def _has_src(attrs: str) -> bool:
    return bool(re.search(r"\bsrc\s*=", attrs or "", re.I))


def _has_defer_or_async(attrs: str) -> bool:
    return bool(re.search(r"\b(defer|async)\b", attrs or "", re.I))


def _add_defer(attrs: str) -> str:
    if _has_defer_or_async(attrs):
        return attrs
    return (attrs or "") + " defer"


def _rewrite_open_tag(attrs: str, force_defer: bool) -> str:
    if force_defer and _has_src(attrs) and not _is_json_ld(attrs):
        attrs = _add_defer(attrs)
    return f"<script{attrs}>"


def _real_head_end(html: str) -> int | None:
    """First </head> after the document <head> — ignore </head> inside later JS strings."""
    open_head = re.search(r"<head\b[^>]*>", html, re.I)
    if not open_head:
        return None
    close = re.search(r"</head\s*>", html[open_head.end() :], re.I)
    if not close:
        return None
    return open_head.end() + close.end()


def _real_body_close_start(html: str) -> int | None:
    """Last </body> before final </html> (earlier hits are JS string literals)."""
    html_close = None
    for m in re.finditer(r"</html\s*>", html, re.I):
        html_close = m
    if not html_close:
        return None
    body_close = None
    for m in re.finditer(r"</body\s*>", html[: html_close.start()], re.I):
        body_close = m
    return body_close.start() if body_close else None


def move_head_scripts_after_css(html: str) -> str:
    """Keep early sync head scripts, but discover CSS before they run."""
    m = HEAD_RE.search(html)
    if not m:
        return html
    open_tag, head, close_tag = m.group(1), m.group(2), m.group(3)
    scripts: list[str] = []

    def take_script(sm: re.Match) -> str:
        attrs = sm.group(1) or ""
        if _is_json_ld(attrs):
            return sm.group(0)
        scripts.append(sm.group(0))
        return ""

    head_wo_scripts = SCRIPT_BLOCK_RE.sub(take_script, head)
    if not scripts:
        return html
    sheets = list(STYLESHEET_RE.finditer(head_wo_scripts))
    bundle = "\n".join(scripts)
    if not sheets:
        new_head = head_wo_scripts + "\n" + bundle + "\n"
    else:
        last = sheets[-1]
        insert_at = last.end()
        new_head = (
            head_wo_scripts[:insert_at]
            + "\n"
            + bundle
            + "\n"
            + head_wo_scripts[insert_at:]
        )
    return html[: m.start()] + open_tag + new_head + close_tag + html[m.end() :]


def defer_body_external_scripts(html: str) -> str:
    """Add defer to <script src> after </head>. Preserve head sync scripts."""
    head_end_pos = _real_head_end(html)
    if head_end_pos is None:
        return html
    head = html[:head_end_pos]
    body = html[head_end_pos:]
    def repl(m: re.Match) -> str:
        attrs = m.group(1) or ""
        if not _has_src(attrs) or _is_json_ld(attrs):
            return m.group(0)
        return _rewrite_open_tag(attrs, force_defer=True)

    return head + SCRIPT_OPEN_RE.sub(repl, body)


def extract_large_trailing_inlines(
    html: str,
    out_dir: Path,
    url_prefix: str = "/js/extracted/",
    min_bytes: int = 8_000,
) -> str:
    """Replace large body inline scripts near </body> with deferred hashed files."""
    head_end = _real_head_end(html)
    body_close = _real_body_close_start(html)
    if head_end is None or body_close is None:
        return html

    start = head_end
    end = body_close
    region = html[start:end]
    out_dir.mkdir(parents=True, exist_ok=True)
    pieces: list[str] = []
    last = 0
    changed = False

    for m in SCRIPT_BLOCK_RE.finditer(region):
        attrs = m.group(1) or ""
        body = m.group(2) or ""
        pieces.append(region[last : m.start()])
        last = m.end()
        if _has_src(attrs) or _is_json_ld(attrs) or len(body.encode("utf-8")) < min_bytes:
            pieces.append(m.group(0))
            continue
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:10]
        name = f"index-script-{digest}.js"
        path = out_dir / name
        path.write_text(body, encoding="utf-8")
        pieces.append(f'<script src="{url_prefix}{name}" defer></script>')
        changed = True

    if not changed:
        return html
    pieces.append(region[last:])
    return html[:start] + "".join(pieces) + html[end:]

def optimize_html(
    html: str,
    *,
    extract_dir: Path | None = None,
    extract: bool = False,
) -> str:
    html = move_head_scripts_after_css(html)
    html = defer_body_external_scripts(html)
    if extract and extract_dir is not None:
        html = extract_large_trailing_inlines(html, extract_dir)
    return html


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path, help="index.html to read")
    p.add_argument("-o", "--output", type=Path, help="Write optimized HTML here (default: in-place)")
    p.add_argument(
        "--extract",
        action="store_true",
        help="Extract large trailing inline scripts to hashed deferred files",
    )
    p.add_argument(
        "--extract-dir",
        type=Path,
        default=None,
        help="Directory for extracted JS (default: <input_dir>/js/extracted)",
    )
    p.add_argument("--dry-run", action="store_true", help="Print stats only")
    args = p.parse_args(argv)

    raw = args.input.read_text(encoding="utf-8")
    extract_dir = args.extract_dir
    if args.extract and extract_dir is None:
        extract_dir = args.input.parent / "js" / "extracted"

    out = optimize_html(raw, extract_dir=extract_dir, extract=args.extract)

    def count_blocking(s: str) -> int:
        n = 0
        for m in SCRIPT_OPEN_RE.finditer(s):
            attrs = m.group(1) or ""
            if _has_src(attrs) and not _has_defer_or_async(attrs) and not _is_json_ld(attrs):
                n += 1
        return n

    print(
        f"blocking_src before={count_blocking(raw)} after={count_blocking(out)} "
        f"bytes {len(raw)} -> {len(out)}"
    )
    if args.dry_run:
        return 0
    dest = args.output or args.input
    dest.write_text(out, encoding="utf-8")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
