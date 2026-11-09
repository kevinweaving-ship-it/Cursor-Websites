#!/bin/bash
# Accept every @go-wifi.co.za address on the box and deliver to gowifi.
# Exact aliases win; anything else catch-alls to kevin@ + openserve@.
set -euo pipefail

DB=/home/user-data/mail/users.sqlite
ALIAS_PCRE=/etc/postfix/go-wifi-catchall.pcre
ACCEPT_PCRE=/etc/postfix/go-wifi-accept.pcre

python3 - <<'PY'
import sqlite3
db = sqlite3.connect("/home/user-data/mail/users.sqlite")
wanted = [
    ("kevin@go-wifi.co.za", "kevin@gowifi.co.za"),
    ("robby@go-wifi.co.za", "robby@gowifi.co.za"),
    ("openserve@go-wifi.co.za", "openserve@gowifi.co.za"),
    ("accounts@go-wifi.co.za", "kevin@gowifi.co.za,openserve@gowifi.co.za"),
    ("support@go-wifi.co.za", "kevin@gowifi.co.za"),
    ("@go-wifi.co.za", "kevin@gowifi.co.za,openserve@gowifi.co.za"),
]
for source, dest in wanted:
    row = db.execute("SELECT destination FROM aliases WHERE source=?", (source,)).fetchone()
    if row is None:
        db.execute(
            "INSERT INTO aliases (source, destination, permitted_senders) VALUES (?,?,NULL)",
            (source, dest),
        )
    elif (row[0] or "") != dest:
        db.execute("UPDATE aliases SET destination=? WHERE source=?", (dest, source))
db.commit()
db.close()
print("aliases ok")
PY

# Exact aliases stay in sqlite (first). Unknown @go-wifi.co.za hits this catch-all.
printf '%s\n' '/^.*@go-wifi\.co\.za$/  kevin@gowifi.co.za,openserve@gowifi.co.za' > "$ALIAS_PCRE"
# Listed recipient so reject_unlisted_recipient does not bounce the mail.
printf '%s\n' '/^.*@go-wifi\.co\.za$/  1' > "$ACCEPT_PCRE"
chmod 644 "$ALIAS_PCRE" "$ACCEPT_PCRE"

# Alias sources count as valid mailboxes (kevin@go-wifi is an alias, not a user).
python3 - <<'PY'
from pathlib import Path
p = Path("/etc/postfix/virtual-mailbox-maps.cf")
text = p.read_text()
want = (
    "query = SELECT 1 FROM users WHERE email='%s' "
    "UNION SELECT 1 FROM aliases WHERE source='%s' AND destination<>'' "
    "UNION SELECT 1 FROM auto_aliases WHERE source='%s' AND destination<>'' "
    "UNION SELECT 1 FROM aliases WHERE source='@' || CASE WHEN instr('%s','@') "
    "THEN substr('%s', instr('%s','@')+1) ELSE '' END AND destination<>''"
)
if "UNION SELECT 1 FROM aliases WHERE source='%s'" not in text:
    import re
    text2, n = re.subn(r"^query\s*=\s*.*$", want, text, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("could not patch virtual-mailbox-maps.cf")
    p.write_text(text2)
    print("mailbox-maps patched")
else:
    print("mailbox-maps already patched")
PY

ALIAS_LINE="sqlite:/etc/postfix/virtual-alias-maps.cf,pcre:$ALIAS_PCRE"
MAILBOX_LINE="sqlite:/etc/postfix/virtual-mailbox-maps.cf,pcre:$ACCEPT_PCRE"
postconf -e "virtual_alias_maps = $ALIAS_LINE"
postconf -e "virtual_mailbox_maps = $MAILBOX_LINE"
postfix check
postfix reload
echo "postfix reloaded"

echo "=== lookups ==="
echo -n "kevin@go-wifi alias: "; postmap -q kevin@go-wifi.co.za sqlite:/etc/postfix/virtual-alias-maps.cf
echo -n "nobody@go-wifi catchall: "; postmap -q nobody@go-wifi.co.za pcre:$ALIAS_PCRE
echo -n "kevin@go-wifi mailbox: "; postmap -q kevin@go-wifi.co.za sqlite:/etc/postfix/virtual-mailbox-maps.cf
echo -n "nobody@go-wifi accept: "; postmap -q nobody@go-wifi.co.za pcre:$ACCEPT_PCRE
echo "ok — box accepts @go-wifi.co.za and delivers to gowifi"
