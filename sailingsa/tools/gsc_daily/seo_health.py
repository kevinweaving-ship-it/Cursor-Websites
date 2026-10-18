"""Daily SEO health on top of the existing GSC collector.

Adds Googlebot-log, sitemap-staleness, crawl-vs-index, canonical-mismatch,
and sustained Search Analytics checks. Does not change the site, sitemap
builder, nginx rate limits, or call Validate Fix.
"""

from __future__ import annotations

import gzip
import json
import re
import socket
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .classify import REAL
from .config import (
    GOOGLEBOT_INACTIVE_HOURS,
    NGINX_ACCESS_LOG_DIR,
    PERF_CLICK_RATIO,
    PERF_IMPR_RATIO,
    PERF_SUSTAINED_DAYS,
    SITEMAP_STALE_DAYS,
    UA,
    server_data_root,
)
from .probe_live import CTX, _NoRedirect

SAST = ZoneInfo("Africa/Johannesburg")
LINE_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" '
    r"(?P<status>\d{3}) (?P<bytes>\S+) "
    r'"(?P<ref>[^"]*)" "(?P<ua>[^"]*)"'
)
UA_GOOGLE = re.compile(
    r"googlebot|google-inspectiontool|adsbot-google|apis-google|mediapartners-google",
    re.I,
)
SSA_PATH_PREFIXES = (
    "/sailor",
    "/regatta",
    "/class",
    "/club",
    "/boat",
    "/event",
    "/events",
    "/sitemap",
    "/about",
    "/sailors",
    "/classes",
    "/clubs",
    "/yearly-events",
    "/stats",
    "/regattas",
)
INDEXED_COV = ("submitted and indexed", "indexed")
CRAWLED_NOT_INDEXED_COV = ("crawled - currently not indexed",)
NOT_CRAWLED_COV = (
    "discovered - currently not indexed",
    "url is unknown to google",
    "crawled currently not indexed",  # not used; keep distinct lists
)


def _parse_ts(raw: str) -> datetime:
    return datetime.strptime(raw, "%d/%b/%Y:%H:%M:%S %z")


def _open_log(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def _first_log_ts(path: Path) -> datetime | None:
    try:
        fh = _open_log(path)
    except OSError:
        return None
    with fh:
        for i, line in enumerate(fh):
            if i > 40:
                break
            m = LINE_RE.match(line)
            if not m:
                continue
            try:
                return _parse_ts(m.group("ts"))
            except Exception:
                continue
    return None


def _file_overlaps_window(path: Path, window_start: datetime, as_of: datetime) -> bool:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=as_of.tzinfo)
    except OSError:
        return True
    # Rotated files: mtime is typically midnight after the contained day.
    content_start = mtime - timedelta(days=2)
    return content_start <= as_of and mtime >= window_start


def _norm_url(url: str) -> str:
    p = urlparse(url or "")
    host = (p.netloc or "").lower()
    path = (p.path or "/").rstrip("/") or "/"
    return f"{p.scheme or 'https'}://{host}{path}"


def verify_googlebot_ip(ip: str, cache: dict[str, bool] | None = None) -> bool:
    """Reverse-DNS then forward-DNS. Never trust User-Agent alone."""
    if cache is not None and ip in cache:
        return cache[ip]
    ok = False
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        host_l = (host or "").lower().rstrip(".")
        if host_l.endswith(".googlebot.com") or host_l.endswith(".google.com"):
            infos = socket.getaddrinfo(host_l, None)
            addrs = {i[4][0] for i in infos}
            ok = ip in addrs
    except Exception:
        ok = False
    if cache is not None:
        cache[ip] = ok
    return ok


def _ssa_googlebot_hit(path: str, status: str, nbytes: str) -> bool:
    """Drop TimAdvisor hits that share the combined access log (no Host field)."""
    if path == "/robots.txt":
        return status == "200" and str(nbytes) == "231"
    if path.startswith("/sitemap"):
        return True
    return any(path == p or path.startswith(p + "/") for p in SSA_PATH_PREFIXES)


