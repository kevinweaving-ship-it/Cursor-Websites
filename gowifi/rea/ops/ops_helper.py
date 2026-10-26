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
    "aerialnet-hansekop-api",
    "aerialnet-voelklip-api",
    "arial-site-watch",
    "tuya-sharing",
}
GOWIFI_CONTROL = {
    "arial-whatsapp-poc",
    "arial-whatsapp-watcher",
    "nginx",
    "aerialnet-hansekop-api",
    "aerialnet-voelklip-api",
    "arial-site-watch",
}
SA_STATUS = {"sailingsa-api", "nginx", "postgresql", "certbot.timer"}
SA_CONTROL = {"sailingsa-api", "nginx"}
API_LIVE = Path("/var/www/sailingsa/api/api.py")
API_HELPER = Path("/var/www/sailingsa/api/regatta_host_code.py")
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


def op_preflight(unit: str) -> dict[str, Any]:
    if not UNIT_RE.match(unit) or unit not in allowed_units(False):
        return {"ok": False, "error": "unit_denied", "unit": unit}
    show = run(
        [
            "systemctl",
            "show",
            unit,
            "-p",
            "ActiveState",
            "-p",
            "SubState",
            "-p",
            "MainPID",
            "-p",
            "NRestarts",
            "-p",
            "ActiveEnterTimestamp",
            "-p",
            "Job",
        ]
    )
    jobs = run(["systemctl", "list-jobs", "--no-pager"])
    busy = any(unit in line for line in jobs.stdout.splitlines() if line.strip() and not line.startswith("No jobs"))
    return {
        "ok": not busy,
        "unit": unit,
        "show": show.stdout.strip(),
        "jobs": jobs.stdout.strip()[:800],
        "busy": busy,
    }


def op_control(action: str, unit: str) -> dict[str, Any]:
    if action not in {"restart", "reload"}:
        return {"ok": False, "error": "action_denied"}
    if not UNIT_RE.match(unit) or unit not in allowed_units(True):
        return {"ok": False, "error": "unit_denied", "unit": unit}
    pre = op_preflight(unit)
    if pre.get("busy"):
        return {"ok": False, "error": "unit_busy", "preflight": pre}
    if unit == "arial-whatsapp-poc":
        return {"ok": False, "error": "whatsapp_poc_guard", "note": "poc restart is denied while the live session is UP. Use status/health only."}
    if unit == "nginx" and action == "reload":
        test = run(["nginx", "-t"])
        if test.returncode != 0:
            return {"ok": False, "error": "nginx_test_failed", "stderr": test.stderr[-800:]}
        proc = run(["systemctl", "reload", "nginx"])
    else:
        proc = run(["systemctl", action, unit])
    health = {}
    if unit == "sailingsa-api":
        health = op_health("sailingsa-api")
    if unit == "arial-whatsapp-watcher":
        health = op_health("whatsapp")
    return {"ok": proc.returncode == 0, "unit": unit, "action": action, "stderr": proc.stderr[-400:], "health": health}


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


