#!/usr/bin/env python3
"""Root-owned ForceCommand helper for REA privileged ops.

Accepts only exact verbs from SSH_ORIGINAL_COMMAND. No shell. Used on
GoWifi via localhost SSH as root, matching sailing-roundup-timer.
On SailingSA the same file runs as rea-ops and uses narrowly scoped sudo.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UNIT_RE = re.compile(r"^[A-Za-z0-9_.:@\\-]+$")
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:@/=+,-]+$")

GOWIFI_STATUS = {
    "arial-whatsapp-poc",
    "arial-whatsapp-watcher",
    "openai-rea-tunnel",
    "sailing-roundup",
    "sailing-roundup.timer",
    "nginx",
    "certbot.timer",
    "rea-inspect-discover.timer",
}
GOWIFI_CONTROL = {"arial-whatsapp-poc", "arial-whatsapp-watcher", "nginx"}
SA_STATUS = {"sailingsa-api", "nginx", "postgresql", "certbot.timer"}
SA_CONTROL = {"sailingsa-api", "nginx"}
BACKUP_TARGETS = {
    "gowifi-whatsapp": ["/opt/arial-whatsapp-poc"],
    "gowifi-aerialnet": ["/opt/aerialnet-arial"],
    "gowifi-roundup": ["/opt/rea/work/sailing-roundup"],
    "sailingsa-api": ["/var/www/sailingsa/api/api.py"],
    "sailingsa-frontend-core": [
        "/var/www/sailingsa/index.html",
        "/var/www/sailingsa/blank.html",
        "/var/www/sailingsa/api/api.py",
    ],
    "gowifi-ops-stage": ["/opt/rea/ops/stage"],
    "sailingsa-ops-stage": ["/opt/rea-ops/stage"],
}


def host_id() -> str:
    if Path("/opt/rea-ops/etc/ops.json").is_file():
        return "sailingsa"
    return "gowifi"


def backup_root() -> Path:
    return Path("/opt/rea-ops/backups" if host_id() == "sailingsa" else "/opt/rea/ops/backups")


def emit(payload: dict[str, Any]) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return 0 if payload.get("ok") else 2


def run(argv: list[str], timeout: int = 40) -> subprocess.CompletedProcess[str]:
    if os.geteuid() != 0:
        argv = ["sudo", "-n", *argv]
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def allowed_units(control: bool = False) -> set[str]:
    if host_id() == "sailingsa":
        return SA_CONTROL if control else SA_STATUS
    return GOWIFI_CONTROL if control else GOWIFI_STATUS


def op_status(unit: str) -> dict[str, Any]:
    if not UNIT_RE.match(unit) or unit not in allowed_units(False):
        return {"ok": False, "error": "unit_denied", "unit": unit}
    show = run(["systemctl", "show", unit, "-p", "Id", "-p", "ActiveState", "-p", "SubState", "-p", "MainPID", "-p", "NRestarts", "-p", "ExecMainStartTimestamp", "-p", "Result", "-p", "UnitFileState"])
    active = run(["systemctl", "is-active", unit])
    return {
        "ok": True,
        "unit": unit,
        "active": active.stdout.strip(),
        "show": show.stdout.strip(),
    }


def op_journal(unit: str, lines: str) -> dict[str, Any]:
    if not UNIT_RE.match(unit) or unit not in allowed_units(False):
        return {"ok": False, "error": "unit_denied", "unit": unit}
    n = max(1, min(int(lines), 200))
    proc = run(["journalctl", "-u", unit, "-n", str(n), "--no-pager"])
    return {"ok": True, "unit": unit, "text": proc.stdout[-12000:], "stderr": proc.stderr[-400:]}


def op_control(action: str, unit: str) -> dict[str, Any]:
    if action not in {"restart", "reload"}:
        return {"ok": False, "error": "action_denied"}
    if not UNIT_RE.match(unit) or unit not in allowed_units(True):
        return {"ok": False, "error": "unit_denied", "unit": unit}
    if unit == "nginx" and action == "reload":
        test = run(["nginx", "-t"])
        if test.returncode != 0:
            return {"ok": False, "error": "nginx_test_failed", "stderr": test.stderr[-800:]}
        proc = run(["systemctl", "reload", "nginx"])
    else:
        proc = run(["systemctl", action, unit])
    return {"ok": proc.returncode == 0, "unit": unit, "action": action, "stderr": proc.stderr[-400:]}


def op_nginx(action: str) -> dict[str, Any]:
    if action == "test":
        proc = run(["nginx", "-t"])
        return {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}
    if action == "reload":
        return op_control("reload", "nginx")
    return {"ok": False, "error": "action_denied"}


def op_backup(target: str) -> dict[str, Any]:
    paths = BACKUP_TARGETS.get(target)
    if not paths:
        return {"ok": False, "error": "target_denied", "target": target}
    root = backup_root()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest = root / f"{target}-{stamp}"
    dest.mkdir(parents=True, exist_ok=False)
    copied = []
    for src in paths:
        src_path = Path(src)
        if not src_path.exists():
            continue
        if src_path.is_dir():
            shutil.copytree(
                src_path,
                dest / src_path.name,
                ignore=shutil.ignore_patterns("auth", "event-whatsapp", "node_modules", "node", "__pycache__"),
                dirs_exist_ok=True,
            )
        else:
            shutil.copy2(src_path, dest / src_path.name)
        copied.append(src)
    (dest / "MANIFEST.json").write_text(json.dumps({"target": target, "copied": copied, "ts": stamp}), encoding="utf-8")
    return {"ok": True, "backup_id": dest.name, "path": str(dest), "copied": copied}


def op_rollback(backup_id: str) -> dict[str, Any]:
    if not SAFE_TOKEN.match(backup_id):
        return {"ok": False, "error": "target_denied"}
    dest = backup_root() / backup_id
    manifest = dest / "MANIFEST.json"
    if not manifest.is_file():
        return {"ok": False, "error": "missing_backup"}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    target = data.get("target")
    paths = BACKUP_TARGETS.get(target or "")
    if not paths:
        return {"ok": False, "error": "target_denied"}
    restored = []
    for src in paths:
        src_path = Path(src)
        backup_item = dest / src_path.name
        if not backup_item.exists():
            continue
        if src_path.is_dir() or backup_item.is_dir():
            if src_path.exists():
                shutil.copytree(backup_item, src_path, dirs_exist_ok=True)
            else:
                shutil.copytree(backup_item, src_path)
        else:
            shutil.copy2(backup_item, src_path)
        restored.append(src)
    return {"ok": True, "backup_id": backup_id, "restored": restored, "note": "files restored; services were not restarted"}


def op_inventory() -> dict[str, Any]:
    timers = subprocess.run(["systemctl", "list-timers", "--all", "--no-pager"], capture_output=True, text=True)
    units = subprocess.run(["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"], capture_output=True, text=True)
    cron = []
    cron_dir = Path("/etc/cron.d")
    if cron_dir.is_dir():
        cron = sorted(p.name for p in cron_dir.iterdir())
    docker_lines = ["docker_unavailable"]
    if shutil.which("docker"):
        docker = subprocess.run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], capture_output=True, text=True)
        if docker.returncode == 0:
            docker_lines = docker.stdout.splitlines()[:20]
    certs = []
    live = Path("/etc/letsencrypt/live")
    if live.is_dir():
        certs = sorted(p.name for p in live.iterdir() if p.is_dir())
    return {
        "ok": True,
        "host": host_id(),
        "timers": timers.stdout.splitlines()[:40],
        "running_services": units.stdout.splitlines()[:60],
        "cron.d": cron,
        "docker": docker_lines,
        "certs": certs,
    }


def dispatch(tokens: list[str]) -> dict[str, Any]:
    if not tokens:
        return {"ok": False, "error": "empty"}
    op, *args = tokens
    if op == "status" and args:
        return op_status(args[0])
    if op == "journal" and args:
        return op_journal(args[0], args[1] if len(args) > 1 else "80")
    if op in {"restart", "reload"} and args:
        return op_control(op, args[0])
    if op == "nginx" and args:
        return op_nginx(args[0])
    if op == "backup" and args:
        return op_backup(args[0])
    if op == "rollback" and args:
        return op_rollback(args[0])
    if op == "inventory":
        return op_inventory()
    return {"ok": False, "error": "denied", "op": op}


def main() -> int:
    raw = os.environ.get("SSH_ORIGINAL_COMMAND")
    if raw is None:
        raw = " ".join(sys.argv[1:])
    # Exact tokens only; no metacharacters.
    if re.search(r"[^A-Za-z0-9_.:@/=+\s,-]", raw or ""):
        return emit({"ok": False, "error": "invalid_chars"})
    tokens = (raw or "").split()
    return emit(dispatch(tokens))


if __name__ == "__main__":
    raise SystemExit(main())
