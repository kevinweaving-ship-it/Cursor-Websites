#!/usr/bin/env python3
"""Read-only audit MCP server for ChatGPT.

Dedicated tools only. No shell, no executable_path, no capture_process_scenario.
Calls the existing allowlisted inspect dispatcher over argv.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

INSPECT = Path(os.environ.get("REA_INSPECT_BIN", "/opt/rea/inspect/bin/rea-inspect"))
PROTOCOL = "2025-11-25"
TARGET = {"type": "string", "enum": ["gowifi", "sailingsa"]}
TARGET_OR_BOTH = {"type": "string", "enum": ["gowifi", "sailingsa", "both"]}
ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "audit_discover",
        "description": "List recently changed allowlisted source and config files on GoWifi and/or SailingSA. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "target": TARGET_OR_BOTH,
                "since": {"type": "string", "description": "ISO-8601 timestamp; optional"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
            },
            "required": ["target"],
        },
        "annotations": ANNOTATIONS,
    },
    {
        "name": "audit_read_file",
        "description": "Read one allowlisted source or config file from GoWifi or SailingSA. Secrets are redacted. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "target": TARGET,
                "path": {"type": "string", "minLength": 1},
                "offset": {"type": "integer", "minimum": 0, "default": 0},
                "length": {"type": "integer", "minimum": 1, "maximum": 1500000, "default": 120000},
            },
            "required": ["target", "path"],
        },
        "annotations": ANNOTATIONS,
    },
    {
        "name": "audit_search_source",
        "description": "Find allowlisted source files by glob on GoWifi or SailingSA. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "target": TARGET,
                "root": {"type": "string", "minLength": 1},
                "glob": {"type": "string", "minLength": 1, "default": "*.py"},
                "since": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 80},
            },
            "required": ["target", "root"],
        },
        "annotations": ANNOTATIONS,
    },
    {
        "name": "audit_database_schema",
        "description": "Return the read-only information_schema catalog for the selected server database. SailingSA is PostgreSQL sailors_master. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"target": TARGET},
            "required": ["target"],
        },
        "annotations": ANNOTATIONS,
    },
    {
        "name": "audit_select_query",
        "description": "Run one allowlisted read-only diagnostic query (SELECT/WITH/EXPLAIN/SHOW only) on the selected server. No writes. No shell.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "target": TARGET,
                "query": {"type": "string", "minLength": 8, "maxLength": 4000},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
            },
            "required": ["target", "query"],
        },
        "annotations": ANNOTATIONS,
    },
    {
        "name": "audit_nginx",
        "description": "Return allowlisted nginx site configuration text for GoWifi or SailingSA/TimAdvisor. Certificate private keys are not included. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"target": TARGET},
            "required": ["target"],
        },
        "annotations": ANNOTATIONS,
    },
    {
        "name": "audit_logs",
        "description": "Return the last N lines of an allowlisted log source. Secrets are redacted. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "target": TARGET,
                "source": {
                    "type": "string",
                    "enum": ["nginx-error", "nginx-access", "sailingsa-api"],
                },
                "lines": {"type": "integer", "minimum": 1, "maximum": 200, "default": 80},
            },
            "required": ["target", "source"],
        },
        "annotations": ANNOTATIONS,
    },
    {
        "name": "audit_deployment",
        "description": "Return live deployment revision metadata (mtime, size, git tip when present) for allowlisted roots. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"target": TARGET},
            "required": ["target"],
        },
        "annotations": ANNOTATIONS,
    },
    {
        "name": "audit_compare",
        "description": "Compare live SailingSA deployed files with the repo snapshot on the REA box. Read-only.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "target": {"type": "string", "enum": ["sailingsa"], "default": "sailingsa"}
            },
        },
        "annotations": ANNOTATIONS,
    },
]


def write_message(payload: dict[str, Any]) -> None:
    line = json.dumps(payload, ensure_ascii=True) + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()


def error_result(code: int, message: str, req_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def ok_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def inspect_call(argv: list[str]) -> dict[str, Any]:
    if not INSPECT.is_file():
        return {"ok": False, "error": "missing_dispatcher", "message": str(INSPECT)}
    proc = subprocess.run(
        [str(INSPECT), *argv],
        capture_output=True,
        text=True,
        timeout=40,
        env={**os.environ, "HOME": os.environ.get("HOME", "/opt/rea")},
    )
    raw = (proc.stdout or "").strip()
    if not raw:
        return {"ok": False, "error": "empty_inspect", "message": (proc.stderr or "")[-800:]}
    try:
        return json.loads(raw.splitlines()[-1])
    except json.JSONDecodeError:
        return {"ok": False, "error": "bad_inspect_json", "raw": raw[-800:]}


def handle_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    target = args.get("target") or "sailingsa"
    if name == "audit_discover":
        argv = [target, "discover"]
        if args.get("since"):
            argv.append(str(args["since"]))
        return inspect_call(argv)
    if name == "audit_read_file":
        argv = [target, "get", str(args["path"])]
        if "offset" in args:
            argv.append(str(int(args["offset"])))
        if "length" in args:
            argv.append(str(int(args["length"])))
        return inspect_call(argv)
    if name == "audit_search_source":
        argv = [target, "find", str(args["root"]), str(args.get("glob") or "*")]
        if args.get("since"):
            argv.append(str(args["since"]))
        return inspect_call(argv)
    if name == "audit_database_schema":
        return inspect_call([target, "schema"])
    if name == "audit_select_query":
        return inspect_call([target, "sql", str(args["query"])])
    if name == "audit_nginx":
        return inspect_call([target, "nginx"])
    if name == "audit_logs":
        argv = [target, "logs", str(args["source"])]
        if "lines" in args:
            argv.append(str(int(args["lines"])))
        return inspect_call(argv)
    if name == "audit_deployment":
        return inspect_call([target, "revision"])
    if name == "audit_compare":
        return inspect_call(["sailingsa", "compare"])
    return {"ok": False, "error": "unknown_tool", "message": name}


def handle(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    req_id = msg.get("id")
    if method is None:
        return None
    if str(method).startswith("notifications/"):
        return None
    if method == "initialize":
        return ok_result(
            req_id,
            {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "rea-audit", "version": "1.0.0"},
                "instructions": (
                    "Read-only production audit tools for GoWifi and SailingSA. "
                    "Use audit_* tools instead of capture_process_scenario. "
                    "No writes, no shell, no secrets."
                ),
            },
        )
    if method == "ping":
        return ok_result(req_id, {})
    if method == "tools/list":
        return ok_result(req_id, {"tools": TOOLS})
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return error_result(-32602, "arguments must be an object", req_id)
        names = {tool["name"] for tool in TOOLS}
        if name not in names:
            return error_result(-32601, f"unknown tool {name}", req_id)
        result = handle_tool(str(name), arguments)
        text = json.dumps(result, ensure_ascii=True)
        return ok_result(
            req_id,
            {
                "content": [{"type": "text", "text": text}],
                "structuredContent": result,
                "isError": not bool(result.get("ok")),
            },
        )
    return error_result(-32601, f"unknown method {method}", req_id)


def read_messages():
    header_buf = []
    content_len = None
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return
        if line.startswith(b"{") or line.startswith(b"["):
            yield json.loads(line.decode("utf-8"))
            continue
        decoded = line.decode("utf-8", errors="replace")
        if decoded.lower().startswith("content-length:"):
            content_len = int(decoded.split(":", 1)[1].strip())
            header_buf = ["cl"]
            continue
        if header_buf and decoded.strip() == "":
            body = sys.stdin.buffer.read(content_len or 0)
            yield json.loads(body.decode("utf-8"))
            header_buf = []
            content_len = None
            continue


def main() -> int:
    for msg in read_messages():
        reply = handle(msg)
        if reply is not None:
            write_message(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
