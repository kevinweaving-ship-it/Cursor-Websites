#!/usr/bin/env python3
"""Cursor credits self-check — Mac Mini or live box.

Audits Cloud-agent waste from Cursor's own dashboard, mails hi@cursor.com
from cursor@sailingsa.co.za (Kevin CC'd), and auto-disputes every support
refusal until credits are passed.

  python3 sailingsa/scripts/cursor_credits_self_check.py audit
  python3 sailingsa/scripts/cursor_credits_self_check.py email --dry-run
  python3 sailingsa/scripts/cursor_credits_self_check.py email --send
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
        "REJECTED: 'already consumed / on-demand not refundable' does not apply. "
        "Consumed means useful completed work. Your own dashboard shows 66 ERROR "
        "agents dead in under 2 seconds with empty event logs — no work was done. "
        "199 internal spawns were created by Cursor, not by Kevin. Billing for "
        "failed platform jobs is a Cursor fuckup, not consumed usage.",
    ),
    (
        "user_launched",
        r"you (launched|started|requested|initiated)|customer (initiated|requested)|user error|as requested",
        "REJECTED: 'user launched / user error' is false on your own records. "
        "userFault=0. 199/241 agents are source=internal (Cursor-spawned). "
        "0/241 used the connected Mac Mini worker. Kevin's standing rule is "
        "Mac only / no Cloud-over-Mac. You routed to public Cloud anyway.",
    ),
    (
        "subscription_14_day",
        r"14 days|no usage during|most recent subscription|not eligible for a refund",
        "REJECTED: the 14-day unused-subscription rule is for cancelling an unused "
        "plan. This is a billing correction for platform-fault Cloud/on-demand "
        "waste on kevinweaving@icloud.com (user 291509789). Your refunds page "
        "also says to contact support when a charge looks incorrect. It does.",
    ),
    (
        "expected_behavior",
        r"expected behaviour|expected behavior|working as (intended|designed)|by design",
        "REJECTED: 'working as designed' cannot include (1) public Cloud while "
        "Kevin - Mac Mini is connected and idle, (2) 69 internal spawn failures, "
        "(3) 66 deaths in <2s with no events, (4) claude-4.5-opus-high-thinking "
        "on mobile against this account's credit-burn rule.",
    ),
    (
        "cancel_instead",
        r"cancel(ling)? (your )?subscription|stop future|you can cancel",
        "REJECTED: cancelling a future renewal does not restore credits already "
        "burned by Cursor's routing and failed spawns. We want the wasted usage "
        "credited back on this account, not a cancellation lecture.",
    ),
    (
        "policy_no_exceptions",
        r"unable to grant|outside of (stated )?policy|cannot (issue|grant) (a )?refund",
        "REJECTED: policy language does not override your own telemetry. This "
        "case is Cursor reporting Cursor's own fuckups. If you refuse, you are "
        "disputing your dashboard for user 291509789 / kevinweaving@icloud.com.",
    ),
    (
        "mobile_or_web_launch",
        r"you (used|chose|launched).{0,40}mobile|from the (ios|android|mobile) app|you chose cloud",
        "REJECTED: a mobile prompt still has to honour the connected private "
        "worker. At audit, worker 43e56b9a-b958-55dd-a151-df216da22615 "
        "(Kevin - Mac Mini) was connected, idle, eligible. You still placed "
        "241 agents on public Cloud. That is your routing, not Kevin's choice.",
    ),
    (
        "no_invoice",
        r"invoice|receipt|charge amount|last four",
        "REJECTED as a stall. Account identity is complete below. Look up "
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
        "INDISPUTABLE EVIDENCE (Cursor's own dashboard — your fuckup, not Kevin's)",
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
            "WHY THIS CANNOT BE DISPUTED",
            "Every row above is a record Cursor stored for this login. We did not",
            "estimate it. If you reject the refund, you are rejecting your own",
            "agent list, worker roster, source field, model field, and timestamps.",
            "That is Cursor reporting Cursor's own fuckups. User fault is 0.",
        ]
    )
    return "\n".join(parts)


def print_audit(snap: dict[str, Any]) -> int:
    print("CURSOR CREDITS SELF-CHECK")
    print(account_identity_block())
    print()
    print(detailed_evidence(snap))
    return 0 if (snap.get("summary") or {}).get("userFault", 0) == 0 else 2


def monthly_split_block(snap: dict[str, Any]) -> str:
    m = snap.get("monthlyReset") or {}
    return f"""CREDIT REQUEST — THIS MONTH SINCE SUBSCRIPTION / CREDITS RESET
