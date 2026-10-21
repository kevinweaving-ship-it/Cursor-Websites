#!/usr/bin/env python3
"""Shared AI / search keys already used by sailor media cards and Latest News.

Writer (article polish): OpenAI ChatGPT, then Perplexity.
Search (media cards + news feed, already live): SerpAPI, then Bing.

Keys are loaded from the same env names and files those features already use.
Values are never returned — only whether a tool is wired.
"""
from __future__ import annotations

import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "SailingRoundupResearch/1.0", "Content-Type": "application/json"}

WRITER_ALIASES = {
    "openai": ("OPENAI_API_KEY", "CHATGPT_API_KEY", "GPT_API_KEY"),
    "perplexity": ("PERPLEXITY_API_KEY",),
}
SEARCH_ALIASES = {
    "serpapi": ("SERPAPI_API_KEY", "SERPAPI_KEY"),
    "bing": ("BING_SEARCH_KEY", "BING_API_KEY"),
}
ALIAS_COPY = (
    ("SERPAPI_KEY", "SERPAPI_API_KEY"),
    ("SERPAPI_API_KEY", "SERPAPI_KEY"),
    ("CHATGPT_API_KEY", "OPENAI_API_KEY"),
    ("GPT_API_KEY", "OPENAI_API_KEY"),
    ("BING_API_KEY", "BING_SEARCH_KEY"),
)
ENV_FILES = (
    ROOT / "data" / "roundup.env",
    ROOT / ".env",
    pathlib.Path("/opt/rea/work/sailing-roundup/data/roundup.env"),
    pathlib.Path("/opt/sailing-roundup/data/roundup.env"),
    pathlib.Path("/var/www/sailingsa/api/.env"),
    pathlib.Path("/etc/sailingsa/api.env"),
)


def _parse_env_file(path: pathlib.Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            out[key] = value
    return out


def load_env(root: pathlib.Path | None = None, extra_files=None, environ=None) -> dict[str, str]:
    """Load live news/media/writer keys without overriding an already-set env var."""
    environ = environ if environ is not None else os.environ
    files = []
    if root:
        files.extend([pathlib.Path(root) / "data" / "roundup.env", pathlib.Path(root) / ".env"])
    files.extend(ENV_FILES)
    files.extend(pathlib.Path(p) for p in (extra_files or []) if p)
    loaded: dict[str, str] = {}
    for path in files:
        if not path or not path.is_file():
            continue
        for key, value in _parse_env_file(path).items():
            if not value:
                continue
            loaded.setdefault(key, value)
            if not (environ.get(key) or "").strip():
                environ[key] = value
    for src, dest in ALIAS_COPY:
        value = (environ.get(src) or loaded.get(src) or "").strip()
        if value and not (environ.get(dest) or "").strip():
            environ[dest] = value
            loaded.setdefault(dest, value)
    return loaded


def _first_key(aliases: tuple[str, ...], environ=None) -> str:
    environ = environ if environ is not None else os.environ
    for name in aliases:
        value = (environ.get(name) or "").strip()
        if value:
            return value
    return ""


def writer_name(environ=None) -> str:
    environ = environ if environ is not None else os.environ
    if _first_key(WRITER_ALIASES["openai"], environ):
        return "openai"
    if _first_key(WRITER_ALIASES["perplexity"], environ):
        return "perplexity"
    return ""


def available(environ=None) -> dict:
    """Which tools are wired. Never includes key material."""
    environ = environ if environ is not None else os.environ
    writers = [name for name, aliases in WRITER_ALIASES.items() if _first_key(aliases, environ)]
    search = [name for name, aliases in SEARCH_ALIASES.items() if _first_key(aliases, environ)]
    writer = writer_name(environ)
    return {
        "writer": writer or None,
        "writers": writers,
        "search": search,
        "openai_model": (environ.get("OPENAI_MODEL") or "gpt-4o-mini") if writer == "openai" else None,
        "media_news_keys": search,
        "wired": bool(writers or search),
    }


def chat(system: str, user: str, environ=None, opener=None) -> tuple[str, str]:
    """Call the first wired writer. Returns (text, provider)."""
    environ = environ if environ is not None else os.environ
    opener = opener or urllib.request.urlopen
    openai = _first_key(WRITER_ALIASES["openai"], environ)
    if openai:
        try:
            payload = json.dumps(
                {
                    "model": environ.get("OPENAI_MODEL") or "gpt-4o-mini",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "temperature": 0.2,
                }
            ).encode()
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={**UA, "Authorization": "Bearer " + openai},
            )
            with opener(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            if text.strip():
                return text.strip(), "openai"
        except Exception:
            pass
    pplx = _first_key(WRITER_ALIASES["perplexity"], environ)
    if pplx:
        try:
            payload = json.dumps(
                {
                    "model": "sonar",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                }
            ).encode()
            req = urllib.request.Request(
                "https://api.perplexity.ai/chat/completions",
                data=payload,
                headers={**UA, "Authorization": "Bearer " + pplx},
            )
            with opener(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            if text.strip():
                return text.strip(), "perplexity"
        except Exception:
            pass
    return "", "official"
