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
    raw_bytes: bytes | None = None
    if content.startswith("b64:"):
        import base64

        raw_bytes = base64.b64decode(content[4:])
    path = real_path(raw)
    reason = path_denied(cfg, path, write=True)
    if reason:
        return fail("path_denied", reason, path=str(path))
    if path.suffix.lower() in {".pem", ".key"} or path.name.endswith(".env"):
        return fail("path_denied", "secret_file")
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    old_stat = path.stat() if existed else None
    binary_ext = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".bin", ".part"}
    if raw_bytes is not None and (path.suffix.lower() in binary_ext or mode == "binary"):
        if mode == "append" and existed:
            with path.open("ab") as fh:
                fh.write(raw_bytes)
        else:
            path.write_bytes(raw_bytes)
        nbytes = len(raw_bytes)
    else:
        text = raw_bytes.decode("utf-8") if raw_bytes is not None else content
        if mode == "append" and existed:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(text)
        else:
            path.write_text(text, encoding="utf-8")
        nbytes = len(text)
    if old_stat is not None:
        os.chmod(path, stat.S_IMODE(old_stat.st_mode))
        try:
            os.chown(path, old_stat.st_uid, old_stat.st_gid)
        except PermissionError:
            pass
    audit(cfg, {"op": "write_file", "path": str(path), "bytes": nbytes, "uid": os.geteuid()})
    return ok(path=str(path), bytes=nbytes, existed=existed)


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
    extra = [
        ["python3", "-m", "compileall"],
        ["/usr/bin/sleep"],
        ["sha256sum"],
        ["unzip", "-l"],
    ]
    allowed = False
    for prefix in list(cfg.get("run_allowlist", [])) + extra:
        if argv[: len(prefix)] == prefix:
            allowed = True
            break
    if not allowed:
        return fail("command_denied", " ".join(argv[:6]))
    skip_bins = {
        "python3",
        "node",
        "nginx",
        "git",
        "sha256sum",
        "unzip",
        "/usr/bin/sleep",
        "/usr/bin/sha256sum",
        "/usr/bin/unzip",
        "/usr/bin/git",
        "/usr/bin/python3",
        "/opt/arial-whatsapp-poc/node/bin/node",
    }
    for item in argv:
        if item.startswith("-") or item in skip_bins:
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


def _command_allowed(cfg: dict[str, Any], argv: list[str]) -> dict[str, Any]:
    if not argv:
        return fail("empty_command", "")
    extra = [
        ["python3", "-m", "compileall"],
        ["/usr/bin/sleep"],
        ["sha256sum"],
        ["unzip", "-l"],
    ]
    allowed = False
    for prefix in list(cfg.get("run_allowlist", [])) + extra:
        if argv[: len(prefix)] == prefix:
            allowed = True
            break
    if not allowed:
        return fail("command_denied", " ".join(argv[:6]))
    return ok()


def jobs_start(cfg: dict[str, Any], argv: list[str], timeout: int = 90) -> dict[str, Any]:
    check = _command_allowed(cfg, argv)
    if not check.get("ok"):
        return check
    jobs = Path(cfg["jobs_dir"])
    jobs.mkdir(parents=True, exist_ok=True)
    job_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    job_dir = jobs / job_id
    job_dir.mkdir()
    (job_dir / "cmd.json").write_text(json.dumps(argv), encoding="utf-8")
    log = job_dir / "log.txt"
    proc = subprocess.Popen(argv, stdout=log.open("w"), stderr=subprocess.STDOUT, start_new_session=True)
    (job_dir / "pid").write_text(str(proc.pid), encoding="utf-8")
    time.sleep(0.2)
    if proc.poll() is not None:
        (job_dir / "status").write_text(str(proc.returncode), encoding="utf-8")
        return ok(job_id=job_id, exit=proc.returncode, log=redact(log.read_text(encoding="utf-8", errors="replace")[-4000:]))
    (job_dir / "status").write_text("running", encoding="utf-8")
    return ok(job_id=job_id, running=True, pid=proc.pid, note="poll with jobs-status; tunnel may expire at ~120s")


def _pid_running(pid: str) -> bool:
    if not pid.isdigit():
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    stat = Path(f"/proc/{pid}/status")
    if stat.is_file():
        for line in stat.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("State:") and "zombie" in line.lower():
                return False
    return Path(f"/proc/{pid}").exists()


