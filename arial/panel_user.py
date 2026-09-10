"""Panel keypad user numbers (Olarm / alarm slot), until names are assigned.

Olarm app users keep via=App and are not shown as the actor.
Panel codes are shown as "User 7" until arial_panel_users.json maps 7 -> name.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

PANEL_USERS_PATH = Path(os.getenv("ARIAL_PANEL_USERS", "/var/www/sailingsa/data/arial_panel_users.json"))
PANEL_USER_LOG = Path(os.getenv("ARIAL_PANEL_USER_LOG", "/var/www/sailingsa/data/arial_panel_user_log.jsonl"))
PANEL_OVERRIDES_PATH = Path(
    os.getenv("ARIAL_PANEL_USER_OVERRIDES", "/var/www/sailingsa/data/arial_panel_user_overrides.json")
)
_USER_RE = re.compile(r"(?i)\buser\s*#?\s*(\d{1,2})\b")
_SKIP_KEYS = {
    "deviceid",
    "eventtime",
    "eventnum",
    "num",
    "at",
    "confirmedat",
    "action",
    "eventaction",
    "eventstate",
    "state",
    "tab",
}
_logged_ats: set[str] = set()


def panel_user_number(*parts: object) -> str:
    for raw in parts:
        if raw is None:
            continue
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int) and 1 <= raw <= 32:
            return str(raw)
        s = str(raw).strip()
        if not s:
            continue
        m = _USER_RE.search(s)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 32:
                return str(n)
        if s.isdigit() and 1 <= int(s) <= 32:
            return str(int(s))
    return ""


def _event_time_key(event: dict | None) -> str:
    ev = event or {}
    raw = ev.get("eventTime") if ev.get("eventTime") not in (None, "") else ev.get("at")
    try:
        n = int(raw or 0)
    except (TypeError, ValueError):
        return str(raw or "").strip()
    if n and n < 10_000_000_000:
        n *= 1000
    return str(n) if n else ""


def load_panel_overrides(path: Path | None = None) -> dict[str, str]:
    p = path or PANEL_OVERRIDES_PATH
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in data.items():
        num = panel_user_number(v)
        if not num:
            continue
        ks = str(k).strip()
        try:
            n = int(ks)
            if n and n < 10_000_000_000:
                n *= 1000
            ks = str(n)
        except (TypeError, ValueError):
            pass
        if ks:
            out[ks] = num
    return out


def panel_user_number_from_event(event: dict | None) -> str:
    ev = event or {}
    key = _event_time_key(ev)
    if key:
        mapped = load_panel_overrides().get(key)
        if mapped:
            return mapped
    parts: list[object] = [
        ev.get("userFullname"),
        ev.get("userName"),
        ev.get("user"),
        ev.get("userId"),
        ev.get("userIndex"),
        ev.get("userNum"),
        ev.get("eventUser"),
        ev.get("eventMsg"),
        ev.get("msg"),
        ev.get("actor"),
        ev.get("olarmUser"),
        ev.get("panelUser"),
    ]
    for k, v in ev.items():
        if str(k).lower() in _SKIP_KEYS:
            continue
        if "user" in str(k).lower() and v not in parts:
            parts.append(v)
    return panel_user_number(*parts)


def load_panel_names(path: Path | None = None) -> dict[str, str]:
    p = path or PANEL_USERS_PATH
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in data.items():
        ks = str(k).strip()
        vs = str(v or "").strip()
        if ks.isdigit() and vs:
            out[str(int(ks))] = vs
    return out


def panel_user_label(num: str, names: dict[str, str] | None = None) -> str:
    n = str(num or "").strip()
    if n.isdigit():
        n = str(int(n))
    if not n:
        return ""
    mapped = (names if names is not None else load_panel_names()).get(n)
    return mapped or f"User {n}"


def is_panel_actor(who: str, names: dict[str, str] | None = None) -> bool:
    s = str(who or "").strip()
    if not s:
        return False
    if panel_user_number(s):
        return True
    known = names if names is not None else load_panel_names()
    return s in set(known.values())


def resolve_area_actor_via(
    *,
    keypad_actor: str = "",
    event: dict | None = None,
    keypad_actors: set[str] | None = None,
) -> tuple[str, str]:
    """Web keypad → Remote + name. Panel code → Panel + User N (or mapped name). App name → App."""
    ev = event or {}
    who = str(keypad_actor or "").strip()
    actors = keypad_actors or set()
    if who and who in actors:
        return who, "Remote"
    num = panel_user_number_from_event(ev)
    if not num and who:
        num = panel_user_number(who)
    if num:
        return panel_user_label(num), "Panel"
    uf = str(ev.get("userFullname") or ev.get("olarmUser") or ev.get("userName") or "").strip()
    if uf and not panel_user_number(uf):
        return "", "App"
    state = str(ev.get("eventState") or ev.get("state") or "").strip().lower()
    if state in {"arm", "stay", "sleep"}:
        return "", "Auto"
    if state in {"disarm", "notready"}:
        return "", "Panel"
    return who, ""


def log_panel_user(rec: dict) -> None:
    try:
        PANEL_USER_LOG.parent.mkdir(parents=True, exist_ok=True)
        with PANEL_USER_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_panel_user_once(rec: dict) -> None:
    key = str((rec or {}).get("at") or "")
    if not key or key in _logged_ats:
        return
    if len(_logged_ats) > 400:
        _logged_ats.clear()
    _logged_ats.add(key)
    log_panel_user(rec)
