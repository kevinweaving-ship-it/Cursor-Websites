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
SA_STATUS = {
    "sailingsa-api",
    "nginx",
    "postgresql",
    "certbot.timer",
    "arial-whatsapp-poc",
    "arial-whatsapp-watcher",
    "arial-api",
    "arial-bing",
    "arial-stanford",
    "arial-voelklip",
    "arial-site-watch",
    "event-whatsapp-ingest",
    "sailingsa-whatsapp-poc",
}
SA_CONTROL = {"sailingsa-api", "nginx"}
# Leftover Arial stack on SailingSA. Bing/Stanford stay up until migrated.
SA_STOP = {
    "arial-whatsapp-poc",
    "arial-whatsapp-watcher",
    "arial-api",
    "arial-voelklip",
    "arial-site-watch",
}
PROTECTED_UNITS = {
    "sailingsa-whatsapp-poc",
    "event-whatsapp-ingest",
    "sailingsa-api",
    "postgresql",
    "openai-rea-tunnel",
}
API_LIVE = Path("/var/www/sailingsa/api/api.py")
API_HELPER = Path("/var/www/sailingsa/api/regatta_host_code.py")
# Live /root/backups/API_MASTER_GOLD/refuse_stale_incoming_api.sh
# Purpose: block the old ~1.4MB GitHub/repo EVENTS/SAILORS api.py.
GOLD_HASH = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"
GOLD_MIN_BYTES = 3900000
STALE_HASHES = {
    "3c7d67404338f7bedbde33f865616c8e509af13aa184a8f193db8d8da3b6b584",
    "8788a6cd32407dc1bd4faab4a108140451d48e0ccd6ffe63ceb4d098946331ca",
    "cf6356c72d6b8a66d1ec200b4e8d3aabe998f837adbfa594fb57f0c334b8ad75",
}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
FRONTEND_EXCLUDES = {"data/hub_hero.json"}
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
    "sailingsa-frontend-sandbox": ["/opt/rea-ops/stage/frontend-sandbox/www"],
    "sailingsa-api-sandbox": ["/opt/rea-ops/stage/api-sandbox/api.py"],
    "sailingsa-arial-leftover": ["/opt/arial-whatsapp-poc"],
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


def stop_units() -> set[str]:
    if host_id() == "sailingsa":
        return SA_STOP
    return set()


def op_control(action: str, unit: str) -> dict[str, Any]:
    if action not in {"restart", "reload", "stop", "disable", "enable"}:
        return {"ok": False, "error": "action_denied"}
    if not UNIT_RE.match(unit):
        return {"ok": False, "error": "unit_denied", "unit": unit}
    if unit in PROTECTED_UNITS and action in {"restart", "stop", "disable"}:
        return {"ok": False, "error": "protected_unit", "unit": unit, "note": "sailingsa-whatsapp-poc, event ingest, and API/DB are protected."}
    if action in {"stop", "disable"}:
        if unit not in stop_units():
            return {"ok": False, "error": "unit_denied", "unit": unit, "note": "stop/disable only for confirmed leftover Arial units on SailingSA."}
        if host_id() == "gowifi" and unit == "arial-whatsapp-poc":
            return {"ok": False, "error": "whatsapp_poc_guard", "note": "GoWifi Arial gateway is the live unique-number session. Do not stop it."}
    elif action in {"restart", "reload"}:
        if unit not in allowed_units(True):
            return {"ok": False, "error": "unit_denied", "unit": unit}
        if unit == "arial-whatsapp-poc":
            return {"ok": False, "error": "whatsapp_poc_guard", "note": "poc restart is denied while the live session is UP. Use status/health only."}
    if action == "enable" and unit not in stop_units() | allowed_units(True):
        return {"ok": False, "error": "unit_denied", "unit": unit}
    pre = op_preflight(unit) if unit in allowed_units(False) else {"busy": False}
    if pre.get("busy") and action in {"restart", "reload", "stop"}:
        return {"ok": False, "error": "unit_busy", "preflight": pre}
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
    if unit == "arial-whatsapp-watcher" and host_id() == "gowifi":
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
    if not path.exists():
        return
    try:
        shutil.chown(path, user=user, group=group)
    except PermissionError:
        pass


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
        # /admin/api/version is the existing deploy check. It may return 200
        # or 401/403 JSON. Also confirm the public blank hub is served.
        pub = subprocess.run(
            ["curl", "-sS", "-m", "12", "-o", "/dev/null", "-w", "%{http_code}", "https://sailingsa.co.za/blank.html"],
            capture_output=True,
            text=True,
        )
        http = curl.stdout.strip()
        pub_http = pub.stdout.strip()
        healthy = active == "active" and http in {"200", "301", "302", "401", "403"} and pub_http in {"200", "301", "302"}
        return {"ok": healthy, "active": active, "http": http, "public": pub_http, "body": body}
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


