"""Talk to the existing Mac Google Chrome window. Never reads cookie files."""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
from pathlib import Path


def is_darwin() -> bool:
    return platform.system() == "Darwin"


def chrome_app() -> Path:
    return Path("/Applications/Google Chrome.app")


def chrome_running() -> bool:
    r = subprocess.run(
        ["pgrep", "-x", "Google Chrome"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def _osascript(script: str, timeout: int = 60) -> str:
    r = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "osascript failed").strip())
    return (r.stdout or "").rstrip("\n")


def activate_chrome() -> None:
    _osascript('tell application "Google Chrome" to activate')


def open_url(url: str) -> None:
    # Open in the already-running Chrome (or launch that one profile once).
    escaped = url.replace("\\", "\\\\").replace('"', '\\"')
    _osascript(
        f'''
        tell application "Google Chrome"
            activate
            if (count of windows) = 0 then
                make new window
            end if
            set URL of active tab of front window to "{escaped}"
        end tell
        '''
    )


def active_url() -> str:
    return _osascript(
        'tell application "Google Chrome" to get URL of active tab of front window'
    )


def active_title() -> str:
    return _osascript(
        'tell application "Google Chrome" to get title of active tab of front window'
    )


def exec_js(javascript: str, timeout: int = 90) -> str:
    # Chrome AppleScript "execute javascript" — uses the live signed-in tab.
    js = javascript.replace("\\", "\\\\").replace('"', '\\"')
    return _osascript(
        f'''
        tell application "Google Chrome"
            execute active tab of front window javascript "{js}"
        end tell
        ''',
        timeout=timeout,
    )


def page_text() -> str:
    return exec_js("document.body ? document.body.innerText : ''")


def is_google_login_url(url: str) -> bool:
    u = (url or "").lower()
    return any(
        x in u
        for x in (
            "accounts.google.com",
            "signin/identifier",
            "servicelogin",
            "challenge/pwd",
            "challenge/totp",
            "challenge/ipp",
        )
    )


def wait_for_load(timeout_s: float = 45.0) -> str:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        try:
            last = active_url()
        except RuntimeError:
            time.sleep(0.6)
            continue
        if last and not last.startswith("chrome://"):
            time.sleep(1.2)
            return last
        time.sleep(0.5)
    return last


def screenshot_login(dest: Path) -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not shutil.which("screencapture"):
        return None
    subprocess.run(["screencapture", "-x", str(dest)], check=False)
    return dest if dest.exists() else None


def inspect_environment() -> dict:
    chrome_support = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    profiles = []
    if chrome_support.is_dir():
        for p in sorted(chrome_support.iterdir()):
            if p.is_dir() and (p.name == "Default" or p.name.startswith("Profile")):
                cookies = p / "Cookies"
                profiles.append(
                    {
                        "name": p.name,
                        "cookies_exist": cookies.exists(),
                        "cookies_mtime": (
                            time.strftime(
                                "%Y-%m-%dT%H:%M:%S",
                                time.localtime(cookies.stat().st_mtime),
                            )
                            if cookies.exists()
                            else None
                        ),
                    }
                )
    return {
        "darwin": is_darwin(),
        "chrome_app": chrome_app().exists(),
        "chrome_running": chrome_running() if is_darwin() else False,
        "profiles": profiles,
        "osascript": bool(shutil.which("osascript")),
        "playwright_importable": _playwright_ok(),
    }


def _playwright_ok() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except Exception:
        return False
