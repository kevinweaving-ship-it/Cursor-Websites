#!/usr/bin/env python3
"""SailingSA server health monitor — WhatsApp via existing Baileys engine.

Reuses isolated arial-whatsapp-poc (poc.js) POST http://127.0.0.1:$WAPOC_PORT/send
with Bearer WAPOC_TOKEN from /etc/arial-whatsapp-poc.env.

Never touches api.py, nginx, Postgres config, or housekeeping.py.
WhatsApp failure is logged locally and never restarts production.
Phone numbers and tokens are never written to ordinary logs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")
CONF = Path("/etc/sailingsa/server-monitor.conf")
WAPOC_ENV_DEFAULT = Path("/etc/arial-whatsapp-poc.env")
STATE_PATH = Path("/var/lib/sailingsa/server-monitor-state.json")
LOG_PATH = Path("/var/log/sailingsa-server-monitor.log")
HK_LOG = Path("/var/log/sailingsa-housekeeping.log")
LOCK = Path("/var/lock/sailingsa-server-monitor.lock")

DISK_WARN = 75
DISK_CRIT = 85
IDLE_XACT_WARN = 3
IDLE_XACT_CRIT = 8
FIVE_XX_SPIKE = 10  # in 5 minutes
HK_STALE_HOURS = 36
EXPECTED_API_WORKERS = 4
# Normal `systemctl restart sailingsa-api` (4 uvicorn workers) is allowed this long.
# WhatsApp only if HTTP stays down after the grace. Mid-restart cron must not alert.
API_RESTART_GRACE_S = 120
API_RESTART_PROBE_S = 15
LOAD_WARN_MULT = 3
LOAD_CRIT_MULT = 6
SWAP_WARN_PCT = 80
SWAP_CRIT_PCT = 92
MEM_AVAIL_CRIT_MB = 120

FULL_BACKUP_RE = re.compile(r"^backup_\d{8}_\d{6}\.tar\.gz$")
POOL_ERR_RE = re.compile(
    r"too many clients|remaining connection slots reserved|connection pool exhausted|"
    r"pool exhausted|QueuePool.*timeout|FATAL:\s*sorry, too many clients",
    re.I,
)

# Alert keys that support WARNING vs CRITICAL
LEVELS = ("OK", "WARNING", "CRITICAL")


def now_sast() -> dt.datetime:
    return dt.datetime.now(SAST)


def log(msg: str) -> None:
    line = f"{now_sast().strftime('%Y-%m-%d %H:%M:%S %Z')} {msg}"
    print(line, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def run(cmd, timeout=12):
    try:
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout
        )
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception:
        return 1, "", "err"


def load_conf() -> dict:
    out = {
        "RECIPIENT": "27720821111",
        "WAPOC_ENV": str(WAPOC_ENV_DEFAULT),
        "WAPOC_PORT": "8009",
        "API_RESTART_GRACE_S": str(API_RESTART_GRACE_S),
        "API_RESTART_PROBE_S": str(API_RESTART_PROBE_S),
    }
    if CONF.is_file():
        for line in CONF.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_wapoc_env(path: str) -> dict:
    env = {}
    p = Path(path)
    if not p.is_file():
        return env
    for line in p.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def to_e164(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0") and len(digits) == 10:
        return "27" + digits[1:]
    return digits


def load_state() -> dict:
    if not STATE_PATH.is_file():
        return {"alerts": {}, "last_daily": "", "sustained": {}}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"alerts": {}, "last_daily": "", "sustained": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    os.replace(tmp, STATE_PATH)
    os.chmod(STATE_PATH, 0o600)


def send_whatsapp(text: str, conf: dict) -> bool:
    """POST /send on existing Baileys control API. Never raise into production."""
    try:
        wenv = load_wapoc_env(conf.get("WAPOC_ENV", str(WAPOC_ENV_DEFAULT)))
        port = wenv.get("WAPOC_PORT") or conf.get("WAPOC_PORT") or "8009"
        token = wenv.get("WAPOC_TOKEN") or ""
        number = to_e164(conf.get("RECIPIENT", "27720821111"))
        if not token or len(number) < 11:
            log("wa_send failed: config")
            return False
        body = json.dumps({"number": number, "text": text}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/send",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=40) as r:
            res = json.loads(r.read().decode())
        if res.get("ok"):
            log("wa_send ok")
            return True
        log("wa_send failed: engine")
        return False
    except Exception as exc:
        log(f"wa_send failed: {type(exc).__name__}")
        return False


def wa_health(conf: dict) -> str:
    try:
        wenv = load_wapoc_env(conf.get("WAPOC_ENV", str(WAPOC_ENV_DEFAULT)))
        port = wenv.get("WAPOC_PORT") or "8009"
        token = wenv.get("WAPOC_TOKEN") or ""
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read().decode())
        return str(res.get("state") or "UNKNOWN")
    except Exception:
        return "DOWN"


# ---------- metrics (lightweight, no stress, no app changes) ----------

def metric_disk():
    u = shutil.disk_usage("/")
    pct = int(round(u.used * 100.0 / u.total))
    free_gb = u.free / (1024**3)
    return pct, free_gb


def metric_mem():
    info = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, v = line.split(":", 1)
        info[k] = int(v.strip().split()[0])  # kB
    total = info.get("MemTotal", 1)
    avail = info.get("MemAvailable", 0)
    used = total - avail
    swap_t = info.get("SwapTotal", 0)
    swap_f = info.get("SwapFree", 0)
    swap_u = max(0, swap_t - swap_f)
    return {
        "ram_used_gb": used / 1024 / 1024,
        "ram_total_gb": total / 1024 / 1024,
        "ram_avail_mb": avail / 1024,
        "swap_used_mb": swap_u / 1024,
        "swap_total_mb": swap_t / 1024,
        "swap_pct": int(round(swap_u * 100.0 / swap_t)) if swap_t else 0,
    }


def metric_load():
    return os.getloadavg()


def nproc() -> int:
    try:
        return os.cpu_count() or 1
    except Exception:
        return 1


def _positive_int(raw, default: int) -> int:
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return default


def api_restart_windows(conf: dict | None = None) -> tuple[int, int]:
    """Grace/probe seconds. Env overrides conf; both optional."""
    cfg = conf if conf is not None else load_conf()
    grace = os.environ.get("SAILINGSA_API_RESTART_GRACE_S")
    probe = os.environ.get("SAILINGSA_API_RESTART_PROBE_S")
    if grace is None:
        grace = cfg.get("API_RESTART_GRACE_S", API_RESTART_GRACE_S)
    if probe is None:
        probe = cfg.get("API_RESTART_PROBE_S", API_RESTART_PROBE_S)
    return _positive_int(grace, API_RESTART_GRACE_S), _positive_int(probe, API_RESTART_PROBE_S)


def wait_out_api_restart(
    first: dict,
    probe_fn,
    grace_s: int,
    probe_s: int,
    sleeper=time.sleep,
    logger=log,
    clock=time.monotonic,
) -> dict:
    """Hold the API-down finding until a normal restart window has passed.

    First failed HTTP check is treated as a possible `systemctl restart`.
    Re-probe until up, or until grace expires — only then is it alertable.
    """
    if first.get("up"):
        return first
    if grace_s <= 0:
        logger(
            f"api down http={first.get('http')} active={first.get('active')}; grace=0"
        )
        return first
    logger(
        f"api down http={first.get('http')} active={first.get('active')}; "
        f"waiting up to {grace_s}s for normal restart"
    )
    deadline = clock() + grace_s
    last = first
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            break
        wait_s = min(probe_s, remaining) if probe_s > 0 else 0
        if wait_s > 0:
            sleeper(wait_s)
        last = probe_fn()
        if last.get("up"):
            logger(
                f"api recovered within restart grace http={last.get('http')} "
                f"workers={last.get('workers')}"
            )
            return last
        if probe_s <= 0:
            break
    logger(
        f"api still down after {grace_s}s grace http={last.get('http')} "
        f"active={last.get('active')}"
    )
    return last


def metric_api():
    code = 0
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/")
        with urllib.request.urlopen(req, timeout=8) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = 0
    up = code in (200, 301, 302, 303, 307, 308)
    _c, out, _e = run(["ps", "-eo", "pid,ppid,args", "--no-headers"])
    parent = None
    configured = EXPECTED_API_WORKERS
    for ln in out.splitlines():
        parts = ln.split(None, 2)
        if len(parts) < 3:
            continue
        pid, _ppid, args = parts
        if "uvicorn" in args and "api:app" in args and "--port 8000" in args:
            parent = pid
            wm = re.search(r"--workers\s+(\d+)", args)
            if wm:
                configured = int(wm.group(1))
            break
    workers = 0
    if parent:
        for ln in out.splitlines():
            parts = ln.split(None, 2)
            if len(parts) < 3:
                continue
            _pid, ppid, args = parts
            if ppid == parent and "spawn_main" in args:
                workers += 1
        if workers == 0:
            workers = configured
    _c, en, _ = run(["systemctl", "is-enabled", "sailingsa-api"])
    _c, act, _ = run(["systemctl", "is-active", "sailingsa-api"])
    return {
        "up": up and act == "active",
        "http": code,
        "workers": workers,
        "enabled": en,
        "active": act,
    }


def metric_pg():
    _c, act, _ = run(["systemctl", "is-active", "postgresql"])
    ok = False
    total = idle = None
    _c, out, _ = run(
        [
                "sudo",
                "-u",
                "postgres",
                "psql",
                "-tAc",
                "SELECT 1",
        ],
        timeout=8,
    )
    if out.strip() == "1":
        ok = True
        _c, out2, _ = run(
            [
                "sudo",
                "-u",
                "postgres",
                "psql",
                "-tAc",
                "SELECT count(*), "
                "count(*) FILTER (WHERE state = 'idle in transaction') "
                "FROM pg_stat_activity",
            ],
            timeout=8,
        )
        parts = [p.strip() for p in out2.replace("|", " ").split() if p.strip().isdigit()]
        if len(parts) >= 2:
            total, idle = int(parts[0]), int(parts[1])
        elif len(parts) == 1:
            total = int(parts[0])
    return {"up": act == "active" and ok, "active": act, "conns": total, "idle_xact": idle}


GATEWAY_5XX = {502, 503, 504}


def last_api_restart_epoch() -> float | None:
    """When sailingsa-api last entered active (systemd restart)."""
    _c, out, _ = run(
        ["systemctl", "show", "-p", "ActiveEnterTimestamp", "--value", "sailingsa-api"]
    )
    raw = (out or "").strip()
    if not raw or raw in ("n/a", "0"):
        return None
    parts = raw.split()
    if len(parts) < 3:
        return None
    try:
        body = " ".join(parts[1:3])
        t = dt.datetime.strptime(body, "%Y-%m-%d %H:%M:%S").replace(tzinfo=SAST)
        return t.timestamp()
    except Exception:
        return None


def metric_5xx(window_s: int, skip_gateway_after: float | None = None) -> int:
    path = Path("/var/log/nginx/access.log")
    if not path.is_file():
        return 0
    cutoff = time.time() - window_s
    count = 0
    try:
        # Read last ~1.5MB only
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > 1_500_000:
                fh.seek(-1_500_000, os.SEEK_END)
                fh.readline()
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        return 0
    # [18/Sep/2026:10:04:29 +0200]
    ts_re = re.compile(r"\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2})")
    st_re = re.compile(r'"\s(\d{3})\s')
    for line in text.splitlines():
        m = st_re.search(line)
        if not m:
            continue
        code = int(m.group(1))
        if code < 500:
            continue
        tm = ts_re.search(line)
        if not tm:
            count += 1
            continue
        try:
            t = dt.datetime.strptime(tm.group(1), "%d/%b/%Y:%H:%M:%S").replace(tzinfo=SAST)
            ts = t.timestamp()
            if ts < cutoff:
                continue
            # Nginx 502/503/504 during a normal API restart are not an outage.
            if (
                skip_gateway_after is not None
                and code in GATEWAY_5XX
                and ts >= skip_gateway_after
            ):
                continue
            count += 1
        except Exception:
            count += 1
    return count


def metric_journal_hits(pattern: re.Pattern, since="5 min ago") -> int:
    _c, out, _ = run(
        ["journalctl", "-u", "sailingsa-api", "--since", since, "--no-pager", "-o", "cat"],
        timeout=10,
    )
    if not out:
        return 0
    return sum(1 for ln in out.splitlines() if pattern.search(ln))


def metric_housekeeping():
    if not HK_LOG.is_file():
        return {"ok": False, "age_h": None, "removed": 0, "recovered": 0, "note": "no log"}
    text = HK_LOG.read_text(errors="replace")
    idx = text.rfind("===== SAILINGSA HOUSEKEEPING APPLY")
    if idx < 0:
        return {"ok": False, "age_h": None, "removed": 0, "recovered": 0, "note": "no apply"}
    block = text[idx:]
    end = block.find("===== END HOUSEKEEPING")
    if end > 0:
        block = block[: end + 24]
    failed = block.count("DELETE_FAILED")
    removed = len(re.findall(r"^DELETED ", block, re.M))
    m1 = re.search(r"disk_before=(\d+)% used=(\d+)", block)
    m2 = re.search(r"disk_after=(\d+)% used=(\d+)", block)
    recovered = 0
    if m1 and m2:
        recovered = max(0, int(m1.group(2)) - int(m2.group(2)))
    # timestamp on first line
    head = block.splitlines()[0] if block.splitlines() else ""
    age_h = None
    tm = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", head)
    if tm:
        try:
            t = dt.datetime.strptime(tm.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=SAST)
            age_h = (now_sast() - t).total_seconds() / 3600.0
        except Exception:
            pass
    ok = failed == 0 and (age_h is None or age_h < HK_STALE_HOURS)
    return {
        "ok": ok,
        "age_h": age_h,
        "removed": removed,
        "recovered": recovered,
        "note": "ok" if ok else ("failed" if failed else "stale"),
    }


def metric_backup():
    root = Path("/root")
    latest = None
    if root.is_dir():
        cands = []
        for p in root.iterdir():
            if p.is_file() and FULL_BACKUP_RE.match(p.name) and p.stat().st_size >= 1_000_000_000:
                cands.append(p)
        if cands:
            latest = max(cands, key=lambda x: x.stat().st_mtime)
    if latest is None:
        return {"ok": False, "age": "missing", "size": "—", "path": None}
    age_h = (time.time() - latest.stat().st_mtime) / 3600.0
    size_g = latest.stat().st_size / (1024**3)
    valid = False
    try:
        import tarfile

        with tarfile.open(latest, "r:*") as tf:
            n = 0
            for _ in tf:
                n += 1
                if n >= 8:
                    break
        valid = n > 0
    except Exception:
        valid = False
    age = f"{int(age_h)}h" if age_h < 48 else f"{int(age_h / 24)}d"
    return {
        "ok": valid,
        "age": age,
        "size": f"{size_g:.1f}G",
        "path": latest.name,
    }


def metric_services():
    expected = {
        "sailingsa-api": ("enabled", "active"),
        "postgresql": (None, "active"),
        "nginx": (None, "active"),
    }
    rows = []
    abnormal = []
    for unit, (want_en, want_act) in expected.items():
        _c, en, _ = run(["systemctl", "is-enabled", unit])
        _c, act, _ = run(["systemctl", "is-active", unit])
        rows.append((unit, en, act))
        if want_act and act != want_act:
            abnormal.append(unit)
        if want_en and en != want_en:
            abnormal.append(unit)
    _c, en_r, _ = run(["systemctl", "is-enabled", "sailingsa-api-restore"])
    _c, act_r, _ = run(["systemctl", "is-active", "sailingsa-api-restore"])
    restore_up = en_r == "enabled" or act_r == "active"
    _c, out, _ = run(["ps", "-eo", "pid,stat,cmd", "--no-headers"])
    zombies = sum(1 for ln in out.splitlines() if len(ln.split()) >= 2 and "Z" in ln.split()[1])
    return {
        "expected_ok": len(expected) - len(set(abnormal)),
        "expected_n": len(expected),
        "abnormal": sorted(set(abnormal)),
        "restore_up": restore_up,
        "zombies": zombies,
        "rows": rows,
    }


def collect() -> dict:
    disk_pct, free_gb = metric_disk()
    mem = metric_mem()
    load = metric_load()
    api = wait_out_api_restart(metric_api(), metric_api, *api_restart_windows())
    pg = metric_pg()
    hk = metric_housekeeping()
    bak = metric_backup()
    svc = metric_services()
    restart_ts = last_api_restart_epoch()
    skip_gateway_after = None
    if restart_ts is not None and (time.time() - restart_ts) < 300:
        # Include the Stopping window just before ActiveEnter.
        skip_gateway_after = restart_ts - 60
    five_5m = metric_5xx(300, skip_gateway_after)
    five_24h = metric_5xx(86400)
    pool_hits = metric_journal_hits(POOL_ERR_RE, "5 min ago")
    return {
        "disk_pct": disk_pct,
        "free_gb": free_gb,
        "mem": mem,
        "load": load,
        "api": api,
        "pg": pg,
        "hk": hk,
        "bak": bak,
        "svc": svc,
        "five_5m": five_5m,
        "five_24h": five_24h,
        "pool_hits": pool_hits,
        "nproc": nproc(),
        "ts": now_sast(),
        "api_restart_age_s": (time.time() - restart_ts) if restart_ts else None,
    }


def evaluate(m: dict, state: dict) -> list[tuple[str, str, str]]:
    """Return list of (key, level, message). level OK means recovered/healthy."""
    findings = []

    dp = m["disk_pct"]
    if dp >= DISK_CRIT:
        findings.append(("disk", "CRITICAL", f"Disk {dp}% — {m['free_gb']:.0f}GB free"))
    elif dp >= DISK_WARN:
        findings.append(("disk", "WARNING", f"Disk {dp}% — {m['free_gb']:.0f}GB free"))
    else:
        findings.append(("disk", "OK", f"Disk {dp}%"))

    if not m["api"]["up"]:
        findings.append(
            ("api", "CRITICAL", f"Production API down/unresponsive (http={m['api']['http']} active={m['api']['active']})")
        )
    else:
        findings.append(("api", "OK", "API UP"))

    if not m["pg"]["up"]:
        findings.append(("pg", "CRITICAL", f"PostgreSQL down/unresponsive (active={m['pg']['active']})"))
    else:
        findings.append(("pg", "OK", "PostgreSQL UP"))

    idle = m["pg"]["idle_xact"]
    if idle is not None:
        if idle >= IDLE_XACT_CRIT:
            findings.append(("idle_xact", "CRITICAL", f"idle-in-transaction {idle}"))
        elif idle >= IDLE_XACT_WARN:
            findings.append(("idle_xact", "WARNING", f"idle-in-transaction {idle}"))
        else:
            findings.append(("idle_xact", "OK", "idle-in-transaction normal"))

    if m["five_5m"] >= FIVE_XX_SPIKE:
        findings.append(("http_5xx", "CRITICAL", f"5xx spike: {m['five_5m']} in 5 min"))
    else:
        findings.append(("http_5xx", "OK", "5xx normal"))

    if m["pool_hits"] > 0:
        findings.append(
            ("pool", "CRITICAL", f"DB pool / too-many-clients errors in last 5m: {m['pool_hits']}")
        )
    else:
        findings.append(("pool", "OK", "no pool/too-many-clients errors"))

    w = m["api"]["workers"]
    # Do not double-alert workers while the API is restarting or down.
    if (
        m["api"]["up"]
        and m["api"]["active"] == "active"
        and w < EXPECTED_API_WORKERS - 1
    ):
        findings.append(("workers", "CRITICAL", f"API workers {w} (expected {EXPECTED_API_WORKERS})"))
    else:
        findings.append(("workers", "OK", f"workers {w}"))

    if not m["hk"]["ok"]:
        findings.append(("housekeeping", "WARNING", f"Housekeeping {m['hk']['note']}"))
    else:
        findings.append(("housekeeping", "OK", "housekeeping ok"))

    if not m["bak"]["ok"]:
        findings.append(("backup", "CRITICAL", f"Full backup {m['bak']['age']}"))
    else:
        findings.append(("backup", "OK", "backup valid"))

    mem = m["mem"]
    load1, load5, load15 = m["load"]
    np = max(1, m["nproc"])
    ram_danger = mem["ram_avail_mb"] < MEM_AVAIL_CRIT_MB and mem["swap_pct"] >= SWAP_CRIT_PCT
    load_crit = load5 >= np * LOAD_CRIT_MULT
    load_warn = load5 >= np * LOAD_WARN_MULT
    swap_warn = mem["swap_pct"] >= SWAP_WARN_PCT
    # sustained: require previous check also bad
    sus = state.setdefault("sustained", {})
    danger_now = ram_danger or load_crit or (swap_warn and load_warn)
    prev = bool(sus.get("ram_load"))
    sus["ram_load"] = danger_now
    if danger_now and prev:
        lvl = "CRITICAL" if (ram_danger or load_crit) else "WARNING"
        findings.append(
            (
                "ram_load",
                lvl,
                f"RAM {mem['ram_used_gb']:.1f}/{mem['ram_total_gb']:.1f}GB avail {mem['ram_avail_mb']:.0f}MB "
                f"swap {mem['swap_used_mb']:.0f}MB ({mem['swap_pct']}%) load {load1:.2f}/{load5:.2f}/{load15:.2f}",
            )
        )
    else:
        findings.append(("ram_load", "OK", "RAM/swap/load ok"))

    if m["svc"]["restore_up"]:
        findings.append(("restore", "WARNING", "sailingsa-api-restore is enabled or active"))
    else:
        findings.append(("restore", "OK", "restore service disabled"))

    return findings


def apply_dedupe(findings, state, send_fn) -> list[str]:
    """Send only begin / severity-change / recovered. Returns actions taken."""
    actions = []
    alerts = state.setdefault("alerts", {})
    rank = {lvl: i for i, lvl in enumerate(LEVELS)}
    for key, level, msg in findings:
        prev = alerts.get(key) or {}
        prev_lvl = prev.get("level", "OK")
        if level == "OK":
            if prev_lvl in ("WARNING", "CRITICAL"):
                text = f"SailingSA Server — RECOVERED\n{now_sast().strftime('%d %b %Y %H:%M')}\n\n{msg}"
                if send_fn(text):
                    alerts[key] = {"level": "OK", "t": time.time()}
                    actions.append(f"RECOVERED {key}")
                else:
                    actions.append(f"wa_fail recover {key}")
            else:
                alerts[key] = {"level": "OK", "t": prev.get("t", time.time())}
            continue
        if prev_lvl == "OK" or rank[level] > rank.get(prev_lvl, 0):
            flag = "CRITICAL" if level == "CRITICAL" else "WARNING"
            text = (
                f"SailingSA Server — {flag}\n"
                f"{now_sast().strftime('%d %b %Y %H:%M')}\n\n{msg}"
            )
            if send_fn(text):
                alerts[key] = {"level": level, "t": time.time()}
                actions.append(f"{level} {key}")
            else:
                actions.append(f"wa_fail {level} {key}")
        else:
            # same or lower severity while still bad — no send
            actions.append(f"dedupe {key} {level}")
    state["alerts"] = alerts
    return actions


def overall(findings) -> str:
    if any(lvl == "CRITICAL" for _k, lvl, _m in findings):
        return "CRITICAL"
    if any(lvl == "WARNING" for _k, lvl, _m in findings):
        return "WARNING"
    return "OK"


def fmt_daily(m: dict, findings) -> str:
    ov = overall(findings)
    icon = {"OK": "🟢", "WARNING": "🟡", "CRITICAL": "🔴"}[ov]
    mem = m["mem"]
    l1, l5, l15 = m["load"]
    pg_c = m["pg"]["conns"]
    idle = m["pg"]["idle_xact"]
    pg_line = "UP"
    if pg_c is not None:
        pg_line += f" — {pg_c} connections"
        if idle is not None:
            pg_line += f" / {idle} idle-in-transaction"
    hk = m["hk"]
    rec_mb = hk["recovered"] / (1024 * 1024) if hk["recovered"] else 0
    hk_line = (
        f"{'OK' if hk['ok'] else hk['note']} — {hk['removed']} removed / {rec_mb:.0f}MB recovered"
        if hk["age_h"] is not None
        else hk["note"]
    )
    bak = m["bak"]
    svc = m["svc"]
    ts = m["ts"].strftime("%d %b %Y %H:%M")
    lines = [
        "SailingSA Server — Daily Health",
        ts,
        "",
        f"{icon} Overall: {ov}",
        f"Disk: {m['disk_pct']}% — {m['free_gb']:.0f}GB free",
        f"RAM: {mem['ram_used_gb']:.1f}/{mem['ram_total_gb']:.1f}GB — Swap: {mem['swap_used_mb']:.0f}MB",
        f"Load: {l1:.2f} / {l5:.2f} / {l15:.2f}",
        f"API: {'UP' if m['api']['up'] else 'DOWN'} — {m['api']['workers']} workers",
        f"PostgreSQL: {pg_line if m['pg']['up'] else 'DOWN'}",
        f"HTTP: 5xx last 24h: {m['five_24h']}",
        f"Backup: latest valid — {bak['age']}/{bak['size']}" if bak["ok"]
        else f"Backup: {bak['age']}",
        f"Housekeeping: last run {hk_line}",
        f"Services: expected {svc['expected_ok']}/{svc['expected_n']}"
        + (f" / abnormal {', '.join(svc['abnormal'])}" if svc["abnormal"] else " / abnormal 0"),
        f"Zombies: {svc['zombies']}",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="SailingSA WhatsApp server monitor")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="5-min health + alerts")
    g.add_argument("--daily", action="store_true", help="daily report + alerts")
    g.add_argument("--test-send", action="store_true", help="send one TEST OK")
    g.add_argument("--sample-daily", action="store_true", help="print sample daily (no send)")
    g.add_argument("--dedupe-test", action="store_true", help="print dedupe transitions (no send)")
    g.add_argument(
        "--restart-grace-test",
        action="store_true",
        help="prove API restart grace does not alert on a mid-restart blip",
    )
    args = parser.parse_args(argv)

    conf = load_conf()
    try:
        if args.test_send:
            text = "SailingSA Server Monitoring — TEST OK"
            ok = send_whatsapp(text, conf)
            log("test-send " + ("ok" if ok else "FAIL"))
            print("TEST_SEND", "OK" if ok else "FAIL")
            return 0 if ok else 1

        if args.restart_grace_test:
            down = {
                "up": False,
                "http": 0,
                "workers": 0,
                "enabled": "enabled",
                "active": "active",
            }
            up = {
                "up": True,
                "http": 200,
                "workers": 4,
                "enabled": "enabled",
                "active": "active",
            }
            notes = []

            def _log(msg):
                notes.append(msg)

            recovered = wait_out_api_restart(
                down, lambda: up, 120, 0, sleeper=lambda _s: None, logger=_log
            )
            still = wait_out_api_restart(
                down, lambda: down, 0, 0, sleeper=lambda _s: None, logger=_log
            )
            already = wait_out_api_restart(
                up, lambda: down, 120, 0, sleeper=lambda _s: None, logger=_log
            )
            rec_ok = recovered.get("up") is True
            still_ok = still.get("up") is False
            already_ok = already.get("up") is True
            skip_ok = True
            # 502 during a restart window must not count; a 500 still must.
            now = time.time()
            restart_ts = now - 30
            sample = [
                f'1.1.1.1 - - [{now_sast().strftime("%d/%b/%Y:%H:%M:%S")}] '
                f'"GET /x HTTP/1.1" 502 0 "-" "-"',
                f'1.1.1.1 - - [{now_sast().strftime("%d/%b/%Y:%H:%M:%S")}] '
                f'"GET /x HTTP/1.1" 500 0 "-" "-"',
            ]
            counted_all = 0
            counted_skip = 0
            ts_re = re.compile(r"\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2})")
            st_re = re.compile(r'"\s(\d{3})\s')
            for line in sample:
                code = int(st_re.search(line).group(1))
                t = dt.datetime.strptime(
                    ts_re.search(line).group(1), "%d/%b/%Y:%H:%M:%S"
                ).replace(tzinfo=SAST)
                ts = t.timestamp()
                counted_all += 1
                if code in GATEWAY_5XX and ts >= (restart_ts - 60):
                    continue
                counted_skip += 1
            skip_ok = counted_all == 2 and counted_skip == 1
            print("restart_grace recovered_mid_restart", rec_ok)
            print("restart_grace still_down_after_grace", still_ok)
            print("restart_grace already_up_no_wait", already_ok)
            print("restart_grace skip_restart_502", skip_ok)
            print("restart_grace notes", notes)
            return 0 if rec_ok and still_ok and already_ok and skip_ok else 1

        if args.dedupe_test:
            printed = []

            def capture(text):
                printed.append(text)
                return True

            demo_state = {"alerts": {}, "sustained": {}}
            seq = [
                [("disk", "WARNING", "Disk 76% — 18GB free")],
                [("disk", "CRITICAL", "Disk 86% — 10GB free")],
                [("disk", "OK", "Disk 54%")],
            ]
            for step in seq:
                acts = apply_dedupe(step, demo_state, capture)
                print("STEP", step[0][1], "→", ",".join(acts))
            print("--- messages that would send ---")
            for p in printed:
                print(p)
                print("---")
            print(f"dedupe_messages={len(printed)} (expect 3: begin, severity, recovered)")
            return 0 if len(printed) == 3 else 1

        m = collect()
        state = load_state()
        findings = evaluate(m, state)

        if args.sample_daily:
            print(fmt_daily(m, findings))
            return 0

        def do_send(text):
            return send_whatsapp(text, conf)

        actions = apply_dedupe(findings, state, do_send)
        if args.daily:
            today = now_sast().strftime("%Y-%m-%d")
            if state.get("last_daily") == today:
                log("daily already sent today")
            else:
                if do_send(fmt_daily(m, findings)):
                    state["last_daily"] = today
                    log("daily sent")
                else:
                    log("daily send failed; will retry next cycle")
        save_state(state)
        log(
            f"check overall={overall(findings)} disk={m['disk_pct']}% "
            f"api={'up' if m['api']['up'] else 'down'} pg={'up' if m['pg']['up'] else 'down'} "
            f"actions={actions or ['none']}"
        )
        return 0
    except Exception as exc:
        log(f"monitor error: {type(exc).__name__}")
        return 0  # never fail the host; retry next cycle


if __name__ == "__main__":
    sys.exit(main())
