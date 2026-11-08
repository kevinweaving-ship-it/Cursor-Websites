#!/usr/bin/env bash
# Codex-on-Mac trial gate. Proves SSH + live fetch. Does not deploy.
# Reversible: delete this file. Safe to run read-only against production.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "FAIL: not This Mac ($(uname -s)). Run from Kevin's Mac Mini."
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "FAIL: codex not on PATH. Open the ChatGPT desktop Codex app or install the CLI, then sign in with ChatGPT."
  exit 1
fi

KEY="${HOME}/.ssh/sailingsa_live_key"
if [[ ! -f "$KEY" ]]; then
  echo "FAIL: missing $KEY"
  exit 1
fi

echo "SSH…"
ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=15 \
  root@102.218.215.253 "echo SSH KEY WORKS" | grep -q "SSH KEY WORKS"
echo "SSH OK"

echo "Live…"
code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://sailingsa.co.za/blank.html)"
if [[ "$code" != "200" ]]; then
  echo "FAIL: blank.html HTTP $code"
  exit 1
fi
echo "Live OK (blank.html 200)"

echo "PASS: Mac + Codex + SSH + live. Deploy only if this chat authorised a live change."
echo "Next: finish that one task in Codex. Do not open Cursor Cloud. Do not switch models."
