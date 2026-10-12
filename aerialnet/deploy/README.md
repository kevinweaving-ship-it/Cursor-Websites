# Aerialnet keypad duplicate (Hansekop + Voëlklip)

Test / audit copies of the live SailingSA keypads, on the GoWifi / Aerialnet box.

| Live gold (leave on Sailing) | Aerialnet copy |
|---|---|
| https://sailingsa.co.za/arial/ | https://aerialnet.co.za/hansekop/ |
| https://sailingsa.co.za/voelklip/ | https://aerialnet.co.za/voelklip/ |

Cams stay on the Sailing box (`sailingsa.co.za:8443` / `:8444`). WhatsApp stays on Sailing until the GoWifi number is linked here.

Olarm + Tuya env files are on the GoWifi box (`/etc/aerialnet-olarm.env`, `/etc/aerialnet-tuya.env`; never commit them). Public `/api/arial/` goes to Hansekop uvicorn `127.0.0.1:8003`. Public `/api/voelklip/` is rewritten to `/api/arial/` on Voëlklip uvicorn `127.0.0.1:8004`. Do not proxy these to sailingsa.co.za, and do not SSH to the Sailing box from the install.

The Aerialnet landing header has **User Login**, which opens the Hansekop keypad (`/hansekop/`).

## Deploy

From a host that can SSH to `box.gowifi.co.za` (`102.209.119.186`):

```bash
GOWIFI_SSH_KEY=~/.ssh/your_key bash aerialnet/deploy/deploy-to-gowifi-box.sh
```

On the box, tokens live in `/etc/aerialnet-olarm.env` and `/etc/aerialnet-tuya.env` (copied from Sailing when reachable; never commit them).
