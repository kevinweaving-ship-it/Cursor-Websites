# Mailbox — investigation@sailingsa.co.za

**Purpose:** outbound address for French / Greek / Polish record requests.  
**Signatory on FOI letters:** **James Porter** (not Kevin Weaving).  
**Status:** mailbox **live**; three FOIs **sent** 21 Nov 2026 — [`SENT.md`](SENT.md).

## Access

- Mail-in-a-Box: `box.gowifi.co.za` (`102.209.119.186`)
- Webmail: https://box.gowifi.co.za/mail — user `investigation@sailingsa.co.za`
- Password on box only: `/root/secrets/investigation-sailingsa.password` (never commit)

```bash
sshpass -p '…' ssh root@102.209.119.186 \
  'doveadm fetch -u investigation@sailingsa.co.za "hdr.from hdr.subject hdr.date" MAILBOX INBOX ALL'
```

## DNS (checked after send, 21 Nov 2026)

| Record | `sailingsa.co.za` |
| --- | --- |
| A | web host (SailingSA) |
| MX | **empty** at public resolvers after send — **fix at GoDaddy** |
| DKIM | outbound messages **were signed** `d=sailingsa.co.za; s=mail` |
| NS | GoDaddy `ns77` / `ns78.domaincontrol.com` |

Add at GoDaddy (MiaB checklist):

| Type | Name | Value |
| --- | --- | --- |
| MX | `@` | `box.gowifi.co.za` priority **10** |
| TXT SPF / DKIM / DMARC | as MiaB prints for the domain | — |

```bash
dig +short MX sailingsa.co.za
# want: 10 box.gowifi.co.za.
```

Without MX, **outbound can work** (it did) but **replies may not arrive**.

## Reply watch

Timer subscription `bruce-sunrise-mail-replies` — every 12 hours. File under [`replies/`](replies/).