def googlebot_activity(
    log_dir: Path,
    *,
    as_of: datetime,
    inactive_hours: int = GOOGLEBOT_INACTIVE_HOURS,
    verify_ip: Callable[[str], bool] | None = None,
) -> dict:
    """Last verified SailingSA Googlebot hit at or before as_of."""
    cache: dict[str, bool] = {}
    verifier = verify_ip or (lambda ip: verify_googlebot_ip(ip, cache))
    last: datetime | None = None
    hits_48 = 0
    verified_ips: set[str] = set()
    window_start = as_of - timedelta(hours=inactive_hours)
    if not log_dir.is_dir():
        return {
            "ok": True,
            "reason": "no_access_log_dir",
            "last_seen": "",
            "hours_ago": None,
            "hits_48h": 0,
            "alert": False,
            "skipped": True,
        }
    files = sorted(log_dir.glob("access.log*"))
    oldest_log_ts: datetime | None = None
    for path in files:
        first_ts = _first_log_ts(path)
        if first_ts is not None and (oldest_log_ts is None or first_ts < oldest_log_ts):
            oldest_log_ts = first_ts
        if not _file_overlaps_window(path, window_start, as_of):
            continue
        try:
            fh = _open_log(path)
        except OSError:
            continue
        with fh:
            for line in fh:
                if not UA_GOOGLE.search(line):
                    continue
                m = LINE_RE.match(line)
                if not m:
                    continue
                try:
                    ts = _parse_ts(m.group("ts"))
                except Exception:
                    continue
                if ts > as_of:
                    continue
                req = m.group("req") or ""
                parts = req.split(" ")
                path_q = parts[1] if len(parts) >= 2 else "/"
                path_only = urlparse(path_q).path or "/"
                if not _ssa_googlebot_hit(path_only, m.group("status"), m.group("bytes")):
                    continue
                ip = m.group("ip")
                if not verifier(ip):
                    continue
                verified_ips.add(ip)
                if last is None or ts > last:
                    last = ts
                if ts >= window_start:
                    hits_48 += 1
    hours_ago = None
    if last is not None:
        hours_ago = round((as_of - last).total_seconds() / 3600.0, 2)
    would_alert = last is None or (hours_ago is not None and hours_ago > inactive_hours)
    covered = oldest_log_ts is not None and oldest_log_ts <= window_start
    skipped = False
    reason = ""
    if would_alert and not covered:
        skipped = True
        would_alert = False
        reason = "insufficient_log_coverage"
    return {
        "ok": not would_alert,
        "last_seen": last.isoformat() if last else "",
        "hours_ago": hours_ago,
        "hits_48h": hits_48,
        "verified_ips": len(verified_ips),
        "inactive_hours": inactive_hours,
        "alert": would_alert,
        "skipped": skipped,
        "reason": reason,
        "log_coverage_start": oldest_log_ts.isoformat() if oldest_log_ts else "",
    }


def sitemap_health(summary: dict, *, as_of_day: date, stale_days: int = SITEMAP_STALE_DAYS) -> dict:
    errors = int(summary.get("errors") or 0)
    warnings = int(summary.get("warnings") or 0)
    last_dl = (summary.get("last_downloaded") or "").strip()[:10]
    count = int(summary.get("count") or 0)
    auth_ok = bool(summary.get("_auth_ok", True))
    age_days = None
    if last_dl:
        try:
            age_days = (as_of_day - date.fromisoformat(last_dl)).days
        except ValueError:
            age_days = None
    fetch_fail = auth_ok and count == 0
    stale = age_days is not None and age_days > stale_days
    # Empty last_downloaded with no sitemap list is an API/auth gap, not 7-day staleness.
    missing_dl = auth_ok and count > 0 and not last_dl
    alert = bool(errors) or fetch_fail or stale or missing_dl
    return {
        "ok": not alert,
        "last_downloaded": last_dl,
        "age_days": age_days,
        "errors": errors,
        "warnings": warnings,
        "count": count,
        "stale_days": stale_days,
        "alert": alert,
        "fetch_failure": fetch_fail or missing_dl or errors > 0,
        "stale": stale,
    }