def _sha256(path: Path) -> str:
    return subprocess.check_output(["sha256sum", str(path)], text=True).split()[0]


def _snapshot_live_api() -> dict[str, Any]:
    incoming = Path("/root/incoming/api.py")
    return {
        "live_hash": _sha256(API_LIVE) if API_LIVE.is_file() else "",
        "live_mtime": API_LIVE.stat().st_mtime if API_LIVE.is_file() else 0,
        "live_immutable": _is_immutable(API_LIVE),
        "incoming_hash": _sha256(incoming) if incoming.is_file() else "",
        "incoming_mtime": incoming.stat().st_mtime if incoming.is_file() else 0,
        "pid": run(["systemctl", "show", "-p", "MainPID", "--value", "sailingsa-api"]).stdout.strip(),
    }


def _api_gate(stage: Path, approved: str) -> dict[str, Any]:
    if not stage.is_file():
        return {"ok": False, "error": "missing_stage", "mutated": False, "restarted": False}
    digest = _sha256(stage)
    size = stage.stat().st_size
    base = {"sha256": digest, "bytes": size, "mutated": False, "restarted": False}
    if size < GOLD_MIN_BYTES:
        return {**base, "ok": False, "error": "stale_size", "note": "Gold lock: repo/stale api.py is under 3.9MB."}
    if digest in STALE_HASHES:
        return {**base, "ok": False, "error": "stale_hash", "note": "Gold lock: known stale GitHub/repo api.py."}
    if not approved:
        return {**base, "ok": False, "error": "approval_required", "note": "Pass approved_sha256 equal to the staged file hash."}
    if not SHA256_RE.match(approved) or approved != digest:
        return {**base, "ok": False, "error": "approval_mismatch", "note": "approved_sha256 must match the staged file."}
    compile_proc = subprocess.run(["python3", "-m", "py_compile", str(stage)], capture_output=True, text=True)
    if compile_proc.returncode != 0:
        return {**base, "ok": False, "error": "compile_failed", "log": (compile_proc.stderr or "")[-800:]}
    extra = Path("/root/backups/API_MASTER_GOLD/approved_revisions")
    if extra.is_file():
        listed = {ln.strip() for ln in extra.read_text(encoding="utf-8").splitlines() if SHA256_RE.match(ln.strip())}
        if digest != GOLD_HASH and digest not in listed:
            return {**base, "ok": False, "error": "not_in_approved_revisions"}
    return {**base, "ok": True, "gold": digest == GOLD_HASH, "allow_replace": digest != GOLD_HASH}


def _safe_unzip(zpath: Path, dest: Path) -> dict[str, Any]:
    import zipfile

    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    skipped: list[str] = []
    rejected: list[str] = []
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.endswith("/"):
                continue
            if name in FRONTEND_EXCLUDES or name.endswith(".bak") or name.endswith(".md"):
                skipped.append(name)
                continue
            if name.startswith("/") or ".." in Path(name).parts:
                rejected.append(name)
                continue
            target = (dest / name).resolve()
            if dest not in target.parents and target != dest:
                rejected.append(name)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)
            extracted.append(name)
    return {"extracted": extracted, "skipped": skipped, "rejected": rejected}


def _own_tree(path: Path, user: str, group: str) -> None:
    if not path.exists():
        return
    run(["chown", "-R", f"{user}:{group}", str(path)])


def op_can_control(unit: str) -> dict[str, Any]:
    if not UNIT_RE.match(unit):
        return {"ok": False, "error": "unit_denied", "unit": unit, "tested": "permission_only"}
    status_ok = unit in allowed_units(False)
    control_ok = unit in allowed_units(True)
    can_stop = unit in stop_units() and unit not in PROTECTED_UNITS
    poc_guard = unit == "arial-whatsapp-poc" and host_id() == "gowifi"
    return {
        "ok": status_ok,
        "unit": unit,
        "can_status": status_ok,
        "can_control": control_ok and not poc_guard,
        "can_stop": can_stop and not poc_guard,
        "protected": unit in PROTECTED_UNITS,
        "poc_guard": poc_guard,
        "tested": "permission_only",
        "note": "No restart was executed.",
    }


