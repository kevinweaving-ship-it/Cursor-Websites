# SailingSA WhatsApp server health

Add-on to permanent housekeeping. **Does not** change `api.py`, pool, SQL, nginx, frontend, or `sailingsa-housekeeping.py`.

## Existing WhatsApp engine (reused)

Isolated Baileys worker already on live:

- Unit: `arial-whatsapp-poc.service` (user `wapoc`)
- Code: `/opt/arial-whatsapp-poc/poc.js` — Baileys 6.7.24
- Control API: `http://127.0.0.1:$WAPOC_PORT/send` (port **8009**)
- Auth: `Authorization: Bearer $WAPOC_TOKEN` from `/etc/arial-whatsapp-poc.env`
- Same path as `/opt/arial-whatsapp-poc/alert_watcher.py` `send_admin()` and `validate.py`

Number format: E.164 digits (`0720821111` → `27720821111`).

Do **not** install another WhatsApp service.

## Install

```bash
scp -i ~/.ssh/sailingsa_live_key sailingsa/deploy/sailingsa-server-monitor.py \
  sailingsa/deploy/sailingsa-server-monitor.wrapper \
  sailingsa/deploy/server-monitor.conf \
  sailingsa/deploy/cron.d-sailingsa-server-monitor \
  sailingsa/deploy/logrotate-sailingsa-server-monitor \
  sailingsa/deploy/install-server-monitor.sh \
  root@102.218.215.253:/root/incoming/server-monitor/

# Files only, then validate, then enable:
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  'bash /root/incoming/server-monitor/install-server-monitor.sh'
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  '/usr/local/sbin/sailingsa-server-monitor --test-send'
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  '/usr/local/sbin/sailingsa-server-monitor --sample-daily'
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  '/usr/local/sbin/sailingsa-server-monitor --dedupe-test'
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  '/usr/local/sbin/sailingsa-server-monitor --restart-grace-test'
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  'bash /root/incoming/server-monitor/install-server-monitor.sh --enable'
```

## Schedule (`CRON_TZ=Africa/Johannesburg`)

| When | Command |
|---|---|
| every 5 minutes | `--check` (alerts only) |
| 10:30 daily | `--daily` (health report + alerts) |

`/etc/cron.d/sailingsa_server_monitor`  
Lock: `/var/lock/sailingsa-server-monitor.lock`  
State: `/var/lib/sailingsa/server-monitor-state.json` (0600)  
Log: `/var/log/sailingsa-server-monitor.log` (no tokens / no phone numbers)

## Alert thresholds + dedupe

| Condition | WARNING | CRITICAL |
|---|---|---|
| Disk | ≥75% | ≥85% |
| API down | — | HTTP still down **after 120s restart grace** |
| PG down | — | unresponsive |
| 5xx spike | — | ≥10 in 5 min (nginx access) |
| pool / too-many-clients | — | any match in last 5 min journal |
| idle-in-transaction | ≥3 | ≥8 |
| API workers | — | &lt;3 while service active |
| housekeeping | fail/stale &gt;36h | — |
| full backup missing/invalid | — | yes |
| RAM/swap/load | sustained swap≥80% and load5≥3×nproc | avail&lt;120MB+swap≥92% or load5≥6×nproc (2 consecutive checks) |
| restore service | 8001 enabled/active | — |

Dedupe: one WhatsApp when a condition **begins**, one if **severity rises**, one **RECOVERED** when healthy. Same level = no resend. 8002 is never alerted.

### API restart grace (all tasks)

A normal `systemctl restart sailingsa-api` takes well under **120 seconds** (4 uvicorn workers). The 5-minute `--check` will often land mid-restart (`http=0` while systemd is still `active`). That is **not** an outage.

- First failed HTTP probe waits up to **120s**, re-probing every **15s**.
- Recovered inside that window → **no WhatsApp** (and no RECOVERED, because nothing was sent).
- Still down after 120s → CRITICAL. That is longer than a normal restart.
- Worker-count CRITICAL is suppressed while the API is down/restarting (avoids a second false alert).

Every deploy / Event URL / live-edit task that restarts the API is covered by this grace. Do not expect a CRITICAL for a clean restart.

Override on the box if needed (`/etc/sailingsa/server-monitor.conf` or env):

```
API_RESTART_GRACE_S=120
API_RESTART_PROBE_S=15
```

`SAILINGSA_API_RESTART_GRACE_S` / `SAILINGSA_API_RESTART_PROBE_S` win over conf.

Prove locally: `/usr/local/sbin/sailingsa-server-monitor --restart-grace-test`

Daily report is always sent at 10:30 even when healthy.

WhatsApp failure: log `wa_send failed: <ExceptionType>` and retry next cycle. Never restart API.
