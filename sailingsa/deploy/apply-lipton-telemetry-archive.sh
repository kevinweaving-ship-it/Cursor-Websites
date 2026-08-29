#!/bin/bash
# Copy Lipton Vakaros GPS + Firestore dumps onto live disk, then load Postgres.
# Does not invent points. Does not restart the API.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
expect "$ROOT/sailingsa/deploy/apply-lipton-telemetry-archive.exp"
