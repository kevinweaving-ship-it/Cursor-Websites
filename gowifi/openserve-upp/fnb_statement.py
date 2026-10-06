#!/usr/bin/env python3
"""Live FNB Online statement fetch.

Writes the same FNB table as a QuickBooks bank pull. Either can run first.
Login can show a popup or not. Dismiss it when it is there, then open
the live statement. Only new rows go into bank_tx / fnb_tx. New money
is allocated (client payment, deposit, bank charge, expense) or flagged
as needs attention.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from company import COMPANY, GOWIFI_FNB

ENV_PATH = Path(os.environ.get("FNB_ENV", "/root/secrets/fnb.env"))
DB = os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db")
PROGRESS_PATH = Path(os.environ.get("FNB_PROGRESS", "/tmp/fnb-fetch.progress"))
DUMP_PATH = Path(os.environ.get("FNB_DUMP", "/tmp/fnb-last-page.txt"))


def _short(text: str | None, n: int = 160) -> str:
    line = (text or "").splitlines()[0].strip()
    low = line.lower()
    if "target page" in low or "browser has been closed" in low:
        return "FNB window closed"
    if "captcha" in low or "perfdrive" in low:
        return "FNB asked for CAPTCHA"
    if "missing x server" in low or "xvfb" in low:
        return "FNB browser has no display"
    return line[:n]


def set_progress(step: str, done: bool = False, error: str | None = None, **extra) -> dict:
    pack = {
        "step": _short(step),
        "at": datetime.now().strftime("%H:%M"),
        "done": done,
        "error": _short(error) if error else None,
    }
    pack.update(extra)
    try:
        PROGRESS_PATH.write_text(json.dumps(pack))
    except OSError:
        pass
    return pack


def read_progress() -> dict:
    try:
        return json.loads(PROGRESS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {"step": "", "done": True, "error": None, "at": ""}


LOGIN_URLS = (
    "https://www.online.fnb.co.za/",
    "https://www.online.fnb.co.za/login",
)
ONLINE_BANK = "https://www.online.fnb.co.za/banking/main.jsp"
PROFILE_DIR = Path(os.environ.get("FNB_CHROME", "/root/secrets/fnb-chrome"))
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
USER_SEL = (
    "input[name='username' i], input[name='user' i], input[name='userid' i], "
    "input[name='userId' i], input[name='user_id' i], input#username, input#user, "
    "input#userId, input#userid, input[type='text'][id*='user' i], "
    "input[type='text'][name*='user' i], input[autocomplete='username'], "
    "input[placeholder*='user' i], input[aria-label*='user' i], "
    "input[placeholder*='ID' i], input[aria-label*='ID number' i]"
)
PHONE_CONFIRM = (
    "one-time pin",
    "once-off pin",
    "one time pin",
    "otp",
    "approve this",
    "approve the login",
    "notification sent",
    "sent a notification",
    "confirm on the app",
    "fnb app",
)
ACCOUNT = GOWIFI_FNB
FNB_DIRECT = frozenset({"fnb_live", "fnb_online", "fnb_api", "fnb_history", "fnb_qb"})
QB_SOURCES = frozenset({"qb_fnb_history", "qb-fnb", "quickbooks"})
SAFE_DISMISS = (
    "close",
    "later",
    "not now",
    "no thanks",
    "maybe later",
    "skip",
    "got it",
    "ok",
    "okay",
    "dismiss",
    "continue",
    "don't show again",
    "do not show again",
    "no",
    "cancel",
    "x",
)
UNSAFE_CLICK = (
    "apply",
    "buy",
    "pay",
    "transfer",
    "subscribe",
    "accept offer",
    "upgrade",
    "open now",
    "get started",
)
BANK_WORDS = frozenset(
    {
        "capitec",
        "fnb",
        "absa",
        "standard",
        "nedbank",
        "investec",
        "tyme",
        "discovery",
        "bank",
        "eft",
        "pay",
        "from",
        "to",
        "netcash",
    }
)
FEE_WORDS = (
    "account fee",
    "bank charge",
    "service fee",
    "int pymt fee",
    "#int",
    "intuity",
    "monthly account fee",
)
EXPENSE_WORDS = (
    "payfast",
    "host africa",
    "rsaweb",
    "rsa web",
    "openserve",
    "dues and subscriptions",
)

FETCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS fnb_fetch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT NOT NULL,
    rows_seen INTEGER,
    inserted INTEGER,
    allocated INTEGER,
    need_recon INTEGER,
    need_recon_amount REAL,
    balance REAL,
    ok INTEGER,
    note TEXT
);
CREATE TABLE IF NOT EXISTS fnb_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT NOT NULL,
    card TEXT,
    description TEXT,
    amount REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_fnb_pending
    ON fnb_pending (COALESCE(paid_on,''), COALESCE(description,''), COALESCE(amount,0));
"""


def _load_env(path: Path = ENV_PATH) -> dict[str, str]:
    data: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            data[key.strip()] = val.strip().strip("'").strip('"')
    for key in ("FNB_USERNAME", "FNB_PASSWORD", "FNB_ACCOUNT_NUMBER"):
        if os.environ.get(key):
            data[key] = os.environ[key]
    return data


