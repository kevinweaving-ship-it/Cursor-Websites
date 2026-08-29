#!/bin/bash
set -euo pipefail
echo '=== units ==='
systemctl list-units --all '*lipton*' --no-pager 2>/dev/null || true
ls /etc/systemd/system/*lipton* /lib/systemd/system/*lipton* /usr/local/lib/*lipton* /usr/local/sbin/*lipton* 2>/dev/null || true
echo '=== guard ==='
head -80 /usr/local/lib/lipton_public_watch_guard.sh 2>/dev/null || true
echo '=== sbin watch head ==='
head -80 /usr/local/sbin/lipton_public_not_dev_watch.py 2>/dev/null || true
echo '=== apply once ==='
ls -la /usr/local/sbin/lipton_apply_nginx_public_proxy_once.py /usr/local/sbin/lipton_* 2>/dev/null || true