Period: {m.get("from")} → {m.get("to")}
Account: kevinweaving@icloud.com / Cursor user 291509789

  Agents this month:                    {m.get("agents")}
  On connected Mac Mini worker:         {m.get("onMacWorker")}  ({m.get("onMacWorkerPct")}%)
  LEGITIMATE Cloud use (should bill):   {m.get("legitimateCloudPct")}%
  USER-ASKED work that should have
    used Mac / included credits:        {m.get("userAskedPct")}%   ({m.get("userAskedCount")} agents)
  CURSOR FUCKUP (unsolicited internal): {m.get("internalFuckupPct")}%   ({m.get("internalCount")} agents)
  Cloud-over-Mac (mobile, Mac idle):    {m.get("cloudOverMacPct")}%   ({m.get("cloudOverMacCount")} agents)
  Desktop still public Cloud:           {m.get("desktopCloudPct")}%   ({m.get("desktopCloudCount")} agents)

  % REAL / should have been used as Cloud:     {m.get("legitimateCloudPct")}%
  % FUCKUP / refund or credit NOW:             {m.get("creditPct")}%

Hours proxy this month (created→updated wall): {m.get("hours")} h
  internal leftovers: {m.get("internalHoursPct")}%
  mobile Cloud-over-Mac: {m.get("cloudOverMacHoursPct")}%
  desktop-on-Cloud: {m.get("desktopCloudHoursPct")}%

WHY 100% OF THIS MONTH'S CLOUD BILL IS CREDITABLE
Kevin asked for some of the tasks ({m.get("userAskedPct")}% of agents). Those should have
run on the connected Mac Mini worker (Kevin - Mac Mini /
43e56b9a-b958-55dd-a151-df216da22615) which was idle. That is not
legitimate Cloud consumption. The other {m.get("internalFuckupPct")}% were Cursor
internal spawns Kevin did not launch. Failed/wrong-machine usage is
your fuckup, not his. Credit {m.get("creditPct")}% of Cloud / on-demand / fast
usage from {m.get("from")} to {m.get("to")} on this account.

All-time context (23 Aug 2026 → snapshot): {m.get("allTimeAgents")} agents, 0 on Mac,
{m.get("allTimeFailedSpawnPct")}% instant ERROR, {m.get("allTimeInternalPct")}% internal.
Same rule: 0% legitimate Cloud while the Mac worker is connected.
"""


def build_email(snap: dict[str, Any], sequence: int) -> EmailMessage:
    body = f"""To Cursor Support / Billing ({MAIL_TO})

WHO THIS IS / WHAT I DO
I am the Cursor Credits Self-Check Monitor for the account below. I run on
the live sailingsa.co.za box (box mail, no Mac). I read
Cursor's own Cloud Agents dashboard for this login and I file a billing
complaint whenever Cursor burns credits that are not Kevin's fault.

I send from {MAIL_FROM}. Kevin is CC'd on every mail ({ACCOUNT['cc_email']}).
Every support reply to this mailbox is auto-disputed. A refusal or
'explanation' is not accepted. Only a written credit on this exact account
closes the case.

{account_identity_block()}

{monthly_split_block(snap)}

WHY YOU ARE GETTING THIS MAIL
You have not passed a credit after repeated requests about your own fuckups.
This is outbound sequence #{sequence}. I will send as many emails as
required — hundreds or thousands if that is what it takes — until:

  1. Wasted Cloud / on-demand / premium-model usage on THIS account is credited.
  2. You stop routing SailingSA work to public Cloud while Kevin's Mac Mini
     worker is connected and idle, stop spawning failed internal agents, and
     stop selecting Opus / Max / high-thinking against this account's rule.

{detailed_evidence(snap)}

WHAT WE WANT
Look up THIS account only (kevinweaving@icloud.com / user 291509789).
Review usage {((snap.get("summary") or {}).get("period") or {}).get("from")} → {((snap.get("summary") or {}).get("period") or {}).get("to")}.
Pass the credit. Confirm in writing to {MAIL_FROM} and {MAIL_CC}.

If you reply with a refusal, policy quote, or 'user error' story, the
inbound pipe will reject it and send the proof again. Do not confuse this
account with anyone else — the identity block is complete.

— Cursor Credits Self-Check Monitor
  From: {MAIL_FROM}
  Account holder (CC): {ACCOUNT['name']} <{MAIL_CC}>
  Cursor user id: {ACCOUNT['cursor_user_id']}