def _save_env(data: dict[str, str], path: Path = ENV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = _load_env(path)
    keep.update({k: v for k, v in data.items() if v is not None})
    lines = [f"{k}={keep[k]}" for k in keep if keep.get(k) is not None]
    path.write_text("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def login_ready(env: dict[str, str] | None = None) -> bool:
    env = env or _load_env()
    return bool((env.get("FNB_USERNAME") or "").strip() and (env.get("FNB_PASSWORD") or "").strip())


def save_login(username: str, password: str, account_number: str | None = None) -> dict:
    username = (username or "").strip()
    password = (password or "").strip()
    if not username or not password:
        raise SystemExit("FNB username and password are required")
    _save_env(
        {
            "FNB_USERNAME": username,
            "FNB_PASSWORD": password,
            "FNB_ACCOUNT_NUMBER": (account_number or ACCOUNT).strip() or ACCOUNT,
        }
    )
    return {"ok": True, "ready": True, "via": "fnb-live", "username": username}


def pick_dismiss(labels: list[str]) -> str | None:
    """Choose a safe popup dismiss. Empty list = no popup this login."""
    for raw in labels:
        label = " ".join((raw or "").lower().split())
        if not label:
            continue
        if any(bad in label for bad in UNSAFE_CLICK):
            continue
        if label in SAFE_DISMISS or any(label.startswith(s) or s in label for s in SAFE_DISMISS):
            return raw
    return None


def normalize_desc(text: str | None) -> str:
    blob = " ".join(str(text or "").lower().replace("\u00a0", " ").split())
    if " / " in blob:
        blob = blob.split(" / ", 1)[0]
    return blob.strip()


def row_key(row: dict) -> tuple:
    acct = re.sub(r"\D", "", str(row.get("account_number") or ACCOUNT))
    day = str(row.get("paid_on") or "")[:10]
    amt = round(float(row.get("amount") or 0), 2)
    bal = row.get("balance")
    try:
        bal = round(float(bal), 2) if bal is not None and bal != "" else None
    except (TypeError, ValueError):
        bal = None
    return (acct, day, amt, bal)


def existing_keys(conn: sqlite3.Connection) -> set[tuple]:
    keys: set[tuple] = set()
    try:
        recs = conn.execute(
            """SELECT account_number, paid_on, amount, balance, description, source
               FROM bank_tx WHERE ours=1"""
        )
    except sqlite3.OperationalError:
        return keys
    for rec in recs:
        if (rec[5] or "") in QB_SOURCES:
            continue
        keys.add(
            row_key(
                {
                    "account_number": rec[0],
                    "paid_on": rec[1],
                    "amount": rec[2],
                    "balance": rec[3],
                    "description": rec[4],
                }
            )
        )
    try:
        for rec in conn.execute(
            """SELECT paid_on, amount, balance, payee, memo, source FROM fnb_tx"""
        ):
            if (rec[5] or "") in {"fnb-xls"}:
                keys.add(
                    row_key(
                        {
                            "account_number": ACCOUNT,
                            "paid_on": rec[0],
                            "amount": rec[1],
                            "balance": rec[2],
                            "description": rec[3],
                        }
                    )
                )
            elif (rec[5] or "") in FNB_DIRECT:
                keys.add(
                    row_key(
                        {
                            "account_number": ACCOUNT,
                            "paid_on": rec[0],
                            "amount": rec[1],
                            "balance": rec[2],
                            "description": rec[3],
                        }
                    )
                )
    except sqlite3.OperationalError:
        pass
    return keys


def to_fnb_row(row: dict) -> dict:
    amount = round(float(row.get("amount") or 0), 2)
    desc = (row.get("description") or "").strip()
    payee = desc.split(" / ")[0].strip() if " / " in desc else desc
    memo = desc.split(" / ", 1)[1].strip() if " / " in desc else ""
    return {
        "paid_on": str(row.get("paid_on") or "")[:10],
        "ref": memo,
        "payee": payee,
        "memo": memo,
        "payment": abs(amount) if amount < 0 else 0.0,
        "deposit": amount if amount > 0 else 0.0,
        "amount": amount,
        "balance": row.get("balance"),
        "qb_type": "",
        "account": f"FNB {ACCOUNT}",
        "bank_status": "",
        "source": row.get("source") or "fnb_live",
        "description": desc,
        "account_number": row.get("account_number") or ACCOUNT,
        "account_name": row.get("account_name") or COMPANY["bank_account_name"],
        "ours": 1,
        "filename": row.get("filename") or "fnb-live",
    }


def _live_client(row: dict):
    from billing import CLIENTS, canon_key, client_row

    blob = f"{row.get('payee') or ''} {row.get('memo') or ''} {row.get('description') or ''}"
    hit = client_row(blob)
    if hit:
        return hit
    words = [
        w
        for w in re.findall(r"[A-Za-z']+", blob)
        if w.lower() not in BANK_WORDS and len(w) > 1
    ]
    for guess in ((" ".join(words[-2:]) if len(words) >= 2 else ""), words[-1] if words else ""):
        if not guess:
            continue
        hit = client_row(guess)
        if hit:
            return hit
        key = canon_key(guess)
        hits = [c for c in CLIENTS if key and key in canon_key(c["name"])]
        if len(hits) == 1:
            return hits[0]
    return None


def allocate_live(row: dict) -> dict:
    from recon import _fnb_alloc

    alloc = _fnb_alloc(row)
    blob = f"{row.get('payee') or ''} {row.get('memo') or ''} {row.get('description') or ''}".lower()
    client = _live_client(row)
    if alloc.get("alloc_kind") == "unallocated" and client and (row.get("deposit") or 0) > 0.004:
            from billing import canon_key

            return {
                "alloc_kind": "client_paid",
                "alloc_to": client["name"],
                "alloc_key": canon_key(client["name"]),
                "result": "paid",
            }
    if alloc.get("alloc_kind") == "unallocated":
        if any(w in blob for w in FEE_WORDS):
            return {
                "alloc_kind": "fee",
                "alloc_to": "FNB bank charge",
                "alloc_key": "",
                "result": "allocated",
            }
        if any(w in blob for w in EXPENSE_WORDS):
            return {
                "alloc_kind": "expense",
                "alloc_to": row.get("payee") or row.get("description"),
                "alloc_key": "",
                "result": "allocated",
            }
        if "netcash" in blob:
            return {
                "alloc_kind": "clearing",
                "alloc_to": "Netcash",
                "alloc_key": "",
                "result": "allocated",
            }
        if (row.get("deposit") or 0) > 0.004:
            return {
                "alloc_kind": "deposit",
                "alloc_to": row.get("payee") or "FNB credit",
                "alloc_key": "",
                "result": "need-recon",
                "what": f"{row.get('payee') or row.get('description') or 'Unknown credit'} · needs recon",
            }
    return alloc


def insert_new(conn: sqlite3.Connection, rows: list[dict]) -> dict:
    """Add only rows not already on the FNB tables. Allocate each new one."""
    from books import ensure_tables
    from recon import ensure as ensure_fnb

    ensure_tables(conn)
    ensure_fnb(conn)
    have = existing_keys(conn)
    inserted = 0
    allocated = 0
    attention: list[dict] = []
    for raw in rows:
        if (raw.get("source") or "") in QB_SOURCES:
            continue
        rec = to_fnb_row(raw)
        key = row_key(rec)
        if key in have:
            continue
        have.add(key)
        alloc = allocate_live(rec)
        rec.update(alloc)
        conn.execute(
            """INSERT OR IGNORE INTO bank_tx
               (account_number, account_name, ours, paid_on, amount, balance, description, source, filename)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                rec["account_number"],
                rec["account_name"],
                1,
                rec["paid_on"],
                rec["amount"],
                rec.get("balance"),
                rec.get("description"),
                rec.get("source") or "fnb_live",
                rec.get("filename"),
            ),
        )
        conn.execute(
            """INSERT OR IGNORE INTO fnb_tx
               (paid_on, ref, payee, memo, payment, deposit, amount, balance, qb_type,
                account, bank_status, alloc_kind, alloc_to, alloc_key, result, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rec["paid_on"],
                rec.get("ref"),
                rec.get("payee"),
                rec.get("memo"),
                rec.get("payment"),
                rec.get("deposit"),
                rec["amount"],
                rec.get("balance"),
                rec.get("qb_type"),
                rec.get("account"),
                rec.get("bank_status"),
                alloc["alloc_kind"],
                alloc["alloc_to"],
                alloc.get("alloc_key") or "",
                alloc["result"],
                rec.get("source") or "fnb_live",
            ),
        )
        inserted += 1
        if alloc.get("result") == "allocated":
            allocated += 1
        else:
            attention.append(
                {
                    "paid_on": rec["paid_on"],
                    "description": rec.get("description"),
                    "amount": rec["amount"],
                    "kind": alloc.get("alloc_kind") or "unallocated",
                    "what": alloc.get("what")
                    or alloc.get("alloc_to")
                    or rec.get("payee")
                    or "Needs recon",
                }
            )
    conn.commit()
    return {
        "inserted": inserted,
        "allocated": allocated,
        "need_recon": len(attention),
        "need_recon_amount": round(sum(abs(float(a["amount"])) for a in attention), 2),
        "attention": attention,
    }


def record_live_card(balance, available=None, note: str = "FNB account card", conn=None) -> None:
    """Write FNB's own Available/Balance the moment we see the account card."""
    if balance is None:
        return
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    own = conn
    try:
        if own is None:
            own = sqlite3.connect(os.environ.get("UPP_DB", DB), timeout=60)
            own.execute("PRAGMA busy_timeout=60000")
        own.executescript(FETCH_SCHEMA)
        own.execute(
            """INSERT INTO fnb_fetch
               (fetched_at, rows_seen, inserted, allocated, need_recon, need_recon_amount,
                balance, ok, note)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (fetched_at, 0, 0, 0, 0, 0.0, float(balance), 1, note),
        )
        if conn is None:
            own.commit()
            own.close()
        else:
            own.commit()
    except sqlite3.Error:
        if conn is None and own is not None:
            try:
                own.close()
            except sqlite3.Error:
                pass
        return
    set_progress(
        f"Bank {balance}" + (f" · Available {available}" if available is not None else "")
    )


def _record_fetch(conn: sqlite3.Connection, pack: dict) -> None:
    conn.executescript(FETCH_SCHEMA)
    conn.execute(
        """INSERT INTO fnb_fetch
           (fetched_at, rows_seen, inserted, allocated, need_recon, need_recon_amount,
            balance, ok, note)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            pack.get("fetched_at"),
            pack.get("rows_seen") or 0,
            pack.get("inserted") or 0,
            pack.get("allocated") or 0,
            pack.get("need_recon") or 0,
            pack.get("need_recon_amount") or 0,
            pack.get("balance"),
            1 if pack.get("ok") else 0,
            pack.get("note") or "",
        ),
    )
    conn.commit()


def last_live_figures(conn: sqlite3.Connection) -> dict:
    """Last figures actually read off the FNB Online account card.

    QuickBooks bank writes the same FNB table. It must not overwrite a newer
    Online card when QB is still old.
    """
    try:
        rec = conn.execute(
            """SELECT fetched_at, balance, ok, note FROM fnb_fetch
               WHERE balance IS NOT NULL
                 AND note LIKE 'FNB account card%'
               ORDER BY id DESC LIMIT 1"""
        ).fetchone()
    except sqlite3.OperationalError:
        return {}
    if not rec:
        return {}
    return {"fetched_at": rec[0], "balance": rec[1], "ok": bool(rec[2]), "note": rec[3]}


def last_fetch(conn: sqlite3.Connection | None = None) -> dict | None:
    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB))
    try:
        own.executescript(FETCH_SCHEMA)
        rec = own.execute(
            """SELECT fetched_at, rows_seen, inserted, allocated, need_recon,
                      need_recon_amount, balance, ok, note
               FROM fnb_fetch ORDER BY id DESC LIMIT 1"""
        ).fetchone()
    except sqlite3.OperationalError:
        rec = None
    if conn is None:
        own.close()
    if not rec:
        return None
    return {
        "fetched_at": rec[0],
        "rows_seen": rec[1],
        "inserted": rec[2],
        "allocated": rec[3],
        "need_recon": rec[4],
        "need_recon_amount": rec[5],
        "balance": rec[6],
        "ok": bool(rec[7]),
        "note": rec[8],
    }


