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
- GitHub push/PR: neither box has `gh` or a working git remote credential.
  Local git on `/var/www/sailingsa` works; publish/PR still needs Cursor,
  Mac `gh`, or the ChatGPT GitHub connector (previously 403).
- Visual browser checks of the public site: REA `capture_browser_scenario`
  with `/opt/chromium/chrome`, or Cursor browser tools.
- WhatsApp delay root-cause: access is enabled; investigation is left to
  ChatGPT + REA.

## Denied on purpose

`/root/secrets`, `/root/gowifi-upp`, Mail-in-a-Box mail data, TLS private
keys, `/opt/arial-whatsapp-poc/state/auth`, `/etc/arial-whatsapp-poc.env`,
unrestricted root, public extra services, `chmod 777`.