def jobs_status(cfg: dict[str, Any], job_id: str) -> dict[str, Any]:
    if not SAFE_TOKEN.match(job_id):
        return fail("job_denied", job_id)
    job_dir = Path(cfg["jobs_dir"]) / job_id
    if not job_dir.is_dir():
        return fail("missing_job", job_id)
    pid = (job_dir / "pid").read_text(encoding="utf-8").strip() if (job_dir / "pid").is_file() else ""
    running = _pid_running(pid)
    status = (job_dir / "status").read_text(encoding="utf-8").strip() if (job_dir / "status").is_file() else "unknown"
    log = redact((job_dir / "log.txt").read_text(encoding="utf-8", errors="replace")[-4000:]) if (job_dir / "log.txt").is_file() else ""
    return ok(job_id=job_id, pid=pid, running=running, status=status, log=log)


def assemble_file(cfg: dict[str, Any], dest: str, parts: int) -> dict[str, Any]:
    path = real_path(dest)
    reason = path_denied(cfg, path, write=True)
    if reason:
        return fail("path_denied", reason, path=str(path))
    n = max(1, min(int(parts), 80))
    chunks = []
    for i in range(n):
        part = Path(str(path) + f".part{i:03d}")
        if not part.is_file():
            return fail("missing_part", str(part))
        chunks.append(part.read_bytes())
    path.write_bytes(b"".join(chunks))
    for i in range(n):
        Path(str(path) + f".part{i:03d}").unlink(missing_ok=True)
    return ok(path=str(path), bytes=path.stat().st_size, parts=n)


def transfer(cfg: dict[str, Any], action: str, src: str, dest: str) -> dict[str, Any]:
    if action == "copy":
        sp = real_path(src)
        dp = real_path(dest)
        if path_denied(cfg, sp) or path_denied(cfg, dp, write=True):
            return fail("path_denied", "copy")
        if not sp.is_file():
            return fail("not_file", str(sp))
        dp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sp, dp)
        return ok(src=str(sp), dest=str(dp), bytes=dp.stat().st_size)
    if action == "to-sailingsa":
        if cfg.get("host_id") != "gowifi":
            return fail("wrong_host", "push from GoWifi")
        sp = real_path(src)
        if path_denied(cfg, sp):
            return fail("path_denied", src)
        if not sp.is_file():
            return fail("not_file", str(sp))
        dest_path = dest or f"/opt/rea-ops/stage/{sp.name}"
        if not dest_path.startswith("/opt/rea-ops/stage/"):
            return fail("path_denied", dest_path)
        import base64

        data = sp.read_bytes()
        if len(data) > 6_000_000:
            return fail("too_large", "max 6MB via ops_transfer")
        chunk = 45_000
        sa = load_config("/opt/rea/ops/etc/ops.sailingsa.client.json")
        if len(data) <= chunk:
            payload = "b64:" + base64.b64encode(data).decode("ascii")
            return helper_call(sa, ["write-file", dest_path, payload], timeout=60)
        parts = 0
        for i in range(0, len(data), chunk):
            payload = "b64:" + base64.b64encode(data[i : i + chunk]).decode("ascii")
            part = f"{dest_path}.part{parts:03d}"
            result = helper_call(sa, ["write-file", part, payload], timeout=60)
            if not result.get("ok"):
                return result
            parts += 1
        return helper_call(sa, ["assemble", dest_path, str(parts)], timeout=60)
    return fail("transfer_denied", action)


def deploy(cfg: dict[str, Any], kind: str, approved: str = "") -> dict[str, Any]:
    allowed = {
        "plan-api",
        "api",
        "api-dry",
        "static",
        "static-clean",
        "frontend",
        "frontend-sandbox",
        "whatsapp-code",
        "aerialnet",
        "stage-api",
    }
    if kind not in allowed:
        return fail("deploy_denied", kind)
    if kind == "stage-api":
        return helper_call(cfg, ["stage-api"], timeout=60)
    argv = ["deploy", kind]
    if approved:
        argv.append(approved)
    return helper_call(cfg, argv, timeout=150)


def health(cfg: dict[str, Any], name: str) -> dict[str, Any]:
    if name not in {"sailingsa-api", "whatsapp", "nginx"}:
        return fail("health_denied", name)
    if name == "nginx":
        return helper_call(cfg, ["nginx", "test"])
    return helper_call(cfg, ["health", name])


def migrate(cfg: dict[str, Any], schema: str) -> dict[str, Any]:
    if schema != "rea_ops":
        return fail(
            "migrate_denied",
            schema,
            note="Only rea_ops probe migrations auto-run. Stage public SQL under /opt/rea-ops/stage/migrations/ for review.",
        )
    return helper_call(cfg, ["migrate", "rea_ops"], timeout=40)


