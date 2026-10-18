#!/usr/bin/env python3
"""Read-only inspect agent for REA (GoWifi local + SailingSA ForceCommand).

No writes to production trees. SQL is SELECT/WITH/EXPLAIN only.
Secrets in file text are redacted before return. Every call is audit-logged.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CODE_SUFFIXES = {
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".json",
    ".md",
    ".sql",
    ".conf",
    ".cfg",
    ".ini",
    ".toml",
    ".yml",
    ".yaml",
    ".j2",
    ".jinja",
    ".jinja2",
    ".vue",
    ".svg",
    ".sh",
    ".service",
    ".timer",
    ".txt",
}
SKIP_DIR_NAMES = {
    "backups",
    "_archive",
    "node_modules",
    "__pycache__",
    ".cache",
    "BACKUP_HTML_20260216_144435",
    "api_restore_8001",
}
SKIP_NAME_RE = re.compile(
    r"""(?ix)
    (\.bak($|\.) | \.bak- | ^api\.bak- | ^blank\.html\. | \.zip$ |
     ^id_ | authorized_keys | \.pem$ | \.key$ | runtime\.key |
     \.env$ | \.env\. | password | secret | credential)
    """
)
DENY_PATH_RE = re.compile(
    r"""(?ix)
    (/root(/|$)|/opt/openai-tunnel/runtime\.key|/opt/rea/\.ssh|
     /etc/ssl/private|/home/user-data/ssl|/var/lib/postgresql|
     /etc/systemd/system/sailingsa-api\.service)
    """
)
SQL_OK_RE = re.compile(r"(?is)^\s*(with|select|explain|show|information_schema)\b")
SQL_BAD_RE = re.compile(
    r"""(?ix)\b(
        insert|update|delete|drop|alter|create|grant|revoke|truncate|
        copy|call|execute|refresh|vacuum|notify|listen|
        security\s+label|lo_import|lo_export|pg_read_file|pg_ls_dir
    )\b|into\s+(temp|temporary|table)|;"""
)
SECRET_RE = re.compile(
    r"""(?ix)
    (?:(password|passwd|secret|api[_-]?key|token|authorization|bearer|
        db_url|database_url|control_plane_api_key)\s*[:=]\s*)([^\s"'\\]+)
    |(\bsk-[A-Za-z0-9_-]{12,})
    |(postgres(?:ql)?://[^\s"'\\]+)
    |(mysql://[^\s"'\\]+)
    """
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config() -> dict[str, Any]:
    default = os.environ.get("REA_INSPECT_CONFIG", "/opt/rea/inspect/etc/inspect.json")
    path = Path(default)
    if not path.is_file():
        alt = Path("/opt/rea-ro/etc/inspect.json")
        path = alt if alt.is_file() else path
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_config_path"] = str(path)
    return data


def audit(cfg: dict[str, Any], event: dict[str, Any]) -> None:
    line = json.dumps({"ts": utc_now(), **event}, ensure_ascii=True)
    log = Path(cfg.get("audit_log", "/tmp/rea-inspect-audit.jsonl"))
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        sys.stderr.write(line + "\n")


def redact(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        if match.group(1):
            return f"{match.group(1)}=<redacted>"
        return "<redacted>"

    return SECRET_RE.sub(repl, text)


def fail(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": code, "message": message, **extra}


def real_path(raw: str) -> Path:
    return Path(raw).expanduser().resolve()


def allowed_file(cfg: dict[str, Any], path: Path, *, for_log: bool = False) -> tuple[bool, str]:
    text = str(path)
    if DENY_PATH_RE.search(text):
        return False, "denied_path"
    prefixes = list(cfg.get("allow_paths", []))
    if for_log:
        prefixes.extend(cfg.get("allow_logs", []))
    if not any(text == p or text.startswith(p.rstrip("/") + "/") for p in prefixes):
        return False, "not_allowlisted"
    if SKIP_NAME_RE.search(path.name):
        return False, "denied_name"
    return True, "ok"


def skip_walk(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES or bool(SKIP_NAME_RE.search(path.name))


def list_path(cfg: dict[str, Any], raw: str, limit: int) -> dict[str, Any]:
    path = real_path(raw)
    ok, reason = allowed_file(cfg, path)
    if not ok:
        return fail("path_denied", reason, path=str(path))
    if not path.exists():
        return fail("not_found", "path does not exist", path=str(path))
    items: list[dict[str, Any]] = []
    if path.is_file():
        st = path.stat()
        items.append(_meta(path, st))
    else:
        try:
            children = sorted(path.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            return fail("read_error", str(exc), path=str(path))
        for child in children:
            if skip_walk(child):
                continue
            try:
                st = child.stat()
            except OSError:
                continue
            items.append(_meta(child, st))
            if len(items) >= limit:
                break
    return {"ok": True, "path": str(path), "count": len(items), "items": items}


def _meta(path: Path, st: os.stat_result) -> dict[str, Any]:
    return {
        "path": str(path),
        "name": path.name,
        "type": "dir" if stat.S_ISDIR(st.st_mode) else "file",
        "size": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "mode": oct(st.st_mode & 0o777),
        "suffix": path.suffix.lower(),
    }


def get_file(cfg: dict[str, Any], raw: str, offset: int, length: int) -> dict[str, Any]:
    path = real_path(raw)
    ok, reason = allowed_file(cfg, path)
    if not ok:
        return fail("path_denied", reason, path=str(path))
    if not path.is_file():
        return fail("not_file", "not a regular file", path=str(path))
    max_bytes = int(cfg.get("max_get_bytes", 1_500_000))
    length = max(1, min(length, max_bytes))
    offset = max(0, offset)
    data = path.read_bytes()
    chunk = data[offset : offset + length]
    text = chunk.decode("utf-8", errors="replace")
    return {
        "ok": True,
        "path": str(path),
        "size": len(data),
        "offset": offset,
        "length": len(chunk),
        "sha256": hashlib.sha256(data).hexdigest(),
        "truncated": offset + length < len(data),
        "text": redact(text),
    }


def find_files(cfg: dict[str, Any], root: str, glob: str, since: str | None, limit: int) -> dict[str, Any]:
    base = real_path(root)
    ok, reason = allowed_file(cfg, base)
    if not ok:
        return fail("path_denied", reason, path=str(base))
    since_ts = None
    if since:
        since_ts = datetime.fromisoformat(since.replace("Z", "+00:00")).timestamp()
    matches: list[dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dpath = Path(dirpath)
        dirnames[:] = [n for n in dirnames if not skip_walk(dpath / n)]
        for name in filenames:
            path = dpath / name
            if skip_walk(path):
                continue
            allowed, _ = allowed_file(cfg, path)
            if not allowed:
                continue
            if glob and glob != "*" and not path.match(glob) and not path.name.endswith(
                glob.lstrip("*")
            ):
                if glob.startswith("*.") and path.suffix.lower() != glob[1:].lower():
                    continue
                if not glob.startswith("*.") and glob not in path.name:
                    continue
            try:
                st = path.stat()
            except OSError:
                continue
            if since_ts is not None and st.st_mtime < since_ts:
                continue
            matches.append(_meta(path, st))
            if len(matches) >= limit:
                return {
                    "ok": True,
                    "root": str(base),
                    "count": len(matches),
                    "truncated": True,
                    "items": matches,
                }
    return {"ok": True, "root": str(base), "count": len(matches), "truncated": False, "items": matches}


def validate_sql(query: str) -> str | None:
    q = query.strip().rstrip(";")
    if not q:
        return "empty_query"
    if ";" in q:
        return "multiple_statements"
    if not SQL_OK_RE.match(q):
        return "not_read_only"
    if SQL_BAD_RE.search(q):
        return "forbidden_keyword"
    return None


def run_sql(cfg: dict[str, Any], query: str, limit: int) -> dict[str, Any]:
    reason = validate_sql(query)
    if reason:
        return fail("sql_denied", reason)
    limit = max(1, min(int(limit), int(cfg.get("max_sql_rows", 200))))
    engine = cfg.get("db", {})
    kind = engine.get("kind")
    if kind == "postgres":
        env = os.environ.copy()
        env_file = engine.get("env_file")
        if env_file:
            for line in Path(env_file).read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.split("=", 1)
                    env[key] = val
        sql = f"SELECT * FROM ({query.rstrip(';')}) AS rea_inspect_q LIMIT {limit}"
        if query.strip().lower().startswith("explain") or query.strip().lower().startswith("show"):
            sql = query.rstrip(";")
        cmd = [
            "psql",
            "-d",
            engine.get("database", "sailors_master"),
            "-U",
            engine.get("user", "rea-ro"),
            "-v",
            "ON_ERROR_STOP=1",
            "--csv",
            "-c",
            sql,
        ]
        host = engine.get("host") or ""
        if host:
            cmd[1:1] = ["-h", host, "-p", str(engine.get("port", 5432))]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=20)
    elif kind == "mysql":
        sql = f"SELECT * FROM ({query.rstrip(';')}) AS rea_inspect_q LIMIT {limit}"
        cmd = [
            "mysql",
            "--batch",
            "--raw",
            "-N",
            "-u",
            engine.get("user", "rea_ro"),
            engine.get("database", "mysql"),
            "-e",
            sql,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    else:
        return fail("sql_unavailable", "no database configured on this host")
    if proc.returncode != 0:
        return fail("sql_error", redact(proc.stderr.strip() or "query failed"))
    return {
        "ok": True,
        "engine": kind,
        "limit": limit,
        "csv": redact(proc.stdout)[:200_000],
    }


def schema(cfg: dict[str, Any]) -> dict[str, Any]:
    engine = cfg.get("db", {})
    if engine.get("kind") == "postgres":
        q = """
        SELECT table_schema, table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog','information_schema')
        ORDER BY 1,2,ordinal_position
        """
        return run_sql(cfg, q, 5000)
    if engine.get("kind") == "mysql":
        q = """
        SELECT table_schema, table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema NOT IN ('information_schema','mysql','performance_schema','sys')
        """
        return run_sql(cfg, q, 5000)
    return fail("sql_unavailable", "no database configured on this host")


def logs(cfg: dict[str, Any], source: str, lines: int) -> dict[str, Any]:
    lines = max(1, min(int(lines), 200))
    mapping = cfg.get("logs", {})
    spec = mapping.get(source)
    if not spec:
        return fail("unknown_log", f"unknown log source {source}", sources=sorted(mapping))
    if spec.get("kind") == "file":
        path = real_path(spec["path"])
        ok, reason = allowed_file(cfg, path, for_log=True)
        if not ok:
            return fail("path_denied", reason, path=str(path))
        proc = subprocess.run(
            ["tail", "-n", str(lines), str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {"ok": True, "source": source, "path": str(path), "text": redact(proc.stdout)}
    if spec.get("kind") == "journal":
        cmd = ["journalctl", "-u", spec["unit"], "-n", str(lines), "--no-pager"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return {"ok": True, "source": source, "unit": spec["unit"], "text": redact(proc.stdout)}
    return fail("unknown_log", "unsupported log kind")


def nginx_files(cfg: dict[str, Any]) -> dict[str, Any]:
    items = []
    for raw in cfg.get("nginx_files", []):
        path = Path(raw)
        if not path.is_file():
            continue
        text = redact(path.read_text(encoding="utf-8", errors="replace"))
        items.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "text": text})
    return {"ok": True, "count": len(items), "items": items}


def revision(cfg: dict[str, Any]) -> dict[str, Any]:
    roots = cfg.get("revision_roots", [])
    items = []
    for raw in roots:
        path = Path(raw)
        if not path.exists():
            continue
        st = path.stat()
        entry: dict[str, Any] = _meta(path, st)
        git_dir = path / ".git" if path.is_dir() else path.parent / ".git"
        if git_dir.exists():
            proc = subprocess.run(
                ["git", "-C", str(path if path.is_dir() else path.parent), "log", "-1", "--format=%h %ci %s"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            entry["git"] = proc.stdout.strip()
        items.append(entry)
    return {"ok": True, "host": cfg.get("host_id"), "items": items}


def discover(cfg: dict[str, Any], since: str | None, limit: int) -> dict[str, Any]:
    collected: list[dict[str, Any]] = []
    truncated = False
    for root in cfg.get("discover_roots", cfg.get("allow_paths", [])):
        result = find_files(cfg, root, "*", since, max(1, limit - len(collected)))
        if result.get("ok"):
            collected.extend(result.get("items", []))
            truncated = truncated or bool(result.get("truncated"))
        if len(collected) >= limit:
            truncated = True
            break
    collected.sort(key=lambda item: item.get("mtime", ""), reverse=True)
    return {
        "ok": True,
        "host": cfg.get("host_id"),
        "since": since,
        "count": len(collected),
        "truncated": truncated,
        "items": collected[:limit],
    }


def handle(cfg: dict[str, Any], req: dict[str, Any]) -> dict[str, Any]:
    op = str(req.get("op") or req.get("cmd") or "").strip().lower()
    limit = int(req.get("limit") or 200)
    if op in {"help", "catalog", ""}:
        return {
            "ok": True,
            "host": cfg.get("host_id"),
            "ops": [
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
            ],
            "allow_paths": cfg.get("allow_paths", []),
            "logs": sorted((cfg.get("logs") or {}).keys()),
            "db": {"kind": (cfg.get("db") or {}).get("kind"), "database": (cfg.get("db") or {}).get("database")},
        }
    if op == "list":
        return list_path(cfg, str(req.get("path") or cfg["allow_paths"][0]), limit)
    if op == "get":
        return get_file(cfg, str(req["path"]), int(req.get("offset") or 0), int(req.get("length") or 120_000))
    if op == "find":
        return find_files(cfg, str(req.get("root") or cfg["allow_paths"][0]), str(req.get("glob") or "*"), req.get("since"), limit)
    if op == "sql":
        return run_sql(cfg, str(req.get("query") or req.get("sql") or ""), int(req.get("limit") or 50))
    if op == "schema":
        return schema(cfg)
    if op == "logs":
        return logs(cfg, str(req.get("source") or "nginx-error"), int(req.get("lines") or 80))
    if op == "nginx":
        return nginx_files(cfg)
    if op == "revision":
        return revision(cfg)
    if op == "discover":
        return discover(cfg, req.get("since"), limit)
    return fail("unknown_op", f"unknown op {op}")


def parse_request(argv: list[str]) -> dict[str, Any]:
    raw = os.environ.get("SSH_ORIGINAL_COMMAND", "").strip()
    if not raw and len(argv) > 1:
        raw = " ".join(argv[1:])
    if not raw:
        return {"op": "help"}
    if raw.startswith("{"):
        return json.loads(raw)
    parts = raw.split(" ", 1)
    req: dict[str, Any] = {"op": parts[0]}
    if len(parts) == 2:
        rest = parts[1]
        if rest.startswith("{"):
            req.update(json.loads(rest))
        elif parts[0] in {"get", "list"}:
            req["path"] = rest
        elif parts[0] == "sql":
            req["query"] = rest
        elif parts[0] == "logs":
            req["source"] = rest
        elif parts[0] == "find":
            req["glob"] = rest
    return req


def main() -> int:
    started = time.time()
    cfg = load_config()
    try:
        req = parse_request(sys.argv)
    except json.JSONDecodeError as exc:
        out = fail("bad_json", str(exc))
        print(json.dumps(out))
        return 2
    result = handle(cfg, req)
    result["duration_ms"] = int((time.time() - started) * 1000)
    audit(
        cfg,
        {
            "host": cfg.get("host_id"),
            "op": req.get("op"),
            "ok": result.get("ok"),
            "path": req.get("path") or req.get("root"),
            "source": req.get("source"),
            "error": result.get("error"),
            "user": os.environ.get("USER") or os.environ.get("LOGNAME"),
        },
    )
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
