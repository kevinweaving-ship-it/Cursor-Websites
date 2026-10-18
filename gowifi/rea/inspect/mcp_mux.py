#!/usr/bin/env python3
"""Stdio MCP multiplexer for the existing OpenAI tunnel main channel.

Preserves all 170 REA tools and adds the dedicated read-only audit_* tools
without modifying the rea-agents package. ChatGPT talks to main only.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from typing import Any

REA_CMD = os.environ.get("REA_MCP_CMD", "/opt/rea/bin/rea mcp").split()
AUDIT_CMD = os.environ.get("REA_AUDIT_MCP_CMD", "/opt/rea/inspect/bin/audit-mcp").split()
AUDIT_PREFIX = "audit_"


class StdioChild:
    def __init__(self, argv: list[str]) -> None:
        env = os.environ.copy()
        env["HOME"] = env.get("HOME", "/opt/rea")
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self.replies: queue.Queue[dict[str, Any]] = queue.Queue()
        self._id = 0
        self._lock = threading.Lock()
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        assert self.proc.stdout is not None
        for raw in self.proc.stdout:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if "id" in msg:
                self.replies.put(msg)

    def next_id(self) -> int:
        with self._lock:
            self._id += 1
            return self._id

    def send_notification(self, method: str, params: Any = None) -> None:
        assert self.proc.stdin is not None
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        self.proc.stdin.flush()

    def request(self, method: str, params: Any = None, timeout: float = 45) -> dict[str, Any]:
        assert self.proc.stdin is not None
        req_id = self.next_id()
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        self.proc.stdin.flush()
        deadline_q: list[dict[str, Any]] = []
        import time

        end = time.time() + timeout
        while time.time() < end:
            try:
                msg = self.replies.get(timeout=0.2)
            except queue.Empty:
                continue
            if msg.get("id") == req_id:
                for extra in deadline_q:
                    self.replies.put(extra)
                return msg
            deadline_q.append(msg)
        for extra in deadline_q:
            self.replies.put(extra)
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": f"{method} timed out"}}


def write_message(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def merge_initialize(rea: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    result = dict(rea.get("result") or {})
    extra = (
        " Dedicated read-only audit_* tools inspect GoWifi and SailingSA production "
        "source, nginx, logs, and SELECT-only SQL. Prefer audit_* over capture_process_scenario."
    )
    result["instructions"] = (result.get("instructions") or "") + extra
    # Keep REA identity so the existing ChatGPT connector still matches.
    return result


def merge_tools(rea: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    rea_tools = list(((rea.get("result") or {}).get("tools")) or [])
    audit_tools = list(((audit.get("result") or {}).get("tools")) or [])
    seen = {tool.get("name") for tool in rea_tools}
    merged = list(rea_tools)
    for tool in audit_tools:
        if tool.get("name") not in seen:
            merged.append(tool)
    return {"tools": merged}


def read_parent_messages():
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return
        if line.startswith(b"{") or line.startswith(b"["):
            yield json.loads(line.decode("utf-8"))
            continue
        decoded = line.decode("utf-8", errors="replace")
        if decoded.lower().startswith("content-length:"):
            length = int(decoded.split(":", 1)[1].strip())
            while True:
                header = sys.stdin.buffer.readline()
                if not header or header in (b"\r\n", b"\n"):
                    break
            body = sys.stdin.buffer.read(length)
            yield json.loads(body.decode("utf-8"))


def main() -> int:
    rea = StdioChild(REA_CMD)
    audit = StdioChild(AUDIT_CMD)
    for msg in read_parent_messages():
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params")
        if method is None:
            continue
        if str(method).startswith("notifications/"):
            rea.send_notification(str(method), params)
            audit.send_notification(str(method), params)
            continue
        if method == "initialize":
            rea_init = rea.request("initialize", params)
            audit.request("initialize", params)
            if "error" in rea_init and "result" not in rea_init:
                write_message({"jsonrpc": "2.0", "id": req_id, "error": rea_init["error"]})
                continue
            write_message({"jsonrpc": "2.0", "id": req_id, "result": merge_initialize(rea_init, {})})
            continue
        if method == "tools/list":
            rea_list = rea.request("tools/list", params)
            audit_list = audit.request("tools/list", params)
            if "error" in rea_list and "result" not in rea_list:
                write_message({"jsonrpc": "2.0", "id": req_id, "error": rea_list["error"]})
                continue
            write_message({"jsonrpc": "2.0", "id": req_id, "result": merge_tools(rea_list, audit_list)})
            continue
        if method == "tools/call":
            name = str((params or {}).get("name") or "")
            child = audit if name.startswith(AUDIT_PREFIX) else rea
            child_reply = child.request("tools/call", params)
            if "result" in child_reply:
                write_message({"jsonrpc": "2.0", "id": req_id, "result": child_reply["result"]})
            else:
                write_message({"jsonrpc": "2.0", "id": req_id, "error": child_reply.get("error") or {"code": -32000, "message": "tool failed"}})
            continue
        if method == "ping":
            write_message({"jsonrpc": "2.0", "id": req_id, "result": {}})
            continue
        # prompts/list and other REA methods stay on REA.
        child_reply = rea.request(str(method), params)
        if "result" in child_reply:
            write_message({"jsonrpc": "2.0", "id": req_id, "result": child_reply["result"]})
        else:
            write_message({"jsonrpc": "2.0", "id": req_id, "error": child_reply.get("error") or {"code": -32601, "message": str(method)}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
