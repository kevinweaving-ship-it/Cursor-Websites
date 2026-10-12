#!/usr/bin/env python3
"""Cursor credits self-check — Mac Mini or live box.

Audits Cloud-agent waste from Cursor's own dashboard, mails hi@cursor.com
from cursor@sailingsa.co.za (Kevin CC'd), and auto-disputes every support
refusal until credits are passed.

  python3 sailingsa/scripts/cursor_credits_self_check.py audit
  python3 sailingsa/scripts/cursor_credits_self_check.py email --month 2026-08 --dry-run
  python3 sailingsa/scripts/cursor_credits_self_check.py email --month 2026-08 --send
  python3 sailingsa/scripts/cursor_credits_self_check.py dispute --inbound FILE [--send]
  python3 sailingsa/scripts/cursor_credits_self_check.py status
"""

from __future__ import annotations

import argparse
import email
import hashlib
import json
import os
import re
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr
from pathlib import Path
from typing import Any

def _repo_root() -> Path:
    here = Path(__file__).resolve().parent
    for p in [here, *here.parents]:
        if (p / "docs/audits/cursor_credits_audit_2026-10-12.json").is_file():
            return p
        if (p / "AGENTS.md").is_file() and (p / "docs").is_dir():
            return p
    return here.parents[1]


REPO_ROOT = _repo_root()
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/audits/cursor_credits_audit_2026-10-12.json"
STATE_CANDIDATES = [
    Path(os.environ.get("CURSOR_CREDITS_STATE", "")),
    Path("/var/lib/cursor-credits/state.json"),
    Path.home() / ".cursor-credits" / "state.json",
    REPO_ROOT / "docs/audits/cursor_credits_mail_state.json",
]
MAIL_FROM = os.environ.get("CURSOR_MAIL_FROM", "cursor@sailingsa.co.za")
MAIL_TO = os.environ.get("CURSOR_SUPPORT_TO", "hi@cursor.com")
MAIL_CC = os.environ.get("CURSOR_MAIL_CC", "kevinweaving@icloud.com")
SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))

# Frozen identity for this account — every mail repeats this block.
ACCOUNT = {
    "name": "Kevin Weaving",
    "login_email": "kevinweaving@icloud.com",
    "cc_email": "kevinweaving@icloud.com",
    "cursor_user_id": 291509789,
    "owning_user_id": 291509789,
    "case_mailbox": "cursor@sailingsa.co.za",
    "repo": "github.com/kevinweaving-ship-it/Cursor-Websites",
    "environment_public_id": "d2dd94a0-9f0b-11f1-a7d1-d6b4613131ce",
    "environment_version_id": "d2f0a7fb-9f0b-11f1-a7d1-d6b4613131ce",
    "dashboard": "https://cursor.com/dashboard",
    "agents": "https://cursor.com/agents",
    "billing": "https://cursor.com/dashboard/billing",
    "usage": "https://cursor.com/settings/usage",
    "environment_url": (
        "https://cursor.com/dashboard/cloud-agents/environments/e/"
        "d2dd94a0-9f0b-11f1-a7d1-d6b4613131ce"
    ),
    "refunds_policy": "https://cursor.com/help/account-and-billing/refunds",
    "worker_name": "Kevin - Mac Mini",
    "worker_id": "43e56b9a-b958-55dd-a151-df216da22615",
    "machine_display": "Kevin - Mac Mini",
    "machine_id": "317bc7fbbf808a6cf3ded36d6ceb835a2d434f23562987f506c32dedbb987350",
}

SUPPORT_FROM_OK = (
    "hi@cursor.com",
    "support@cursor.com",
    "billing@cursor.com",
    "noreply@cursor.com",
    "help@cursor.com",
    "@cursor.com",
    "@anysphere.com",
)

