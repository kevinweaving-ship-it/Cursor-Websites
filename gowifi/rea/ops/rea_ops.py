#!/usr/bin/env python3
"""Constrained REA operations dispatcher.

Runs as `rea` on GoWifi or `rea-ops` on SailingSA. Privileged actions go
through the existing localhost/root ForceCommand pattern (NoNewPrivileges
on the ChatGPT tunnel cannot sudo).
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SECRET_RE = re.compile(
    r"""(?ix)
    (?:(password|passwd|secret|api[_-]?key|token|authorization|bearer|
        db_url|database_url|wapoc_token|control_plane_api_key)\s*[:=]\s*)([^\s"'\\]+)
    |(\bsk-[A-Za-z0-9_-]{12,})
    |(postgres(?:ql)?://[^\s"'\\]+)
    |(mysql://[^\s"'\\]+)
    """
)
SQL_WRITE_BAD = re.compile(
    r"""(?ix)\b(drop|alter|truncate|grant|revoke|create\s+role|create\s+user|
        security\s+label|lo_import|lo_export|pg_read_file|pg_ls_dir|copy\s+program)\b"""
)
SQL_SELECT_OK = re.compile(r"(?is)^\s*(with|select|explain|show)\b")
UNIT_RE = re.compile(r"^[A-Za-z0-9_.:@\\-]+$")
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:@/=+,-]+$")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def redact(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        if match.group(1):
            return f"{match.group(1)}=<redacted>"
        return "<redacted>"

    return SECRET_RE.sub(repl, text or "")


def load_config(path: str | None = None) -> dict[str, Any]:
    candidates = []
    if path:
        candidates.append(Path(path))
    env = os.environ.get("REA_OPS_CONFIG")
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            Path("/opt/rea/ops/etc/ops.json"),
            Path("/opt/rea-ops/etc/ops.json"),
        ]
    )
    for cand in candidates:
        if cand.is_file():
            data = json.loads(cand.read_text(encoding="utf-8"))
            data["_config_path"] = str(cand)
            return data
    raise SystemExit("ops config not found")


def audit(cfg: dict[str, Any], event: dict[str, Any]) -> None:
    line = json.dumps({"ts": utc_now(), **event}, ensure_ascii=True)
    log = Path(cfg.get("audit_log", "/tmp/rea-ops-audit.jsonl"))
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        sys.stderr.write(line + "\n")


def fail(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": code, "message": message, **extra}


def ok(**extra: Any) -> dict[str, Any]:
    return {"ok": True, **extra}


def real_path(raw: str) -> Path:
    return Path(raw).expanduser().resolve()


def path_denied(cfg: dict[str, Any], path: Path, *, write: bool = False) -> str | None:
    text = str(path)
    for part in cfg.get("deny_path_substrings", []):
        if part in text:
            return "denied_path"
    name_re = cfg.get("deny_name_regex")
    if name_re and re.search(name_re, path.name, re.I):
        return "denied_name"
    if path.name in {"auth", "event-whatsapp"}:
        return "denied_secret_dir"
    roots = cfg.get("allow_write_paths" if write else "allow_read_paths", [])
    if not any(text == p or text.startswith(p.rstrip("/") + "/") for p in roots):
        return "not_allowlisted"
    return None


def run(argv: list[str], timeout: int = 40, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        input=input_text,
        env={**os.environ, "HOME": os.environ.get("HOME", "/opt/rea")},
    )


def helper_call(cfg: dict[str, Any], argv: list[str], timeout: int = 45) -> dict[str, Any]:
    helper = cfg.get("helper") or {}
    kind = helper.get("kind")
    if kind == "local-sudo":
        cmd = ["sudo", "-n", "/usr/local/sbin/rea-ops-helper", *argv]
        proc = run(cmd, timeout=timeout)
        raw = (proc.stdout or "").strip()
        if raw:
            try:
                return json.loads(raw.splitlines()[-1])
            except json.JSONDecodeError:
                return fail("bad_helper_json", redact(raw[-800:]))
        return fail("empty_helper", redact((proc.stderr or "")[-800:] or f"exit {proc.returncode}"))
    if kind == "localhost-root-ssh":
        key = helper["key"]
        cmd = [
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
            "KbdInteractiveAuthentication=no",
            "-o",
            "RequestTTY=no",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "UserKnownHostsFile=/opt/rea/.ssh/known_hosts",
            "-o",
            "AddressFamily=inet",
            f"{helper.get('user', 'root')}@{helper.get('host', '127.0.0.1')}",
            " ".join(shlex.quote(a) for a in argv),
        ]
        proc = run(cmd, timeout=timeout)
        raw = (proc.stdout or "").strip()
        if raw:
            try:
                return json.loads(raw.splitlines()[-1])
            except json.JSONDecodeError:
                return fail("bad_helper_json", redact(raw[-800:]), stderr=redact((proc.stderr or "")[-400:]))
        return fail("empty_helper", redact((proc.stderr or "")[-800:] or f"exit {proc.returncode}"))
    if kind == "remote-user-ssh":
        cmd = [
            "/usr/bin/ssh",
            "-T",
            "-o",
            "BatchMode=yes",
            helper["alias"],
            " ".join(shlex.quote(a) for a in argv),
        ]
        proc = run(cmd, timeout=timeout)
        raw = (proc.stdout or "").strip()
        if raw:
            try:
                return json.loads(raw.splitlines()[-1])
            except json.JSONDecodeError:
                return fail("bad_helper_json", redact(raw[-800:]))
        return fail("empty_helper", redact((proc.stderr or "")[-800:] or f"exit {proc.returncode}"))
    return fail("no_helper", "privileged helper is not configured")


def read_file(cfg: dict[str, Any], raw: str, offset: int = 0, length: int = 120000) -> dict[str, Any]:
    path = real_path(raw)
    reason = path_denied(cfg, path)
    if reason:
        return fail("path_denied", reason, path=str(path))
    if not path.is_file():
        return fail("not_file", str(path))
    data = path.read_bytes()
    chunk = data[offset : offset + min(length, 1500000)]
    text = redact(chunk.decode("utf-8", errors="replace"))
    return ok(path=str(path), offset=offset, length=len(chunk), size=len(data), text=text)


def write_file(cfg: dict[str, Any], raw: str, content: str, mode: str = "replace") -> dict[str, Any]:
    if content.startswith("b64:"):
        import base64

        content = base64.b64decode(content[4:]).decode("utf-8")
    path = real_path(raw)
    reason = path_denied(cfg, path, write=True)
    if reason:
        return fail("path_denied", reason, path=str(path))
    if path.suffix.lower() in {".pem", ".key"} or path.name.endswith(".env"):
        return fail("path_denied", "secret_file")
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    old_stat = path.stat() if existed else None
    if mode == "append" and existed:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(content)
    else:
        path.write_text(content, encoding="utf-8")
    if old_stat is not None:
        os.chmod(path, stat.S_IMODE(old_stat.st_mode))
        try:
            os.chown(path, old_stat.st_uid, old_stat.st_gid)
        except PermissionError:
            pass
    audit(cfg, {"op": "write_file", "path": str(path), "bytes": len(content), "uid": os.geteuid()})
    return ok(path=str(path), bytes=len(content), existed=existed)


def list_dir(cfg: dict[str, Any], raw: str, limit: int = 80) -> dict[str, Any]:
    path = real_path(raw)
    reason = path_denied(cfg, path)
    if reason:
        return fail("path_denied", reason, path=str(path))
    if not path.is_dir():
        return fail("not_dir", str(path))
    rows = []
    for child in sorted(path.iterdir(), key=lambda p: p.name)[:limit]:
        if child.name in {"auth", "event-whatsapp"}:
            rows.append({"name": child.name, "denied": True})
            continue
        st = child.stat()
        rows.append(
            {
                "name": child.name,
                "path": str(child),
                "dir": child.is_dir(),
                "size": st.st_size,
                "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            }
        )
    return ok(path=str(path), entries=rows)


def service_status(cfg: dict[str, Any], unit: str) -> dict[str, Any]:
    if not UNIT_RE.match(unit) or unit not in cfg.get("units_status", []):
        return fail("unit_denied", unit)
    return helper_call(cfg, ["status", unit])


def service_control(cfg: dict[str, Any], action: str, unit: str) -> dict[str, Any]:
    if action not in {"restart", "reload"}:
        return fail("action_denied", action)
    if not UNIT_RE.match(unit) or unit not in cfg.get("units_control", []):
        return fail("unit_denied", unit)
    return helper_call(cfg, [action, unit])


def journal(cfg: dict[str, Any], unit: str, lines: int = 80) -> dict[str, Any]:
    if not UNIT_RE.match(unit) or unit not in cfg.get("units_status", []):
        return fail("unit_denied", unit)
    lines = max(1, min(int(lines), 200))
    return helper_call(cfg, ["journal", unit, str(lines)])


def nginx_op(cfg: dict[str, Any], action: str) -> dict[str, Any]:
    if action not in {"test", "reload"}:
        return fail("action_denied", action)
    return helper_call(cfg, ["nginx", action])


def backup(cfg: dict[str, Any], target: str) -> dict[str, Any]:
    if not SAFE_TOKEN.match(target):
        return fail("target_denied", target)
    return helper_call(cfg, ["backup", target], timeout=90)


def rollback(cfg: dict[str, Any], backup_id: str) -> dict[str, Any]:
    if not SAFE_TOKEN.match(backup_id):
        return fail("target_denied", backup_id)
    return helper_call(cfg, ["rollback", backup_id], timeout=90)


def http_check(cfg: dict[str, Any], url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return fail("url_denied", "scheme")
    if parsed.hostname not in cfg.get("http_allow_hosts", []):
        return fail("url_denied", parsed.hostname or "")
    if parsed.username or parsed.password:
        return fail("url_denied", "userinfo")
    proc = run(["/usr/bin/curl", "-sS", "-o", "/tmp/rea-ops-http.out", "-w", "%{http_code} %{time_total}", "-m", "15", "-X", "GET", url], timeout=20)
    body = Path("/tmp/rea-ops-http.out").read_text(encoding="utf-8", errors="replace")[:2000] if Path("/tmp/rea-ops-http.out").exists() else ""
    return ok(url=url, curl=proc.stdout.strip(), body=redact(body), stderr=redact(proc.stderr[-200:]))


def db_query(cfg: dict[str, Any], query: str, limit: int = 50, write: bool = False) -> dict[str, Any]:
    q = query.strip().rstrip(";")
    if SQL_WRITE_BAD.search(q):
        return fail("sql_denied", "dangerous_keyword")
    db = cfg.get("db") or {}
    limit = max(1, min(int(limit), 200))
    if not write:
        if not SQL_SELECT_OK.search(q):
            return fail("sql_denied", "select_only")
    if db.get("kind") == "postgres":
        argv = ["psql", "-d", db["database"], "-U", db["user"], "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t", "-c", q + f" LIMIT {limit}" if q.lower().startswith("select") and " limit " not in q.lower() else q]
        proc = run(argv, timeout=30)
        if proc.returncode != 0:
            return fail("sql_error", redact(proc.stderr[-600:]))
        return ok(rows=redact(proc.stdout)[:8000])
    if db.get("kind") == "mariadb":
        argv = ["mysql", "--batch", "--raw", "-u", db["user"], db.get("database") or "rea_ops", "-e", q]
        proc = run(argv, timeout=30)
        if proc.returncode != 0:
            return fail("sql_error", redact(proc.stderr[-600:]))
        return ok(rows=redact(proc.stdout)[:8000])
    return fail("db_unavailable", "no application database configured")


def git_op(cfg: dict[str, Any], root: str, action: str, extra: list[str] | None = None) -> dict[str, Any]:
    path = real_path(root)
    reason = path_denied(cfg, path, write=action in {"add", "commit", "branch"})
    if reason:
        return fail("path_denied", reason, path=str(path))
    if not (path / ".git").exists() and path.name != ".git" and not (path.parent / ".git").exists():
        if action != "status":
            return fail("not_git", str(path))
    extra = extra or []
    if action == "status":
        argv = ["git", "-C", str(path), "status", "-sb"]
    elif action == "diff":
        argv = ["git", "-C", str(path), "diff", "--stat"]
    elif action == "log":
        argv = ["git", "-C", str(path), "log", "-5", "--oneline"]
    elif action == "branch":
        name = extra[0] if extra else ""
        if not re.match(r"^cursor/[a-z0-9._-]+$", name):
            return fail("branch_denied", name)
        argv = ["git", "-C", str(path), "checkout", "-B", name]
    elif action == "add":
        rel = extra[0] if extra else ""
        add_path = (path / rel).resolve()
        if path_denied(cfg, add_path, write=True):
            return fail("path_denied", "add_target")
        argv = ["git", "-C", str(path), "add", "--", rel]
    elif action == "commit":
        msg = extra[0] if extra else "REA ops commit"
        argv = ["git", "-C", str(path), "-c", "user.email=rea-ops@localhost", "-c", "user.name=REA ops", "commit", "-m", msg]
    elif action == "push":
        argv = ["git", "-C", str(path), "push", "-u", "origin", "HEAD"]
    else:
        return fail("git_denied", action)
    proc = run(argv, timeout=40)
    out = redact((proc.stdout or "") + "\n" + (proc.stderr or ""))
    if action == "push" and proc.returncode != 0:
        return fail("git_push_unavailable", out[-800:], note="No GitHub credentials or remotes on this box")
    return ok(action=action, exit=proc.returncode, output=out[-4000:])


def run_check(cfg: dict[str, Any], argv: list[str]) -> dict[str, Any]:
    if not argv:
        return fail("empty_command", "")
    allowed = False
    for prefix in cfg.get("run_allowlist", []):
        if argv[: len(prefix)] == prefix:
            allowed = True
            break
    if not allowed:
        return fail("command_denied", " ".join(argv[:6]))
    for item in argv:
        if item.startswith("-") or item in {"python3", "node", "nginx", "git"}:
            continue
        if item.startswith("/"):
            reason = path_denied(cfg, real_path(item))
            if reason:
                return fail("path_denied", reason, path=item)
    proc = run(argv, timeout=60)
    return ok(exit=proc.returncode, stdout=redact(proc.stdout)[-4000:], stderr=redact(proc.stderr)[-2000:])


def inventory(cfg: dict[str, Any]) -> dict[str, Any]:
    return helper_call(cfg, ["inventory"])


def whatsapp_status(cfg: dict[str, Any]) -> dict[str, Any]:
    if cfg.get("host_id") != "gowifi":
        return fail("wrong_host", "whatsapp is on the Arial/GoWifi box")
    files = {}
    for raw in [
        "/opt/arial-whatsapp-poc/state/health.json",
        "/opt/arial-whatsapp-poc/state/link_watch.json",
        "/opt/arial-whatsapp-poc/state/alerts_recent.json",
    ]:
        path = Path(raw)
        if path.is_file() and not path_denied(cfg, path):
            try:
                files[path.name] = redact(path.read_text(encoding="utf-8", errors="replace")[:4000])
            except OSError as exc:
                files[path.name] = {"error": str(exc)}
        else:
            files[path.name] = {"error": "unreadable"}
    tails = {}
    for raw, n in [
        ("/opt/arial-whatsapp-poc/state/poc.log", 40),
        ("/var/www/aerialnet/data/whatsapp_log.jsonl", 20),
        ("/opt/arial-whatsapp-poc/state/events.jsonl", 10),
    ]:
        path = Path(raw)
        if path.is_file() and not path_denied(cfg, path):
            proc = run(["/usr/bin/tail", "-n", str(n), str(path)])
            tails[path.name] = redact(proc.stdout[-6000:])
        else:
            tails[path.name] = {"error": "unreadable"}
    return ok(
        units={
            "poc": helper_call(cfg, ["status", "arial-whatsapp-poc"]),
            "watcher": helper_call(cfg, ["status", "arial-whatsapp-watcher"]),
        },
        journal={
            "poc": helper_call(cfg, ["journal", "arial-whatsapp-poc", "40"]),
            "watcher": helper_call(cfg, ["journal", "arial-whatsapp-watcher", "40"]),
        },
        files=files,
        tails=tails,
        note="Diagnosis only. No WhatsApp messages were sent.",
    )


def jobs_start(cfg: dict[str, Any], argv: list[str], timeout: int = 90) -> dict[str, Any]:
    check = run_check(cfg, argv)
    if not check.get("ok") and check.get("error") == "command_denied":
        return check
    jobs = Path(cfg["jobs_dir"])
    jobs.mkdir(parents=True, exist_ok=True)
    job_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    job_dir = jobs / job_id
    job_dir.mkdir()
    (job_dir / "cmd.json").write_text(json.dumps(argv), encoding="utf-8")
    log = job_dir / "log.txt"
    proc = subprocess.Popen(argv, stdout=log.open("w"), stderr=subprocess.STDOUT)
    (job_dir / "pid").write_text(str(proc.pid), encoding="utf-8")
    try:
        proc.wait(timeout=min(int(timeout), 600))
        (job_dir / "status").write_text(str(proc.returncode), encoding="utf-8")
        return ok(job_id=job_id, exit=proc.returncode, log=redact(log.read_text(encoding="utf-8", errors="replace")[-4000:]))
    except subprocess.TimeoutExpired:
        (job_dir / "status").write_text("running", encoding="utf-8")
        return ok(job_id=job_id, running=True, pid=proc.pid, note="poll with jobs-status; tunnel may expire at ~120s")


def jobs_status(cfg: dict[str, Any], job_id: str) -> dict[str, Any]:
    if not SAFE_TOKEN.match(job_id):
        return fail("job_denied", job_id)
    job_dir = Path(cfg["jobs_dir"]) / job_id
    if not job_dir.is_dir():
        return fail("missing_job", job_id)
    pid = (job_dir / "pid").read_text(encoding="utf-8").strip() if (job_dir / "pid").is_file() else ""
    running = False
    if pid.isdigit():
        running = Path(f"/proc/{pid}").exists()
    status = (job_dir / "status").read_text(encoding="utf-8").strip() if (job_dir / "status").is_file() else "unknown"
    log = redact((job_dir / "log.txt").read_text(encoding="utf-8", errors="replace")[-4000:]) if (job_dir / "log.txt").is_file() else ""
    return ok(job_id=job_id, pid=pid, running=running, status=status, log=log)


def jobs_cancel(cfg: dict[str, Any], job_id: str) -> dict[str, Any]:
    if not SAFE_TOKEN.match(job_id):
        return fail("job_denied", job_id)
    job_dir = Path(cfg["jobs_dir"]) / job_id
    pid_path = job_dir / "pid"
    if not pid_path.is_file():
        return fail("missing_job", job_id)
    pid = pid_path.read_text(encoding="utf-8").strip()
    if pid.isdigit() and Path(f"/proc/{pid}").exists():
        os.kill(int(pid), 15)
        time.sleep(0.4)
        if Path(f"/proc/{pid}").exists():
            os.kill(int(pid), 9)
        (job_dir / "status").write_text("cancelled", encoding="utf-8")
        return ok(job_id=job_id, cancelled=True, pid=pid)
    return ok(job_id=job_id, cancelled=False, note="not running")


def dispatch(cfg: dict[str, Any], argv: list[str]) -> dict[str, Any]:
    if not argv:
        return fail("usage", "missing operation")
    op, *args = argv
    if op == "read-file":
        return read_file(cfg, args[0], int(args[1]) if len(args) > 1 else 0, int(args[2]) if len(args) > 2 else 120000)
    if op == "write-file":
        return write_file(cfg, args[0], args[1] if len(args) > 1 else "")
    if op == "list":
        return list_dir(cfg, args[0] if args else cfg["allow_read_paths"][0])
    if op == "status":
        return service_status(cfg, args[0])
    if op in {"restart", "reload"}:
        return service_control(cfg, op, args[0])
    if op == "journal":
        return journal(cfg, args[0], int(args[1]) if len(args) > 1 else 80)
    if op == "nginx":
        return nginx_op(cfg, args[0])
    if op == "backup":
        return backup(cfg, args[0])
    if op == "rollback":
        return rollback(cfg, args[0])
    if op == "http":
        return http_check(cfg, args[0])
    if op == "db-query":
        return db_query(cfg, args[0], int(args[1]) if len(args) > 1 else 50, write=False)
    if op == "db-exec":
        return db_query(cfg, args[0], write=True)
    if op == "git":
        return git_op(cfg, args[0], args[1], args[2:])
    if op == "run":
        return run_check(cfg, args)
    if op == "inventory":
        return inventory(cfg)
    if op == "whatsapp-status":
        return whatsapp_status(cfg)
    if op == "jobs-start":
        return jobs_start(cfg, args)
    if op == "jobs-status":
        return jobs_status(cfg, args[0])
    if op == "jobs-cancel":
        return jobs_cancel(cfg, args[0])
    return fail("unknown_op", op)


def main() -> int:
    cfg = load_config()
    if os.environ.get("SSH_ORIGINAL_COMMAND"):
        argv = shlex.split(os.environ["SSH_ORIGINAL_COMMAND"])
    else:
        argv = sys.argv[1:]
    result = dispatch(cfg, argv)
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
