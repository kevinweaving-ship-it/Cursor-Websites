#!/usr/bin/env python3
"""SailingSA permanent server housekeeping.

Infrastructure only. Never deletes production/user data, media, PDFs,
telemetry, Postgres, source, credentials, or KEEP/known-good artifacts.

Usage:
  sailingsa-housekeeping.py --dry-run   # report only (default)
  sailingsa-housekeeping.py --apply     # approved safe-retention cleanup
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tarfile
from collections import namedtuple
from pathlib import Path

KEEP_LIST = Path("/etc/sailingsa/housekeeping-keep.list")
LOG_PATH = Path("/var/log/sailingsa-housekeeping.log")

FULL_KEEP = 3
API_BAK_KEEP = 10
RELEASE_DAYS = 14
TMP_HOURS = 48
FULL_MIN_BYTES = 1_000_000_000  # 1 GiB-ish: real full backups are ~11G

FULL_BACKUP_RE = re.compile(r"^backup_\d{8}_\d{6}\.tar\.gz$")
API_TS_RE = re.compile(r"^api\.py\.\d{8}_\d{6}(\.bak)?$")
KEEP_NAME_RE = re.compile(
    r"(KEEP|known[-_]?good|KNOWN[-_]?GOOD|BEFORE_BIO)", re.I
)
CRED_NAME_RE = re.compile(
    r"(?i)(\.env$|cookie|secret|password|passwd|credential|\.pem$|"
    r"id_rsa|id_ed25519|\.key$|authorized_keys|super_session)"
)
PDF_RE = re.compile(r"(?i)\.pdf$")

PROTECTED_PREFIXES = (
    "/media",
    "/var/www/sailingsa/frontend/media",
    "/var/www/sailingsa/frontend/public/media",
    "/var/www/sailingsa/media",
    "/var/www/sailingsa/uploads",
    "/var/www/sailingsa/frontend/uploads",
    "/var/www/sailingsa/frontend/public/uploads",
    "/var/lib/postgresql",
    "/var/lib/pgsql",
    "/root/.ssh",
    "/etc/ssh",
    "/home",
    "/root/lipton-vakaros-archive",
    "/var/lib/sailingsa",
)

# Production source is never a deletion root. Only timestamped api.py baks
# inside the api directory are eligible, and only via the bak rule.
PROD_SOURCE_PREFIXES = (
    "/var/www/sailingsa",
)

API_BAK_DIRS = (
    Path("/var/www/sailingsa/api"),
    Path("/root/backups"),
)
RELEASE_DIR = Path("/root/releases")
FULL_BACKUP_DIR = Path("/root")
TMP_DIR = Path("/tmp")

Action = namedtuple("Action", "op path reason bytes")


def now() -> dt.datetime:
    return dt.datetime.now()


def ts() -> str:
    return now().strftime("%Y-%m-%d %H:%M:%S")


def run(cmd, timeout=30):
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return p.returncode, (p.stdout or ""), (p.stderr or "")
    except Exception as exc:
        return 1, "", str(exc)


def disk_use_pct(mount="/"):
    usage = shutil.disk_usage(mount)
    pct = int(round(usage.used * 100.0 / usage.total))
    return pct, usage


def disk_band(pct):
    if pct >= 85:
        return "CRITICAL"
    if pct >= 75:
        return "WARNING"
    return "OK"


def load_keep_list():
    kept = set()
    if not KEEP_LIST.is_file():
        return kept
    for line in KEEP_LIST.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        kept.add(os.path.realpath(line))
    return kept


def is_keep_named(path: Path) -> bool:
    return bool(KEEP_NAME_RE.search(str(path)))


def is_protected_path(path: Path, keep_set) -> str | None:
    real = os.path.realpath(str(path))
    if real in keep_set:
        return "keep-list"
    if is_keep_named(path):
        return "keep-name"
    if CRED_NAME_RE.search(path.name) or CRED_NAME_RE.search(real):
        return "credential"
    if PDF_RE.search(path.name):
        return "pdf"
    for pref in PROTECTED_PREFIXES:
        if real == pref or real.startswith(pref.rstrip("/") + "/"):
            return f"protected:{pref}"
    # Live api.py itself
    if real == "/var/www/sailingsa/api/api.py":
        return "production-source"
    if real.startswith("/etc/") and "logrotate" not in real and "cron" not in real:
        if path.suffix in {".env", ".key", ".pem"} or "credential" in real:
            return "etc-credential"
    return None


def file_age_hours(path: Path) -> float:
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return 0.0
    return max(0.0, (now().timestamp() - mtime) / 3600.0)


def size_of(path: Path) -> int:
    try:
        if path.is_dir() and not path.is_symlink():
            total = 0
            for root, _dirs, files in os.walk(path, followlinks=False):
                for name in files:
                    fp = Path(root) / name
                    try:
                        total += fp.stat().st_size
                    except OSError:
                        pass
            return total
        return path.stat().st_size
    except OSError:
        return 0


def tar_valid(path: Path) -> bool:
    try:
        if path.stat().st_size < 1024:
            return False
        with tarfile.open(path, "r:*") as tf:
            # Lightweight integrity: read members; do not extract.
            for _ in tf:
                pass
        return True
    except Exception:
        return False


def iter_timestamped_api_baks(directory: Path):
    if not directory.is_dir():
        return []
    out = []
    for p in directory.iterdir():
        if not p.is_file() or p.is_symlink():
            continue
        if API_TS_RE.match(p.name):
            out.append(p)
    out.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return out


def classify_full_backups():
    full, scoped = [], []
    if not FULL_BACKUP_DIR.is_dir():
        return full, scoped
    for p in FULL_BACKUP_DIR.iterdir():
        if not p.is_file() or p.is_symlink():
            continue
        if not p.name.startswith("backup_") or not p.name.endswith(".tar.gz"):
            continue
        if FULL_BACKUP_RE.match(p.name) and p.stat().st_size >= FULL_MIN_BYTES:
            full.append(p)
        else:
            scoped.append(p)
    full.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    scoped.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return full, scoped


def plan_full_backups(keep_set, actions, reports):
    full, scoped = classify_full_backups()
    for p in scoped:
        reports.append(
            f"SCOPED_BACKUP_REPORT {p} size={size_of(p)} "
            f"(not a full backup; not deleted)"
        )
    retained_valid = []
    for p in full:
        why = is_protected_path(p, keep_set)
        valid = tar_valid(p)
        if why:
            reports.append(f"KEEP_FULL {p} reason={why} tar_valid={valid}")
            retained_valid.append(p)
            continue
        if valid:
            retained_valid.append(p)
        else:
            reports.append(f"INVALID_FULL_BACKUP_REPORT {p} (not deleted)")
    # Keep latest FULL_KEEP valid backups. Delete older only if newer
    # retained backups exist and are tar-valid.
    keepers = [p for p in retained_valid[:FULL_KEEP] if tar_valid(p)]
    for p in keepers:
        reports.append(f"RETAIN_FULL {p} size={size_of(p)}")
    for p in full:
        if p in keepers:
            continue
        why = is_protected_path(p, keep_set)
        if why:
            reports.append(f"SKIP_DELETE {p} reason={why}")
            continue
        newer_ok = [k for k in keepers if k.stat().st_mtime > p.stat().st_mtime]
        if len(keepers) < 1 or not newer_ok:
            reports.append(
                f"SKIP_DELETE {p} reason=no-newer-valid-retained-full-backup"
            )
            continue
        if not all(tar_valid(k) for k in newer_ok):
            reports.append(f"SKIP_DELETE {p} reason=newer-retained-not-tar-valid")
            continue
        actions.append(
            Action("delete", p, f"full-backup-retention keep={FULL_KEEP}", size_of(p))
        )


def plan_api_baks(keep_set, actions, reports):
    for directory in API_BAK_DIRS:
        files = iter_timestamped_api_baks(directory)
        named = []
        if directory.is_dir():
            for p in directory.iterdir():
                if not p.is_file():
                    continue
                if p.name.startswith("api.py") and not API_TS_RE.match(p.name):
                    named.append(p)
        for p in named:
            reports.append(
                f"NAMED_API_BAK_REPORT {p} size={size_of(p)} "
                f"(ambiguous name; not deleted)"
            )
        keepers = []
        for p in files:
            why = is_protected_path(p, keep_set)
            if why:
                reports.append(f"KEEP_API_BAK {p} reason={why}")
                keepers.append(p)
                continue
            if len(keepers) < API_BAK_KEEP:
                keepers.append(p)
                reports.append(f"RETAIN_API_BAK {p}")
            else:
                actions.append(
                    Action(
                        "delete",
                        p,
                        f"api-bak-retention dir={directory} keep={API_BAK_KEEP}",
                        size_of(p),
                    )
                )


def plan_releases(keep_set, actions, reports):
    if not RELEASE_DIR.is_dir():
        return
    cutoff = now() - dt.timedelta(days=RELEASE_DAYS)
    for p in sorted(RELEASE_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file() or p.is_symlink():
            continue
        why = is_protected_path(p, keep_set)
        if why:
            reports.append(f"KEEP_RELEASE {p} reason={why}")
            continue
        mtime = dt.datetime.fromtimestamp(p.stat().st_mtime)
        if mtime >= cutoff:
            reports.append(f"RETAIN_RELEASE {p} age_days={(now() - mtime).days}")
            continue
        actions.append(
            Action(
                "delete",
                p,
                f"release-age>{RELEASE_DAYS}d intermediate",
                size_of(p),
            )
        )


def plan_tmp(keep_set, actions, reports):
    if not TMP_DIR.is_dir():
        return
    # /tmp/ssa_*
    for p in sorted(TMP_DIR.glob("ssa_*")):
        _consider_tmp(p, keep_set, actions, reports, "tmp-ssa>48h")
    # stress-test / matrix / diagnostic JSON in /tmp only
    extra_globs = (
        "ssa_*stress*",
        "*matrix*.json",
        "*matrix*.jsonl",
        "ssa_*.json",
        "ssa_*.jsonl",
        "ssa_*.patch",
        "cursor_diag_*",
        "ssa_diag_*",
    )
    seen = set()
    for pat in extra_globs:
        for p in TMP_DIR.glob(pat):
            real = os.path.realpath(str(p))
            if real in seen:
                continue
            seen.add(real)
            _consider_tmp(p, keep_set, actions, reports, f"tmp-diag:{pat}>48h")


def _consider_tmp(p: Path, keep_set, actions, reports, reason):
    why = is_protected_path(p, keep_set)
    if why:
        reports.append(f"SKIP_TMP {p} reason={why}")
        return
    # Never delete PDFs / media / uploads even if they somehow match
    if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        reports.append(f"SKIP_TMP {p} reason=media-or-pdf")
        return
    if file_age_hours(p) < TMP_HOURS:
        reports.append(f"RETAIN_TMP {p} age_h={file_age_hours(p):.1f}")
        return
    actions.append(Action("delete", p, reason, size_of(p)))


def plan_pycache(keep_set, actions, reports):
    candidates = [Path("/root/__pycache__"), Path("/tmp/__pycache__")]
    for base in (Path("/tmp"),):
        if not base.is_dir():
            continue
        for root, dirs, _files in os.walk(base, followlinks=False):
            if "__pycache__" in dirs:
                candidates.append(Path(root) / "__pycache__")
    seen = set()
    for p in candidates:
        real = os.path.realpath(str(p))
        if real in seen or not p.exists():
            continue
        seen.add(real)
        why = is_protected_path(p, keep_set)
        if why:
            reports.append(f"SKIP_PYCACHE {p} reason={why}")
            continue
        if any(real.startswith(pref.rstrip("/") + "/") or real == pref
               for pref in PROD_SOURCE_PREFIXES):
            reports.append(f"SKIP_PYCACHE {p} reason=production-source")
            continue
        if file_age_hours(p) < TMP_HOURS:
            reports.append(f"RETAIN_PYCACHE {p} age_h={file_age_hours(p):.1f}")
            continue
        actions.append(Action("delete", p, "disposable-pycache>48h", size_of(p)))


def leftover_named_root_baks(reports):
    root = Path("/root")
    if not root.is_dir():
        return
    count = 0
    for p in root.iterdir():
        if not p.is_file():
            continue
        if p.name.startswith("api.py.bak") or (
            p.name.startswith("api.py.") and p.name.endswith(".bak")
            and not API_TS_RE.match(p.name)
        ):
            count += 1
            if count <= 25:
                reports.append(
                    f"LEFTOVER_NAMED_BAK_REPORT {p} size={size_of(p)} "
                    "(not auto-deleted; add to KEEP or remove manually)"
                )
    if count > 25:
        reports.append(f"LEFTOVER_NAMED_BAK_REPORT ... +{count - 25} more (total {count})")


def process_audit(reports):
    _code, out, _err = run(
        ["ss", "-lntp"], timeout=20
    )
    reports.append("LISTEN_PORTS_BEGIN")
    for line in (out or "").splitlines():
        if any(x in line for x in (":800", ":8080", ":5432", ":80 ", ":443 ")):
            reports.append("  " + line.strip())
    reports.append("LISTEN_PORTS_END")
    reports.append(
        "NOTE 8002=sailingsa-admin-api — reported only; NEVER touched "
        "until separately decided."
    )
    reports.append(
        "NOTE 8001=sailingsa-api-restore — must remain disabled/inactive."
    )

    for unit in (
        "sailingsa-api",
        "sailingsa-api-restore",
        "sailingsa-admin-api",
    ):
        _c, enabled, _e = run(["systemctl", "is-enabled", unit])
        _c, active, _e = run(["systemctl", "is-active", unit])
        reports.append(
            f"SERVICE {unit} enabled={enabled.strip()} active={active.strip()}"
        )

    _c, out, _e = run(
        ["systemctl", "list-unit-files", "--type=service", "--no-pager"],
        timeout=20,
    )
    for line in (out or "").splitlines():
        low = line.lower()
        if any(k in low for k in ("restore", "test", "tmp", "cursor-diag")):
            if "sailingsa" in low or "restore" in low or "cursor" in low:
                reports.append(f"RESTORE_OR_TEST_UNIT {line.strip()}")

    _c, out, _e = run(["ps", "-eo", "pid,ppid,stat,cmd", "--no-headers"])
    uvicorn = []
    zombies = []
    unexpected = []
    for line in (out or "").splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, st, cmd = parts
        if "Z" in st:
            zombies.append(line.strip())
        if "uvicorn" in cmd:
            uvicorn.append(line.strip())
        if any(x in cmd for x in ("/tmp/", "/root/backup", "/root/releases/")):
            if "sailingsa-housekeeping" not in cmd:
                unexpected.append(line.strip())
    reports.append(f"UVICORN_PROCESSES count={len(uvicorn)}")
    for u in uvicorn:
        reports.append(f"  UVICORN {u}")
    reports.append(f"ZOMBIES count={len(zombies)}")
    for z in zombies[:20]:
        reports.append(f"  ZOMBIE {z}")
    reports.append(f"PROCS_FROM_BACKUP_OR_TMP count={len(unexpected)}")
    for u in unexpected[:20]:
        reports.append(f"  UNEXPECTED_LOC {u}")
    reports.append("PROCESS_POLICY no automatic kill of unknown production processes")


def assert_action_safe(action: Action, keep_set) -> str | None:
    p = action.path
    why = is_protected_path(p, keep_set)
    if why:
        return why
    real = os.path.realpath(str(p))
    if real == "/var/www/sailingsa/api/api.py":
        return "live-api.py"
    if PDF_RE.search(p.name):
        return "pdf"
    for pref in PROTECTED_PREFIXES:
        if real == pref or real.startswith(pref.rstrip("/") + "/"):
            return f"protected:{pref}"
    # Refuse deletes under production source except timestamped api baks
    if real.startswith("/var/www/sailingsa/"):
        if not (
            real.startswith("/var/www/sailingsa/api/")
            and API_TS_RE.match(os.path.basename(real))
        ):
            return "production-source"
    return None


def apply_action(action: Action, dry_run: bool, keep_set, results):
    blocked = assert_action_safe(action, keep_set)
    if blocked:
        results.append(f"BLOCKED {action.path} reason={blocked}")
        return False
    if dry_run:
        results.append(
            f"WOULD_DELETE {action.path} bytes={action.bytes} reason={action.reason}"
        )
        return True
    try:
        if action.path.is_dir() and not action.path.is_symlink():
            shutil.rmtree(action.path)
        else:
            action.path.unlink()
        results.append(
            f"DELETED {action.path} bytes={action.bytes} reason={action.reason}"
        )
        return True
    except OSError as exc:
        results.append(f"DELETE_FAILED {action.path} err={exc}")
        return False


def append_log(text: str):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(text)
            if not text.endswith("\n"):
                fh.write("\n")
    except OSError:
        pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="SailingSA housekeeping")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report only (default)")
    mode.add_argument("--apply", action="store_true", help="perform safe cleanup")
    args = parser.parse_args(argv)
    dry_run = not args.apply

    keep_set = load_keep_list()
    actions: list[Action] = []
    reports: list[str] = []

    pct_before, usage_before = disk_use_pct("/")
    band = disk_band(pct_before)

    plan_full_backups(keep_set, actions, reports)
    plan_api_baks(keep_set, actions, reports)
    plan_releases(keep_set, actions, reports)
    plan_tmp(keep_set, actions, reports)
    plan_pycache(keep_set, actions, reports)
    leftover_named_root_baks(reports)

    # Safety filter: drop any action that touches protected data
    safe_actions = []
    for a in actions:
        blocked = assert_action_safe(a, keep_set)
        if blocked:
            reports.append(f"FILTERED {a.path} reason={blocked}")
        else:
            safe_actions.append(a)

    results = []
    for a in safe_actions:
        apply_action(a, dry_run, keep_set, results)

    pct_after, usage_after = disk_use_pct("/")
    process_lines = []
    process_audit(process_lines)

    mode_s = "DRY-RUN" if dry_run else "APPLY"
    lines = [
        f"===== SAILINGSA HOUSEKEEPING {mode_s} {ts()} =====",
        f"disk_before={pct_before}% used={usage_before.used} avail={usage_before.free} band={band}",
        f"keep_list={KEEP_LIST} keep_entries={len(keep_set)}",
        f"retention full_keep={FULL_KEEP} api_bak_keep={API_BAK_KEEP} "
        f"release_days={RELEASE_DAYS} tmp_hours={TMP_HOURS}",
        f"policy WARNING/CRITICAL clean only safe-retention items; "
        f"never delete production/user data for space",
        "--- PLAN / REPORT ---",
        *reports,
        "--- ACTIONS ---",
        *results,
        f"actions_proposed={len(safe_actions)} actions_blocked={len(actions) - len(safe_actions)}",
        f"disk_after={pct_after}% used={usage_after.used} avail={usage_after.free} "
        f"band={disk_band(pct_after)}",
        "--- PROCESS AUDIT ---",
        *process_lines,
        "===== END HOUSEKEEPING =====",
        "",
    ]
    text = "\n".join(lines)
    print(text)
    if not dry_run:
        append_log(text)
    else:
        append_log(f"{ts()} DRY-RUN proposed={len(safe_actions)} disk={pct_before}%\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
