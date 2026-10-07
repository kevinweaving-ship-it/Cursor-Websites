# Cursor Mac prompt — dump all Openserve billing mail onto the box

Paste everything under **PROMPT** into Cursor on the Mac. One job only.

---

## PROMPT

```
You are on Kevin’s Mac. One job: find EVERY email from Openserve billing and put the files on box.gowifi.co.za so the box agent can reconcile Openserve cost vs clients.

Do not invent invoices. Do not delete anything on the box. Do not edit gowifi frontend. Do not touch Intuit/QuickBooks.

## Sender / what to keep

Must catch all mail from:
- nbcustnb@openserve.co.za
- nobody@openserve.co.za
- any From / To / Cc / Subject containing openserve, INATS, BRINATS, 940000000

Keep every attachment that is an account, statement, invoice, breakdown, CSV, or zip:
- *.csv
- *.zip (INATS / BRINATS / invoice csv)
- invoice / statement / credit PDFs
- filenames containing INATS, BRINATS, Detailed, Statement, Credit, CN

Skip images (png/jpg/gif). Skip marketing. Keep the original .eml too.

Openserve resends the same file. Deduplicate by sha256. Keep one copy. Record how many times it was sent.

## Where to search on the Mac

Search ALL of these. Do not stop at the first inbox:
- Apple Mail (all accounts): kevinweaving@icloud.com, kevin@gowifi.co.za, kevin@go-wifi.co.za, accounts@gowifi.co.za, accounts@go-wifi.co.za
- ~/Library/Mail (V8/V9/V10 .emlx)
- iCloud Mail if mounted
- Any local mailbox export / “On My Mac”
- Spotlight: mdfind for nbcustnb@openserve.co.za and INATS / BRINATS / 940000000

If Mail.app needs permission, ask Kevin once, then continue.

## Local dump folder

Create:
~/Openserve-Mail-Dump/
  eml/          full original messages
  attachments/  csv / zip / pdf
  INDEX.json    one row per unique file: filename, sha256, kind, account, month, sent_on, from, subject, mailbox, copies

kind = statement | invoice | invoice_csv | credit | other
account if in the name/subject (9400000004653 / 4655 / 4657 / 4759 / 4815)
month from filename date like 20260131 → 2026-01

## Put it on the box

Host: box.gowifi.co.za = 102.209.119.186
User: root
Dest (create if missing, do not wipe existing files):
  /root/gowifi-upp/openserve-mail/mac-dump/

Use rsync, not a blind overwrite:

  rsync -av --ignore-existing \
    ~/Openserve-Mail-Dump/eml/ \
    root@102.209.119.186:/root/gowifi-upp/openserve-mail/mac-dump/eml/
  rsync -av --ignore-existing \
    ~/Openserve-Mail-Dump/attachments/ \
    root@102.209.119.186:/root/gowifi-upp/openserve-mail/mac-dump/attachments/
  scp ~/Openserve-Mail-Dump/INDEX.json \
    root@102.209.119.186:/root/gowifi-upp/openserve-mail/mac-dump/INDEX.json

Also copy unique attachments into:
  /root/gowifi-upp/openserve-mail/
without replacing a different file of the same name (prefix sha256[0:8]_ if clash).

If SSH needs Kevin’s key or password, use his existing box login. Do not invent a password.

## After upload — report only

Do not run a full books rewrite. Print:
- how many messages found
- how many unique files
- months have vs missing for Webstream 9400000004759 and Office Connect 9400000004657 from 2024-09 through last complete month
- especially say if 2026-02 … 2026-09 are now on the box
- remote path and INDEX.json counts

Then stop. The box agent will ingest and reconcile.
```

---

## What the box already has

Folder: `/root/gowifi-upp/openserve-mail`  
Invoices on the box today: Webstream + Office Connect **2025-09 → 2026-01** only.  
Missing until this dump lands: **2026-02 → 2026-09** (and earlier than 2025-09).  
Cost truth is the invoice CSV per B-number + VAT. Do not invent costs.