def _inspect_status(ins: dict) -> dict:
    if not isinstance(ins, dict):
        return {}
    if "indexStatusResult" in ins:
        return ins.get("indexStatusResult") or {}
    if "inspectionResult" in ins:
        return (ins.get("inspectionResult") or {}).get("indexStatusResult") or {}
    return ins if "coverageState" in ins or "verdict" in ins else {}


def indexing_split(inspections: dict) -> dict:
    """Split URL Inspection sample: not crawled vs crawled-not-indexed vs indexed."""
    buckets = Counter()
    crawled_not_indexed: list[str] = []
    not_crawled: list[str] = []
    indexed: list[str] = []
    canonical_gsc: list[dict] = []
    for url, ins in (inspections or {}).items():
        st = _inspect_status(ins if isinstance(ins, dict) else {})
        cov = (st.get("coverageState") or "").strip()
        cov_l = cov.lower()
        last = st.get("lastCrawlTime") or ""
        uc = (st.get("userCanonical") or "").strip()
        gc = (st.get("googleCanonical") or "").strip()
        verdict = (st.get("verdict") or "").upper()
        if verdict == "PASS" or cov_l in INDEXED_COV or cov_l == "submitted and indexed":
            buckets["indexed"] += 1
            indexed.append(url)
        elif cov_l.startswith("crawled") and "not indexed" in cov_l:
            buckets["crawled_not_indexed"] += 1
            crawled_not_indexed.append(url)
        elif (not last and cov_l in ("url is unknown to google", "discovered - currently not indexed")) or (
            "discovered" in cov_l and "not indexed" in cov_l
        ) or cov_l == "url is unknown to google":
            buckets["not_crawled"] += 1
            not_crawled.append(url)
        elif "duplicate" in cov_l and "canonical" in cov_l:
            buckets["canonical_gsc"] += 1
            canonical_gsc.append({"url": url, "userCanonical": uc, "googleCanonical": gc, "coverage": cov})
        elif "alternate" in cov_l and "canonical" in cov_l:
            buckets["canonical_gsc"] += 1
            canonical_gsc.append({"url": url, "userCanonical": uc, "googleCanonical": gc, "coverage": cov})
        else:
            buckets["other"] += 1
        if uc and gc and _norm_url(uc) != _norm_url(gc):
            if not any(x["url"] == url for x in canonical_gsc):
                canonical_gsc.append(
                    {"url": url, "userCanonical": uc, "googleCanonical": gc, "coverage": cov}
                )
                buckets["canonical_gsc"] += 1
    return {
        "indexed": len(indexed),
        "crawled_not_indexed": len(crawled_not_indexed),
        "not_crawled": len(not_crawled),
        "canonical_gsc_mismatch": len(canonical_gsc),
        "other": buckets.get("other", 0),
        "crawled_not_indexed_urls": crawled_not_indexed[:12],
        "not_crawled_urls": not_crawled[:12],
        "canonical_gsc_examples": canonical_gsc[:12],
        "note": (
            "not_crawled = Google has not fetched the URL (unknown/discovered). "
            "crawled_not_indexed = fetched but excluded from the index. "
            "Sample is the daily watchlist, not Page Indexing totals."
        ),
    }


def _first_hop(url: str) -> tuple[int, str]:
    opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=CTX))
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with opener.open(req, timeout=15) as resp:
            return resp.status, resp.headers.get("Location") or ""
    except urllib.error.HTTPError as e:
        loc = ""
        try:
            loc = e.headers.get("Location") or ""
        except Exception:
            loc = ""
        return e.code, loc
    except Exception:
        return 0, ""


