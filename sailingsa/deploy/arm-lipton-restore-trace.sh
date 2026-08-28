#!/bin/bash
# Record WHO writes nginx snippet / api.py / unit files. Do not guess.
set -euo pipefail
EV=/root/lipton-trace-evidence
LOG=/root/lipton-trace.log
mkdir -p "$EV"
ts() { date -Is; }

{
  echo "===== TRACE START $(ts) ====="
  echo "=== running lipton procs ==="
  ps auxww | grep -Ei 'lipton|lw-g|lw-gold|watch_guard|url-hold' | grep -v grep || true
  echo "=== pstree ==="
  pstree -ap 2178771 2>/dev/null || true
  pgrep -af 'lw-g' || true
  echo "=== /proc for lw-g loops ==="
  for pid in $(pgrep -f 'lw-g' || true); do
    echo "--- pid $pid ---"
    tr '\0' ' ' < /proc/$pid/cmdline; echo
    echo "ppid=$(awk '/PPid/{print $2}' /proc/$pid/status) comm=$(awk '/Name/{print $2}' /proc/$pid/status)"
    ls -l /proc/$pid/exe /proc/$pid/cwd 2>/dev/null || true
    echo "open files:"
    ls -l /proc/$pid/fd 2>/dev/null | awk '{print $NF}' | grep -E 'nginx|api.py|lipton|lw-g|cron|systemd' || true
  done
} >> "$LOG" 2>&1

# Copy every live writer we can see, before anyone stubs them
cp -a /root/lw-g14c.py "$EV/" 2>/dev/null || true
cp -a /usr/local/lib/lipton_public_watch_guard.sh "$EV/" 2>/dev/null || true
cp -a /usr/local/sbin/lipton_public_watch_guard.sh "$EV/" 2>/dev/null || true
cp -a /etc/systemd/system/sailingsa-lipton-public-watch.service "$EV/" 2>/dev/null || true
cp -a /etc/systemd/system/sailingsa-lipton-url-hold.service "$EV/" 2>/dev/null || true
cp -a /etc/nginx/snippets/lipton-public-proxy.conf "$EV/snippet-now.conf" 2>/dev/null || true
ls /root/lw-g*.py /root/lw-gold*.py /root/lw-guard*.sh 2>/dev/null | tee -a "$LOG" | while read -r f; do
  cp -a "$f" "$EV/" 2>/dev/null || true
done

echo "=== copied evidence ===" >> "$LOG"
ls -la "$EV" >> "$LOG"

echo "=== lw-g14c.py head ===" >> "$LOG"
head -80 /root/lw-g14c.py >> "$LOG" 2>&1 || true
echo "=== lw-g14c.py writes/markers ===" >> "$LOG"
grep -nE 'chattr|proxy_pass|NOT_DEV|snippet|api.py|nginx|systemd|cron|open\(|write|LIPTON_' /root/lw-g14c.py >> "$LOG" 2>&1 || true
echo "=== watch_guard.sh ===" >> "$LOG"
wc -c /usr/local/lib/lipton_public_watch_guard.sh >> "$LOG"
head -120 /usr/local/lib/lipton_public_watch_guard.sh >> "$LOG" 2>&1 || true

# auditd if present
if command -v auditctl >/dev/null 2>&1; then
  systemctl start auditd 2>/dev/null || service auditd start 2>/dev/null || true
  auditctl -D 2>/dev/null || true
  auditctl -w /etc/nginx/snippets/lipton-public-proxy.conf -p wa -k lipton_snip
  auditctl -w /var/www/sailingsa/api/api.py -p wa -k lipton_api
  auditctl -w /etc/systemd/system/sailingsa-lipton-public-watch.service -p wa -k lipton_unit
  auditctl -w /usr/local/lib/lipton_public_watch_guard.sh -p wa -k lipton_guard
  echo "auditctl rules set" >> "$LOG"
  auditctl -l >> "$LOG" 2>&1 || true
else
  echo "auditctl missing — using inotify + poll" >> "$LOG"
