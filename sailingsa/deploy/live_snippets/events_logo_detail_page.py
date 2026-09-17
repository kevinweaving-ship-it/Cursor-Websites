"""Live-only named-event HTML path. Source of truth is
/var/www/sailingsa/api/api.py events_logo_detail_page.

Do not SCP repo api.py over live. This snippet records the surgical
replacement: no OG PNG generation on the HTML request; serve stale
cached HTML without waiting on _EVENTS_LOGOS_HTML_LOCK.
"""


def _events_logos_cache_peek_detail(slug: str):
    """Usable cached HTML even if TTL expired. Never waits on the HTML lock."""
    import os
    import re as _re

    key = (slug or "").strip().lower()
    details = _EVENTS_LOGOS_HTML_CACHE.setdefault("details", {})
    ent = details.get(key)
    if ent and len(ent) > 1 and (ent[1] or "").strip():
        return ent[1]
    safe = _re.sub(r"[^a-z0-9_-]+", "_", key)[:120]
    disk = os.path.join(_EVENTS_LOGOS_DISK, f"detail-{safe}.html")
    try:
        if os.path.isfile(disk) and os.path.getsize(disk) > 400:
            html = open(disk, encoding="utf-8", errors="replace").read()
            if (html or "").strip():
                return html
    except Exception:
        pass
    return None


def _events_logos_render_detail_html(slug: str):
    """Build named-event HTML. Do not generate or wait for /api/og/events_logos."""
    d = _events_logos_gallery_deps()
    elg = d.pop("elg")
    parts = elg.detail_page_parts(slug, **d)
    if not parts:
        return None
    title, canonical_path, inner = parts
    inner = f"{inner}{_regatta_live_board_toggle_script()}"
    import facebook_og as _fb

    og_image_url = f"{_canonical_base_url()}/api/og/events_logos/{slug}.png"
    _fb_detail_head = _fb.render_facebook_head(
        title=title,
        description=f'Named event: {title.split(" | ")[0]}. Regattas and hosts on SailingSA.',
        canonical_url=_canonical_base_url() + canonical_path,
        og_image_url=og_image_url,
        og_type="website",
    )
    extra_head = f"<style>{elg.detail_extra_css()}</style>"
    resp = _html_with_gold_header(title, inner, extra_head)
    html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
    return _fb.inject_facebook_head(html, _fb_detail_head)


def _events_logos_schedule_detail_rebuild(slug: str) -> None:
    """Refresh cache in the background. Request path must not wait."""

    def _run():
        got = _EVENTS_LOGOS_HTML_LOCK.acquire(blocking=False)
        if not got:
            return
        try:
            html = _events_logos_render_detail_html(slug)
            if html:
                _events_logos_cache_set_detail(slug, html)
        except Exception as e:
            print(f"[events_logo_detail] background rebuild failed {slug}: {e}", flush=True)
        finally:
            _EVENTS_LOGOS_HTML_LOCK.release()

    threading.Thread(
        target=_run, name=f"events-logos-rebuild-{(slug or '')[:40]}", daemon=True
    ).start()


def events_logo_detail_page(slug: str):
    """Gold-std event-logo page — cached for visitor click speed."""
    raw = (slug or "").strip().lower().strip("/")
    if raw == "dinghy-provincials":
        return RedirectResponse(url="/events-logos/dinghy-provincials-championship", status_code=301)
    cached = _events_logos_cache_get_detail(slug)
    if cached:
        return HTMLResponse(cached, headers={"Cache-Control": "public, max-age=300"})
    stale = _events_logos_cache_peek_detail(slug)
    if stale:
        _events_logos_schedule_detail_rebuild(slug)
        return HTMLResponse(stale, headers={"Cache-Control": "public, max-age=300"})
    with _EVENTS_LOGOS_HTML_LOCK:
        cached = _events_logos_cache_get_detail(slug)
        if cached:
            return HTMLResponse(cached, headers={"Cache-Control": "public, max-age=300"})
        stale = _events_logos_cache_peek_detail(slug)
        if stale:
            return HTMLResponse(stale, headers={"Cache-Control": "public, max-age=300"})
        html = _events_logos_render_detail_html(slug)
        if not html:
            raise HTTPException(status_code=404, detail="Event logo not found")
        _events_logos_cache_set_detail(slug, html)
        return HTMLResponse(html, headers={"Cache-Control": "public, max-age=300"})
