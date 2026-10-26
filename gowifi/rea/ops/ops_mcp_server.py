#!/usr/bin/env python3
"""ChatGPT-facing ops MCP tools. No generic shell. Prefer these over capture_process_scenario."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import rea_ops
except ImportError:
    import importlib.machinery
    import importlib.util

    _path = Path(__file__).resolve().parent / "rea-ops"
    _spec = importlib.util.spec_from_loader("rea_ops", importlib.machinery.SourceFileLoader("rea_ops", str(_path)))
    rea_ops = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(rea_ops)

PROTOCOL = "2025-11-25"
TARGET = {"type": "string", "enum": ["gowifi", "sailingsa"]}
RO = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
RW = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}

TOOLS = [
    {"name": "ops_whatsapp_status", "description": "Arial WhatsApp diagnosis: unit state, journal, health.json, recent send/retry log tails. Does not send messages.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {}}, "annotations": RO},
    {"name": "ops_inventory", "description": "List running services, timers, cron.d, docker, and certificate names on GoWifi or SailingSA.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET}, "required": ["target"]}, "annotations": RO},
    {"name": "ops_read_file", "description": "Read one allowlisted application file. Secrets are redacted. Auth/session files are denied.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "path": {"type": "string"}, "offset": {"type": "integer", "default": 0}, "length": {"type": "integer", "default": 120000}}, "required": ["target", "path"]}, "annotations": RO},
    {"name": "ops_write_file", "description": "Write one allowlisted application file. Does not touch secrets, nginx private keys, or WhatsApp auth state.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "path": {"type": "string"}, "content": {"type": "string"}}, "required": ["target", "path", "content"]}, "annotations": RW},
    {"name": "ops_logs", "description": "Read allowlisted journal units or log files.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "unit": {"type": "string"}, "lines": {"type": "integer", "default": 80}}, "required": ["target", "unit"]}, "annotations": RO},
    {"name": "ops_service", "description": "status, restart, or reload an allowlisted unit. Prefer status. Do not restart merely to prove access.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "action": {"type": "string", "enum": ["status", "restart", "reload"]}, "unit": {"type": "string"}}, "required": ["target", "action", "unit"]}, "annotations": RW},
    {"name": "ops_nginx", "description": "nginx -t or reload on the selected box.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "action": {"type": "string", "enum": ["test", "reload"]}}, "required": ["target", "action"]}, "annotations": RW},
    {"name": "ops_db", "description": "Application database query (SELECT) or constrained DML. DDL and GRANT are denied. Use schema rea_ops / database rea_ops for probes.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "mode": {"type": "string", "enum": ["query", "exec"]}, "sql": {"type": "string"}}, "required": ["target", "mode", "sql"]}, "annotations": RW},
    {"name": "ops_run", "description": "Run an allowlisted build/check/test command such as python3 -m py_compile or node --check.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "argv": {"type": "array", "items": {"type": "string"}}}, "required": ["target", "argv"]}, "annotations": RO},
    {"name": "ops_git", "description": "Local git status/diff/log/branch/add/commit. Push only if an existing remote credential already works.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "root": {"type": "string"}, "action": {"type": "string", "enum": ["status", "diff", "log", "branch", "add", "commit", "push"]}, "arg": {"type": "string"}}, "required": ["target", "root", "action"]}, "annotations": RW},
    {"name": "ops_backup", "description": "Create a scoped backup of an allowlisted target.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "name": {"type": "string"}}, "required": ["target", "name"]}, "annotations": RO},
    {"name": "ops_rollback", "description": "Restore files from a backup id. Does not restart services.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "backup_id": {"type": "string"}}, "required": ["target", "backup_id"]}, "annotations": RW},
    {"name": "ops_http_check", "description": "GET-only HTTP check against an allowlisted local or public hostname.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "url": {"type": "string"}}, "required": ["target", "url"]}, "annotations": RO},
    {"name": "ops_jobs", "description": "Start, poll, or cancel a long-running allowlisted command. Tunnel deadline is ~120s so poll by job_id.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "action": {"type": "string", "enum": ["start", "status", "cancel"]}, "argv": {"type": "array", "items": {"type": "string"}}, "job_id": {"type": "string"}}, "required": ["target", "action"]}, "annotations": RW},
    {"name": "ops_health", "description": "Health of sailingsa-api, WhatsApp UP state, or nginx -t. Does not send messages or restart.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "name": {"type": "string", "enum": ["sailingsa-api", "whatsapp", "nginx"]}}, "required": ["target", "name"]}, "annotations": RO},
    {"name": "ops_deploy", "description": "Existing deploy workflow: plan-api, stage-api, api (wraps /root/deploy_api_verified.sh), static probe, frontend zip (excludes hub_hero.json), whatsapp-code, aerialnet. Destructive kinds are explicit.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "kind": {"type": "string", "enum": ["plan-api", "stage-api", "api", "static", "static-clean", "frontend", "whatsapp-code", "aerialnet"]}}, "required": ["target", "kind"]}, "annotations": RW},
    {"name": "ops_migrate", "description": "Auto-run only rea_ops probe SQL. Public schema DDL is denied and must stay staged for review.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "schema": {"type": "string", "enum": ["rea_ops"]}}, "required": ["target", "schema"]}, "annotations": RW},
    {"name": "ops_deps", "description": "Compile/check or install Python deps into a stage venv. Does not mutate system site-packages.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "kind": {"type": "string", "enum": ["py-compile", "py-file", "node-check", "pip-stage"]}, "root": {"type": "string"}}, "required": ["target", "kind", "root"]}, "annotations": RO},
    {"name": "ops_transfer", "description": "Copy an allowlisted file on the same box, or push a staged file from GoWifi to /opt/rea-ops/stage on SailingSA.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "action": {"type": "string", "enum": ["copy", "to-sailingsa"]}, "src": {"type": "string"}, "dest": {"type": "string"}}, "required": ["target", "action", "src"]}, "annotations": RW},
    {"name": "ops_gh", "description": "REA GitHub identity: status/keygen/clone/whoami/probe-push. Never prints private keys. ChatGPT GitHub connector is UNVERIFIED unless tested in ChatGPT itself.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"target": TARGET, "action": {"type": "string", "enum": ["status", "keygen", "clone", "whoami", "probe-push"]}, "arg": {"type": "string"}}, "required": ["target", "action"]}, "annotations": RW},
]


def write_message(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def cfg_for(target: str) -> dict[str, Any]:
    if target == "sailingsa":
        path = "/opt/rea/ops/etc/ops.sailingsa.client.json"
        if Path(path).is_file():
            return rea_ops.load_config(path)
        # When running on SailingSA itself.
        return rea_ops.load_config("/opt/rea-ops/etc/ops.json")
    return rea_ops.load_config("/opt/rea/ops/etc/ops.json")


def call_target(target: str, argv: list[str]) -> dict[str, Any]:
    if target == "sailingsa" and Path("/opt/rea/ops/etc/ops.sailingsa.client.json").is_file():
        cfg = cfg_for("sailingsa")
        return rea_ops.helper_call(cfg, argv)
    cfg = cfg_for(target)
    return rea_ops.dispatch(cfg, argv)


def handle(name: str, args: dict[str, Any]) -> dict[str, Any]:
    target = args.get("target") or "gowifi"
    if name == "ops_whatsapp_status":
        return call_target("gowifi", ["whatsapp-status"])
    if name == "ops_inventory":
        return call_target(target, ["inventory"])
    if name == "ops_read_file":
        return call_target(target, ["read-file", args["path"], str(args.get("offset") or 0), str(args.get("length") or 120000)])
    if name == "ops_write_file":
        import base64

        content = args["content"]
        if target == "sailingsa" and Path("/opt/rea/ops/etc/ops.sailingsa.client.json").is_file():
            payload = "b64:" + base64.b64encode(content.encode("utf-8")).decode("ascii")
            return call_target(target, ["write-file", args["path"], payload])
        return rea_ops.write_file(cfg_for(target), args["path"], content)
    if name == "ops_logs":
        return call_target(target, ["journal", args["unit"], str(args.get("lines") or 80)])
    if name == "ops_service":
        return call_target(target, [args["action"], args["unit"]])
    if name == "ops_nginx":
        return call_target(target, ["nginx", args["action"]])
    if name == "ops_db":
        return call_target(target, ["db-exec" if args["mode"] == "exec" else "db-query", args["sql"]])
    if name == "ops_run":
        return call_target(target, ["run", *list(args.get("argv") or [])])
    if name == "ops_git":
        extra = [args["arg"]] if args.get("arg") else []
        return call_target(target, ["git", args["root"], args["action"], *extra])
    if name == "ops_backup":
        return call_target(target, ["backup", args["name"]])
    if name == "ops_rollback":
        return call_target(target, ["rollback", args["backup_id"]])
    if name == "ops_http_check":
        return call_target(target, ["http", args["url"]])
    if name == "ops_jobs":
        action = args["action"]
        if action == "start":
            return call_target(target, ["jobs-start", *list(args.get("argv") or [])])
        if action == "status":
            return call_target(target, ["jobs-status", args.get("job_id") or ""])
        return call_target(target, ["jobs-cancel", args.get("job_id") or ""])
    if name == "ops_health":
        return call_target(target, ["health", args["name"]])
    if name == "ops_deploy":
        return call_target(target, ["deploy", args["kind"]])
    if name == "ops_migrate":
        return call_target(target, ["migrate", args["schema"]])
    if name == "ops_deps":
        return call_target(target, ["deps", args["kind"], args["root"]])
    if name == "ops_transfer":
        argv = ["transfer", args["action"], args["src"]]
        if args.get("dest"):
            argv.append(args["dest"])
        return call_target(target, argv)
    if name == "ops_gh":
        extra = [args["arg"]] if args.get("arg") else []
        return call_target(target, ["gh", args["action"], *extra])
    return {"ok": False, "error": "unknown_tool", "name": name}


def main() -> int:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        method = msg.get("method")
        req_id = msg.get("id")
        if method is None:
            continue
        if str(method).startswith("notifications/"):
            continue
        if method == "initialize":
            write_message({"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": {"name": "rea-ops", "version": "1.0.0"}}})
            continue
        if method == "tools/list":
            write_message({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
            continue
        if method == "tools/call":
            params = msg.get("params") or {}
            name = str(params.get("name") or "")
            args = params.get("arguments") or {}
            result = handle(name, args)
            text = json.dumps(result, ensure_ascii=True)
            write_message({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": text}]}})
            continue
        if method == "ping":
            write_message({"jsonrpc": "2.0", "id": req_id, "result": {}})
            continue
        write_message({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": str(method)}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