def deps(cfg: dict[str, Any], kind: str, root: str) -> dict[str, Any]:
    path = real_path(root)
    if path_denied(cfg, path):
        return fail("path_denied", str(path))
    if kind == "py-compile":
        return run_check(cfg, ["python3", "-m", "compileall", "-q", str(path)])
    if kind == "py-file":
        return run_check(cfg, ["python3", "-m", "py_compile", str(path)])
    if kind == "node-check":
        node = "/opt/arial-whatsapp-poc/node/bin/node" if Path("/opt/arial-whatsapp-poc/node/bin/node").is_file() else "node"
        return run_check(cfg, [node, "--check", str(path)])
    if kind == "pip-stage":
        req = path / "requirements.txt" if path.is_dir() else path
        if path_denied(cfg, req):
            return fail("path_denied", str(req))
        venv = Path(cfg.get("stage_dir", "/tmp")) / "venv"
        if not venv.is_dir():
            proc = run(["python3", "-m", "venv", str(venv)], timeout=60)
            if proc.returncode != 0:
                return fail("venv_failed", redact(proc.stderr[-600:]))
        pip = str(venv / "bin" / "pip")
        proc = run([pip, "install", "-q", "-r", str(req)], timeout=120)
        return ok(exit=proc.returncode, stdout=redact(proc.stdout)[-2000:], stderr=redact(proc.stderr)[-2000:], venv=str(venv))
    return fail("deps_denied", kind)


def github_key_path(cfg: dict[str, Any]) -> Path:
    if cfg.get("host_id") == "sailingsa":
        return Path("/opt/rea-ops/.ssh/id_rea_github")
    return Path("/opt/rea/.ssh/id_rea_github")


def gh_op(cfg: dict[str, Any], action: str, extra: list[str] | None = None) -> dict[str, Any]:
    extra = extra or []
    key = github_key_path(cfg)
    pub = Path(str(key) + ".pub")
    repo = extra[0] if extra else "https://github.com/kevinweaving-ship-it/Cursor-Websites.git"
    if action == "status":
        fingerprint = ""
        pubkey = ""
        if pub.is_file():
            pubkey = pub.read_text(encoding="utf-8").strip()
            proc = run(["ssh-keygen", "-lf", str(pub)])
            fingerprint = proc.stdout.strip()
        gh_bin = shutil.which("gh")
        return ok(
            key_exists=key.is_file(),
            pub_exists=pub.is_file(),
            fingerprint=fingerprint,
            public_key=pubkey,
            gh_cli=gh_bin or "",
            note="ChatGPT GitHub connector is UNVERIFIED from this box. Add this public key as a write deploy key, or use ChatGPT's GitHub connector after refresh.",
        )
    if action == "keygen":
        key.parent.mkdir(parents=True, exist_ok=True)
        if not key.is_file():
            proc = run(["ssh-keygen", "-t", "ed25519", "-f", str(key), "-N", "", "-C", "rea-ops-github"], timeout=20)
            if proc.returncode != 0:
                return fail("keygen_failed", redact(proc.stderr[-400:]))
            os.chmod(key, 0o600)
        return gh_op(cfg, "status")
    if action == "clone":
        dest = Path(cfg.get("stage_dir", "/tmp")) / "github" / "Cursor-Websites"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not (dest / ".git").exists():
            shutil.rmtree(dest, ignore_errors=True)
        if (dest / ".git").exists():
            proc = run(["git", "-C", str(dest), "remote", "-v"], timeout=20)
            ls = run(["git", "-C", str(dest), "rev-parse", "--abbrev-ref", "HEAD"], timeout=20)
            return ok(path=str(dest), action="existing", exit=0, output=redact((proc.stdout + ls.stdout + proc.stderr)[-1500:]))
        proc = run(["git", "clone", "--depth", "1", repo, str(dest)], timeout=90)
        return {
            "ok": proc.returncode == 0,
            "path": str(dest),
            "action": "clone",
            "exit": proc.returncode,
            "output": redact((proc.stdout or "") + "\n" + (proc.stderr or ""))[-1500:],
        }
    if action == "probe-push":
        dest = Path(cfg.get("stage_dir", "/tmp")) / "github" / "Cursor-Websites"
        if not (dest / ".git").exists():
            return fail("not_cloned", str(dest))
        branch = extra[0] if extra and extra[0].startswith("cursor/") else "cursor/rea-ops-probe-c1ba"
        run(["git", "-C", str(dest), "checkout", "-B", branch], timeout=20)
        marker = dest / "gowifi/rea/ops/.rea-github-probe"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("probe\n", encoding="utf-8")
        run(["git", "-C", str(dest), "add", "--", "gowifi/rea/ops/.rea-github-probe"], timeout=20)
        run(
            [
                "git",
                "-C",
                str(dest),
                "-c",
                "user.email=rea-ops@localhost",
                "-c",
                "user.name=REA ops",
                "commit",
                "-m",
                "REA github probe (do not merge)",
            ],
            timeout=20,
        )
        env_ssh = f"ssh -i {key} -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
        # Prefer SSH remote for the deploy-key path; HTTPS clone has no write creds.
        run(["git", "-C", str(dest), "remote", "remove", "rea-ssh"], timeout=10)
        run(
            [
                "git",
                "-C",
                str(dest),
                "remote",
                "add",
                "rea-ssh",
                "git@github.com:kevinweaving-ship-it/Cursor-Websites.git",
            ],
            timeout=10,
        )
        proc = subprocess.run(
            ["git", "-C", str(dest), "push", "-u", "rea-ssh", branch],
            capture_output=True,
            text=True,
            timeout=40,
            env={**os.environ, "GIT_SSH_COMMAND": env_ssh, "HOME": os.environ.get("HOME", "/opt/rea")},
        )
        out = redact((proc.stdout or "") + "\n" + (proc.stderr or ""))
        # Clean local probe file regardless of push result.
        if marker.exists():
            marker.unlink()
        run(["git", "-C", str(dest), "checkout", "--", "gowifi/rea/ops/.rea-github-probe"], timeout=10)
        if proc.returncode != 0:
            return fail(
                "git_push_unavailable",
                out[-800:],
                branch=branch,
                note="Expected until a write deploy key is added for this REA public key. ChatGPT GitHub connector remains UNVERIFIED.",
            )
        return ok(action="probe-push", branch=branch, output=out[-800:], note="Push succeeded. Delete the throwaway branch after review.")
    if action == "whoami":
        proc = run(["git", "ls-remote", "https://github.com/kevinweaving-ship-it/Cursor-Websites.git", "HEAD"], timeout=30)
        return ok(exit=proc.returncode, output=redact((proc.stdout + proc.stderr)[-800:]), note="HTTPS clone/ls-remote only. Write needs deploy key or ChatGPT GitHub connector.")
    return fail("gh_denied", action)


