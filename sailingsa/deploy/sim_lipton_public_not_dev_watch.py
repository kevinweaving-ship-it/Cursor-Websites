#!/usr/bin/env python3
"""Sim: watchdog strips public nginx alias and api.py playback hijack; keeps -dev."""
from __future__ import annotations

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "lipton_public_not_dev_watch",
    Path(__file__).resolve().parent / "lipton_public_not_dev_watch.py",
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def main() -> int:
    nginx = """
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        default_type text/html;
        add_header Cache-Control "no-store";
        add_header X-Robots-Tag "noindex, nofollow";
        alias /var/www/sailingsa/lipton-dev.html;
    }

    location = /regatta/2026-08-29-lipton-challenge-cup {
        default_type text/html;
        add_header Cache-Control "no-store";
        alias /var/www/sailingsa/lipton-dev.html;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        default_type text/html;
        add_header Cache-Control "no-store";
        alias /var/www/sailingsa/lipton-dev.html;
    }
        location = /regatta {
"""
    new, n = mod.fix_nginx(nginx)
    assert n >= 3, n
    assert "lipton-challenge-cup-dev" in new
    assert new.count("alias /var/www/sailingsa/lipton-dev.html") == 1
    assert "LIPTON_NGINX_PUBLIC_PROXY_V1" in new
    assert "proxy_pass http://127.0.0.1:8000" in new
    assert "include /etc/nginx/snippets/lipton-public-proxy.conf" not in new
    assert mod._public_aliased(new) is False

    base = """
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        default_type text/html;
        add_header Cache-Control "no-store";
        add_header X-Robots-Tag "noindex, nofollow";
        alias /var/www/sailingsa/lipton-dev.html;
    }
        location = /regatta {
"""
    proxied, pn = mod.fix_nginx(base)
    assert pn == 1
    assert "LIPTON_NGINX_PUBLIC_PROXY_V1" in proxied
    assert "proxy_pass http://127.0.0.1:8000" in proxied
    assert "include /etc/nginx/snippets/lipton-public-proxy.conf" not in proxied
    assert "lipton-challenge-cup-dev" in proxied

    fat = """
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        default_type text/html;
        etag off;
        if_modified_since off;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        add_header X-Robots-Tag "noindex, nofollow";
        alias /var/www/sailingsa/lipton-dev.html;
    }
        location = /regatta {
"""
    fat_new, fn = mod.fix_nginx(fat)
    assert fn >= 1
    assert "LIPTON_NGINX_PUBLIC_PROXY_V1" in fat_new
    assert "proxy_pass http://127.0.0.1:8000" in fat_new
    assert "include /etc/nginx/snippets/lipton-public-proxy.conf" not in fat_new
    assert fat_new.count("alias /var/www/sailingsa/lipton-dev.html") == 1

    with_inc = """
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        default_type text/html;
        add_header Cache-Control "no-store";
        add_header X-Robots-Tag "noindex, nofollow";
        alias /var/www/sailingsa/lipton-dev.html;
    }
    # LIPTON_NGINX_PUBLIC_PROXY_V1
    include /etc/nginx/snippets/lipton-public-proxy.conf;
        location = /regatta {
"""
    inc_new, ic = mod.fix_nginx(with_inc)
    assert "include /etc/nginx/snippets/lipton-public-proxy.conf" not in inc_new
    assert "proxy_pass http://127.0.0.1:8000" in inc_new
    assert ic >= 1

    live_shape = """
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        default_type text/html;
        etag off;
        if_modified_since off;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        add_header X-Robots-Tag "noindex, nofollow";
        alias /var/www/sailingsa/lipton-dev.html;
    }
    # LIPTON_NGINX_PUBLIC_PROXY_V1
    location = /regatta/2026-08-29-lipton-challenge-cup-old {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
    include /etc/nginx/snippets/lipton-public-proxy.conf;
    location = /regatta {
        proxy_pass http://127.0.0.1:8000/regatta;
    }
"""
    live_new, ln = mod.fix_nginx(live_shape)
    assert "include /etc/nginx/snippets/lipton-public-proxy.conf" not in live_new
    assert mod._public_slug_proxied(live_new) is True
    assert mod._public_aliased(live_new) is False
    assert live_new.count("alias /var/www/sailingsa/lipton-dev.html") == 1
    assert ln >= 1

    stub = "[Service]\nExecStart=/bin/true\nDescription=disabled — must not restore old Lipton event page\n"
    assert mod._unit_is_stub(stub) is True
    assert mod._unit_is_stub(mod.WATCH_UNIT_BODY) is False
    assert "while true" in mod.WATCH_UNIT_BODY
    assert "while true" in mod.HOLD_UNIT_BODY
    assert "aa-lipton-url-hold" in str(mod.CRON_HOLD)

    api = '''
def serve_regatta_standalone(slug: str, request: Request):
    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup" and not allow_lipton_event:
        return serve_lipton_dev_playback_page(request, public=True)
    return _serve_regatta_standalone_impl(slug, request)

def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Playback HTML. The public Lipton URL is this page; -dev is the same file."""
    from pathlib import Path as _P
    names = ()
'''
    out, changed = mod.fix_api(api)
    assert changed
    assert mod.HIJACK.search(api)
    assert not mod.HIJACK.search(out)
    assert "LIPTON_PUBLIC_NOT_DEV_V4 hijack public=True" in out
    assert "if public:" in out
    head, _sep, _play = out.partition("def serve_lipton_dev_playback_page")
    assert "public=True" not in head
    assert "allow_lipton_event" not in head
    hijack_plain = '''
def serve_regatta_standalone(slug: str, request: Request, *, allow_lipton_event: bool = False):
    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup":
        return serve_lipton_dev_playback_page(request, public=True)
    return _serve_regatta_standalone_impl(slug, request)

def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Playback HTML. Public Lipton URL only. Old weather page is -old."""
    from pathlib import Path as _P
    names = ()
'''
    out2, changed2 = mod.fix_api(hijack_plain)
    assert changed2
    assert mod.HIJACK.search(hijack_plain)
    assert not mod.HIJACK.search(out2)
    head2, _s2, _p2 = out2.partition("def serve_lipton_dev_playback_page")
    assert "public=True" not in head2

    assert "lipton_public_watch_guard.sh" in mod.CRON_PUBLIC_BODY
    assert "zzz-lipton-public-live" in str(mod.CRON_ZZZ)
    assert callable(mod.ensure_watch_service)
    src = Path(__file__).resolve().parent / "lipton_public_not_dev_watch.py"
    assert "LIPTON_WATCH_DEBOUNCE_V1" in src.read_text(encoding="utf-8")
    assert "LIPTON_WATCH_UNIT_RESTORE_V1" in src.read_text(encoding="utf-8")
    assert callable(mod._overnight_hold)
    print("PASS watchdog strips public nginx alias, inserts public proxy, keeps -dev")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
