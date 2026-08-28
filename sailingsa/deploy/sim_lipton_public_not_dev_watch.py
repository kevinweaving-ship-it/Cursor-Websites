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
    ngx_path = Path(__file__).resolve().parent / "lipton_ngx_public_restore.py"
    ngx_spec = importlib.util.spec_from_file_location("lipton_ngx_public_restore", ngx_path)
    ngxmod = importlib.util.module_from_spec(ngx_spec)
    ngx_spec.loader.exec_module(ngxmod)
    ngx_new, ngx_n = ngxmod.fix_nginx(live_shape)
    assert "include /etc/nginx/snippets/lipton-public-proxy.conf" not in ngx_new
    assert ngxmod._public_slug_proxied(ngx_new) is True
    assert ngx_new.count("alias /var/www/sailingsa/lipton-dev.html") == 1
    assert ngx_n >= 1
    locked = """
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        alias /var/www/sailingsa/lipton-dev.html;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup {
        # LIPTON_PUBLIC_LIVE_BOARD_LOCKED 2026-08-28
        proxy_pass http://127.0.0.1:8000;
        add_header X-Lipton-Page "live-board" always;
    }
"""
    assert ngxmod._public_slug_proxied(locked) is True
    assert ngxmod.fix_nginx(locked)[1] == 0
    assert mod._public_slug_proxied(locked) is True
    assert mod.fix_nginx(locked)[1] == 0
    assert callable(ngxmod.restore_watch_golds)
    assert callable(ngxmod.restore_once)
    assert "lw-g22.py" in str(ngxmod.WATCH_DSTS)
    assert "lipton_ngx_public_restore.py --loop" in mod.GUARD_BODY
    assert "LIPTON_NGINX_LOOP_V1" in ngx_path.read_text(encoding="utf-8")
    assert "/usr/local/lib/lipton_public_not_dev_watch.py" in str(ngxmod.WATCH_DSTS)
    assert "/usr/local/sbin/lipton_public_not_dev_watch.py" in str(ngxmod.WATCH_DSTS)
    v2 = """
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        alias /var/www/sailingsa/lipton-dev.html;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup {
        # LIPTON_NGINX_PUBLIC_ALIAS_V2 — new dev playback page (not API proxy)
        default_type text/html;
        alias /var/www/sailingsa/lipton-new-dev.html;
        add_header X-Lipton-Page "new-dev-public" always;
    }
"""
    assert mod._public_aliased(v2) is True
    assert mod._public_slug_proxied(v2) is False
    v2n, v2c = mod.fix_nginx(v2)
    assert v2c >= 1
    assert "proxy_pass http://127.0.0.1:8000" in v2n
    assert "lipton-new-dev.html" not in v2n
    assert v2n.count("alias /var/www/sailingsa/lipton-dev.html") == 1
    assert ngxmod._public_aliased(v2) is True
    ngx_v2, ngx_v2n = ngxmod.fix_nginx(v2)
    assert ngx_v2n >= 1
    assert "proxy_pass http://127.0.0.1:8000" in ngx_v2
    assert "lipton-new-dev.html" not in ngx_v2
    leftover = """
    # LIPTON_NGINX_PUBLIC_ALIAS_V3 public + -dev both serve lipton-dev.html playback.
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        alias /var/www/sailingsa/lipton-dev.html;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup {
        # LIPTON_NGINX_PUBLIC_PROXY_V1
        proxy_pass http://127.0.0.1:8000;
    }
"""
    assert mod._public_aliased(leftover) is False
    left_new, left_n = mod.fix_nginx(leftover)
    assert "LIPTON_NGINX_PUBLIC_ALIAS" not in left_new
    assert "proxy_pass" in left_new
    assert left_n >= 1
    assert left_new.count("alias /var/www/sailingsa/lipton-dev.html") == 1
    copyv1 = """
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        alias /var/www/sailingsa/lipton-dev.html;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup {
        # LIPTON_NGINX_PUBLIC_COPY_V1 — verbatim copy of -dev (lipton-public.html)
        default_type text/html;
        alias /var/www/sailingsa/lipton-public.html;
        add_header X-Lipton-Page "public-copy-of-dev" always;
    }
"""
    assert mod._public_aliased(copyv1) is True
    cnew, cn = mod.fix_nginx(copyv1)
    assert cn >= 1
    assert "lipton-public.html" not in cnew
    assert "proxy_pass http://127.0.0.1:8000" in cnew

    stub = "[Service]\nExecStart=/bin/true\nDescription=disabled — must not restore old Lipton event page\n"
    assert mod._unit_is_stub(stub) is True
    assert mod._unit_is_stub(mod.WATCH_UNIT_BODY) is False
    assert "lw-g14.py" in mod.WATCH_UNIT_BODY
    assert "lw-g14.py" in mod.HOLD_UNIT_BODY
    assert "lw-g13b.py" in mod.WATCH_UNIT_BODY
    assert "lw-g13b.py" in mod.HOLD_UNIT_BODY
    assert "lw-gold7.py" in mod.WATCH_UNIT_BODY
    assert "--loop" in mod.WATCH_UNIT_BODY
    assert "--loop" not in mod.HOLD_UNIT_BODY
    assert mod._unit_needs_rewrite(mod.WATCH_UNIT_BODY, mod.WATCH_UNIT_BODY) is False
    hold_looped = mod.HOLD_UNIT_BODY.replace("/usr/bin/python3 \"$f\"", "/usr/bin/python3 \"$f\" --loop")
    assert "--loop" in hold_looped
    assert mod._unit_needs_rewrite(hold_looped, mod.HOLD_UNIT_BODY) is True
    assert mod._nginx_must_reload("down", True) is True
    assert mod._nginx_must_reload("playback", False) is True
    assert mod._nginx_must_reload("live", False) is False
    assert mod._nginx_must_reload("down", False) is False
    assert mod._nginx_must_reload("live", False, True) is True
    assert "lw-g22.py" in mod.WATCH_UNIT_BODY
    assert "lw-g21.py" in mod.WATCH_UNIT_BODY
    assert "lw-g20.py" in mod.WATCH_UNIT_BODY
    assert callable(mod._seconds_since_origin_probe)
    assert callable(mod._seconds_since_heartbeat)
    assert "lw-g19.py" in mod.WATCH_UNIT_BODY
    assert "lw-g18.py" in mod.WATCH_UNIT_BODY
    assert "lw-g14d.py" in mod.WATCH_UNIT_BODY
    assert "lw-g14c.py" in mod.WATCH_UNIT_BODY
    assert mod._unit_needs_rewrite(mod.WATCH_UNIT_BODY, mod.WATCH_UNIT_BODY) is False
    assert mod._unit_needs_rewrite(mod.WATCH_UNIT_BODY + "\n", mod.WATCH_UNIT_BODY) is False
    assert mod._unit_needs_rewrite(stub, mod.WATCH_UNIT_BODY) is True
    alt_watch = mod.WATCH_UNIT_BODY.replace("lw-g19.py ", "")
    assert "lw-g19.py" not in alt_watch
    assert mod._unit_needs_rewrite(alt_watch, mod.WATCH_UNIT_BODY) is False
    alt_hold = mod.HOLD_UNIT_BODY.replace("lw-g19.py ", "")
    assert mod._unit_needs_rewrite(alt_hold, mod.HOLD_UNIT_BODY) is False
    oneshot = "[Service]\nType=oneshot\nDescription=disabled\nExecStart=/bin/true\n"
    assert mod._unit_is_stub(oneshot) is True
    assert "is-active --quiet sailingsa-lipton-public-watch.service" in mod.HOLD_UNIT_BODY
    assert "while true" in mod.WATCH_UNIT_BODY
    assert "while true" in mod.HOLD_UNIT_BODY
    assert "aa-lipton-url-hold" in str(mod.CRON_HOLD)
    assert "aa-lipton-ngx" in str(mod.CRON_NGX)
    assert "sailingsa-lipton-schedule" in str(mod.CRON_SCHED)
    assert "cron_lipton_schedule_poll.sh" in mod.CRON_SCHED_BODY
    assert "cron_lipton_schedule_poll.sh" in ngxmod.CRON_SCHED_BODY
    assert callable(ngxmod.restore_schedule_cron)
    assert "dst.stat().st_size >= len(data)" in ngx_path.read_text(encoding="utf-8")
    assert "lipton_ngx_public_restore.py" in mod.GUARD_BODY
    watch_src = Path(__file__).resolve().parent.joinpath("lipton_public_not_dev_watch.py").read_text(encoding="utf-8")
    assert "LIPTON_WATCH_ENABLE_V1" in watch_src
    assert "LIPTON_WATCH_ENABLE_V1" in mod.GUARD_BODY
    assert '["systemctl", "is-enabled", unit_name]' in watch_src
    assert callable(mod.ensure_guard)
    assert callable(mod.ensure_ngx_restore)
    guard_only = "[Service]\nExecStart=/bin/bash -c 'while true; do /usr/local/lib/lipton_public_watch_guard.sh; sleep 3; done'\n"
    assert mod._unit_is_stub(guard_only) is True

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

    hijack_in = '''
def serve_regatta_standalone(slug: str, request: Request, *, allow_lipton_event: bool = False):
    slug_s = str(slug or "").strip()
    if slug_s in (
        "2026-08-29-lipton-challenge-cup",
        "2026-08-29-lipton-challenge-cup-old",
    ):
        return serve_lipton_dev_playback_page(request, public=True)
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    return _serve_regatta_standalone_impl(slug, request)

def _serve_regatta_standalone_impl(slug: str, request: Request):
    slug_s = str(slug or "").strip()
    if slug_s in (
        "2026-08-29-lipton-challenge-cup",
        "2026-08-29-lipton-challenge-cup-old",
    ):
        return serve_lipton_dev_playback_page(request, public=True)
    return None

def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Playback HTML."""
    if public:
        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", _request)
    names = ()
'''
    out3, changed3 = mod.fix_api(hijack_in)
    assert changed3
    assert mod.HIJACK_IN.search(hijack_in)
    assert not mod.HIJACK_IN.search(out3)
    assert "if slug_s in (" not in out3
    assert "challenge-cup-dev" in out3
    assert "LIPTON_PUBLIC_NOT_DEV_V4 hijack public=True" in out3 or "if public:" in out3

    assert "lipton_public_watch_guard.sh" in mod.CRON_PUBLIC_BODY
    assert "zzz-lipton-public-live" in str(mod.CRON_ZZZ)
    assert callable(mod.ensure_watch_service)
    mixed = """
    location = /regatta/2026-08-29-lipton-challenge-cup {
        proxy_pass http://127.0.0.1:8000;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        default_type text/html;
        alias /var/www/sailingsa/lipton-dev.html;
    }
"""
    assert mod._public_aliased(mixed) is True
    assert mod._public_slug_proxied(mixed) is False
    already = """
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        alias /var/www/sailingsa/lipton-dev.html;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup {
        # LIPTON_NGINX_PUBLIC_PROXY_V1
        proxy_pass http://127.0.0.1:8000;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        # LIPTON_NGINX_PUBLIC_PROXY_V1
        proxy_pass http://127.0.0.1:8000;
    }
"""
    already_new, already_n = mod.fix_nginx(already)
    assert already_n == 0
    assert already_new == already

    src = Path(__file__).resolve().parent / "lipton_public_not_dev_watch.py"
    src_txt = src.read_text(encoding="utf-8")
    assert "LIPTON_WATCH_DEBOUNCE_V1" in src_txt
    assert "LIPTON_WATCH_LOOP_V1" in src_txt
    assert "LIPTON_WATCH_UNIT_RESTORE_V1" in src_txt
    assert "nginx not proxied; skipped API restart" in src_txt
    assert "overnight skipped restart (bind window)" in src_txt
    assert "skipped reload (snippet-only)" in src_txt
    assert "origin playback with clean disk; nginx reloaded" in src_txt
    assert '"--resolve"' not in src_txt
    assert "X-Forwarded-Proto: https" in src_txt
    assert callable(mod._overnight_hold)
    print("PASS watchdog strips public nginx alias, inserts public proxy, keeps -dev")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