def attention_open(conn: sqlite3.Connection) -> list[dict]:
    out = []
    try:
        for rec in conn.execute(
            """SELECT id, paid_on, payee, memo, amount, alloc_kind, alloc_to, result
               FROM fnb_tx
               WHERE source IN ('fnb_live','fnb_online','fnb_api','fnb_history','fnb_qb')
                 AND (result='need-recon' OR alloc_kind='unallocated')
               ORDER BY paid_on DESC, id DESC LIMIT 40"""
        ):
            out.append(
                {
                    "id": rec[0],
                    "paid_on": rec[1],
                    "description": " / ".join(p for p in (rec[2], rec[3]) if p),
                    "amount": rec[4],
                    "kind": rec[5],
                    "what": rec[6] or "Needs recon",
                }
            )
    except sqlite3.OperationalError:
        return []
    return out


def _frame_ok(frame) -> bool:
    try:
        url = frame.url or ""
    except Exception:
        return False
    junk = ("doubleclick", "googletag", "metrics.fnb", "fls.doubleclick", "facebook", "hotjar")
    return not any(x in url for x in junk)


def _all_text(page) -> str:
    bits = []
    frames = []
    try:
        frames = list(page.frames)
    except Exception:
        frames = []
    if not frames:
        frames = [page]
    for frame in frames:
        if not _frame_ok(frame):
            continue
        try:
            bits.append(frame.inner_text("body"))
        except Exception:
            continue
    return "\n".join(bits)


def _stay_online(page, logged_in: bool = False) -> bool:
    """Stay on Online Banking. Public fnb.co.za is not a fetch."""
    try:
        url = page.url or ""
    except Exception:
        return False
    if "online.fnb.co.za" in url and "validate.perfdrive.com" not in url:
        return False
    dest = ONLINE_BANK if logged_in else LOGIN_URLS[0]
    set_progress("Opening FNB Online")
    try:
        page.goto(dest, wait_until="domcontentloaded", timeout=45000)
        return True
    except Exception:
        return False


def _looks_blocked(text: str, url: str = "") -> bool:
    blob = f"{text or ''} {url or ''}".lower()
    return any(
        w in blob
        for w in (
            "please solve this captcha",
            "validate.perfdrive.com",
            "i am human",
            "before granting access",
            "shieldsquare",
        )
    )