def _write_frontend_fixture(zpath: Path) -> None:
    import zipfile

    zpath.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("index.html", "<!doctype html><title>sandbox</title><p>ok</p>\n")
        zf.writestr("data/hub_hero.json", '{"do_not_overwrite":true}\n')
        zf.writestr("data/ok.json", '{"keep":true}\n')
        zf.writestr("../evil.txt", "traversal\n")
        zf.writestr("notes.md", "skip me\n")
        zf.writestr("backup.bak", "skip me\n")


def op_deploy(kind: str, approved: str = "") -> dict[str, Any]:
    if kind == "plan-api":
        incoming = Path("/opt/rea-ops/stage/api.py")
        live = API_LIVE
        staged = Path("/opt/rea-ops/stage/api.py")
        live_hash = _sha256(live) if live.is_file() else ""
        staged_hash = _sha256(staged) if staged.is_file() else ""
        return {
            "ok": True,
            "kind": "api",
            "stage_exists": staged.is_file(),
            "live_exists": live.is_file(),
            "immutable": _is_immutable(live),
            "live_sha256": live_hash,
            "staged_sha256": staged_hash,
            "gold_sha256": GOLD_HASH,
            "gold_min_bytes": GOLD_MIN_BYTES,
            "script": "/root/deploy_api_verified.sh",
            "note": "Gold lock blocks stale/repo api.py. A named approved_sha256 is required to install a new revision. ALLOW_API_REPLACE is set only after that gate.",
        }
    if kind == "api":
        if host_id() != "sailingsa":
            return {"ok": False, "error": "wrong_host", "mutated": False, "restarted": False}
        stage = Path("/opt/rea-ops/stage/api.py")
        before = _snapshot_live_api()
        gate = _api_gate(stage, approved)
        if not gate.get("ok"):
            after = _snapshot_live_api()
            gate["unchanged"] = after == before
            return gate
        if gate["sha256"] == before["live_hash"]:
            return {
                "ok": True,
                "error": "same_revision",
                "note": "Staged file matches live api.py. Refusing a no-op replace so production is not restarted for testing.",
                "sha256": gate["sha256"],
                "mutated": False,
                "restarted": False,
                "unchanged": True,
            }
        pre = op_preflight("sailingsa-api")
        if pre.get("busy"):
            return {"ok": False, "error": "unit_busy", "preflight": pre, "mutated": False, "restarted": False}
        backup = op_backup("sailingsa-api")
        was_immutable = _is_immutable(API_LIVE)
        incoming = Path("/root/incoming/api.py")
        incoming.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stage, incoming)
        helper = Path("/opt/rea-ops/stage/regatta_host_code.py")
        if helper.is_file():
            shutil.copy2(helper, Path("/root/incoming/regatta_host_code.py"))
        env = os.environ.copy()
        if gate.get("allow_replace"):
            env["ALLOW_API_REPLACE"] = "1"
        proc = subprocess.run(["/root/deploy_api_verified.sh"], capture_output=True, text=True, timeout=90, env=env)
        after = _snapshot_live_api()
        mutated = after["live_hash"] != before["live_hash"]
        restarted = after["pid"] != before["pid"]
        if API_LIVE.is_file() and _is_immutable(API_LIVE):
            _chattr(API_LIVE, False)
        _restore_owner(API_LIVE, "www-data", "www-data")
        _apply_sailingsa_acl(API_LIVE)
        if was_immutable and API_LIVE.is_file():
            _chattr(API_LIVE, True)
        health = op_health("sailingsa-api")
        payload = {
            "ok": proc.returncode == 0 and health.get("ok") is True and mutated,
            "exit": proc.returncode,
            "log": (proc.stdout + proc.stderr)[-4000:],
            "health": health,
            "backup": backup,
            "immutable_restored": was_immutable,
            "mutated": mutated,
            "restarted": restarted,
            "sha256": gate["sha256"],
        }
        refused = "REFUSED" in payload["log"] or "Only Master/Gold" in payload["log"]
        if refused or not mutated:
            payload["ok"] = not mutated
            payload["note"] = "Deploy refused or live file unchanged. No recovery restart."
            payload["restarted"] = restarted
            return payload
        if not payload["ok"] and backup.get("ok"):
            payload["recovery"] = op_rollback(backup["backup_id"])
            run(["systemctl", "restart", "sailingsa-api"])
            payload["recovery_health"] = op_health("sailingsa-api")
            payload["recovered"] = True
        return payload
    if kind == "api-dry":
        if host_id() != "sailingsa":
            return {"ok": False, "error": "wrong_host"}
        stage = Path("/opt/rea-ops/stage/api.py")
        gate = _api_gate(stage, approved)
        if not gate.get("ok"):
            return gate
        before = _snapshot_live_api()
        sandbox = Path("/opt/rea-ops/stage/api-sandbox")
        sandbox.mkdir(parents=True, exist_ok=True)
        dest = sandbox / "api.py"
        if dest.exists():
            dest.unlink()
        shutil.copy2(stage, dest)
        backup = op_backup("sailingsa-api-sandbox")
        dest.write_text(dest.read_text(encoding="utf-8", errors="replace") + "\n# rea-dry\n", encoding="utf-8")
        restored = op_rollback(backup["backup_id"]) if backup.get("ok") else {"ok": False}
        after = _snapshot_live_api()
        compile_proc = subprocess.run(["python3", "-m", "py_compile", str(dest)], capture_output=True, text=True)
        return {
            "ok": after == before and restored.get("ok") is True and compile_proc.returncode == 0,
            "kind": "api-dry",
            "gate": {k: gate.get(k) for k in ("sha256", "bytes", "gold", "allow_replace")},
            "live_unchanged": after == before,
            "sandbox": str(dest),
            "backup": backup,
            "rollback": restored,
            "mutated": False,
            "restarted": False,
            "note": "Validated against /opt/rea-ops/stage/api-sandbox only. Production api.py was not replaced.",
        }
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
        unzipped = _safe_unzip(zpath, web)
        _own_tree(web, "www-data", "www-data")
        _apply_sailingsa_acl(web)
        return {"ok": True, "backup": backup, "unzip": unzipped, "note": "Production frontend deploy. Prefer frontend-sandbox for tests."}
    if kind == "frontend-sandbox":
        if host_id() != "sailingsa":
            return {"ok": False, "error": "wrong_host"}
        root = Path("/opt/rea-ops/stage/frontend-sandbox")
        www = root / "www"
        zpath = root / "fixture.zip"
        if www.exists():
            shutil.rmtree(www)
        www.mkdir(parents=True, exist_ok=True)
        (www / "data").mkdir(parents=True, exist_ok=True)
        (www / "data" / "hub_hero.json").write_text('{"live":true}\n', encoding="utf-8")
        (www / "keep.txt").write_text("before\n", encoding="utf-8")
        _write_frontend_fixture(zpath)
        backup = op_backup("sailingsa-frontend-sandbox")
        unzipped = _safe_unzip(zpath, www)
        try:
            _own_tree(www, "www-data", "www-data")
        except Exception:
            pass
        hero = (www / "data" / "hub_hero.json").read_text(encoding="utf-8")
        evil = Path("/opt/rea-ops/stage/evil.txt")
        ok_json = (www / "data" / "ok.json").is_file()
        index = (www / "index.html").is_file()
        notes = (www / "notes.md").exists()
        bak = (www / "backup.bak").exists()
        rollback = op_rollback(backup["backup_id"]) if backup.get("ok") else {"ok": False}
        hero_after = (www / "data" / "hub_hero.json").read_text(encoding="utf-8") if (www / "data" / "hub_hero.json").is_file() else ""
        return {
            "ok": (
                hero.startswith('{"live":true}')
                and not evil.exists()
                and ok_json
                and index
                and not notes
                and not bak
                and "../evil.txt" in unzipped.get("rejected", [])
                and "data/hub_hero.json" in unzipped.get("skipped", [])
                and rollback.get("ok") is True
                and hero_after.startswith('{"live":true}')
            ),
            "unzip": unzipped,
            "backup": backup,
            "rollback": rollback,
            "hero_preserved": hero.startswith('{"live":true}'),
            "traversal_blocked": not evil.exists(),
            "mutated_production": Path("/var/www/sailingsa/rea-ops-probe.html").exists() is False,
            "note": "Isolated under /opt/rea-ops/stage/frontend-sandbox. Production web root was not published to.",
        }
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