def live_canonical_mismatches(
    examples: list[dict],
    *,
    hop: Callable[[str], tuple[int, str]] | None = None,
) -> list[dict]:
    """Live defect only when user and Google URLs both still HTTP 200 (dual indexable)."""
    fn = hop or _first_hop
    cache: dict[str, tuple[int, str]] = {}

    def cached(url: str) -> tuple[int, str]:
        if url not in cache:
            cache[url] = fn(url)
        return cache[url]

    out = []
    for ex in examples:
        chosen = (ex.get("googleCanonical") or "").strip()
        user = (ex.get("userCanonical") or ex.get("url") or "").strip()
        if not chosen or not user or _norm_url(chosen) == _norm_url(user):
            continue
        g_status, g_loc = cached(chosen)
        u_status, u_loc = cached(user)
        live_dual_200 = g_status == 200 and u_status == 200
        if live_dual_200:
            out.append(
                {
                    **ex,
                    "google_url_status": g_status,
                    "google_url_location": g_loc,
                    "user_url_status": u_status,
                    "user_url_location": u_loc,
                    "live_dual_200": True,
                }
            )
    return out


def _yesterday_reals(root: Path, day: str) -> set[str] | None:
    p = root / (date.fromisoformat(day) - timedelta(days=1)).isoformat() / "report.json"
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return set(data.get("real_urls") or [])


def _sa_tuple(sa: dict | None) -> tuple[float | None, float | None]:
    if not sa:
        return None, None
    clicks = sa.get("clicks")
    impr = sa.get("impressions")
    if clicks is None and impr is None:
        return None, None
    return float(clicks or 0), float(impr or 0)


def _load_day_sa(root: Path, day: str) -> dict | None:
    p = root / day / "report.json"
    if not p.is_file():
        return None
    try:
        return (json.loads(p.read_text(encoding="utf-8")).get("search_analytics") or {}) or None
    except Exception:
        return None


def performance_trend(
    root: Path,
    day: str,
    today_sa: dict,
    *,
    click_ratio: float = PERF_CLICK_RATIO,
    impr_ratio: float = PERF_IMPR_RATIO,
    sustained_days: int = PERF_SUSTAINED_DAYS,
) -> dict:
    """Alert only if clicks AND impressions drop vs prior week, for sustained_days runs."""
    d = date.fromisoformat(day)
    today_c, today_i = _sa_tuple(today_sa)
    prior_day = (d - timedelta(days=7)).isoformat()
    prior_sa = _load_day_sa(root, prior_day)
    prior_c, prior_i = _sa_tuple(prior_sa)
    def _breach(c, i, pc, pi) -> bool:
        if None in (c, i, pc, pi) or pc <= 0 or pi <= 0:
            return False
        return (c / pc) <= click_ratio and (i / pi) <= impr_ratio

    today_breach = _breach(today_c, today_i, prior_c, prior_i)
    consecutive = 0
    if today_breach:
        consecutive = 1
        for back in range(1, sustained_days):
            d2 = (d - timedelta(days=back)).isoformat()
            sa2 = _load_day_sa(root, d2)
            p2 = _load_day_sa(root, (date.fromisoformat(d2) - timedelta(days=7)).isoformat())
            c2, i2 = _sa_tuple(sa2)
            pc2, pi2 = _sa_tuple(p2)
            if _breach(c2, i2, pc2, pi2):
                consecutive += 1
            else:
                break
    alert = consecutive >= sustained_days
    return {
        "ok": not alert,
        "alert": alert,
        "today": {"clicks": today_c, "impressions": today_i},
        "prior_week": {"day": prior_day, "clicks": prior_c, "impressions": prior_i},
        "click_ratio": (
            None
            if today_c is None or prior_c is None or prior_c <= 0
            else round(today_c / prior_c, 3)
        ),
        "impr_ratio": (
            None
            if today_i is None or prior_i is None or prior_i <= 0
            else round(today_i / prior_i, 3)
        ),
        "consecutive_breach_days": consecutive,
        "thresholds": {
            "click_ratio": click_ratio,
            "impr_ratio": impr_ratio,
            "sustained_days": sustained_days,
        },
    }