def _display_alive(display: str) -> bool:
    env = os.environ.copy()
    env["DISPLAY"] = display
    xdpy = shutil.which("xdpyinfo")
    if xdpy:
        try:
            return subprocess.run(
                [xdpy, "-display", display],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    return Path(f"/tmp/.X{display.lstrip(':')}-lock").exists() and bool(
        subprocess.run(["pgrep", "-f", f"Xvfb {display}"], stdout=subprocess.DEVNULL).returncode == 0
        if shutil.which("pgrep")
        else Path(f"/tmp/.X{display.lstrip(':')}-lock").exists()
    )


def _ensure_display() -> str:
    """Headed Chrome on the box — FNB blocks HeadlessChrome. Own login only."""
    display = (os.environ.get("FNB_DISPLAY") or os.environ.get("DISPLAY") or ":99").strip() or ":99"
    if _display_alive(display):
        os.environ["DISPLAY"] = display
        return display
    xvfb = shutil.which("Xvfb")
    if not xvfb:
        os.environ.pop("DISPLAY", None)
        return ""
    lock = Path(f"/tmp/.X{display.lstrip(':')}-lock")
    if lock.exists() and not _display_alive(display):
        try:
            lock.unlink()
        except OSError:
            pass
    try:
        subprocess.Popen(
            [xvfb, display, "-screen", "0", "1400x900x24", "-nolisten", "tcp", "-ac"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        os.environ.pop("DISPLAY", None)
        return ""
    for _ in range(20):
        time.sleep(0.15)
        if _display_alive(display):
            os.environ["DISPLAY"] = display
            return display
    os.environ.pop("DISPLAY", None)
    return ""


def _clear_stale_chrome() -> None:
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        path = PROFILE_DIR / name
        try:
            path.unlink()
        except OSError:
            pass


def _open_browser(pw):
    """Own FNB Online login. Real Chrome when present, headed, keep the session."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(PROFILE_DIR, 0o700)
    except OSError:
        pass
    _clear_stale_chrome()
    display = _ensure_display()
    if not display:
        raise RuntimeError("FNB browser needs Xvfb on the box")
    kwargs = {
        "headless": False,
        "viewport": {"width": 1400, "height": 900},
        "user_agent": BROWSER_UA,
        "locale": "en-ZA",
        "timezone_id": "Africa/Johannesburg",
        "ignore_https_errors": False,
        "args": [
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
        ],
        "ignore_default_args": ["--enable-automation"],
    }
    last = None
    for channel in ("chrome", "chromium", None):
        try:
            extra = {"channel": channel} if channel else {}
            return pw.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                **extra,
                **kwargs,
            )
        except Exception as exc:
            last = exc
            _clear_stale_chrome()
    raise last or RuntimeError("FNB browser failed to open")


def _dump_page(page, label: str) -> None:
    text = _all_text(page)
    text = re.sub(r"(password|pin|otp)[:\s]+\S+", r"\1: ***", text, flags=re.I)
    url = ""
    try:
        url = page.url
    except Exception:
        url = ""
    frames = []
    try:
        frames = [f.url for f in page.frames]
    except Exception:
        frames = []
    try:
        DUMP_PATH.write_text(f"{label}\nURL {url}\nFRAMES {frames}\n\n{text[:80000]}")
    except OSError:
        pass
    try:
        page.screenshot(path="/tmp/fnb-last.png", full_page=True, timeout=3000)
    except Exception:
        pass


def _first_visible(page, selector: str, timeout: int = 8000):
    deadline = time.time() + timeout / 1000.0
    while time.time() < deadline:
        frames = []
        try:
            frames = list(page.frames)
        except Exception:
            frames = []
        if not frames:
            frames = [page]
        for frame in frames:
            if not _frame_ok(frame):
                continue
            try:
                loc = frame.locator(selector)
                n = loc.count()
            except Exception:
                continue
            for i in range(min(n, 12)):
                el = loc.nth(i)
                try:
                    if el.is_visible():
                        return el
                except Exception:
                    continue
        try:
            page.wait_for_timeout(250)
        except Exception:
            break
    return None


def _username_box(page):
    el = _first_visible(page, USER_SEL, timeout=12000)
    if el:
        return el
    frames = []
    try:
        frames = list(page.frames)
    except Exception:
        frames = []
    for frame in frames:
        try:
            if frame.locator("input[type='password']").count() == 0:
                continue
        except Exception:
            continue
        for sel in ("input[type='text']", "input[type='email']", "input[type='tel']", "input:not([type])"):
            try:
                loc = frame.locator(sel)
                n = loc.count()
            except Exception:
                continue
            for i in range(min(n, 8)):
                cand = loc.nth(i)
                try:
                    if cand.is_visible():
                        return cand
                except Exception:
                    continue
    return None


def _looks_logged_in(text: str, account: str) -> bool:
    blob = (text or "").lower()
    digits = re.sub(r"\D", "", account or "")
    if digits and digits[-4:] in re.sub(r"\D", "", text or ""):
        return True
    return any(
        w in blob
        for w in (
            "transaction history",
            "live statement",
            "successful",
            "pending transactions",
            "gowifi",
            "available balance",
            "account summary",
            "devices and browsers",
            "my bank accounts",
            "business solutions",
            "integration channel",
        )
    )


def page_kind(text: str, account: str = ACCOUNT) -> str:
    """After login FNB is not always the same page. Skip / accounts / statement vary."""
    blob = (text or "").lower()
    digits = re.sub(r"\D", "", account or "")
    body_digits = re.sub(r"\D", "", text or "")
    if "devices and browsers" in blob or ("manage devices" in blob and "skip" in blob):
        return "devices"
    if "successful" in blob and "pending" in blob and ("description" in blob or "amount" in blob):
        return "statement"
    if digits and digits in body_digits and ("available" in blob or "gowifi fnb main" in blob):
        return "accounts"
    if "integration channel" in blob or "transaction history" in blob and "subscribe" in blob:
        return "channel"
    if "my bank accounts" in blob or "welcome" in blob:
        return "welcome"
    return "other"


def parse_account_card(text: str, account: str = ACCOUNT) -> dict:
    """Balance then Available on My Bank Accounts. Do not invent."""
    digits = re.sub(r"\D", "", account or "")
    blob = " ".join((text or "").replace("\u00a0", " ").split())
    money = r"R\s*([\d]+(?:[ ,]\d{3})*\.\d{2})"
    if digits:
        m = re.search(rf"{digits}\s+{money}\s+{money}", blob, re.I)
        if m:
            return {
                "balance": float(m.group(1).replace(" ", "").replace(",", "")),
                "available": float(m.group(2).replace(" ", "").replace(",", "")),
            }
    m = re.search(rf"available(?:\s+balance)?\s*{money}", blob, re.I)
    b = re.search(rf"(?:(?<!available )balance)\s*{money}", blob, re.I)
    out = {"balance": None, "available": None}
    if b:
        out["balance"] = float(b.group(1).replace(" ", "").replace(",", ""))
    if m:
        out["available"] = float(m.group(1).replace(" ", "").replace(",", ""))
    return out


def keys_from_channel_text(text: str) -> dict:
    """Read Client ID / Secret off the Integration Channel page. Never log the secret."""
    blob = text or ""
    cid = re.search(r"client\s*id\s*[:#]?\s*([A-Za-z0-9._-]{12,})", blob, re.I)
    secret = re.search(r"client\s*secret\s*[:#]?\s*([A-Za-z0-9._-]{12,})", blob, re.I)
    return {
        "client_id": cid.group(1) if cid else "",
        "client_secret": secret.group(1) if secret else "",
    }


def _dismiss_popups(page) -> int:
    """Login sometimes has a popup, sometimes not. Never fail if none."""
    closed = 0
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    for _ in range(4):
        labels = []
        frames = []
        try:
            frames = list(page.frames)
        except Exception:
            frames = [page]
        for frame in frames:
            try:
                labels.extend(
                    frame.locator(
                        "button, [role='button'], a, [aria-label='Close'], .close, .modal-close"
                    ).all_text_contents()
                )
            except Exception:
                pass
            try:
                labels.extend(
                    frame.locator("[aria-label]").evaluate_all(
                        "els => els.map(e => e.getAttribute('aria-label') || '')"
                    )
                )
            except Exception:
                pass
        choice = pick_dismiss(labels)
        if not choice:
            break
        clicked = False
        for frame in frames:
            try:
                loc = frame.get_by_role("button", name=re.compile(re.escape(choice), re.I))
                if loc.count():
                    loc.first.click(timeout=1500)
                    closed += 1
                    clicked = True
                    page.wait_for_timeout(400)
                    break
            except Exception:
                pass
            try:
                frame.locator("button, [aria-label='Close'], .close").filter(
                    has_text=re.compile(re.escape(choice), re.I)
                ).first.click(timeout=1500)
                closed += 1
                clicked = True
                page.wait_for_timeout(400)
                break
            except Exception:
                continue
        if not clicked:
            break
    return closed


def _fill_login(page, username: str, password: str) -> None:
    """Wait for FNB's real form (SPA / iframe). Do not hang 30s on a missing label."""
    set_progress("Looking for FNB login")
    if _first_visible(page, "input[type='password']", timeout=2000) is None:
        _click_named(page, ("Log on", "Log in", "Login", "Sign in"))
        page.wait_for_timeout(800)
        _dismiss_popups(page)
    user_el = _username_box(page)
    if not user_el:
        _dump_page(page, "no-username")
        raise RuntimeError("FNB login form not on the page")
    set_progress("Typing FNB username")
    user_el.fill(username, timeout=5000)
    pass_el = _first_visible(page, "input[type='password'], input[name='password'], input#password", timeout=8000)
    if not pass_el:
        _dump_page(page, "no-password")
        raise RuntimeError("FNB password field not on the page")
    set_progress("Typing FNB password")
    pass_el.fill(password, timeout=5000)
    set_progress("Submitting FNB login")
    clicked = _click_named(page, ("Log on", "Log in", "Login", "Sign in", "Continue"))
    if not clicked:
        try:
            pass_el.press("Enter")
        except Exception:
            pass


def _wait_after_login(page, account: str) -> None:
    set_progress("Waiting for FNB after login")
    for i in range(40):
        try:
            page.wait_for_timeout(2000)
        except Exception:
            break
        if "www.fnb.co.za" in ((getattr(page, "url", "") or "")) and "online.fnb.co.za" not in (page.url or ""):
            set_progress("Back to FNB Online")
            _stay_online(page, logged_in=_looks_logged_in(_all_text(page), account))
        _dismiss_popups(page)
        text = _all_text(page)
        low = text.lower()
        if any(w in low for w in PHONE_CONFIRM) and not _looks_logged_in(text, account):
            set_progress(f"Waiting for FNB phone confirm ({(i + 1) * 2}s)")
            continue
        if _looks_logged_in(text, account):
            set_progress("Logged in to FNB")
            return
        if _first_visible(page, "input[type='password']", timeout=200) is None and i > 3:
            set_progress("Logged in to FNB")
            return
    _dump_page(page, "after-login")


def _skip_devices(page) -> bool:
    text = _all_text(page)
    if page_kind(text) != "devices":
        return False
    set_progress("Skip devices")
    return _click_named(page, ("Skip",))


def _latest_page(page):
    try:
        pages = [p for p in page.context.pages if not p.is_closed()]
    except Exception:
        return page
    return pages[-1] if pages else page


def _wait_kind(page, account: str, want: str, timeout_ms: int = 8000) -> bool:
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        if page_kind(_all_text(page), account) == want:
            return True
        try:
            page.wait_for_timeout(400)
        except Exception:
            return False
    return False


def _click_account_register(page, account: str) -> bool:
    """Live Successful/Pending register. Not Email / eZi / recreated statements."""
    digits = re.sub(r"\D", "", account or "")
    names = (
        "Gowifi FNB Main",
        "GoWifi FNB Main",
        digits[-8:] if len(digits) >= 8 else digits,
        digits,
        "Successful",
        "Successful transactions",
    )
    if _click_named(page, tuple(n for n in names if n)):
        return True
    frames = []
    try:
        frames = list(page.frames)
    except Exception:
        frames = [page]
    for frame in frames:
        try:
            loc = frame.locator("a, button, [role='button'], [role='link']").filter(
                has_text=re.compile(r"^Statements?$", re.I)
            )
            n = loc.count()
        except Exception:
            continue
        for i in range(min(n, 6)):
            el = loc.nth(i)
            try:
                nearby = (el.inner_text() or "") + " "
                if re.search(r"email|recreated|ezi|older than", nearby, re.I):
                    continue
                el.click(timeout=2000)
                return True
            except Exception:
                continue
    return False


def _wait_text(page, needles: tuple[str, ...], timeout_ms: int = 8000) -> bool:
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        blob = _all_text(page).lower()
        if any((n or "").lower() in blob for n in needles if n):
            return True
        try:
            page.wait_for_timeout(400)
        except Exception:
            return False
    return False


def _click_href(page, pattern: str) -> bool:
    """Click a real link. FNB nav is a frameset — text clicks miss the content frame."""
    pat = re.compile(pattern, re.I)
    frames = []
    try:
        frames = list(page.frames)
    except Exception:
        frames = [page]
    for frame in frames:
        if not _frame_ok(frame):
            continue
        try:
            loc = frame.locator("a").filter(has_text=pat)
            if loc.count():
                loc.first.click(timeout=800, force=True)
                return True
        except Exception:
            continue
    return _click_named(page, (pattern,))


def _walk_to_statement(page, account: str) -> dict:
    """Skip → My bank accounts → Gowifi FNB Main → Statements → Successful."""
    balances = {"balance": None, "available": None}
    digits = re.sub(r"\D", "", account or "")
    _skip_devices(page)
    page.wait_for_timeout(400)
    set_progress("My bank accounts")
    _click_href(page, r"My bank accounts")
    _wait_text(page, ("Gowifi FNB Main", "Gowifi", digits[-8:] if len(digits) >= 8 else digits), 8000)
    _skip_devices(page)
    got = parse_account_card(_all_text(page), account)
    if got.get("balance") is not None:
        balances = got
        record_live_card(got.get("balance"), got.get("available"))
        set_progress(f"Bank {got.get('balance')} · Available {got.get('available')}")
    set_progress("Gowifi FNB Main")
    _click_href(page, r"Gowifi FNB Main")
    if not _wait_text(page, ("Successful", "Pending", "Statement"), 5000):
        set_progress("Statements")
        _click_href(page, r"^Statements?$")
        _wait_text(page, ("Successful", "Pending"), 5000)
    if page_kind(_all_text(page), account) != "statement":
        set_progress("Successful")
        _click_href(page, r"Successful")
        _wait_text(page, ("Successful", "Pending", "CUPIDO", digits), 5000)
    if page_kind(_all_text(page), account) == "statement":
        set_progress("On statement")
    return balances


def _open_statement(page, account: str) -> dict:
    return _walk_to_statement(page, account)


def _tag_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        row = dict(row)
        row["source"] = "fnb_live"
        row["account_number"] = row.get("account_number") or ACCOUNT
        row["account_name"] = row.get("account_name") or COMPANY["bank_account_name"]
        row["ours"] = 1
        row["filename"] = "fnb-live"
        out.append(row)
    return out


def _read_page_rows(page) -> list[dict]:
    from books import parse_fnb_history, parse_fnb_online_table

    text = _all_text(page)
    parsed = parse_fnb_online_table(text, "fnb-live")
    rows = parsed.get("rows") or []
    if not rows:
        parsed = parse_fnb_history(text, "fnb-live")
        rows = parsed.get("rows") or []
    if not rows:
        rows = parse_fnb_live_text(text)
    if rows:
        return _tag_rows(rows)
    out = []
    frames = []
    try:
        frames = list(page.frames)
    except Exception:
        frames = [page]
    for frame in frames:
        try:
            tables = frame.locator("table").all()
        except Exception:
            tables = []
        for table in tables:
            try:
                html_text = table.inner_text()
            except Exception:
                continue
            parsed = parse_fnb_online_table(html_text, "fnb-live")
            if parsed.get("rows"):
                out.extend(parsed["rows"])
                continue
            live = parse_fnb_live_text(html_text)
            if live:
                out.extend(live)
                continue
            try:
                for tr in table.locator("tr").all():
                    cells = [c.inner_text().strip() for c in tr.locator("th,td").all()]
                    row = _row_from_cells(cells)
                    if row:
                        out.append(row)
            except Exception:
                continue
        try:
            for row_el in frame.locator("[role=row]").all():
                cells = [
                    c.inner_text().strip()
                    for c in row_el.locator("[role=cell], [role=gridcell], [role=columnheader]").all()
                ]
                row = _row_from_cells(cells)
                if row:
                    out.append(row)
        except Exception:
            continue
    return _tag_rows(out)


def _live_money(raw: str) -> float | None:
    text = (raw or "").replace("\u00a0", " ").strip()
    if not text:
        return None
    cr = bool(re.search(r"\bcr\b", text, re.I))
    dr = bool(re.search(r"\bdr\b", text, re.I))
    m = re.search(r"-?R?\s*([\d]+(?:[ ,]\d{3})*\.\d{2})", text)
    if not m:
        return None
    val = float(m.group(1).replace(" ", "").replace(",", ""))
    if text.lstrip().startswith("-") or dr:
        val = -abs(val)
    elif cr:
        val = abs(val)
    return val


def _live_date(raw: str) -> str | None:
    text = " ".join((raw or "").replace("\u00a0", " ").split())
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})$", text)
    if m:
        mon = {
            "jan": "01",
            "feb": "02",
            "mar": "03",
            "apr": "04",
            "may": "05",
            "jun": "06",
            "jul": "07",
            "aug": "08",
            "sep": "09",
            "oct": "10",
            "nov": "11",
            "dec": "12",
        }.get(m.group(2)[:3].lower())
        if mon:
            return f"{m.group(3)}-{mon}-{int(m.group(1)):02d}"
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), m.group(3)
        if month > 12 and day <= 12:
            day, month = month, day
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year}-{month:02d}-{day:02d}"
    m = re.match(r"^(\d{4})[/-](\d{2})[/-](\d{2})$", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def _live_date_prefix(line: str) -> tuple[str | None, str]:
    text = (line or "").replace("\u00a0", " ").strip()
    m = re.match(
        r"^(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})",
        text,
    )
    if not m:
        return None, text
    return _live_date(m.group(1)), text[m.end() :].strip()


def _row_from_cells(cells: list[str]) -> dict | None:
    if len(cells) < 3:
        return None
    day = None
    day_i = None
    for i, cell in enumerate(cells):
        got = _live_date(cell)
        if got:
            day, day_i = got, i
            break
    if not day:
        return None
    monies = []
    for i, cell in enumerate(cells):
        if i == day_i:
            continue
        if not re.search(r"\.\d{2}", cell.replace(",", "")):
            continue
        val = _live_money(cell)
        if val is not None:
            monies.append((i, val))
    if len(monies) < 2:
        return None
    amount, balance = monies[-2][1], monies[-1][1]
    skip = {day_i, monies[-2][0], monies[-1][0]}
    desc = " ".join(cells[i] for i in range(len(cells)) if i not in skip and cells[i] and _live_money(cells[i]) is None)
    if not desc or desc.lower() in {"description", "details", "what"}:
        return None
    return {
        "paid_on": day,
        "amount": amount,
        "balance": balance,
        "description": desc,
        "source": "fnb_live",
    }


def parse_fnb_live_text(text: str) -> list[dict]:
    """FNB register as one line or 4 stacked cells. Not the old 6-line paste only."""
    lines = [ln.replace("\u00a0", " ").rstrip() for ln in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    rows: list[dict] = []
    i = 0
    while i < len(lines):
        day = _live_date(lines[i].strip())
        if not day:
            i += 1
            continue
        block = [ln.strip() for ln in lines[i + 1 : i + 6]]
        if len(block) >= 5:
            amount = _live_money(block[3])
            balance = _live_money(block[4])
            if amount is not None and balance is not None and _live_date(block[0]) is None:
                desc = block[0]
                if block[1]:
                    desc = f"{desc} / {block[1]}".strip(" /")
                rows.append(
                    {
                        "paid_on": day,
                        "amount": amount,
                        "balance": balance,
                        "description": desc,
                        "source": "fnb_live",
                    }
                )
                i += 6
                continue
        if len(block) >= 3:
            amount = _live_money(block[1])
            balance = _live_money(block[2])
            if amount is not None and balance is not None and block[0] and _live_money(block[0]) is None:
                rows.append(
                    {
                        "paid_on": day,
                        "amount": amount,
                        "balance": balance,
                        "description": block[0],
                        "source": "fnb_live",
                    }
                )
                i += 4
                continue
        i += 1
    if rows:
        return rows
    money_re = re.compile(r"-?R?\s*[\d]+(?:[ ,]\d{3})*\.\d{2}")
    for raw in lines:
        day, rest = _live_date_prefix(raw)
        if not day or not rest:
            continue
        rest = re.sub(r"^\d{1,2}:\d{2}(?::\d{2})?\s+", "", rest)
        hits = list(money_re.finditer(rest))
        if len(hits) < 2:
            continue
        amount = _live_money(hits[-2].group())
        balance = _live_money(hits[-1].group())
        desc = rest[: hits[-2].start()].strip()
        if amount is None or balance is None or not desc:
            continue
        if desc.lower() in {"description", "details", "amount", "balance", "date"}:
            continue
        rows.append(
            {
                "paid_on": day,
                "amount": amount,
                "balance": balance,
                "description": desc,
                "source": "fnb_live",
            }
        )
    return rows


def parse_balances(text: str) -> dict:
    """Posted balance first. Available is after pending."""
    blob = " ".join((text or "").replace("\u00a0", " ").split())
    money = r"R?\s*([\d]+(?:[ ,]\d{3})*(?:\.\d{2})?)"
    available = None
    balance = None
    av = re.search(r"available(?:\s+balance)?\s*[:=]?\s*" + money, blob, re.I)
    bal = re.search(r"(?:current|ledger|posted)?\s*balance\s*[:=]?\s*" + money, blob, re.I)
    if av:
        available = float(av.group(1).replace(" ", "").replace(",", ""))
    if bal:
        balance = float(bal.group(1).replace(" ", "").replace(",", ""))
    return {"balance": balance, "available": available}


def parse_pending_table(text: str) -> list[dict]:
    """Pending card table: date/time, card, description, amount. Not posted."""
    out = []
    for raw in (text or "").replace("\u00a0", " ").splitlines():
        line = " ".join(raw.split())
        if not line:
            continue
        m = re.search(
            r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})"
            r"(?:\s+(\d{1,2}:\d{2}(?::\d{2})?))?"
            r"(?:\s+(\d{4,6}\*+\d+))?"
            r"\s+(.+?)\s+(-?[\d,.]+)$",
            line,
        )
        if not m:
            continue
        day, clock, card, desc = m.group(1), m.group(2) or "", m.group(3) or "", (m.group(4) or "").strip()
        paid_on = day
        if "/" in day:
            p = day.split("/")
            if len(p) == 3 and len(p[2]) == 4:
                paid_on = f"{p[2]}-{int(p[1]):02d}-{int(p[0]):02d}"
        elif re.match(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", day):
            try:
                paid_on = datetime.strptime(day, "%d %B %Y").strftime("%Y-%m-%d")
            except ValueError:
                try:
                    paid_on = datetime.strptime(day, "%d %b %Y").strftime("%Y-%m-%d")
                except ValueError:
                    paid_on = day
        if clock:
            paid_on = f"{paid_on} {clock}"
        try:
            amount = -abs(float(m.group(5).replace(",", "")))
        except ValueError:
            continue
        if desc.lower() in {"description", "amount"}:
            continue
        if card and card not in desc:
            desc = f"{desc} / {card}"
        out.append(
            {
                "paid_on": paid_on,
                "card": card,
                "description": desc,
                "amount": amount,
                "what": "Pending · not posted",
            }
        )
    return out


def _click_named(page, names: tuple[str, ...]) -> bool:
    frames = []
    try:
        frames = list(page.frames)
    except Exception:
        frames = [page]
    if page not in frames:
        frames = [page, *frames]
    for name in names:
        if not name or name.lower() in {"accounts", "account", "statement"}:
            continue
        pat = re.compile(rf"^{re.escape(name)}$", re.I)
        for frame in frames:
            for role in ("tab", "link", "button"):
                try:
                    loc = frame.get_by_role(role, name=pat)
                    if loc.count():
                        loc.first.click(timeout=800, force=True)
                        return True
                except Exception:
                    continue
            try:
                loc = frame.get_by_text(pat)
                if loc.count():
                    loc.first.click(timeout=800, force=True)
                    return True
            except Exception:
                continue
    return False


def replace_pending(conn: sqlite3.Connection, rows: list[dict]) -> list[dict]:
    conn.executescript(FETCH_SCHEMA)
    conn.execute("DELETE FROM fnb_pending")
    for row in rows:
        conn.execute(
            """INSERT OR IGNORE INTO fnb_pending (paid_on, card, description, amount)
               VALUES (?,?,?,?)""",
            (row.get("paid_on"), row.get("card") or "", row.get("description") or "", row.get("amount")),
        )
    conn.commit()
    return pending_open(conn)


def pending_open(conn: sqlite3.Connection) -> list[dict]:
    out = []
    try:
        for rec in conn.execute(
            "SELECT paid_on, card, description, amount FROM fnb_pending ORDER BY paid_on DESC, id DESC"
        ):
            out.append(
                {
                    "paid_on": rec[0],
                    "card": rec[1],
                    "description": rec[2],
                    "amount": rec[3],
                    "what": "Pending · not posted",
                }
            )
    except sqlite3.OperationalError:
        return []
    return out


def allocate_choices() -> list[dict]:
    from billing import SERVICE_CLIENTS

    out = [{"kind": "client_paid", "to": c["name"], "label": c["name"]} for c in SERVICE_CLIENTS]
    out.extend(
        (
            {"kind": "fee", "to": "FNB bank charge", "label": "Bank charge"},
            {"kind": "expense", "to": "Expense", "label": "Expense"},
            {"kind": "deposit", "to": "Deposit", "label": "Deposit"},
        )
    )
    return out


def apply_alloc(conn: sqlite3.Connection, tx_id: int, kind: str, to: str) -> dict:
    from billing import canon_key, client_row

    kind = (kind or "").strip()
    to = (to or "").strip()
    if kind == "client_paid":
        hit = client_row(to)
        to = (hit or {}).get("name") or to
        key = canon_key(to)
        result = "paid"
    elif kind in {"fee", "expense", "deposit", "clearing"}:
        key = ""
        result = "allocated"
    else:
        return {"ok": False, "error": "Unknown allocate choice"}
    conn.execute(
        """UPDATE fnb_tx SET alloc_kind=?, alloc_to=?, alloc_key=?, result=? WHERE id=?""",
        (kind, to, key, result, int(tx_id)),
    )
    conn.commit()
    return {"ok": True, "id": int(tx_id), "kind": kind, "to": to}


def ensure_channel_keys(env: dict[str, str] | None = None) -> dict:
    """Subscribe On my own behalf and save Client ID/Secret. Same path Sage/Xero use."""
    env = env or _load_env()
    if (env.get("FNB_CLIENT_ID") or "").strip() and (env.get("FNB_CLIENT_SECRET") or "").strip():
        return {"ok": True, "has_api": True, "note": "keys already on the box"}
    user = (env.get("FNB_USERNAME") or "").strip()
    password = (env.get("FNB_PASSWORD") or "").strip()
    if not user or not password:
        return {"ok": False, "has_api": False, "note": "need FNB login to open Integration Channel"}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": False, "has_api": False, "note": "playwright not installed on the box"}
    found = {"client_id": "", "client_secret": ""}
    set_progress("Opening FNB Integration Channel")
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
        except Exception as exc:
            return {"ok": False, "has_api": False, "note": f"fnb browser: {exc}"}
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        try:
            for url in LOGIN_URLS:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(1000)
                    _fill_login(page, user, password)
                    break
                except Exception:
                    continue
            _wait_after_login(page, env.get("FNB_ACCOUNT_NUMBER") or ACCOUNT)
            _skip_devices(page)
            page.wait_for_timeout(800)
            set_progress("Business solutions")
            _click_named(page, ("Business solutions", "Business Solutions"))
            page.wait_for_timeout(800)
            set_progress("Integration Channel")
            _click_named(page, ("Integration Channel", "Get Started"))
            page.wait_for_timeout(1000)
            _click_named(page, ("API",))
            page.wait_for_timeout(600)
            _click_named(page, ("Transaction History", "Transaction history"))
            page.wait_for_timeout(600)
            found = keys_from_channel_text(_all_text(page))
            if not (found["client_id"] and found["client_secret"]):
                set_progress("Subscribe On my own behalf")
                _click_named(page, ("Subscribe",))
                page.wait_for_timeout(700)
                _click_named(page, ("On my own behalf", "On my own behalf "))
                page.wait_for_timeout(500)
                _click_named(page, ("REST API", "REST"))
                page.wait_for_timeout(800)
                found = keys_from_channel_text(_all_text(page))
            if found["client_id"] and found["client_secret"]:
                _save_env(
                    {
                        "FNB_CLIENT_ID": found["client_id"],
                        "FNB_CLIENT_SECRET": found["client_secret"],
                        "FNB_ACCOUNT_NUMBER": (env.get("FNB_ACCOUNT_NUMBER") or ACCOUNT),
                    }
                )
                set_progress("Saved FNB API keys")
                browser.close()
                return {"ok": True, "has_api": True, "note": "Integration Channel keys saved"}
            _dump_page(page, "channel-no-keys")
            set_progress("No Client ID on Integration Channel")
        except Exception as exc:
            set_progress("Integration Channel failed", error=str(exc)[:180])
            _dump_page(page, "channel-failed")
            browser.close()
            return {"ok": False, "has_api": False, "note": str(exc)[:180]}
        browser.close()
    return {"ok": False, "has_api": False, "note": "Client ID not on Integration Channel page"}


def fetch_live(env: dict[str, str] | None = None) -> dict:
    env = env or _load_env()
    user = (env.get("FNB_USERNAME") or "").strip()
    password = (env.get("FNB_PASSWORD") or "").strip()
    account = (env.get("FNB_ACCOUNT_NUMBER") or ACCOUNT).strip()
    if not user or not password:
        set_progress("Need FNB login on the box", done=True, error="no login")
        return {"ok": False, "error": "FNB username/password missing in /root/secrets/fnb.env", "rows": []}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        set_progress("Playwright missing", done=True, error="playwright")
        return {"ok": False, "error": "playwright not installed on the box", "rows": []}
    rows: list[dict] = []
    pending: list[dict] = []
    balances = {"balance": None, "available": None}
    note = ""
    set_progress("Opening FNB")
    with sync_playwright() as pw:
        try:
            context = _open_browser(pw)
            page = context.pages[0] if context.pages else context.new_page()
            page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        except Exception as exc:
            set_progress("FNB browser failed", done=True, error=str(exc)[:180])
            return {"ok": False, "error": f"fnb browser: {exc}", "rows": [], "pending": []}
        last = LOGIN_URLS[0]
        logged = False
        try:
            set_progress("Opening FNB login")
            page.goto(LOGIN_URLS[0], wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1800)
            _stay_online(page, logged_in=False)
            _dismiss_popups(page)
            if _looks_blocked(_all_text(page), page.url):
                raise RuntimeError("FNB asked for CAPTCHA")
            if _looks_logged_in(_all_text(page), account):
                set_progress("Already logged in to FNB")
                logged = True
            else:
                set_progress("Logging in")
                _fill_login(page, user, password)
                logged = True
        except Exception as exc:
            last = f"{LOGIN_URLS[0]}: {exc}"
            _dump_page(page, "login-fail")
        try:
            if not logged:
                raise RuntimeError(last or "FNB login form not on the page")
            _wait_after_login(page, account)
            _stay_online(page, logged_in=True)
            set_progress("Checking popup")
            _dismiss_popups(page)
            page.wait_for_timeout(400)
            _skip_devices(page)
            page.wait_for_timeout(400)
            got = _walk_to_statement(page, account)
            if got.get("balance") is not None:
                balances.update(got)
            page = _latest_page(page)
            _dismiss_popups(page)
            set_progress("Reading posted")
            _click_named(page, ("Successful", "Posted", "Successful transactions", "Transactions"))
            page.wait_for_timeout(900)
            rows = _read_page_rows(page)
            if not rows:
                set_progress("No rows yet · still reading FNB")
                page.wait_for_timeout(2000)
                rows = _read_page_rows(page)
            parsed_bal = parse_balances(_all_text(page))
            if parsed_bal.get("balance") is not None or parsed_bal.get("available") is not None:
                for key, val in parsed_bal.items():
                    if val is not None:
                        balances[key] = val
            set_progress(f"Posted {len(rows)} · reading pending")
            _click_named(page, ("Pending", "Pending transactions"))
            page.wait_for_timeout(800)
            _dismiss_popups(page)
            pending = parse_pending_table(_all_text(page))
            if not pending:
                for frame in list(getattr(page, "frames", []) or []):
                    try:
                        for table in frame.locator("table").all():
                            pending.extend(parse_pending_table(table.inner_text()))
                    except Exception:
                        continue
            note = f"live {last} rows={len(rows)} pending={len(pending)}"
            if rows or pending:
                set_progress(f"Got {len(rows)} posted, {len(pending)} pending")
            elif balances.get("balance") is not None:
                _dump_page(page, "no-rows")
                set_progress(
                    f"On FNB · Bank {balances.get('balance')} · no register lines yet"
                )
                note = f"live-balances {last} url={getattr(page, 'url', '')}"
            else:
                _dump_page(page, "no-rows")
                set_progress("On FNB but no statement rows", error="no statement rows")
                note = f"live-empty {last} url={getattr(page, 'url', '')}"
        except Exception as exc:
            note = f"live-failed: {exc}"
            set_progress("FNB read failed", error=str(exc)[:180])
            _dump_page(page, "read-failed")
            rows = []
        try:
            set_progress("Logging off FNB")
            _click_named(page, ("Log off", "Log Off", "Logout", "Log out"))
            page.wait_for_timeout(800)
        except Exception:
            pass
        context.close()
    return {
        "ok": bool(rows or pending or balances.get("balance") is not None),
        "rows": rows,
        "pending": pending,
        "balance": balances.get("balance"),
        "available": balances.get("available"),
        "note": note,
        "error": None if (rows or pending or balances.get("balance") is not None) else (note or "FNB statement not read"),
        "via": "fnb-live",
    }


def pull(conn: sqlite3.Connection | None = None) -> dict:
    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB), timeout=60)
    if conn is None:
        own.execute("PRAGMA busy_timeout=60000")
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    set_progress("Fetching FNB")
    try:
        live = fetch_live()
        rows = live.get("rows") or []
        if rows:
            set_progress(f"Allocating {len(rows)} rows")
        added = insert_new(own, rows)
        pending = replace_pending(own, live.get("pending") or [])
        balance = live.get("balance")
        if balance is None and rows:
            with_bal = [r for r in rows if r.get("balance") is not None]
            if with_bal:
                balance = with_bal[0].get("balance")
        # Failed live pull must not write the old book as if it were FNB.
        pending_amt = round(sum(abs(float(p.get("amount") or 0)) for p in pending), 2)
        available = live.get("available")
        if available is None and balance is not None:
            available = round(float(balance) - pending_amt, 2)
        pack = {
            "ok": bool(live.get("ok") or added.get("inserted")),
            "via": "fnb-live",
            "fetched_at": fetched_at,
            "rows_seen": len(rows),
            "inserted": added["inserted"],
            "allocated": added["allocated"],
            "need_recon": added["need_recon"],
            "need_recon_amount": added["need_recon_amount"],
            "attention": added["attention"],
            "pending": pending,
            "pending_amount": pending_amt,
            "balance": balance,
            "available": available,
            "note": live.get("note") or live.get("error") or "",
            "error": None if live.get("ok") or rows else (live.get("error") or live.get("note")),
        }
        _record_fetch(own, pack)
        if pack.get("ok"):
            set_progress(
                f"Done · {pack['inserted']} new of {pack['rows_seen']} posted",
                done=True,
                inserted=pack["inserted"],
                rows_seen=pack["rows_seen"],
            )
        else:
            set_progress(
                pack.get("error") or pack.get("note") or "FNB fetch failed",
                done=True,
                error=pack.get("error") or pack.get("note"),
            )
        if conn is None:
            own.close()
        return pack
    except Exception as exc:
        if conn is None:
            own.close()
        set_progress("FNB fetch failed", done=True, error=str(exc)[:180])
        raise