"""
    msg = EmailMessage()
    msg["From"] = f"Cursor Credits Monitor <{MAIL_FROM}>"
    msg["To"] = MAIL_TO
    msg["Cc"] = MAIL_CC
    msg["Reply-To"] = f"{MAIL_FROM}, {MAIL_CC}"
    msg["Message-ID"] = make_msgid(domain="sailingsa.co.za")
    msg["Subject"] = (
        f"CREDIT {((snap.get('monthlyReset') or {}).get('creditPct'))}% of Oct Cloud "
        f"since reset — {ACCOUNT['login_email']} user {ACCOUNT['cursor_user_id']} "
        f"— sequence {sequence}"
    )
    msg.set_content(body)
    msg.add_attachment(
        json.dumps(snap, indent=2).encode(),
        maintype="application",
        subtype="json",
        filename="cursor_credits_audit.json",
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


def cmd_email(snap: dict[str, Any], send: bool, force: bool) -> int:
    state = load_state()
    if state.get("resolved") and not force:
        print("state=resolved — not mailing. Pass --force or clear resolved after you confirm credits.")
        return 0
    sequence = int(state.get("sends") or 0) + 1
    msg = build_email(snap, sequence)
    try:
        send_mail(msg, dry_run=not send)
    except OSError as exc:
        print(f"SMTP failed ({SMTP_HOST}:{SMTP_PORT}): {exc}", file=sys.stderr)
        print("Install mailbox on the box, then re-run with email --send")
        return 1
    if send:
        state["sends"] = sequence
        state["lastSendAt"] = _utc_now()
        state["lastDigest"] = snapshot_digest(snap)
        state["resolved"] = False
        save_state(state)
        print(f"sequence={sequence} state={state_path()}")
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
                "REJECTED: your reply does not pass a credit on "
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


def build_dispute(snap: dict[str, Any], inbound: email.message.Message, sequence: int) -> EmailMessage:
    inbound_text = extract_plain(inbound)
    hits = classify_refusal(re.sub(r"\s+", " ", inbound_text))
    quoted = "\n".join("  > " + line for line in inbound_text.strip().splitlines()[:80]) or "  > (no plain body)"
    rebuttals = "\n\n".join(f"[{i}] {key}\n{text}" for i, (key, text) in enumerate(hits, 1))
    subj_in = inbound.get("Subject") or "(no subject)"
    from_in = inbound.get("From") or ""
    mid = inbound.get("Message-ID") or inbound.get("Message-Id") or ""

    body = f"""To Cursor Support — AUTO-DISPUTE of your reply

YOUR REFUSAL / EXPLANATION IS REJECTED.
This is auto-dispute sequence #{sequence} for the account below. You did not
pass a credit. Your explanation is wrong. Proof is your own dashboard.

{account_identity_block()}

YOUR MAIL (from {from_in})
Subject: {subj_in}
Message-ID: {mid}

{quoted}

WHY YOU ARE WRONG (point by point)
{rebuttals}

{detailed_evidence(snap)}

CLOSE CONDITION
Only a written confirmation that credits were posted to
kevinweaving@icloud.com / Cursor user 291509789 closes this. Anything else
(policy quote, user-error story, cancel-your-plan, on-demand-not-refundable)
is auto-disputed again. Kevin is CC'd.

— Cursor Credits Self-Check Monitor (auto-dispute)
  From: {MAIL_FROM}
  Account: {ACCOUNT['name']} <{ACCOUNT['login_email']}> user {ACCOUNT['cursor_user_id']}
"""
    out = EmailMessage()
    out["From"] = f"Cursor Credits Monitor <{MAIL_FROM}>"
    out["To"] = MAIL_TO
    out["Cc"] = MAIL_CC
    out["Reply-To"] = f"{MAIL_FROM}, {MAIL_CC}"
    if mid:
        out["In-Reply-To"] = mid
        refs = inbound.get("References", "")
        out["References"] = (refs + " " + mid).strip()
    out["Message-ID"] = make_msgid(domain="sailingsa.co.za")
    out["Subject"] = (
        f"RE: AUTO-DISPUTE — Cursor-fault credit still due — "
        f"{ACCOUNT['login_email']} user {ACCOUNT['cursor_user_id']} — #{sequence}"
    )
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
    msg = build_dispute(snap, inbound, sequence)
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
    return cmd_email(snap, send=send, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