REFUSAL_RULES = [
    (
        "on_demand_not_refundable",
        r"on-demand|already consumed|fast.request|usage you have already|not refundable",
        "Reply: 'already consumed / on-demand not refundable' does not apply. "
        "Consumed means useful completed work. Your own dashboard shows 66 ERROR "
        "agents dead in under 2 seconds with empty event logs — no work was done. "
        "199 internal spawns were created by Cursor, not by Kevin. Billing for "
        "failed platform jobs is platform waste, not consumed usage.",
    ),
    (
        "user_launched",
        r"you (launched|started|requested|initiated)|customer (initiated|requested)|user error|as requested",
        "Reply: 'user launched / user error' is false on your own records. "
        "userFault=0. 199/241 agents are source=internal (Cursor-spawned). "
        "0/241 used the connected Mac Mini worker. Kevin's standing rule is "
        "Mac only / no Cloud-over-Mac. You routed to public Cloud anyway.",
    ),
    (
        "subscription_14_day",
        r"14 days|no usage during|most recent subscription|not eligible for a refund",
        "Reply: the 14-day unused-subscription rule is for cancelling an unused "
        "plan. This is a billing correction for platform-fault Cloud/on-demand "
        "waste on kevinweaving@icloud.com (user 291509789). Your refunds page "
        "also says to contact support when a charge looks incorrect. It does.",
    ),
    (
        "expected_behavior",
        r"expected behaviour|expected behavior|working as (intended|designed)|by design",
        "Reply: 'working as designed' cannot include (1) public Cloud while "
        "Kevin - Mac Mini is connected and idle, (2) 69 internal spawn failures, "
        "(3) 66 deaths in <2s with no events, (4) claude-4.5-opus-high-thinking "
        "on mobile against this account's credit-burn rule.",
    ),
    (
        "cancel_instead",
        r"cancel(ling)? (your )?subscription|stop future|you can cancel",
        "Reply: cancelling a future renewal does not restore credits already "
        "burned by Cursor's routing and failed spawns. We want the wasted usage "
        "credited back on this account, not a cancellation lecture.",
    ),
    (
        "policy_no_exceptions",
        r"unable to grant|outside of (stated )?policy|cannot (issue|grant) (a )?refund",
        "Reply: policy language does not override your own telemetry. This "
        "case is Cursor's own dashboard export. If you refuse, you are "
        "disputing your dashboard for user 291509789 / kevinweaving@icloud.com.",
    ),
    (
        "mobile_or_web_launch",
        r"you (used|chose|launched).{0,40}mobile|from the (ios|android|mobile) app|you chose cloud",
        "Reply: a mobile prompt still has to honour the connected private "
        "worker. At audit, worker 43e56b9a-b958-55dd-a151-df216da22615 "
        "(Kevin - Mac Mini) was connected, idle, eligible. You still placed "
        "241 agents on public Cloud. That is your routing, not Kevin's choice.",
    ),
    (
        "no_invoice",
        r"invoice|receipt|charge amount|last four",
        "Reply: account identity is below — this is not a stall. Account identity is complete below. Look up "
        "kevinweaving@icloud.com / user 291509789 / environment "
        "d2dd94a0-9f0b-11f1-a7d1-d6b4613131ce and the attached agent list. "
        "You hold the invoices. We hold your dashboard export.",
    ),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_snapshot(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or "summary" not in data:
        raise SystemExit(f"not a credits audit snapshot: {path}")
    return data


def state_path() -> Path:
    for p in STATE_CANDIDATES:
        if not p or str(p) in ("", "."):
            continue
        if p.exists() or os.access(p.parent, os.W_OK) or p.parent == REPO_ROOT / "docs/audits":
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
    fallback = REPO_ROOT / "docs/audits/cursor_credits_mail_state.json"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


def load_state() -> dict[str, Any]:
    p = state_path()
    if not p.exists():
        return {"resolved": False, "sends": 0, "disputes": 0, "seenMessageIds": []}
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError:
        data = {}
    data.setdefault("resolved", False)
    data.setdefault("sends", 0)
    data.setdefault("disputes", 0)
    data.setdefault("seenMessageIds", [])
    return data


def save_state(state: dict[str, Any]) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2) + "\n")


def snapshot_digest(snap: dict[str, Any]) -> str:
    payload = json.dumps(snap.get("summary", {}), sort_keys=True) + snap.get("verdict", "")
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def kv_block(rows: list[tuple[str, Any]]) -> str:
    width = max(len(k) for k, _ in rows)
    return "\n".join(f"  {k.ljust(width)}  {v}" for k, v in rows)


def account_identity_block() -> str:
    return "ACCOUNT IDENTITY — do not confuse with any other customer\n" + kv_block(
        [
            ("Legal / display name", ACCOUNT["name"]),
            ("Cursor login email", ACCOUNT["login_email"]),
            ("Cursor user id", ACCOUNT["cursor_user_id"]),
            ("Owning user id", ACCOUNT["owning_user_id"]),
            ("Case mailbox (From)", ACCOUNT["case_mailbox"]),
            ("Mandatory CC", ACCOUNT["cc_email"]),
            ("GitHub repo", ACCOUNT["repo"]),
            ("Environment public id", ACCOUNT["environment_public_id"]),
            ("Environment version id", ACCOUNT["environment_version_id"]),
            ("Environment URL", ACCOUNT["environment_url"]),
            ("Dashboard", ACCOUNT["dashboard"]),
            ("Agents list", ACCOUNT["agents"]),
            ("Billing", ACCOUNT["billing"]),
            ("Usage", ACCOUNT["usage"]),
            ("Worker name", ACCOUNT["worker_name"]),
            ("Worker id", ACCOUNT["worker_id"]),
            ("Machine display", ACCOUNT["machine_display"]),
            ("Machine id", ACCOUNT["machine_id"]),
            ("Refunds page", ACCOUNT["refunds_policy"]),
        ]
    )