def op_decommission(unit: str) -> dict[str, Any]:
    if host_id() != "sailingsa" or unit not in SA_STOP:
        return {"ok": False, "error": "unit_denied", "unit": unit, "note": "Decommission is leftover Arial units on SailingSA only."}
    if unit in PROTECTED_UNITS:
        return {"ok": False, "error": "protected_unit", "unit": unit}
    backup = op_backup("sailingsa-arial-leftover") if unit.startswith("arial-whatsapp") else {"ok": True, "skipped": True}
    stopped = op_control("stop", unit)
    disabled = op_control("disable", unit)
    return {
        "ok": stopped.get("ok") is True and disabled.get("ok") is True,
        "unit": unit,
        "backup": backup,
        "stopped": stopped,
        "disabled": disabled,
        "deleted": False,
        "auth_copied": False,
        "note": "Stopped and disabled. Tree and auth were not deleted or copied.",
    }


def op_inspect_arial() -> dict[str, Any]:
    units = sorted(allowed_units(False) | (SA_STATUS if host_id() == "sailingsa" else GOWIFI_STATUS))
    rows = []
    for unit in units:
        if not any(x in unit for x in ("arial", "whatsapp", "bing", "stanford", "voelklip", "hansekop", "tuya", "ingest")):
            continue
        show = run(["systemctl", "show", unit, "-p", "ActiveState", "-p", "UnitFileState", "-p", "FragmentPath", "-p", "Description", "-p", "After", "-p", "Wants", "-p", "MainPID"])
        rows.append({"unit": unit, "show": show.stdout.strip()[:600], "can_stop": unit in stop_units()})
    nginx_hits = []
    nginx = Path("/etc/nginx/sites-enabled")
    if nginx.is_dir():
        for p in nginx.iterdir():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if any(s in text for s in ("/api/bing/", "/api/stanford/", "/api/arial", "8004", "8005", "8006", "8003")):
                nginx_hits.append(p.name)
    return {
        "ok": True,
        "host": host_id(),
        "units": rows,
        "nginx_sites": nginx_hits,
        "protected": sorted(PROTECTED_UNITS),
        "stop_allow": sorted(stop_units()),
        "note": "Bing/Stanford remain live on SailingSA until a GoWifi install is verified. Do not copy WhatsApp auth.",
    }


