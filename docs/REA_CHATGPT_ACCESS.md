# ChatGPT + REA access (Arial and SailingSA)

Operational access for ChatGPT through the existing REA 6.4.0 tunnel on
the Arial / GoWifi box. Cursor is not required for routine work once the
connector has rediscovered `ops_*` tools.

## Architecture

ChatGPT talks only to tunnel channel `main` (`openai-rea-tunnel`). The mux
exposes REA tools plus `audit_*` and `ops_*`. The tunnel runs as `rea`
(UID 996) with `NoNewPrivileges=yes`, so ChatGPT cannot sudo from that
process. Privileged work uses:

- GoWifi: `ssh -i /opt/rea/.ssh/id_rea_ops root@127.0.0.1` → ForceCommand
  `/usr/local/sbin/rea-ops-helper`
- SailingSA: `ssh sailingsa-ops` → `rea-ops` ForceCommand
  `/opt/rea-ops/bin/ops-agent`

## How access survives reboot and connector updates

| Item | Survives reboot | Survives connector update |
| --- | --- | --- |
| User `rea` / `rea-ops` / `rea-ro` | yes | yes |
| Groups `adm`, `systemd-journal`, `www-data` | yes | yes |
| POSIX ACLs on app trees | yes (ext4) | yes |
| `/etc/sudoers.d/rea-ops` | yes | yes |
| ForceCommand authorized_keys | yes | yes |
| `openai-rea-tunnel.service` enabled | yes | must stay `ExecStart` / mux path |
| ChatGPT tool list | n/a | **refresh connector + new chat** |

## Recovery if access breaks

1. On GoWifi: `systemctl is-active openai-rea-tunnel` and
   `curl -sS http://127.0.0.1:18780/readyz`.
2. Confirm mux: `grep OPS_CMD /opt/rea/inspect/bin/mcp-mux`.
3. Confirm helper key:
   `grep rea-ops-helper /root/.ssh/authorized_keys`.
4. As `rea`: `/opt/rea/ops/bin/rea-ops whatsapp-status`.
5. As `rea`: `ssh -o BatchMode=yes sailingsa-ops status sailingsa-api`.
6. Re-run `gowifi/rea/ops/install-gowifi-ops.sh` and
   `install-sailingsa-ops.sh` if files were overwritten.
7. In ChatGPT: Connectors → refresh the custom MCP plugin → new chat.
   Server config cannot complete that step.

## What still needs a human, Cursor, browser, or GitHub

- ChatGPT Business/Enterprise/Edu to add or refresh a custom MCP connector.
  The mobile app cannot add connectors.
- OpenAI safety may still block `capture_process_scenario`. Use `ops_*`.
- Tunnel deadline ~120s. Long jobs: `ops_jobs` start then poll.
- GitHub write: REA has its own ed25519 keys. HTTPS clone of the public
  repo works. Push stays unavailable until a human adds a **write deploy
  key**. Cursor cannot add that key (403). The ChatGPT GitHub connector
  is **UNVERIFIED** from this server path — confirm PR create in ChatGPT
  after connector refresh. `gh` may be installed as a CLI fallback; it
  still needs a human-provided token (`gh auth login`) and must never
  receive Cursor’s token.

  GoWifi (`/opt/rea/.ssh/id_rea_github.pub`):
  `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIZUbaqtPqcweuv3PR+IO5t+XJH0A8DKpNl81OIhSkNP rea-ops-github@gowifi`

  SailingSA (`/opt/rea-ops/.ssh/id_rea_github.pub`):
  `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKKpToPKDJLUM1HQ810tF6iPgduZEU4CbvutALEQQf6b rea-ops-github@sailingsa`
- Visual browser checks of the public site: REA `capture_browser_scenario`
  with `/opt/chromium/chrome`, or Cursor browser tools.
- WhatsApp delay root-cause: access is enabled; investigation is left to
  ChatGPT + REA.

## Deploy path ChatGPT should use

1. `ops_deploy` `stage-api` / `plan-api` then `api` on `sailingsa`.
   Wraps the **live** `/root/deploy_api_verified.sh`, which currently
   refuses any `api.py` that is not the Master/Gold hash. Restore
   `chattr +i` if it was set. Do not bypass that Gold check.
2. Frontend: write or `ops_transfer` a zip to `/opt/rea-ops/stage/frontend.zip`,
   then `ops_deploy` `frontend` (excludes `data/hub_hero.json`).
3. Harmless static probe: write `rea-ops-probe.html` to stage, `static`,
   `ops_http_check`, then `static-clean`.
4. Services: `ops_health` / `ops_service` `status` first. `nginx` reload
   is allowed after `nginx -t`. Do not restart `arial-whatsapp-poc` while UP.
5. Long work: `ops_jobs` start → status → cancel.

## Denied on purpose

`/root/secrets`, `/root/gowifi-upp`, Mail-in-a-Box mail data, TLS private
keys, `/opt/arial-whatsapp-poc/state/auth`, `/etc/arial-whatsapp-poc.env`,
unrestricted root, public extra services, `chmod 777`.