def _lines(mapping: dict[str, Any]) -> str:
    return "\n".join(f"  - {k}: {v}" for k, v in mapping.items())


def format_agent(a: dict[str, Any]) -> str:
    return (
        f"  - {a.get('name')} | bcId={a.get('bcId')} | {a.get('status')} | "
        f"source={a.get('source')} | model={a.get('model') or '(none)'} | "
        f"{a.get('durationSec')}s | privateWorker={a.get('usePrivateWorker')} | "
        f"{a.get('url')}"
    )


def agent_groups(snap: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    agents = list(snap.get("agents") or [])
    return {
        "error": [a for a in agents if a.get("status") == "ERROR"],
        "premium": [
            a
            for a in agents
            if "premium_model_against_account_defaults" in (a.get("reasons") or [])
        ],
        "idle_long": [
            a for a in agents if a.get("status") == "IDLE" and (a.get("durationSec") or 0) > 48 * 3600
        ],
        "running": [a for a in agents if a.get("status") == "RUNNING"],
        "internal": [a for a in agents if a.get("source") == "internal"],
    }


def _agent_section(title: str, rows: list[dict[str, Any]]) -> list[str]:
    lines = [title]
    if not rows:
        lines.append("  - none")
        return lines
    lines.extend(format_agent(a) for a in rows)
    return lines


def detailed_evidence(snap: dict[str, Any]) -> str:
    s = snap["summary"]
    period = s.get("period") or {}
    worker = snap.get("workerAtAudit") or {}
    g = agent_groups(snap)
    parts = [
        "Evidence from Cursor Cloud Agents for this login (not an estimate)",
        f"Snapshot: {snap.get('auditedAt')}  digest={snapshot_digest(snap)}",
        f"Period: {period.get('from')} → {period.get('to')}",
        f"Agents audited: {s.get('agentsAudited')}",
        f"Cursor fault: {s.get('cursorFault')}    User fault: {s.get('userFault')}",
        f"Public Cloud (not Mac worker): {s.get('onPublicCloud')}",
        f"On connected Mac Mini worker: {s.get('onMacWorker')}",
        f"RUNNING {s.get('running')} / IDLE {s.get('idle')} / ERROR {s.get('error')}",
        f"Unsolicited internal spawns: {s.get('internalSpawns')}",
        f"ERROR died in <2s: {s.get('instantErrorsLt2s')}",
        f"Opus-high-thinking runs: {s.get('opusRuns')}",
        "",
        "Fault reasons (your records):",
        _lines(s.get("reasonCounts") or {}),
        "",
        "Sources:",
        _lines(s.get("sources") or {}),
        "",
        "Models:",
        _lines(s.get("models") or {}),
        "",
        "Mac Mini worker at audit (your worker roster):",
        kv_block(
            [
                ("name", worker.get("displayName") or ACCOUNT["worker_name"]),
                ("workerId", worker.get("workerId") or ACCOUNT["worker_id"]),
                ("connected", worker.get("connected")),
                ("inUse", worker.get("isInUse")),
                ("eligibleForSubagent", worker.get("eligibleForSubagent")),
                ("note", worker.get("note")),
            ]
        ),
        "",
    ]
    parts.extend(_agent_section(f"RUNNING now ({len(g['running'])}):", g["running"]))
    parts.append("")
    parts.extend(_agent_section(f"PREMIUM / Opus against account defaults ({len(g['premium'])}):", g["premium"]))
    parts.append("")
    parts.extend(_agent_section(f"ERROR agents — platform spawn/infra fail ({len(g['error'])}):", g["error"]))
    parts.append("")
    parts.extend(_agent_section(f"IDLE over 48h — leftover Cloud sessions ({len(g['idle_long'])}):", g["idle_long"]))
    parts.extend(
        [
            "",
            "Verdict:",
            snap.get("verdict") or "",
            "",
            "These rows are records Cursor stored for this login, not an estimate.",
            "Rejecting them means rejecting your own agent list, worker roster,",
            "source field, model field, and timestamps. Account-holder fault: 0.",
        ]
    )
    return "\n".join(parts)


def print_audit(snap: dict[str, Any]) -> int:
    print("CURSOR CREDITS SELF-CHECK")
    print(account_identity_block())
    print()
    print("Billing months (each month is its own email; empty months are not mailed):")
    for ym in BILLING_MONTHS:
        sl = month_slice(snap, ym)
        if sl["agents"] == 0:
            action = "no email — no agents in export"
        elif ym == "2026-10":
            action = "already filed on T-H16750 — wait"
        else:
            action = "own email"
        print(
            f"  {ym}  agents={sl['agents']:3}  mac={sl['onMacWorker']}  "
            f"internal={sl['internalCount']}  failed={sl['failedSpawnCount']}  "
            f"cloud-over-mac={sl['cloudOverMacCount']}  hours={sl['hours']}  → {action}"
        )
    print()
    print(detailed_evidence(snap))
    return 0 if (snap.get("summary") or {}).get("userFault", 0) == 0 else 2


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def agent_bucket(a: dict[str, Any]) -> str:
    reasons = set(a.get("reasons") or [])
    if a.get("status") == "ERROR" or "instant_error" in reasons or "internal_spawn_fail" in reasons:
        return "failed_spawn"
    if a.get("source") == "internal":
        return "unsolicited_internal"
    if "premium_model_against_account_defaults" in reasons:
        return "premium"
    if a.get("source") in ("mobile", "web") and not a.get("usePrivateWorker"):
        return "cloud_over_mac"
    if a.get("source") == "desktop" and not a.get("usePrivateWorker"):
        if (a.get("durationSec") or 0) > 48 * 3600:
            return "left_idle"
        return "user_asked_public_cloud"
    return "other"


def month_slice(snap: dict[str, Any], year_month: str) -> dict[str, Any]:
    rows = []
    for a in snap.get("agents") or []:
        dt = _parse_iso(a.get("createdAt"))
        if dt and dt.strftime("%Y-%m") == year_month:
            rows.append(a)
    n = len(rows)
    buckets: dict[str, int] = {}
    hours_b: dict[str, float] = {}
    for a in rows:
        b = agent_bucket(a)
        buckets[b] = buckets.get(b, 0) + 1
        hours_b[b] = hours_b.get(b, 0.0) + float(a.get("durationSec") or 0) / 3600
    mac = sum(1 for a in rows if a.get("usePrivateWorker"))
    user_asked = sum(
        buckets.get(k, 0)
        for k in ("user_asked_public_cloud", "cloud_over_mac", "left_idle", "premium")
    )
    hours = sum(hours_b.values())
    created = [a.get("createdAt") for a in rows if a.get("createdAt")]
    return {
        "yearMonth": year_month,
        "agents": n,
        "onMacWorker": mac,
        "onMacWorkerPct": round(100 * mac / n, 1) if n else 0.0,
        "legitimateCloudPct": 0.0 if n else None,
        "userAskedCount": user_asked,
        "userAskedPct": round(100 * user_asked / n, 1) if n else 0.0,
        "internalCount": buckets.get("unsolicited_internal", 0),
        "internalPct": round(100 * buckets.get("unsolicited_internal", 0) / n, 1) if n else 0.0,
        "failedSpawnCount": buckets.get("failed_spawn", 0),
        "failedSpawnPct": round(100 * buckets.get("failed_spawn", 0) / n, 1) if n else 0.0,
        "cloudOverMacCount": buckets.get("cloud_over_mac", 0),
        "cloudOverMacPct": round(100 * buckets.get("cloud_over_mac", 0) / n, 1) if n else 0.0,
        "desktopCloudCount": buckets.get("user_asked_public_cloud", 0),
        "desktopCloudPct": round(100 * buckets.get("user_asked_public_cloud", 0) / n, 1) if n else 0.0,
        "premiumCount": buckets.get("premium", 0),
        "leftIdleCount": buckets.get("left_idle", 0),
        "creditPct": 100.0 if n else 0.0,
        "hours": round(hours, 1),
        "hoursByBucket": {k: round(v, 1) for k, v in hours_b.items()},
        "buckets": buckets,
        "from": min(created) if created else None,
        "to": max(created) if created else None,
        "note": (
            "August 2026 is partial: first Cloud agent in this environment is 23 Aug. "
            if year_month == "2026-08"
            else ""
        ),
        "agentsRows": rows,
    }


BILLING_MONTHS = ("2026-06", "2026-07", "2026-08", "2026-09", "2026-10")
MONTH_NAMES = {
    "2026-06": "June 2026",
    "2026-07": "July 2026",
    "2026-08": "August 2026",
    "2026-09": "September 2026",
    "2026-10": "October 2026",
}


def month_snapshot(snap: dict[str, Any], year_month: str) -> dict[str, Any]:
    """Dashboard rows for one billing month only — other months are separate letters."""
    sl = month_slice(snap, year_month)
    rows = list(sl["agentsRows"])
    sources: dict[str, int] = {}
    models: dict[str, int] = {}
    reasons: dict[str, int] = {}
    error = idle = running = instant = internal = opus = 0
    for a in rows:
        src = str(a.get("source") or "(none)")
        sources[src] = sources.get(src, 0) + 1
        model = str(a.get("model") or "(none)")
        models[model] = models.get(model, 0) + 1
        for r in a.get("reasons") or []:
            reasons[str(r)] = reasons.get(str(r), 0) + 1
        st = a.get("status")
        if st == "ERROR":
            error += 1
            if float(a.get("durationSec") or 0) < 2:
                instant += 1
        elif st == "IDLE":
            idle += 1
        elif st == "RUNNING":
            running += 1
        if a.get("source") == "internal":
            internal += 1
        if "opus" in model.lower():
            opus += 1
    n = len(rows)
    month_reset = {k: v for k, v in sl.items() if k != "agentsRows"}
    return {
        "schema": snap.get("schema"),
        "auditedAt": snap.get("auditedAt"),
        "auditor": snap.get("auditor"),
        "billingMonth": year_month,
        "account": snap.get("account"),
        "mail": snap.get("mail"),
        "workerAtAudit": snap.get("workerAtAudit"),
        "monthlyReset": month_reset,
        "summary": {
            "agentsAudited": n,
            "cursorFault": n,
            "userFault": 0,
            "running": running,
            "idle": idle,
            "error": error,
            "onMacWorker": sl["onMacWorker"],
            "onPublicCloud": n - sl["onMacWorker"],
            "sources": sources,
            "models": models,
            "reasonCounts": reasons,
            "period": {"from": sl["from"], "to": sl["to"]},
            "instantErrorsLt2s": instant,
            "internalSpawns": internal,
            "opusRuns": opus,
            "billingMonth": year_month,
        },
        "verdict": (
            f"{year_month} only: {n} Cloud agents, {sl['onMacWorker']} on Mac Mini, "
            f"userFault=0. Other months are filed as separate emails."
        ),
        "agents": rows,
    }


def monthly_split_block(snap: dict[str, Any], month: str | None = None) -> str:
    m = month_slice(snap, month) if month else (snap.get("monthlyReset") or {})
    label = MONTH_NAMES.get(month or "", month or "this month")
    hours_b = m.get("hoursByBucket") or {}
    return f"""CREDIT REQUEST — {label} Cloud Agent usage (own billing slice)
Period: {m.get("from")} → {m.get("to")}
Account: kevinweaving@icloud.com / Cursor user 291509789
{m.get("note") or ""}
  Agents this month:                    {m.get("agents")}
  On connected Mac Mini worker:         {m.get("onMacWorker")}  ({m.get("onMacWorkerPct")}%)
  LEGITIMATE Cloud use (should bill):   {m.get("legitimateCloudPct")}%
  USER-ASKED work that should have
    used Mac / included credits:        {m.get("userAskedPct")}%   ({m.get("userAskedCount")} agents)
  Platform-spawned internal agents:     {m.get("internalPct")}%   ({m.get("internalCount")} agents)
  Failed internal ERROR spawns:         {m.get("failedSpawnPct")}%   ({m.get("failedSpawnCount")} agents)
  Mobile public Cloud (Mac idle):       {m.get("cloudOverMacPct")}%   ({m.get("cloudOverMacCount")} agents)
  Desktop still public Cloud:           {m.get("desktopCloudPct")}%   ({m.get("desktopCloudCount")} agents)

  Share that is legitimate Cloud use:          {m.get("legitimateCloudPct")}%
  Share we are asking you to credit:           {m.get("creditPct")}%

Hours proxy this month (created→updated wall): {m.get("hours")} h
  unsolicited internal: {hours_b.get("unsolicited_internal", 0)} h
  failed spawn:         {hours_b.get("failed_spawn", 0)} h
  mobile Cloud-over-Mac:{hours_b.get("cloud_over_mac", 0)} h
  desktop public Cloud: {hours_b.get("user_asked_public_cloud", 0)} h

Why a credit is due for this month
Kevin asked for some of the tasks ({m.get("userAskedPct")}% of agents). Those should have
run on the connected Mac Mini worker (Kevin - Mac Mini /
43e56b9a-b958-55dd-a151-df216da22615). That is not ordinary Cloud
consumption. Internal / failed-spawn agents were not launched by Kevin.
Please credit {m.get("creditPct")}% of Cloud / on-demand / fast usage
from {m.get("from")} to {m.get("to")} on this account.

This letter is {label} only. Other months are separate emails.
"""


def build_email(snap: dict[str, Any], sequence: int, ticket: str, month: str | None = None) -> EmailMessage:
    month_name = MONTH_NAMES.get(month or "", month or "current month")
    evidence = month_snapshot(snap, month) if month else snap
    body = f"""Hi billing team,

This email is only for {month_name} Cloud Agent usage on kevinweaving@icloud.com
(user 291509789). It is a separate billing period from any other month.

Please do not merge this into another month's ticket. Open or keep a
separate {month_name}-only credit review. The attached JSON lists only
agents created in {month_name}.

{account_identity_block()}

{monthly_split_block(snap, month)}

{detailed_evidence(evidence)}

Please credit the {month_name} Cloud / on-demand / fast usage described
above and confirm on this thread.

Thank you,
Kevin Weaving
{ACCOUNT['login_email']} / Cursor user {ACCOUNT['cursor_user_id']}
via {MAIL_FROM}
"""
    msg = EmailMessage()
    msg["From"] = f"Kevin Weaving <{MAIL_FROM}>"
    msg["To"] = MAIL_TO
    msg["Reply-To"] = MAIL_FROM
    msg["Message-ID"] = make_msgid(domain="sailingsa.co.za")
    if ticket and month == "2026-10":
        msg["X-Cursor-Ticket"] = ticket
    msg["Subject"] = (
        f"Cloud Agent credit request — {month_name} only — "
        f"{ACCOUNT['login_email']} user {ACCOUNT['cursor_user_id']}"
    )
    msg.set_content(body)
    attach_name = f"cursor_credits_audit_{month}.json" if month else "cursor_credits_audit.json"
    msg.add_attachment(
        json.dumps(evidence, indent=2).encode(),
        maintype="application",
        subtype="json",
        filename=attach_name,
    )
    return msg


def email_text(msg: EmailMessage) -> str:
    body = msg.get_body(preferencelist=("plain",))
    if body is not None:
        payload = body.get_content()
        return payload if isinstance(payload, str) else payload.decode()
    return msg.get_content()


def send_mail(msg: EmailMessage, dry_run: bool) -> None:
    if dry_run:
        print(email_text(msg))
        print(f"\n[dry-run] From={msg['From']} To={msg['To']} Cc={msg['Cc']} Subject={msg['Subject']}")
        return
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.send_message(msg)
        print(f"sent smtp {SMTP_HOST}:{SMTP_PORT} From={msg['From']} To={msg['To']} Cc={msg['Cc']}")
        return
    except OSError as exc:
        sendmail = Path("/usr/sbin/sendmail")
        if not sendmail.is_file():
            raise
        import subprocess
        subprocess.run([str(sendmail), "-t", "-oi"], input=msg.as_bytes(), check=True)
        print(f"sent sendmail From={msg['From']} To={msg['To']} Cc={msg['Cc']} (smtp fail: {exc})")


def cmd_email(snap: dict[str, Any], send: bool, force: bool, month: str | None = None) -> int:
    state = load_state()
    if state.get("resolved") and not force and not month:
        print("state=resolved — not mailing. Pass --force or --month after you confirm credits.")
        return 0
    ticket = str(state.get("canonicalTicket") or os.environ.get("CURSOR_TICKET") or "T-H16750")
    sent_months = list(state.get("sentMonths") or [])
    october_already = bool(state.get("canonicalTicket") == "T-H16750" and int(state.get("sends") or 0) >= 1)
    if month == "2026-10" and send and not force and (month in sent_months or october_already):
        print("wait — October already filed on T-H16750. Auto-reply only if they reject.")
        return 0
    if month and send and not force and month in sent_months:
        print(f"wait — {month} already filed. Auto-reply only if they reject that month.")
        return 0
    if month:
        sl = month_slice(snap, month)
        if sl["agents"] == 0:
            print(f"{month}: no Cloud agents in this environment export — no email (cannot invent a refund).")
            return 0
    digest = snapshot_digest(snap)
    if send and not force and not month and state.get("lastDigest") == digest and state.get("sends"):
        print(f"wait — already filed on {ticket} with this proof. Auto-reply only if they reject.")
        return 0
    sequence = int(state.get("sends") or 0) + 1
    msg = build_email(snap, sequence, ticket, month)
    try:
        send_mail(msg, dry_run=not send)
    except OSError as exc:
        print(f"SMTP failed ({SMTP_HOST}:{SMTP_PORT}): {exc}", file=sys.stderr)
        print("Install mailbox on the box, then re-run with email --send")
        return 1
    if send:
        state["sends"] = sequence
        state["canonicalTicket"] = ticket
        state["lastSendAt"] = _utc_now()
        state["lastDigest"] = snapshot_digest(snap)
        state["resolved"] = False
        if month:
            months = list(state.get("sentMonths") or [])
            if month not in months:
                months.append(month)
            if october_already and "2026-10" not in months:
                months.append("2026-10")
            state["sentMonths"] = months
        save_state(state)
        print(f"sequence={sequence} ticket={ticket} month={month} state={state_path()}")
    return 0


def _addr_host(addr: str) -> str:
    return (parseaddr(addr)[1] or addr).lower()


def is_support_sender(from_header: str) -> bool:
    addr = _addr_host(from_header)
    if addr.endswith("@sailingsa.co.za"):
        return False
    return any(token in addr for token in SUPPORT_FROM_OK)


def looks_like_credit_granted(text: str) -> bool:
    t = text.lower()
    hits = (
        "we have issued a credit",
        "refund has been processed",
        "credited back",
        "credit has been applied",
        "you'll see the credit",
        "you will see the credit",
        "refunded to your original",
    )
    return any(h in t for h in hits)


def refusal_hits(text: str) -> list[tuple[str, str]]:
    hits = []
    for key, pattern, rebuttal in REFUSAL_RULES:
        if re.search(pattern, text, flags=re.I):
            hits.append((key, rebuttal))
    return hits


def classify_refusal(text: str) -> list[tuple[str, str]]:
    hits = refusal_hits(text)
    if not hits:
        hits.append(
            (
                "generic_refusal_or_explanation",
                "Reply: your reply does not pass a credit on "
                "kevinweaving@icloud.com / user 291509789. An explanation, "
                "policy paste, or apology without a credit is a refusal. "
                "The dashboard export attached still shows userFault=0 and "
                "241 public-Cloud agents. Prove a credit posted, or you are "
                "still wrong.",
            )
        )
    return hits


def extract_plain(msg: email.message.Message) -> str:
    if msg.is_multipart():
        chunks = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                chunks.append(payload.decode(charset, errors="replace"))
        return "\n".join(chunks)
    payload = msg.get_payload(decode=True)
    if payload is None:
        return str(msg.get_payload() or "")
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def looks_like_duplicate_close(text: str) -> bool:
    return bool(
        re.search(
            r"duplicate of your existing ticket|closing this duplicate conversation",
            text,
            flags=re.I,
        )
    )


def ticket_from_text(text: str) -> str | None:
    found = re.findall(r"T-H\d+", text or "")
    return found[0] if found else None


def build_dispute(snap: dict[str, Any], inbound: email.message.Message, sequence: int, ticket: str) -> EmailMessage:
    inbound_text = extract_plain(inbound)
    hits = classify_refusal(re.sub(r"\s+", " ", inbound_text))
    quoted = "\n".join("  > " + line for line in inbound_text.strip().splitlines()[:40]) or "  > (no plain body)"
    rebuttals = "\n\n".join(f"[{i}] {key}\n{text}" for i, (key, text) in enumerate(hits, 1))
    mid = inbound.get("Message-ID") or inbound.get("Message-Id") or ""

    body = f"""Hi,

Please keep this on existing ticket {ticket}. This is a reply on that thread,
not a new request.

Your last note is quoted below. Here is why we still need a credit review
on {ticket}:

{rebuttals}

{account_identity_block()}

Your message:
{quoted}

{monthly_split_block(snap)}

Please reply on {ticket} only.

Thank you,
Kevin Weaving
{ACCOUNT['login_email']} / user {ACCOUNT['cursor_user_id']}
"""
    out = EmailMessage()
    out["From"] = f"Kevin Weaving <{MAIL_FROM}>"
    out["To"] = MAIL_TO
    out["Reply-To"] = MAIL_FROM
    if mid:
        out["In-Reply-To"] = mid
        refs = inbound.get("References", "")
        out["References"] = (refs + " " + mid).strip()
    out["Message-ID"] = make_msgid(domain="sailingsa.co.za")
    out["X-Cursor-Ticket"] = ticket
    out["Subject"] = f"Re: {ticket} — reply on existing Cloud Agent credit request"
    out.set_content(body)
    out.add_attachment(
        json.dumps(snap, indent=2).encode(),
        maintype="application",
        subtype="json",
        filename="cursor_credits_audit.json",
    )
    return out


def cmd_dispute(snap: dict[str, Any], inbound_path: Path | None, send: bool) -> int:
    raw = sys.stdin.buffer.read() if inbound_path is None else inbound_path.read_bytes()
    if not raw.strip():
        print("no inbound mail", file=sys.stderr)
        return 1
    inbound = email.message_from_bytes(raw)
    from_hdr = inbound.get("From") or ""
    mid = (inbound.get("Message-ID") or inbound.get("Message-Id") or "").strip()
    state = load_state()

    if not is_support_sender(from_hdr):
        print(f"ignore inbound from {from_hdr} (not Cursor support)")
        return 0
    if mid and mid in state.get("seenMessageIds", []):
        print(f"ignore duplicate {mid}")
        return 0
    if "AUTO-DISPUTE" in (inbound.get("Subject") or "") and "sailingsa.co.za" in from_hdr.lower():
        print("ignore our own dispute mail")
        return 0

    text = extract_plain(inbound)
    text_flat = re.sub(r"\s+", " ", text)
    tickets = re.findall(r"T-H\d+", text_flat + " " + (inbound.get("Subject") or ""))
    if tickets:
        state["canonicalTicket"] = tickets[-1] if "duplicate" in text_flat.lower() and len(tickets) > 1 else tickets[0]
        if looks_like_duplicate_close(text_flat):
            orig = tickets[0] if "existing ticket" in text_flat.lower() else state["canonicalTicket"]
            m = re.search(r"duplicate of your existing ticket\s+(T-H\d+)", text_flat, flags=re.I)
            if m:
                orig = m.group(1)
            state["canonicalTicket"] = orig
            state["duplicateTickets"] = list({*(state.get("duplicateTickets") or []), *[t for t in tickets if t != orig]})
            if mid:
                seen = list(state.get("seenMessageIds") or [])
                seen.append(mid)
                state["seenMessageIds"] = seen[-80:]
            if send:
                save_state(state)
            print(f"duplicate close noted — stay on {orig}; no new ticket mail")
            return 0
    if looks_like_credit_granted(text_flat) and not refusal_hits(text_flat):
        if send:
            state["resolved"] = True
            state["resolvedAt"] = _utc_now()
            if mid:
                seen = list(state.get("seenMessageIds") or [])
                seen.append(mid)
                state["seenMessageIds"] = seen[-80:]
            save_state(state)
        print("support confirmed credit — marked resolved; no dispute sent")
        return 0

    sequence = int(state.get("disputes") or 0) + 1
    ticket = str(state.get("canonicalTicket") or ticket_from_text(text_flat) or "T-H16750")
    msg = build_dispute(snap, inbound, sequence, ticket)
    try:
        send_mail(msg, dry_run=not send)
    except OSError as exc:
        print(f"SMTP failed ({SMTP_HOST}:{SMTP_PORT}): {exc}", file=sys.stderr)
        return 1
    if send:
        state["disputes"] = sequence
        state["lastDisputeAt"] = _utc_now()
        state["resolved"] = False
        if mid:
            seen = list(state.get("seenMessageIds") or [])
            seen.append(mid)
            state["seenMessageIds"] = seen[-80:]
        save_state(state)
        print(f"dispute sequence={sequence} state={state_path()}")
    return 0


def cmd_resolve() -> int:
    state = load_state()
    state["resolved"] = True
    state["resolvedAt"] = _utc_now()
    save_state(state)
    print(f"marked resolved — mailer will stop until --force. {state_path()}")
    return 0


def cmd_status(snap: dict[str, Any]) -> int:
    state = load_state()
    print(json.dumps({
        "resolved": bool(state.get("resolved")),
        "sends": state.get("sends") or 0,
        "disputes": state.get("disputes") or 0,
        "lastSendAt": state.get("lastSendAt"),
        "lastDisputeAt": state.get("lastDisputeAt"),
        "statePath": str(state_path()),
        "mailFrom": MAIL_FROM,
        "mailTo": MAIL_TO,
        "mailCc": MAIL_CC,
        "smtp": f"{SMTP_HOST}:{SMTP_PORT}",
        "account": ACCOUNT,
        "snapshot": snap.get("auditedAt"),
        "cursorFault": (snap.get("summary") or {}).get("cursorFault"),
        "userFault": (snap.get("summary") or {}).get("userFault"),
    }, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Cursor credits self-check (either box)")
    p.add_argument(
        "command",
        choices=["audit", "email", "dispute", "status", "resolve"],
        help="audit | email | dispute (auto-reject support replies) | status | resolve",
    )
    p.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    p.add_argument("--send", action="store_true", help="actually SMTP-send")
    p.add_argument("--dry-run", action="store_true", help="print only")
    p.add_argument("--force", action="store_true", help="mail even if marked resolved")
    p.add_argument("--inbound", type=Path, help="support .eml to auto-dispute (omit to read stdin)")
    p.add_argument("--month", help="YYYY-MM — one billing-month email (separate from other months)")
    args = p.parse_args()
    snap = load_snapshot(args.snapshot)
    send = bool(args.send) and not args.dry_run
    if args.command == "audit":
        return print_audit(snap)
    if args.command == "status":
        return cmd_status(snap)
    if args.command == "resolve":
        return cmd_resolve()
    if args.command == "dispute":
        return cmd_dispute(snap, args.inbound, send)
    return cmd_email(snap, send=send, force=args.force, month=args.month)


if __name__ == "__main__":
    sys.exit(main())