def _when_label(stamp: str | None) -> str | None:
    if not stamp:
        return None
    text = str(stamp).replace("T", " ").split(".")[0]
    text = re.sub(r"([+-]\d{2}:\d{2}|Z)$", "", text).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt)
            if fmt == "%Y-%m-%d":
                return dt.strftime("%d %b %Y")
            return dt.strftime("%d %b %Y, %H:%M")
        except ValueError:
            continue
    return text


def system_balance(conn: sqlite3.Connection) -> float | None:
    for sql in (
        """SELECT balance FROM bank_tx
           WHERE ours=1 AND source IN ('fnb_live','fnb_online','fnb_api','fnb_history','fnb_qb')
           ORDER BY paid_on DESC, id DESC LIMIT 1""",
        """SELECT balance FROM fnb_tx
           WHERE source IN ('fnb_live','fnb_online','fnb_api','fnb_history','fnb_qb')
           ORDER BY paid_on DESC, id DESC LIMIT 1""",
    ):
        try:
            rec = conn.execute(sql).fetchone()
        except sqlite3.OperationalError:
            rec = None
        if rec and rec[0] is not None:
            try:
                return round(float(rec[0]), 2)
            except (TypeError, ValueError):
                return None
    return None


def card_overlay(conn: sqlite3.Connection | None = None) -> dict:
    """Last fetch + unmatched items for the FNB card."""
    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB))
    fetch = last_fetch(own) or {}
    live = last_live_figures(own)
    attention = attention_open(own)
    pending = pending_open(own)
    need_amt = round(sum(abs(float(a.get("amount") or 0)) for a in attention), 2)
    pending_amt = round(sum(abs(float(p.get("amount") or 0)) for p in pending), 2)
    sys_bal = system_balance(own)
    live_bal = live.get("balance")
    available = None
    if live_bal is not None and pending_amt:
        available = round(float(live_bal) - pending_amt, 2)
    elif sys_bal is not None:
        available = round(float(sys_bal) - pending_amt, 2)
    if conn is None:
        own.close()
    last_ok = bool(live.get("ok") or fetch.get("ok"))
    stamp = live.get("fetched_at") or fetch.get("fetched_at")
    return {
        "last_fetched": stamp,
        "last_fetched_label": _when_label(stamp),
        "last_inserted": fetch.get("inserted") or 0,
        "last_ok": last_ok,
        "system_balance": sys_bal,
        "live_balance": live_bal,
        "available": available,
        "pending": pending,
        "pending_amount": pending_amt,
        "matched": bool(last_ok and need_amt <= 0.004),
        "attention": attention,
        "attention_amount": need_amt,
        "choices": allocate_choices(),
    }


