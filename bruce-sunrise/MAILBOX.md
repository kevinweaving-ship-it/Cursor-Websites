# Mailbox — investigation@sailingsa.co.za

**Purpose:** outbound address for French / Greek / Polish record requests on MV SUNRISE. Drafts: [`REQUESTS.md`](REQUESTS.md).

## What this Cloud run found (21 Nov 2026, Africa/Johannesburg)

| Check | Result |
| --- | --- |
| `sailingsa.co.za` **MX** | **None.** Dig returns no MX. Web A = `102.218.215.253`. |
| GoWifi mail host | `box.gowifi.co.za` → `102.209.119.186`. `gowifi.co.za` MX already points here. |
| MiaB admin HTTPS | `https://box.gowifi.co.za/admin` → **200** |
| SMTP 25 from Cloud | Timed out on both IPs (expected; use submission **587** from the Mac) |
| SSH from this Cloud VM | Ports **22 open**, **Permission denied** (no `sailingsa_live_key` / REA key on Cloud) |
| REA | Mail-in-a-Box mail data is **denied** on purpose (`docs/REA_CHATGPT_ACCESS.md`) |

So: create the mailbox on **GoWifi Mail-in-a-Box**, then point **DNS MX** at it. Do this from **This Mac** (keys live there). Do not invent that the address already works.

---

## Create the address (Mac)

### 1. Host the domain on Mail-in-a-Box (if not already)

Open: https://box.gowifi.co.za/admin → **Mail** → **Mail Domains**

- Add **`sailingsa.co.za`** if missing.
- Open the **DNS** checklist for that domain (MiaB shows the exact MX / SPF / DKIM / DMARC lines).

### 2. Add the user

**UI:** Mail → Users → Add  
Email: **`investigation@sailingsa.co.za`**  
Password: generate a long random one; store in your password manager (not in this public repo).

**API (same box, from Mac):**

```bash
# Replace ADMIN_EMAIL / ADMIN_PASS with the MiaB admin login (never commit them).
curl -sS -u 'ADMIN_EMAIL:ADMIN_PASS' \
  -d 'email=investigation@sailingsa.co.za&password=GENERATE_A_LONG_PASSWORD' \
  https://box.gowifi.co.za/admin/mail/users/add
```

Optional alias later: `investigation+greece@…` etc. — MiaB supports plus-addressing if the catch-all / user is set that way; otherwise one inbox is enough.

### 3. DNS at GoDaddy (ns77 / ns78.domaincontrol.com)

Until MX exists, mail to `@sailingsa.co.za` will **not** land in MiaB (some MTAs may try the A record; SailingSA host has **no** SMTP on 25 from outside).

Add what MiaB’s DNS page prints. Minimum:

| Type | Name | Value |
| --- | --- | --- |
| **MX** | `@` | `box.gowifi.co.za` priority **10** |
| **TXT** (SPF) | `@` | as MiaB shows (usually includes `box.gowifi.co.za`) |
| **TXT** (DKIM) | MiaB hostname | as MiaB shows |
| **TXT** (DMARC) | `_dmarc` | as MiaB shows (start `p=none` if unsure) |

Do **not** remove the existing Google site-verification TXT.

Propagate, then:

```bash
dig +short MX sailingsa.co.za
# expect: 10 box.gowifi.co.za.
```

### 4. Client

- Webmail: https://box.gowifi.co.za/mail (or MiaB’s webmail URL)
- Or IMAP/SMTP: host `box.gowifi.co.za`, IMAP 993, SMTP **587** STARTTLS, user `investigation@sailingsa.co.za`

Send a test to your own iCloud / Gmail, then reply, before any FOI.

---

## After it works

1. Send the three letters in [`REQUESTS.md`](REQUESTS.md) (France first if only one trip).
2. File every reply PDF under `bruce-sunrise/replies/` (gitignored if personal).
3. Update [`OPEN_RECORDS.md`](OPEN_RECORDS.md) when a document closes.
