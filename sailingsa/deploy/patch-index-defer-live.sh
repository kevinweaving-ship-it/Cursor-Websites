#!/usr/bin/env bash
# Deprecated alias — use restore-pre-grok-header-live.sh (site-wide header + defer fix).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec bash "$ROOT/sailingsa/deploy/restore-pre-grok-header-live.sh"
