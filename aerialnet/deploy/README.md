# Aerialnet keypad duplicate (Hansekop + Voëlklip)

Test / audit copies of the live SailingSA keypads, on the GoWifi / Aerialnet box.

| Live gold (leave on Sailing) | Aerialnet copy |
|---|---|
| https://sailingsa.co.za/arial/ | https://aerialnet.co.za/hansekop/ |
| https://sailingsa.co.za/voelklip/ | https://aerialnet.co.za/voelklip/ |

Hansekop Olarm + Tuya run on the GoWifi box (`:8003`, `tuya-sharing` `:8007`). Keypad nginx lives in Mail-in-a-Box’s extra file `/home/user-data/www/aerialnet.co.za.conf` (same pattern as `gowifi.co.za.conf`). Mail owns `local.conf` and may rewrite it; it **includes** the extra file, so keypad APIs survive a mail rebuild. Do not patch `local.conf`. Alarm WhatsApp (Baileys) also runs on this box; Sailing must not keep the same number logged in. The keypad WhatsApp tab reads `/var/www/aerialnet/data/whatsapp_log.jsonl` (wapoc must be able to write that file).

Sailing `/arial/` still serves the old keypad API; its Tuya sharing worker is stopped, so the SSA breaker is stale. Voëlklip home cams stay on Sailing (`sailingsa.co.za:8443` / `:8444`) until hikpoc is copied.

The Aerialnet landing header has **User Login**, which opens the Hansekop keypad (`/hansekop/`).

## Deploy

From a host that can SSH to `box.gowifi.co.za` (`102.209.119.186`):

```bash
GOWIFI_SSH_KEY=~/.ssh/your_key bash aerialnet/deploy/deploy-to-gowifi-box.sh
```

On the box, tokens live in `/etc/aerialnet-olarm.env` and `/etc/aerialnet-tuya.env` (copied from Sailing when reachable; never commit them).