def jobs_cancel(cfg: dict[str, Any], job_id: str) -> dict[str, Any]:
    if not SAFE_TOKEN.match(job_id):
        return fail("job_denied", job_id)
    job_dir = Path(cfg["jobs_dir"]) / job_id
    pid_path = job_dir / "pid"
    if not pid_path.is_file():
        return fail("missing_job", job_id)
    pid = pid_path.read_text(encoding="utf-8").strip()
    if _pid_running(pid):
        try:
            os.killpg(int(pid), 15)
        except ProcessLookupError:
            os.kill(int(pid), 15)
        time.sleep(0.4)
        if _pid_running(pid):
            try:
                os.killpg(int(pid), 9)
            except ProcessLookupError:
                os.kill(int(pid), 9)
        (job_dir / "status").write_text("cancelled", encoding="utf-8")
        return ok(job_id=job_id, cancelled=True, pid=pid, running=_pid_running(pid))
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
    if op in {"stop", "disable", "enable", "decommission"}:
        return helper_call(cfg, [op, args[0] if args else ""])
    if op == "can-control":
        return helper_call(cfg, ["can-control", args[0] if args else ""])
    if op == "inspect-arial":
        return helper_call(cfg, ["inspect-arial"])
    if op == "retarget-ingest":
        return helper_call(cfg, ["retarget-ingest"], timeout=40)
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
    if op == "deploy":
        return deploy(cfg, args[0] if args else "", args[1] if len(args) > 1 else "")
    if op == "stage-api":
        return deploy(cfg, "stage-api")
    if op == "health":
        return health(cfg, args[0] if args else "")
    if op == "preflight":
        return helper_call(cfg, ["preflight", args[0]])
    if op == "migrate":
        return migrate(cfg, args[0] if args else "")
    if op == "deps":
        return deps(cfg, args[0] if args else "", args[1] if len(args) > 1 else cfg.get("stage_dir", "/tmp"))
    if op == "transfer":
        return transfer(cfg, args[0] if args else "", args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else "")
    if op == "assemble":
        return assemble_file(cfg, args[0], int(args[1]) if len(args) > 1 else 0)
    if op == "gh":
        return gh_op(cfg, args[0] if args else "status", args[1:])
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