fi

# inotify logger
if command -v inotifywait >/dev/null 2>&1; then
  nohup inotifywait -m -e modify,attrib,move,create,delete,close_write \
    --timefmt '%Y-%m-%dT%H:%M:%S' --format '%T %e %w%f' \
    /etc/nginx/snippets/lipton-public-proxy.conf \
    /var/www/sailingsa/api/api.py \
    /etc/systemd/system/sailingsa-lipton-public-watch.service \
    /etc/cron.d \
    /usr/local/lib \
    /root \
    >> /root/lipton-inotify.log 2>&1 &
  echo "inotify pid $!" >> "$LOG"
else
  echo "inotifywait missing" >> "$LOG"
fi

# poller: on mtime change dump lsof + ps + last audit
cat > /root/lipton-trace-poller.py <<'PY'
#!/usr/bin/python3
import os, time, subprocess, hashlib
from pathlib import Path

LOG = Path("/root/lipton-trace.log")
FILES = [
    Path("/etc/nginx/snippets/lipton-public-proxy.conf"),
    Path("/var/www/sailingsa/api/api.py"),
    Path("/etc/systemd/system/sailingsa-lipton-public-watch.service"),
    Path("/etc/systemd/system/sailingsa-lipton-url-hold.service"),
    Path("/usr/local/lib/lipton_public_watch_guard.sh"),
    Path("/root/lw-g14c.py"),
]

def stamp(p: Path):
    try:
        st = p.stat()
        data = p.read_bytes()[:200]
        return (st.st_mtime_ns, st.st_size, hashlib.sha1(data).hexdigest(), data[:80])
    except OSError as e:
        return (0, 0, str(e), b"")

def dump(reason: str):
    lines = [f"\n===== CHANGE {time.strftime('%Y-%m-%dT%H:%M:%S')} {reason} ====="]
    try:
        out = subprocess.check_output(["ps","auxww"], text=True, errors="replace")
        for ln in out.splitlines():
            if any(x in ln.lower() for x in ("lipton", "lw-g", "lw-gold", "watch_guard", "nginx", "chattr")):
                lines.append(ln)
    except Exception as e:
        lines.append(f"ps fail {e}")
    try:
        out = subprocess.check_output(["lsof", "+D", "/etc/nginx/snippets"], text=True, errors="replace", timeout=5)
        lines.append("lsof snippets:\n" + out)
    except Exception as e:
        lines.append(f"lsof fail {e}")
    try:
        out = subprocess.check_output(["ausearch", "-k", "lipton_snip", "-ts", "recent"], text=True, errors="replace", timeout=8)
        lines.append("ausearch snip:\n" + out[-4000:])
    except Exception as e:
        lines.append(f"ausearch fail {e}")
    LOG.write_text(LOG.read_text(encoding="utf-8", errors="replace") + "\n".join(lines) + "\n", encoding="utf-8")

prev = {p: stamp(p) for p in FILES}
LOG.write_text(LOG.read_text(encoding="utf-8", errors="replace") + f"\npoller start {time.strftime('%Y-%m-%dT%H:%M:%S')} stamps { {str(k):v[0] for k,v in prev.items()} }\n", encoding="utf-8")
while True:
    time.sleep(0.4)
    for p in FILES:
        now = stamp(p)
        if now != prev[p]:
            dump(f"{p} {prev[p]} -> {now}")
            prev[p] = now
PY
chmod 755 /root/lipton-trace-poller.py
nohup python3 /root/lipton-trace-poller.py >/tmp/lipton-trace-poller.out 2>&1 &
echo "poller pid $!" >> "$LOG"

echo "===== TRACE ARMED $(ts) =====" >> "$LOG"
echo "evidence $EV"
echo "log $LOG"
wc -c /root/lw-g14c.py /usr/local/lib/lipton_public_watch_guard.sh 2>/dev/null || true
pgrep -af 'lw-g14c|trace-poller|inotifywait' || true
tail -30 "$LOG"
