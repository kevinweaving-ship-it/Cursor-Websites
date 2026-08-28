#!/bin/bash
set -euo pipefail
echo '=== unit files ==='
systemctl cat sailingsa-lipton-public-watch.service || true
echo '===== HOLD ====='
systemctl cat sailingsa-lipton-url-hold.service || true
echo '=== unit paths ==='
systemctl show -p FragmentPath -p DropInPaths sailingsa-lipton-public-watch.service sailingsa-lipton-url-hold.service || true
ls -la /etc/systemd/system/sailingsa-lipton* /lib/systemd/system/sailingsa-lipton* 2>/dev/null || true
echo '=== cron contents ==='
echo '-- aa --'; cat /etc/cron.d/aa-lipton-url-hold || true
echo '-- not-dev --'; cat /etc/cron.d/sailingsa-lipton-public-not-dev || true
echo '-- zzz --'; cat /etc/cron.d/zzz-lipton-public-live || true