def op_retarget_ingest() -> dict[str, Any]:
    if host_id() != "sailingsa":
        return {"ok": False, "error": "wrong_host"}
    unit = Path("/etc/systemd/system/event-whatsapp-ingest.service")
    if not unit.is_file():
        return {"ok": False, "error": "missing_unit"}
    text = unit.read_text(encoding="utf-8")
    backup = Path("/opt/rea-ops/backups") / f"event-whatsapp-ingest.service.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(text, encoding="utf-8")
    new = text.replace("arial-whatsapp-poc.service", "sailingsa-whatsapp-poc.service")
    if "sailingsa-whatsapp-poc.service" not in new:
        return {"ok": False, "error": "retarget_failed"}
    unit.write_text(new, encoding="utf-8")
    run(["systemctl", "daemon-reload"])
    # Do not restart ingest or WhatsApp.
    after = run(["systemctl", "show", "event-whatsapp-ingest", "-p", "After", "-p", "Wants", "-p", "ActiveState"])
    return {
        "ok": "sailingsa-whatsapp-poc.service" in after.stdout and "arial-whatsapp-poc.service" not in after.stdout,
        "backup": str(backup),
        "show": after.stdout.strip(),
        "restarted": False,
        "note": "Caller retargeted to sailingsa-whatsapp-poc. Ingest was not restarted. Leftover inbox files were left in place.",
    }


def op_migrate(schema: str) -> dict[str, Any]:
    if schema != "rea_ops":
        return {"ok": False, "error": "migrate_denied", "note": "Only rea_ops probe migrations are auto-run. Public DDL stays file-staged for review."}
    sql = Path("/opt/rea-ops/stage/migrations/probe.sql")
    if not sql.is_file():
        return {"ok": False, "error": "missing_migration"}
    text = sql.read_text(encoding="utf-8")
    if re.search(r"(?i)\b(drop\s+database|drop\s+schema|grant|revoke|copy\s+program)\b", text):
        return {"ok": False, "error": "sql_denied"}
    staged = Path("/tmp/rea-ops-probe.sql")
    staged.write_text(text, encoding="utf-8")
    os.chmod(staged, 0o644)
    proc = subprocess.run(
        ["sudo", "-n", "-u", "postgres", "psql", "-d", "sailors_master", "-v", "ON_ERROR_STOP=1", "-f", str(staged)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    staged.unlink(missing_ok=True)
    return {"ok": proc.returncode == 0, "log": (proc.stdout + proc.stderr)[-1500:]}


def dispatch(tokens: list[str]) -> dict[str, Any]:
    if not tokens:
        return {"ok": False, "error": "empty"}
    op, *args = tokens
    if op == "status" and args:
        return op_status(args[0])
    if op == "journal" and args:
        return op_journal(args[0], args[1] if len(args) > 1 else "80")
    if op in {"restart", "reload", "stop", "disable", "enable"} and args:
        return op_control(op, args[0])
    if op == "decommission" and args:
        return op_decommission(args[0])
    if op == "inspect-arial":
        return op_inspect_arial()
    if op == "retarget-ingest":
        return op_retarget_ingest()
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
        return op_deploy(args[0], args[1] if len(args) > 1 else "")
    if op == "can-control" and args:
        return op_can_control(args[0])
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
