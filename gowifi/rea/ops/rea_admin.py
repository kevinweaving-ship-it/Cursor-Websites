#!/usr/bin/env python3
"""Safe REA management CLI for ChatGPT capture_process_scenario.

No unrestricted root shell. Tokens must match the helper charset.
Works as UID 996 with NoNewPrivileges via existing ForceCommand SSH.

Usage:

  /opt/rea/ops/bin/rea-admin gowifi -- capabilities
  /opt/rea/ops/bin/rea-admin gowifi -- status arial-whatsapp-poc
  /opt/rea/ops/bin/rea-admin sailingsa -- inspect-arial
  /opt/rea/ops/bin/rea-admin sailingsa -- status sailingsa-whatsapp-poc
  /opt/rea/ops/bin/rea-admin sailingsa -- can-control arial-whatsapp-poc
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:@/=+,-]+$")
ALLOWED_OPS = {
    "backup",
    "can-control",
    "capabilities",
    "decommission",
    "deploy",
    "disable",
    "enable",
    "health",
    "inspect-arial",
    "inventory",
    "journal",
    "migrate",
    "nginx",
    "preflight",
    "reload",
    "restart",
    "retarget-ingest",
    "rollback",
    "stage-api",
    "status",
    "stop",
    "whatsapp-status",
}
DENIED_OPS = {"admin", "exec-b64", "bash", "sh", "sudo", "rm", "dd", "mkfs", "fdisk"}


def _parse(proc: subprocess.CompletedProcess[str]) -> dict:
    raw = (proc.stdout or "").strip()
    if not raw:
        return {"ok": False, "error": "empty", "stderr": (proc.stderr or "")[-400:], "exit": proc.returncode}
    try:
        return json.loads(raw.splitlines()[-1])
    except json.JSONDecodeError:
        return {"ok": False, "error": "not_json", "raw": raw[-400:], "stderr": (proc.stderr or "")[-200:]}


def run_gowifi(tokens: list[str], timeout: int) -> dict:
    key = "/opt/rea/.ssh/id_rea_ops"
    argv = [
        "/usr/bin/ssh",
        "-n",
        "-T",
        "-i",
        key,
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "RequestTTY=no",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "UserKnownHostsFile=/opt/rea/.ssh/known_hosts",
        "-o",
        "AddressFamily=inet",
        "root@127.0.0.1",
        *tokens,
    ]
    return _parse(subprocess.run(argv, capture_output=True, text=True, timeout=timeout + 15))


def run_sailingsa(tokens: list[str], timeout: int) -> dict:
    payload = " ".join(tokens)
    argv = ["/usr/bin/ssh", "-T", "-o", "BatchMode=yes", "sailingsa-ops", payload]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout + 20)
    data = _parse(proc)
    data["via"] = "sailingsa-ops"
    return data


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] not in {"gowifi", "sailingsa", "arial"}:
        sys.stderr.write("usage: rea-admin gowifi|sailingsa -- <op> [args]\n")
        return 2
    target = "gowifi" if argv[0] in {"gowifi", "arial"} else "sailingsa"
    rest = argv[1:]
    if rest and rest[0] == "--":
        rest = rest[1:]
    if not rest:
        sys.stderr.write("missing operation\n")
        return 2
    if any(not SAFE_TOKEN.match(tok) for tok in rest):
        print(json.dumps({"ok": False, "error": "invalid_chars", "target": target}))
        return 2
    op = rest[0]
    if op in DENIED_OPS:
        print(json.dumps({"ok": False, "error": "denied_unrestricted_shell", "op": op, "target": target}))
        return 2
    if op not in ALLOWED_OPS:
        print(json.dumps({"ok": False, "error": "denied", "op": op, "target": target}))
        return 2
    timeout = int(os.environ.get("REA_ADMIN_TIMEOUT", "90"))
    result = run_gowifi(rest, timeout) if target == "gowifi" else run_sailingsa(rest, timeout)
    result["target"] = target
    result["general_root_shell"] = False
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
