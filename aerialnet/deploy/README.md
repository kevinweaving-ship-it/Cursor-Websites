# Aerialnet keypad duplicate (Hansekop + Voëlklip)

Test / audit copies of the live SailingSA keypads, on the GoWifi / Aerialnet box.

| Live gold (leave on Sailing) | Aerialnet copy |
|---|---|
| https://sailingsa.co.za/arial/ | https://aerialnet.co.za/hansekop/ |
| https://sailingsa.co.za/voelklip/ | https://aerialnet.co.za/voelklip/ |

Olarm and the Smart Life worker run on this box. Do not proxy `/api/arial/` or `/api/voelklip/` to sailingsa.co.za, and do not SSH to the Sailing box from the install.

| Piece | How it was created | On the GoWifi box |
|---|---|---|
| Olarm | Bearer token from [login.olarm.com](https://login.olarm.com) → API. See `docs/ARIAL_OLARM_DIGEST.md` in history. Commands are `POST /api/v4/devices/{id}/actions` with `area-disarm` / `area-arm`. | `/etc/aerialnet-olarm.env` (`OLARM_API_TOKEN`). Hansekop device `0bb544db-30b0-453d-bf39-d323538ebd5e` on `127.0.0.1:8003`. Voëlklip `d6f25654-5fe8-4a85-a7ba-f8ff1449144a` on `127.0.0.1:8004`. |
| Tuya meter, lights, home | Not the IoT Core keys. Those return `28841002` (subscription expired). The live path is Smart Life device sharing, same as Home Assistant: client `HA_3y9q4ak7g4ephrvke`, schema `haauthorize`, QR `tuyaSmart--qrLogin`. User Code is in the Smart Life app (Me → Settings → Account and Security). Worker: `aerialnet/tuya-sharing/worker.py`. | Env `/etc/aerialnet-tuya.env` (ingest + control tokens, home name `Aerial Networks HSK`). Install `/opt/tuya-sharing`. Login: `login.py qr USER_CODE` then `login.py poll`, then `systemctl enable --now tuya-sharing`. Control `127.0.0.1:8007` (`/health`, `/home`, `/light`). Meter pushes to `/api/arial/meter/ingest`. |
| WhatsApp | Hansekop alerts use the Baileys worker `arial-whatsapp-poc` (`poc.js`, control `:8009`). That engine was not committed. Sailing keeps its own WhatsApp. | Not installed. Do not point this box at Sailing's WhatsApp. |
| Hikvision / HYC | Voëlklip streams were `/opt/hikpoc` + go2rtc. That tree was not committed. The Hermanus Yacht Club camera stays on the Sailing box. | Voëlklip pages still call `sailingsa.co.za:8443` / `:8444` until a local go2rtc exists. Do not move HYC. |

The Aerialnet landing header has **User Login**, which opens the Hansekop keypad (`/hansekop/`).

## Deploy

From a host that can SSH to `box.gowifi.co.za` (`102.209.119.186`):

```bash
GOWIFI_SSH_KEY=~/.ssh/your_key bash aerialnet/deploy/deploy-to-gowifi-box.sh
```

On the box, tokens live in `/etc/aerialnet-olarm.env` and `/etc/aerialnet-tuya.env`. Never commit them, and never copy them off the Sailing box.
