# Marine Megastore Facebook LIVE — where records live

You do not need to keep these. They are on the live server. **Do not put the App secret in git.**

## New Graph app (instant LIVE)

- **Name:** SailingSA MM Live
- **App ID:** `1614644650032287`
- **Dashboard:** https://developers.facebook.com/apps/1614644650032287/dashboard/
- **Contact:** kevin@arial.co.za
- **Use case:** Manage everything on your Page
- **Business portfolio:** none connected yet
- **Product:** Facebook Login for Business (added by Meta with the Page use case)
- **Login config:** `MM Page LIVE` — ID `1475623934360046`
- **Config permissions:** `business_management`, `pages_show_list`, `pages_read_engagement`, `pages_read_user_content`, `pages_manage_metadata`
- **Live Video API:** Ready for testing
**Paused 2026-09-12:** Facebook Login dialog “Choose the Businesses…”. Kevin’s list was Go-Wifi, Matthew Baker’s Business, Tim Advisor — **Marine Megastore was not listed**. Page token still empty. Resume at `https://sailingsa.co.za/api/super-admin/mm-fb/connect-business`. Do not grant Go-Wifi / Tim Advisor / Matthew Baker.
- **OAuth redirect:** `https://sailingsa.co.za/auth/facebook/callback`

**Secret and full record (live only, root):**

- `/etc/sailingsa/mm-fb-app.env` — `MM_FB_APP_ID` / `MM_FB_APP_SECRET` (root:www-data, 640)
- `/root/SAILINGSA_MM_FB_LIVE.txt` — full written record including secret (root, 600)
- systemd: `/etc/systemd/system/sailingsa-api.service.d/mm-fb-app.conf`

## Still used for sailor Facebook login — do not replace

- **Name:** SailingSA Login
- **App ID:** `885045914172033`
- systemd: `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET`
- Consumer app. Cannot do Page `live_videos`.

## Paths on live

| What | Path |
| --- | --- |
| Page token (empty until saved) | `/var/www/sailingsa/api/data/mm_fb_page.token` |
| Webhook verify token | `/var/www/sailingsa/api/data/mm_fb_verify.token` |
| Login-for-Business config_id | `/var/www/sailingsa/api/data/mm_fb_config_id.txt` |
| Graph helper | `/var/www/sailingsa/deploy/mm_fb_graph_live.py` |
| Feed JSON | `/var/www/sailingsa/api/data/event_fb_feeds.json` |
| Webhook | `https://sailingsa.co.za/api/facebook/mm-live-webhook` |
| Super-admin connect | `https://sailingsa.co.za/api/super-admin/mm-fb/connect` |
| MM Page | `marin.megastoresa` |

Graph helper reads `MM_FB_APP_ID` first, then falls back to `FACEBOOK_APP_ID`.