def evaluate_health(
    *,
    day: str,
    google: dict,
    probes: list[dict],
    sitemap_summary: dict,
    search_analytics: dict,
    data_root: Path | None = None,
    log_dir: Path | None = None,
    as_of: datetime | None = None,
    hop: Callable[[str], tuple[int, str]] | None = None,
    verify_ip: Callable[[str], bool] | None = None,
    skip_logs: bool = False,
) -> dict:
    root = data_root or server_data_root()
    as_of = as_of or datetime.now(SAST)
    auth = google.get("auth") or ""
    sm_in = dict(sitemap_summary or {})
    sm_in["_auth_ok"] = auth == "OK"
    sm = sitemap_health(sm_in, as_of_day=date.fromisoformat(day))
    inspections = google.get("inspections") or {}
    split = indexing_split(inspections)
    live_mm = live_canonical_mismatches(split.get("canonical_gsc_examples") or [], hop=hop)
    perf = performance_trend(root, day, search_analytics or {})
    if skip_logs:
        bot = {
            "ok": True,
            "alert": False,
            "last_seen": "",
            "hours_ago": None,
            "hits_48h": None,
            "skipped": True,
        }
    else:
        bot = googlebot_activity(
            log_dir or NGINX_ACCESS_LOG_DIR,
            as_of=as_of,
            verify_ip=verify_ip,
        )

    alerts: list[str] = []
    if bot.get("alert") and not bot.get("skipped"):
        if bot.get("last_seen"):
            alerts.append(
                f"Googlebot inactive {bot.get('hours_ago')}h "
                f"(threshold {GOOGLEBOT_INACTIVE_HOURS}h; last {bot.get('last_seen')})"
            )
        else:
            alerts.append(f"No verified SailingSA Googlebot hits in {GOOGLEBOT_INACTIVE_HOURS}h")
    if sm["alert"]:
        if sm["fetch_failure"] and sm["errors"]:
            alerts.append(f"GSC sitemap errors={sm['errors']} last_download={sm['last_downloaded'] or 'n/a'}")
        elif sm["stale"]:
            alerts.append(
                f"GSC sitemap last download {sm['last_downloaded']} is {sm['age_days']}d old "
                f"(threshold {SITEMAP_STALE_DAYS}d)"
            )
        elif sm["fetch_failure"]:
            alerts.append("GSC sitemap list empty or lastDownloaded missing")
    if live_mm:
        alerts.append(
            f"{len(live_mm)} live canonical mismatch(es) "
            f"(user and Google URLs both HTTP 200): {live_mm[0]['url']}"
        )
    today_real = {p.get("url") for p in probes if p.get("classification") == REAL and p.get("url")}
    y_real = _yesterday_reals(root, day)
    if y_real is not None:
        new_real = sorted(today_real - y_real)
        if new_real:
            alerts.append(
                f"{len(new_real)} new REAL indexing/live defect(s) vs yesterday: {new_real[0]}"
            )
    if perf["alert"]:
        alerts.append(
            f"Sustained search drop vs prior week: clicks {perf['today']['clicks']} "
            f"vs {perf['prior_week']['clicks']} ({perf['click_ratio']}), "
            f"impr {perf['today']['impressions']} vs {perf['prior_week']['impressions']} "
            f"({perf['impr_ratio']}) for {perf['consecutive_breach_days']} days"
        )

    return {
        "run_date": day,
        "googlebot": bot,
        "sitemap": sm,
        "indexing": split,
        "canonical_live_mismatches": live_mm,
        "performance": perf,
        "alerts": alerts,
        "healthy": not alerts,
        "crawl_vs_index": (
            "not_crawling"
            if split["not_crawled"] and not split["crawled_not_indexed"] and not split["indexed"]
            else "mixed"
        ),
    }


