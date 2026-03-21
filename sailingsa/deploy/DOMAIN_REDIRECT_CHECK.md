# Domain redirect check (live) — www.sailingsa.co.za

**Checked:** Live server nginx config (`/etc/nginx/sites-enabled/timadvisor`).

## Return

- **Web server type:** nginx
- **Current redirect rules for www (sailingsa):**
  - Port 80: `if ($host = www.sailingsa.co.za) { return 301 https://$host$request_uri; }` → sends to **https://www.sailingsa.co.za** (keeps www).
  - No rule redirects **www** → **apex** (sailingsa.co.za).
- **Redirect type:** HTTP→HTTPS is **301**. **www→apex is not 301** (www is not redirected to sailingsa.co.za).
- **Both domains:** They are in the same HTTPS `server` block (`server_name sailingsa.co.za www.sailingsa.co.za`), so **both serve the same content**; they do not serve separately. For Google/crawl you want **www → 301 to sailingsa.co.za**.

## Intended fix (for live)

Add an HTTPS server block that catches **www.sailingsa.co.za** only and returns **301** to **https://sailingsa.co.za**; keep the main sailingsa HTTPS block with **server_name sailingsa.co.za** only. See `nginx-timadvisor-patched.conf` (SailingSA section) for the reference.
