#!/usr/bin/env python3
"""GoWifi-side REA inspect dispatcher.

ChatGPT invokes this through existing REA MCP:
  capture_process_scenario
    executable: /opt/rea/inspect/bin/rea-inspect
    arguments:  [target, op, ...]

Targets: gowifi | sailingsa | both
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path("/opt/rea/inspect")
LOCAL_AGENT = ROOT / "bin" / "inspect-agent"
REMOTE_HOST = "sailingsa-inspect"
REPO = ROOT / "repo"
CATALOG = ROOT / "CATALOG.md"


def emit(payload: Any, code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2 if sys.stdout.isatty() else None))
    return code


def local_call(req: dict[str, Any]) -> dict[str, Any]:
    proc = subprocess.run(
        [str(LOCAL_AGENT), json.dumps(req, ensure_ascii=True)],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "REA_INSPECT_CONFIG": str(ROOT / "etc" / "inspect.json")},
    )
    if not proc.stdout.strip():
        return {"ok": False, "error": "empty_local", "message": proc.stderr[-800:]}
    try:
        return json.loads(proc.stdout.splitlines()[-1])
    except json.JSONDecodeError:
        return {"ok": False, "error": "bad_local_json", "raw": proc.stdout[-800:]}


def remote_call(req: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(req, ensure_ascii=True)
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", REMOTE_HOST, payload],
        capture_output=True,
        text=True,
        timeout=40,
    )
    if not proc.stdout.strip():
        return {
            "ok": False,
            "error": "empty_remote",
            "message": proc.stderr[-800:] or "no output from SailingSA inspect agent",
        }
    try:
        return json.loads(proc.stdout.splitlines()[-1])
    except json.JSONDecodeError:
        return {"ok": False, "error": "bad_remote_json", "raw": proc.stdout[-800:], "stderr": proc.stderr[-400:]}


def call(target: str, req: dict[str, Any]) -> dict[str, Any]:
    if target == "gowifi":
        return local_call(req)
    if target == "sailingsa":
        return remote_call(req)
    if target == "both":
        return {"ok": True, "gowifi": local_call(req), "sailingsa": remote_call(req)}
    return {"ok": False, "error": "bad_target", "message": "target must be gowifi, sailingsa, or both"}


def help_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "usage": "rea-inspect <gowifi|sailingsa|both> <op> [args]",
        "mcp": {
            "tools": [
                "audit_discover",
                "audit_read_file",
                "audit_search_source",
                "audit_database_schema",
                "audit_select_query",
                "audit_nginx",
                "audit_logs",
                "audit_deployment",
                "audit_compare",
            ],
            "avoid": "capture_process_scenario",
            "executable": "/opt/rea/inspect/bin/rea-inspect",
            "examples": [
                ["sailingsa", "schema"],
                ["sailingsa", "sql", "SELECT count(*) FROM sailors"],
                ["sailingsa", "get", "/var/www/sailingsa/api/api.py"],
                ["gowifi", "list", "/opt/aerialnet-arial"],
                ["both", "discover"],
                ["sailingsa", "compare"],
            ],
            "browser": {
                "tool": "capture_browser_scenario",
                "executable_path": "/opt/chromium/chrome",
            },
            "catalog": str(CATALOG),
        },
        "ops": [
            "help",
            "catalog",
            "list",
            "get",
            "find",
            "sql",
            "schema",
            "logs",
            "nginx",
            "revision",
            "discover",
            "compare",
        ],
    }


COMPARE_MAP = [
    ("/var/www/sailingsa/api/api.py", "api.py"),
    ("/var/www/sailingsa/blank.html", "sailingsa/frontend/blank.html"),
    ("/var/www/sailingsa/index.html", "sailingsa/frontend/index.html"),
    ("/var/www/sailingsa/js", "sailingsa/frontend/js"),
    ("/var/www/sailingsa/css", "sailingsa/frontend/css"),
    ("/var/www/sailingsa/templates", "sailingsa/frontend/templates"),
]


def file_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_sailingsa() -> dict[str, Any]:
    rows = []
    for live, repo_rel in COMPARE_MAP:
        live_info = remote_call({"op": "get", "path": live, "offset": 0, "length": 32})
        repo_path = REPO / repo_rel
        repo_sha = file_sha(repo_path)
        live_sha = live_info.get("sha256") if live_info.get("ok") else None
        status = "missing"
        if live_sha and repo_sha:
            status = "match" if live_sha == repo_sha else "differ"
        elif live_sha:
            status = "live_only"
        elif repo_sha:
            status = "repo_only"
        if live_info.get("ok") and Path(live).suffix == "" and live_info.get("size", 0) == 0:
            status = "dir"
        rows.append(
            {
                "live": live,
                "repo": str(repo_path),
                "status": status,
                "live_sha256": live_sha,
                "repo_sha256": repo_sha,
                "live_size": live_info.get("size"),
                "live_error": None if live_info.get("ok") else live_info.get("message"),
            }
        )
    return {"ok": True, "target": "sailingsa", "items": rows}


def build_req(op: str, args: list[str]) -> dict[str, Any]:
    req: dict[str, Any] = {"op": op}
    if op in {"list", "get"} and args:
        req["path"] = args[0]
        if op == "get" and len(args) > 1:
            req["offset"] = int(args[1])
        if op == "get" and len(args) > 2:
            req["length"] = int(args[2])
    elif op == "sql" and args:
        req["query"] = " ".join(args)
    elif op == "logs" and args:
        req["source"] = args[0]
        if len(args) > 1:
            req["lines"] = int(args[1])
    elif op == "find":
        if args:
            req["root"] = args[0]
        if len(args) > 1:
            req["glob"] = args[1]
        if len(args) > 2:
            req["since"] = args[2]
    elif op == "discover" and args:
        req["since"] = args[0]
    return req


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "help"}:
        return emit(help_payload())
    if argv[0] == "catalog":
        if CATALOG.is_file():
            return emit({"ok": True, "path": str(CATALOG), "text": CATALOG.read_text(encoding="utf-8")})
        return emit(help_payload())
    target, *rest = argv
    if target not in {"gowifi", "sailingsa", "both"}:
        if target in {
            "help",
            "list",
            "get",
            "find",
            "sql",
            "schema",
            "logs",
            "nginx",
            "revision",
            "discover",
            "compare",
        }:
            rest = [target, *rest]
            target = "sailingsa"
        else:
            return emit({"ok": False, "error": "bad_target", "message": "first arg must be gowifi, sailingsa, or both"}, 2)
    op = rest[0] if rest else "help"
    args = rest[1:]
    if op in {"help", "catalog"}:
        return emit(help_payload())
    if op == "compare":
        return emit(compare_sailingsa())
    result = call(target, build_req(op, args))
    return emit(result, 0 if result.get("ok") else 1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