def _is_immutable(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    proc = run(["lsattr", str(path)])
    attrs = (proc.stdout.split() or [""])[0]
    return "i" in attrs


def _chattr(path: Path, add: bool) -> None:
    flag = "+i" if add else "-i"
    run(["chattr", flag, str(path)])


def _restore_owner(path: Path, user: str, group: str) -> None:
    if path.exists():
        shutil.chown(path, user=user, group=group)


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
        immutable = src_path.is_file() and _is_immutable(src_path)
        if immutable:
            _chattr(src_path, False)
        if src_path.is_dir() or backup_item.is_dir():
            if src_path.exists():
                shutil.copytree(backup_item, src_path, dirs_exist_ok=True)
            else:
                shutil.copytree(backup_item, src_path)
        else:
            shutil.copy2(backup_item, src_path)
        if immutable:
            _chattr(src_path, True)
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


def op_health(name: str) -> dict[str, Any]:
    if name == "sailingsa-api":
        active = run(["systemctl", "is-active", "sailingsa-api"]).stdout.strip()
        curl = subprocess.run(
            [
                "curl",
                "-sS",
                "-k",
                "-m",
                "12",
                "-o",
                "/tmp/rea-ops-health.out",
                "-w",
                "%{http_code}",
                "-H",
                "Host: sailingsa.co.za",
                "https://127.0.0.1/admin/api/version",
            ],
            capture_output=True,
            text=True,
        )
        body = Path("/tmp/rea-ops-health.out").read_text(encoding="utf-8", errors="replace")[:400] if Path("/tmp/rea-ops-health.out").is_file() else ""
        return {"ok": active == "active" and curl.stdout.strip() in {"200", "301", "302"}, "active": active, "http": curl.stdout.strip(), "body": body}
    if name == "whatsapp":
        health = Path("/opt/arial-whatsapp-poc/state/health.json")
        text = health.read_text(encoding="utf-8", errors="replace") if health.is_file() else "{}"
        data = json.loads(text) if text.strip().startswith("{") else {}
        active = run(["systemctl", "is-active", "arial-whatsapp-poc"]).stdout.strip()
        return {"ok": active == "active" and data.get("state") == "UP", "active": active, "state": data.get("state"), "reconnects": data.get("reconnects"), "qrAvailable": data.get("qrAvailable")}
    return {"ok": False, "error": "health_denied", "name": name}


def op_stage_live_api() -> dict[str, Any]:
    src = API_LIVE
    dest = Path("/opt/rea-ops/stage/api.py")
    if not src.is_file():
        return {"ok": False, "error": "missing_live_api"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    os.chmod(dest, 0o640)
    try:
        shutil.chown(dest, user="rea-ops", group="rea-ops")
    except LookupError:
        pass
    helper_note = None
    if API_HELPER.is_file():
        hdest = Path("/opt/rea-ops/stage/regatta_host_code.py")
        shutil.copy2(API_HELPER, hdest)
        helper_note = str(hdest)
    return {
        "ok": True,
        "path": str(dest),
        "immutable": _is_immutable(src),
        "sha256": subprocess.check_output(["sha256sum", str(dest)], text=True).split()[0],
        "helper": helper_note,
    }


def _apply_sailingsa_acl(path: Path) -> None:
    run(["setfacl", "-m", "u:rea-ops:rwX", str(path)])


def op_deploy(kind: str) -> dict[str, Any]:
    if kind == "plan-api":
        incoming = Path("/opt/rea-ops/stage/api.py")
        live = API_LIVE
        return {
            "ok": True,
            "kind": "api",
            "stage_exists": incoming.is_file(),
            "live_exists": live.is_file(),
            "immutable": _is_immutable(live),
            "script": "/root/deploy_api_verified.sh",
            "note": "Existing script copies incoming→live, clears chattr +i, restarts sailingsa-api. Helper restores +i when it was set.",
        }
    if kind == "api":
        if host_id() != "sailingsa":
            return {"ok": False, "error": "wrong_host"}
        stage = Path("/opt/rea-ops/stage/api.py")
        if not stage.is_file():
            return {"ok": False, "error": "missing_stage", "path": str(stage)}
        pre = op_preflight("sailingsa-api")
        if pre.get("busy"):
            return {"ok": False, "error": "unit_busy", "preflight": pre}
        backup = op_backup("sailingsa-api")
        was_immutable = _is_immutable(API_LIVE)
        incoming = Path("/root/incoming/api.py")
        incoming.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stage, incoming)
        helper = Path("/opt/rea-ops/stage/regatta_host_code.py")
        if helper.is_file():
            shutil.copy2(helper, Path("/root/incoming/regatta_host_code.py"))
        proc = subprocess.run(["/root/deploy_api_verified.sh"], capture_output=True, text=True, timeout=90)
        if was_immutable and API_LIVE.is_file():
            _chattr(API_LIVE, True)
        _restore_owner(API_LIVE, "www-data", "www-data")
        _apply_sailingsa_acl(API_LIVE)
        health = op_health("sailingsa-api")
        payload = {
            "ok": proc.returncode == 0 and health.get("ok") is True,
            "exit": proc.returncode,
            "log": (proc.stdout + proc.stderr)[-4000:],
            "health": health,
            "backup": backup,
            "immutable_restored": was_immutable,
        }
        if not payload["ok"] and backup.get("ok"):
            payload["recovery"] = op_rollback(backup["backup_id"])
            run(["systemctl", "restart", "sailingsa-api"])
            payload["recovery_health"] = op_health("sailingsa-api")
        return payload
    if kind == "static":
        src = Path("/opt/rea-ops/stage/rea-ops-probe.html")
        dest = Path("/var/www/sailingsa/rea-ops-probe.html")
        if not src.is_file():
            return {"ok": False, "error": "missing_stage", "path": str(src)}
        shutil.copy2(src, dest)
        _restore_owner(dest, "www-data", "www-data")
        os.chmod(dest, 0o644)
        _apply_sailingsa_acl(dest)
        return {"ok": True, "path": str(dest)}
    if kind == "static-clean":
        dest = Path("/var/www/sailingsa/rea-ops-probe.html")
        if dest.is_file():
            dest.unlink()
        return {"ok": True, "removed": str(dest)}
    if kind == "frontend":
        zpath = Path("/opt/rea-ops/stage/frontend.zip")
        if not zpath.is_file():
            return {"ok": False, "error": "missing_stage", "path": str(zpath)}
        web = Path("/var/www/sailingsa")
        backup = op_backup("sailingsa-frontend-core")
        proc = subprocess.run(
            ["unzip", "-o", str(zpath), "-x", "data/hub_hero.json", "*.bak", "*.md", "-d", str(web)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Match existing deploy-with-key.sh owner, then restore REA ACL.
        run(["chown", "-R", "www-data:www-data", str(web)])
        _apply_sailingsa_acl(web)
        return {"ok": proc.returncode == 0, "backup": backup, "log": (proc.stdout + proc.stderr)[-2000:]}
    if kind == "whatsapp-code":
        staged = list(Path("/opt/rea/ops/stage").glob("*.py")) + list(Path("/opt/rea/ops/stage").glob("*.js"))
        copied = []
        for src in staged:
            dest = Path("/opt/arial-whatsapp-poc") / src.name
            if dest.is_file():
                shutil.copy2(src, dest)
                shutil.chown(dest, user="wapoc", group="wapoc")
                copied.append(src.name)
        return {"ok": True, "copied": copied, "restarted": False}
    if kind == "aerialnet":
        src_root = Path("/opt/rea/ops/stage/aerialnet")
        dest_root = Path("/opt/aerialnet-arial")
        if not src_root.is_dir():
            return {"ok": False, "error": "missing_stage", "path": str(src_root)}
        backup = op_backup("gowifi-aerialnet")
        copied = []
        for src in src_root.rglob("*"):
            if src.is_file() and src.suffix.lower() not in {".env", ".pem", ".key"}:
                rel = src.relative_to(src_root)
                dest = dest_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() or dest.suffix in {".py", ".js", ".json", ".html", ".css"}:
                    shutil.copy2(src, dest)
                    copied.append(str(rel))
        return {"ok": True, "copied": copied[:80], "backup": backup, "restarted": False}
    return {"ok": False, "error": "deploy_denied", "kind": kind}


def op_migrate(schema: str) -> dict[str, Any]:
    if schema != "rea_ops":
        return {"ok": False, "error": "migrate_denied", "note": "Only rea_ops probe migrations are auto-run. Public DDL stays file-staged for review."}
    sql = Path("/opt/rea-ops/stage/migrations/probe.sql")
    if not sql.is_file():
        return {"ok": False, "error": "missing_migration"}
    text = sql.read_text(encoding="utf-8")
    if re.search(r"(?i)\b(drop\s+database|drop\s+schema|grant|revoke|copy\s+program)\b", text):
        return {"ok": False, "error": "sql_denied"}
    proc = subprocess.run(["sudo", "-n", "-u", "postgres", "psql", "-d", "sailors_master", "-v", "ON_ERROR_STOP=1", "-f", str(sql)], capture_output=True, text=True, timeout=30)
    return {"ok": proc.returncode == 0, "log": (proc.stdout + proc.stderr)[-1500:]}


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
    if op == "health" and args:
        return op_health(args[0])
    if op == "preflight" and args:
        return op_preflight(args[0])
    if op == "stage-api":
        return op_stage_live_api()
    if op == "deploy" and args:
        return op_deploy(args[0])
    if op == "migrate" and args:
        return op_migrate(args[0])
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