def write_health(dest: Path, health: dict) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "seo_health.json"
    path.write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")
    return path


def health_lines(health: dict) -> list[str]:
    bot = health.get("googlebot") or {}
    sm = health.get("sitemap") or {}
    idx = health.get("indexing") or {}
    perf = health.get("performance") or {}
    lines = ["SEO HEALTH"]
    if bot.get("skipped"):
        lines.append("Googlebot logs: skipped")
    elif bot.get("ok"):
        lines.append(
            f"Googlebot: OK last {bot.get('hours_ago')}h ago "
            f"({bot.get('hits_48h')} verified hits/48h)"
        )
    else:
        lines.append(
            f"Googlebot: INACTIVE last={bot.get('last_seen') or 'none'} "
            f"hours_ago={bot.get('hours_ago')}"
        )
    age = sm.get("age_days")
    age_s = "n/a" if age is None else f"{age}d"
    lines.append(
        f"Sitemap: dl {sm.get('last_downloaded') or 'n/a'} "
        f"age={age_s} errors={sm.get('errors')} "
        f"{'OK' if sm.get('ok') else 'ALERT'}"
    )
    lines.append(
        f"Index sample: indexed {idx.get('indexed', 0)} | "
        f"crawled-not-indexed {idx.get('crawled_not_indexed', 0)} | "
        f"not-crawled {idx.get('not_crawled', 0)} | "
        f"GSC canonical-diff {idx.get('canonical_gsc_mismatch', 0)}"
    )
    live_n = len(health.get("canonical_live_mismatches") or [])
    lines.append(f"Live canonical 200-vs-200 mismatches: {live_n}")
    pr = perf.get("click_ratio")
    ir = perf.get("impr_ratio")
    lines.append(
        f"Search 7d vs prior week: clicks ratio {pr} impr ratio {ir} "
        f"{'ALERT' if perf.get('alert') else 'OK'}"
    )
    lines.append("not-crawled ≠ crawled-but-not-indexed (see seo_health.json)")
    alerts = health.get("alerts") or []
    if alerts:
        lines.append("SEO ALERTS:")
        for a in alerts[:6]:
            lines.append(f"- {a}")
    return lines


def replay(day: str, data_root: Path | None = None, log_dir: Path | None = None) -> dict:
    """Recompute health from a saved daily folder. No GSC API calls."""
    root = data_root or server_data_root()
    dest = root / day
    google = json.loads((dest / "gsc_api.json").read_text(encoding="utf-8"))
    probes = json.loads((dest / "probes.json").read_text(encoding="utf-8"))
    report = json.loads((dest / "report.json").read_text(encoding="utf-8"))
    as_of = datetime.combine(date.fromisoformat(day), datetime.min.time(), tzinfo=SAST) + timedelta(
        hours=9
    )
    health = evaluate_health(
        day=day,
        google=google,
        probes=probes,
        sitemap_summary=report.get("sitemap") or {},
        search_analytics=report.get("search_analytics") or {},
        data_root=root,
        log_dir=log_dir,
        as_of=as_of,
    )
    write_health(dest, health)
    return health


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Replay SEO health from saved GSC daily files")
    ap.add_argument("--day", required=True)
    ap.add_argument("--data-root", default="")
    ap.add_argument("--log-dir", default="")
    args = ap.parse_args(argv)
    root = Path(args.data_root) if args.data_root else server_data_root()
    log_dir = Path(args.log_dir) if args.log_dir else NGINX_ACCESS_LOG_DIR
    health = replay(args.day, data_root=root, log_dir=log_dir)
    print("\n".join(health_lines(health)))
    print("ALERTS", health.get("alerts"))
    return 0 if health.get("healthy") else 2


if __name__ == "__main__":
    raise SystemExit(main())