def self_test() -> int:
    failed = 0
    if pick_dismiss([]) is not None:
        print("FAIL no-popup")
        failed += 1
    elif pick_dismiss(["Apply now", "Buy"]) is not None:
        print("FAIL unsafe-popup")
        failed += 1
    elif pick_dismiss(["What's new", "Close"]) != "Close":
        print("FAIL dismiss-close", pick_dismiss(["What's new", "Close"]))
        failed += 1
    elif pick_dismiss(["Got it"]) != "Got it":
        print("FAIL dismiss-got-it")
        failed += 1
    else:
        print("OK popup-optional")
    from books import ensure_tables
    from recon import ensure

    conn = sqlite3.connect(":memory:")
    ensure_tables(conn)
    ensure(conn)
    first = [
        {
            "paid_on": "2026-10-05",
            "amount": -520.0,
            "balance": 4554.66,
            "description": "PAYFAST*Host Africa Oct",
            "source": "fnb_live",
        },
        {
            "paid_on": "2026-10-01",
            "amount": -2223.94,
            "balance": 5074.66,
            "description": "RSAWEB 436784018 NETCASH",
            "source": "fnb_live",
        },
        {
            "paid_on": "2026-09-30",
            "amount": 329.0,
            "balance": 7298.60,
            "description": "CAPITEC P PEARSON",
            "source": "fnb_live",
        },
    ]
    a = insert_new(conn, first)
    b = insert_new(conn, first)
    n = conn.execute("SELECT COUNT(*) FROM bank_tx").fetchone()[0]
    fn = conn.execute("SELECT COUNT(*) FROM fnb_tx WHERE source='fnb_live'").fetchone()[0]
    kinds = {
        r[0]: r[1]
        for r in conn.execute("SELECT payee, alloc_kind FROM fnb_tx WHERE source='fnb_live'")
    }
    if a["inserted"] != 3 or b["inserted"] != 0 or n != 3 or fn != 3:
        print("FAIL dedup", a, b, n, fn)
        failed += 1
    elif kinds.get("PAYFAST*Host Africa Oct") != "expense":
        print("FAIL alloc-payfast", kinds)
        failed += 1
    elif kinds.get("RSAWEB 436784018 NETCASH") != "clearing":
        print("FAIL alloc-netcash", kinds)
        failed += 1
    elif kinds.get("CAPITEC P PEARSON") != "client_paid":
        print("FAIL alloc-pearson", kinds)
        failed += 1
    else:
        print("OK dedup-and-alloc")
    mystery = insert_new(
        conn,
        [
            {
                "paid_on": "2026-10-06",
                "amount": 88.0,
                "balance": 4642.66,
                "description": "UNKNOWN CREDIT XYZ",
                "source": "fnb_live",
            }
        ],
    )
    if mystery["need_recon"] != 1 or mystery["need_recon_amount"] != 88:
        print("FAIL attention", mystery)
        failed += 1
    else:
        print("OK needs-attention", mystery["attention"][0]["what"])
    overlay = card_overlay(conn)
    if overlay["matched"] or overlay["attention_amount"] != 88 or overlay["system_balance"] != 4642.66:
        print("FAIL overlay", overlay)
        failed += 1
    else:
        print("OK card-overlay-attention")
    live_before = conn.execute("SELECT COUNT(*) FROM fnb_tx WHERE source='fnb_live'").fetchone()[0]
    conn.execute(
        "DELETE FROM fnb_tx WHERE COALESCE(source,'') NOT IN ('fnb_live','fnb_online','fnb_api')"
    )
    live_after = conn.execute("SELECT COUNT(*) FROM fnb_tx WHERE source='fnb_live'").fetchone()[0]
    if live_before != live_after or live_after != 4:
        print("FAIL preserve-live", live_before, live_after)
        failed += 1
    else:
        print("OK preserve-live")
    pend = parse_pending_table(
        "03 October 2026 15:00:39  485442******9008  WWW.UI.COM  499.22"
    )
    if (
        len(pend) != 1
        or pend[0]["amount"] != -499.22
        or pend[0]["paid_on"] != "2026-10-03 15:00:39"
        or "WWW.UI.COM" not in pend[0]["description"]
        or "485442" not in pend[0]["description"]
    ):
        print("FAIL pending-parse", pend)
        failed += 1
    else:
        print("OK pending-parse")
    label = _when_label("2026-10-06T13:04:00+02:00")
    if label != "06 Oct 2026, 13:04" or "SAST" in (label or "") or "UTC" in (label or "") or "+" in (label or ""):
        print("FAIL when-label", label)
        failed += 1
    else:
        print("OK when-label")
    live_rows = parse_fnb_live_text(
        "06 Oct 2026 G CUPIDO 760.00 5,314.66\n"
        "05 Oct 2026 PAYFAST*Host Africa Oct -520.00 4,554.66\n"
        "01 Oct 2026 RSAWEB 436784018 NETCASH 0.00 -2,223.94 5,074.66\n"
    )
    stacked = parse_fnb_live_text("06 Oct 2026\nG CUPIDO\n760.00\n5,314.66\n")
    if (
        len(live_rows) != 3
        or live_rows[0]["amount"] != 760
        or live_rows[0]["balance"] != 5314.66
        or live_rows[0]["paid_on"] != "2026-10-06"
        or "CUPIDO" not in live_rows[0]["description"]
        or live_rows[1]["amount"] != -520
        or live_rows[2]["amount"] != -2223.94
        or len(stacked) != 1
        or stacked[0]["amount"] != 760
    ):
        print("FAIL live-parse", live_rows, stacked)
        failed += 1
    else:
        print("OK live-parse")
    fill = Path(__file__).read_text().split("def _fill_login", 1)[-1].split("def _wait_after_login", 1)[0]
    if "get_by_label" in fill:
        print("FAIL login-no-label-hang")
        failed += 1
    else:
        print("OK login-waits-for-form")
    set_progress("Opening FNB")
    prog = read_progress()
    if prog.get("step") != "Opening FNB" or prog.get("done"):
        print("FAIL progress", prog)
        failed += 1
    else:
        print("OK progress")
    if page_kind("My Devices and Browsers Manage devices Skip") != "devices":
        print("FAIL page-devices")
        failed += 1
    elif page_kind("Welcome Kevin Weaving My bank accounts") != "welcome":
        print("FAIL page-welcome")
        failed += 1
    elif page_kind("Gowifi FNB Main 62860060278 R 5,314.66 R 4,815.44 Available Balance") != "accounts":
        print("FAIL page-accounts")
        failed += 1
    elif page_kind("Successful Pending Date Description Amount Balance 06 Oct 2026 G CUPIDO") != "statement":
        print("FAIL page-statement")
        failed += 1
    else:
        print("OK page-kind-varies")
    card_bal = parse_account_card("Gowifi FNB Main 62860060278 R 5,314.66 R 4,815.44")
    if card_bal.get("balance") != 5314.66 or card_bal.get("available") != 4815.44:
        print("FAIL account-card", card_bal)
        failed += 1
    else:
        print("OK account-available")
    keys = keys_from_channel_text("Client ID: abcdefghijklmnop\nClient Secret: qrstuvwxyz1234567890")
    if keys["client_id"] != "abcdefghijklmnop" or keys["client_secret"] != "qrstuvwxyz1234567890":
        print("FAIL channel-keys", keys)
        failed += 1
    else:
        print("OK channel-keys")
    if not _looks_blocked("Please solve this CAPTCHA", "https://validate.perfdrive.com/x"):
        print("FAIL captcha-detect")
        failed += 1
    elif any("www.fnb.co.za/" == u.rstrip("/") or u.rstrip("/") == "https://www.fnb.co.za" for u in LOGIN_URLS):
        print("FAIL no-fnb-homepage", LOGIN_URLS)
        failed += 1
    else:
        print("OK own-login-online-only")
    open_fn = Path(__file__).read_text().split("def _display_alive", 1)[-1].split("def _dump_page", 1)[0]
    here = Path(__file__).read_text().split("def self_test", 1)[0]
    api = Path(__file__).with_name("fnb_api.py").read_text().split("def self_test", 1)[0]
    src = here + api
    if "channel" not in open_fn or '"chrome"' not in open_fn or "_display_alive" not in open_fn:
        print("FAIL own-login-real-chrome")
        failed += 1
    elif any(w in src for w in ("Banklink", "Stitch", "OFX", "Scheduled Export")):
        print("FAIL no-third-party-fetch")
        failed += 1
    else:
        print("OK own-login-real-chrome")
    click_reg = Path(__file__).read_text().split("def _click_account_register", 1)[-1].split("def _walk_to_statement", 1)[0]
    if "Gowifi FNB Main" not in click_reg or "email" not in click_reg.lower():
        print("FAIL account-register-click")
        failed += 1
    else:
        print("OK account-register-click")
    live_conn = sqlite3.connect(":memory:")
    record_live_card(5314.66, 4815.44, conn=live_conn)
    figs = last_live_figures(live_conn)
    ov = card_overlay(live_conn)
    if figs.get("balance") != 5314.66 or ov.get("live_balance") != 5314.66:
        print("FAIL live-card-balance", figs, ov)
        failed += 1
    else:
        print("OK live-card-balance")
    _record_fetch(
        live_conn,
        {
            "fetched_at": "2026-10-06 15:00",
            "rows_seen": 2,
            "inserted": 0,
            "allocated": 0,
            "need_recon": 0,
            "need_recon_amount": 0,
            "balance": 5074.66,
            "ok": True,
            "note": "QB FNB 62860060278 · 2 posted · 0 new",
        },
    )
    stale = last_live_figures(live_conn)
    if stale.get("balance") != 5314.66:
        print("FAIL qb-does-not-clobber-live-card", stale)
        failed += 1
    else:
        print("OK qb-does-not-clobber-live-card")
    class _F:
        def __init__(self, url):
            self.url = url
    if _frame_ok(_F("https://9689447.fls.doubleclick.net/x")) or not _frame_ok(_F("https://www.online.fnb.co.za/banking/main.jsp")):
        print("FAIL skip-ad-frames")
        failed += 1
    else:
        print("OK skip-ad-frames")
    live_src = Path(__file__).read_text().split("def fetch_live", 1)[-1].split("def pull", 1)[0]
    if "Log off" not in live_src:
        print("FAIL log-off-after-fetch")
        failed += 1
    else:
        print("OK log-off-after-fetch")
    live_conn.close()
    conn.close()
    return failed


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "test":
        raise SystemExit(self_test())
    if cmd == "pull":
        print(json.dumps(pull(), indent=2))
    elif cmd == "last":
        print(json.dumps(last_fetch(), indent=2))
    else:
        print(json.dumps({"ready": login_ready(), "via": "fnb-live"}, indent=2))
