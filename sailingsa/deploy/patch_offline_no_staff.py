from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-no-staff-off-{stamp}"))
text = API.read_text(encoding="utf-8")

# After is_staff detected, skip staff entirely for humans (and don't put in bots unless quarantined)
old = '''            if is_bot:
                kind = "bot"
                who = f"Bot {ip}"
            elif is_staff:
                kind = "signed"
                who = f"Staff {ip}"
            else:
                kind = "anon"
                who = f"Guest {ip}"
'''
new = '''            # Staff (Tim/Kevin signed-in IPs) never appear as Done/offline visitors
            if is_staff and not is_bot:
                continue
            if is_bot:
                kind = "bot"
                who = f"Bot {ip}"
            else:
                kind = "anon"
                who = f"Guest {ip}"
'''
if old not in text:
    raise SystemExit("staff branch not found")
text = text.replace(old, new, 1)

# Update helper docstring if it says staff labeled
text = text.replace(
    "Humans = non-bot IPs with public page hits (staff labeled Staff, not hidden).",
    "Humans = non-bot, non-staff public visitors only.",
    1,
)

API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print("OK staff hidden from offline")
