#!/usr/bin/env python3
"""Voelklip Tuya switch 401: don't restore another site's keypad login."""

from pathlib import Path

APP = Path("/var/www/sailingsa/arial/app.js")
CARD = Path("/var/www/sailingsa/arial/home-card.js")
VOEL = Path("/var/www/sailingsa/voelklip/index.html")


def patch_app(t: str) -> str:
    old_logout = """        try { localStorage.removeItem("arialUser"); } catch (e) {}
        try { sessionStorage.removeItem("arialUser"); } catch (e) {}"""
    new_logout = """        try { localStorage.removeItem(siteKey("arialUser")); } catch (e) {}
        try { sessionStorage.removeItem(siteKey("arialUser")); } catch (e) {}
        try { localStorage.removeItem("arialUser"); } catch (e) {}
        try { sessionStorage.removeItem("arialUser"); } catch (e) {}"""
    if old_logout not in t:
        raise SystemExit("logout storage block not found")
    t = t.replace(old_logout, new_logout, 1)

    old_set = """        try { localStorage.setItem("arialUser", JSON.stringify(user)); } catch (e) {}
        try { sessionStorage.removeItem("arialUser"); } catch (e) {}"""
    new_set = """        try { localStorage.setItem(siteKey("arialUser"), JSON.stringify(user)); } catch (e) {}
        try { sessionStorage.removeItem(siteKey("arialUser")); } catch (e) {}"""
    if old_set not in t:
        raise SystemExit("setLoggedIn storage block not found")
    t = t.replace(old_set, new_set, 1)

    old_rest = """        var saved = JSON.parse(localStorage.getItem("arialUser") || "null");
        if (!saved) saved = JSON.parse(sessionStorage.getItem("arialUser") || "null");
        if (saved) {"""
    new_rest = """        var saved = JSON.parse(localStorage.getItem(siteKey("arialUser")) || "null");
        if (!saved) saved = JSON.parse(sessionStorage.getItem(siteKey("arialUser")) || "null");
        if (!saved) saved = JSON.parse(localStorage.getItem("arialUser") || "null");
        if (!saved) saved = JSON.parse(sessionStorage.getItem("arialUser") || "null");
        if (saved && !userAllowedHere(saved)) saved = null;
        if (saved) {"""
    if old_rest not in t:
        raise SystemExit("restore block not found")
    t = t.replace(old_rest, new_rest, 1)

    # last setLoggedIn on restore still needs allowed check
    old_ok = """            if (saved.code && CODES[saved.code]) setLoggedIn(CODES[saved.code]);
        }"""
    new_ok = """            if (saved.code && CODES[saved.code] && userAllowedHere(CODES[saved.code])) setLoggedIn(CODES[saved.code]);
        }"""
    if old_ok not in t:
        raise SystemExit("restore setLoggedIn not found")
    t = t.replace(old_ok, new_ok, 1)

    if "window.arialRejectNeedLogin" not in t:
        t = t.replace(
            "    function rejectNeedLogin() {",
            "    function rejectNeedLogin() {",
            1,
        )
        t = t.replace(
            """    function requireLogin() {
        if (isLoggedIn()) return true;
        rejectNeedLogin();
        return false;
    }""",
            """    window.arialRejectNeedLogin = rejectNeedLogin;

    function requireLogin() {
        if (isLoggedIn()) return true;
        rejectNeedLogin();
        return false;
    }""",
            1,
        )
        if "window.arialRejectNeedLogin" not in t:
            raise SystemExit("failed to export arialRejectNeedLogin")
    return t


def patch_card(t: str) -> str:
    old = '.then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.detail || "failed"); }); })'
    new = '.then(function (r) { return r.json().then(function (j) { if (r.status === 401 && typeof window.arialRejectNeedLogin === "function") window.arialRejectNeedLogin(); if (!r.ok) throw new Error(j.detail || "failed"); }); })'
    if old not in t:
        raise SystemExit("switch then() not found")
    return t.replace(old, new)


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    APP.write_text(patch_app(app), encoding="utf-8")
    print("patched app.js")
    card = CARD.read_text(encoding="utf-8")
    CARD.write_text(patch_card(card), encoding="utf-8")
    print("patched home-card.js")
    for html_path in (
        VOEL,
        Path("/var/www/sailingsa/arial/index.html"),
        Path("/var/www/sailingsa/bing/index.html"),
        Path("/var/www/sailingsa/stanford/index.html"),
    ):
        if not html_path.is_file():
            continue
        html = html_path.read_text(encoding="utf-8")
        html2 = (
            html.replace("app.js?v=249", "app.js?v=250")
            .replace("app.js?v=248", "app.js?v=250")
            .replace("home-card.js?v=hc4", "home-card.js?v=hc5")
        )
        if html2 != html:
            html_path.write_text(html2, encoding="utf-8")
            print("bumped", html_path)


if __name__ == "__main__":
    main()
