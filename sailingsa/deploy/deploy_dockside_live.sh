#!/bin/bash
# Run on the live server. Installs Dockside Chat only if the live files still
# match the hashes recorded before staging. Restores those files if checks fail.
set -euo pipefail

EXPECTED_HTML="b551e6e0afbc1c90f336f367359a71374316795573e49e0abfd22ec95c88f5d2"
EXPECTED_API="8d94e00beb8aad8aa2fb79f227ef4b85f0912601b750fca028b32ac1591919fe"
EXPECTED_ROUNDUP="2e1260ac86fd69560c81e2f87e66ef6a54f335cc8f82ac36328e34e2cb7d244e"
STAGE="${STAGE:-/tmp/dockside-stage}"
WEB="/var/www/sailingsa"
API="$WEB/api/api.py"
BAK="/root/backups/dockside-$(date +%Y%m%d_%H%M%S)"
PY="$WEB/api/venv/bin/python"

hash_of() { sha256sum "$1" | awk '{print $1}'; }

require_hash() {
  local path="$1" expected="$2" now
  now="$(hash_of "$path")"
  if [[ "$now" != "$expected" ]]; then
    echo "STOP_HASH_CHANGED $path"
    echo "expected $expected"
    echo "actual   $now"
    exit 2
  fi
}

require_hash "$WEB/blank.html" "$EXPECTED_HTML"
require_hash "$WEB/index.html" "$EXPECTED_HTML"
require_hash "$API" "$EXPECTED_API"
require_hash "$WEB/js/landing-roundup-cards.js" "$EXPECTED_ROUNDUP"

mkdir -p "$BAK" "$WEB/sailingsa/backend"
cp -a "$WEB/blank.html" "$WEB/index.html" "$API" "$BAK/"
echo "BACKUP $BAK"

python3 - "$STAGE" "$API" "$WEB/blank.html" "$BAK" << 'PY'
import pathlib, sys
stage, api_path, html_sample, bak = sys.argv[1:]
api = pathlib.Path(api_path).read_text(encoding="utf-8")
bell_old = (
    "box-sizing:border-box;\">0</span>'\n"
    "        + '</button>'\n"
    "    )"
)
bell_new = (
    "box-sizing:border-box;\">0</span>'\n"
    "        + '</button>'\n"
    "        + '<script src=\"/js/dockside-chat.js?v=dockside1\" defer></script>'\n"
    "    )"
)
if api.count(bell_old) != 1:
    raise SystemExit("STOP bell anchor missing")
if "DOCKSIDE_CHAT_ROUTES_v1" in api or 'id="dockside-landing"' in pathlib.Path(html_sample).read_text(encoding="utf-8"):
    raise SystemExit("STOP dockside already present")
api = api.replace(bell_old, bell_new, 1)
api += """
# DOCKSIDE_CHAT_ROUTES_v1 — topics, comments, replies, notifications.
try:
    from sailingsa.backend.dockside_chat import register_dockside_routes
    register_dockside_routes(
        app,
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        is_super_admin=_session_role_is_super_admin,
    )
except Exception as _dockside_exc:
    print(f"[dockside] routes not registered: {_dockside_exc}", flush=True)
"""
out_api = pathlib.Path(bak) / "api.py.new"
out_api.write_text(api, encoding="utf-8")
snippet = pathlib.Path(stage, "dockside-landing.html").read_text(encoding="utf-8").strip() + "\n"
script = '<script id="landing-roundup-card" src="/js/landing-roundup-cards.js?v=roundup-reads-20261027" defer></script>'
section = '<section id="temp-landing-hero-image"'
for name in ("blank.html", "index.html"):
    src = pathlib.Path("/var/www/sailingsa") / name
    text = src.read_text(encoding="utf-8")
    if text.count(script) != 1 or text.count(section) < 1:
        raise SystemExit(f"STOP html anchor missing in {name}")
    at = text.find(section, text.find(script))
    if at < 0:
        raise SystemExit(f"STOP upcoming section missing in {name}")
    patched = text[:at] + snippet + text[at:]
    for needle in ("Weekly Roundup", 'id="dockside-landing"', 'id="temp-landing-hero-image"', "landing-roundup-cards.js"):
        if needle not in patched:
            raise SystemExit(f"STOP patched html lost {needle}")
    (pathlib.Path(bak) / (name + ".new")).write_text(patched, encoding="utf-8")
print("PATCH_OK")
PY

"$PY" -m py_compile "$BAK/api.py.new"
"$PY" -m py_compile "$STAGE/dockside_chat.py"

# Hashes again, immediately before the live files are replaced.
require_hash "$WEB/blank.html" "$EXPECTED_HTML"
require_hash "$WEB/index.html" "$EXPECTED_HTML"
require_hash "$API" "$EXPECTED_API"

install -m 644 "$STAGE/dockside_chat.py" "$WEB/sailingsa/backend/dockside_chat.py"
install -m 644 "$STAGE/dockside-chat.js" "$WEB/js/dockside-chat.js"
install -m 644 "$STAGE/dockside-chat.css" "$WEB/css/dockside-chat.css"
install -m 644 "$STAGE/dockside.html" "$WEB/dockside.html"
chown www-data:www-data \
  "$WEB/sailingsa/backend/dockside_chat.py" \
  "$WEB/js/dockside-chat.js" \
  "$WEB/css/dockside-chat.css" \
  "$WEB/dockside.html"

locked=1
trap 'if [[ "${locked:-1}" == 0 ]]; then chattr +i "$API" || true; fi' EXIT
chattr -i "$API"
locked=0
cp -a "$BAK/api.py.new" "$API"
chown www-data:www-data "$API"
chattr +i "$API"
locked=1
cp -a "$BAK/blank.html.new" "$WEB/blank.html"
cp -a "$BAK/index.html.new" "$WEB/index.html"
chown www-data:www-data "$WEB/blank.html" "$WEB/index.html"

cat > "$BAK/ROLLBACK.sh" << EOF
#!/bin/bash
set -euo pipefail
chattr -i "$API" || true
cp -a "$BAK/api.py" "$API"
chown www-data:www-data "$API"
chattr +i "$API"
cp -a "$BAK/blank.html" "$WEB/blank.html"
cp -a "$BAK/index.html" "$WEB/index.html"
chown www-data:www-data "$WEB/blank.html" "$WEB/index.html"
rm -f "$WEB/js/dockside-chat.js" "$WEB/css/dockside-chat.css" "$WEB/dockside.html" "$WEB/sailingsa/backend/dockside_chat.py"
systemctl restart sailingsa-api
echo "Restored files from $BAK"
echo "Tables were left in place. Drop them only if this feature should be removed:"
echo "DROP TABLE IF EXISTS public.dockside_reports, public.dockside_notifications, public.dockside_follows, public.dockside_posts, public.dockside_topics;"
EOF
chmod 700 "$BAK/ROLLBACK.sh"
cp -a "$BAK/ROLLBACK.sh" /root/backups/dockside-ROLLBACK.sh

if ! systemctl restart sailingsa-api; then
  echo "STOP_RESTART_FAILED"
  bash "$BAK/ROLLBACK.sh"
  exit 1
fi
ready=0
for _ in $(seq 1 24); do
  if systemctl is-active --quiet sailingsa-api && curl -fsS --max-time 15 "https://sailingsa.co.za/auth/session" -o /tmp/dockside-session.json; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  echo "STOP_API_INACTIVE"
  bash "$BAK/ROLLBACK.sh"
  exit 1
fi

check_pages() {
  local url="$1" file
  file="$(mktemp)"
  curl -fsS --max-time 30 "$url" -o "$file" || return 1
  grep -q 'id="dockside-landing"' "$file" || return 1
  grep -q 'Weekly Roundup' "$file" || return 1
  grep -q 'id="temp-landing-hero-image"' "$file" || return 1
  grep -q 'landing-roundup-cards.js' "$file" || return 1
  rm -f "$file"
}

pages_ok=0
for _ in $(seq 1 8); do
  if check_pages "https://sailingsa.co.za/" && check_pages "https://sailingsa.co.za/blank.html"; then
    pages_ok=1
    break
  fi
  sleep 2
done
if [[ "$pages_ok" != 1 ]]; then
  echo "STOP_PAGE_CHECK"
  bash "$BAK/ROLLBACK.sh"
  exit 1
fi
if ! curl -fsS "https://sailingsa.co.za/login.html" | grep -q "auth_returnTo"; then
  echo "STOP_LOGIN_CHECK"
  bash "$BAK/ROLLBACK.sh"
  exit 1
fi
if ! curl -fsS "https://sailingsa.co.za/dockside.html" | grep -q 'id="dockside-page"'; then
  echo "STOP_DISCUSSIONS_CHECK"
  bash "$BAK/ROLLBACK.sh"
  exit 1
fi
session_code="$(curl -s -o /tmp/dockside-session.json -w '%{http_code}' https://sailingsa.co.za/auth/session)"
if [[ "$session_code" != "200" ]] || ! grep -q '"valid"' /tmp/dockside-session.json; then
  echo "STOP_SESSION_CHECK"
  bash "$BAK/ROLLBACK.sh"
  exit 1
fi

if ! "$PY" - "$BAK" << 'PY'
import json, urllib.request, urllib.error, subprocess, pathlib, sys
bak = sys.argv[1]
base = "https://sailingsa.co.za"

def call(method, path, body=None, cookie=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", "session=" + cookie)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode()
            payload = json.loads(raw) if raw else {}
            return res.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:200]}
        return exc.code, payload

code, me = call("GET", "/api/dockside/me")
assert code == 200 and me.get("signed_in") is False, me
code, current = call("GET", "/api/dockside/current")
assert code == 200 and current.get("topic") is None, current
code, denied = call("POST", "/api/dockside/topics", {"subject": "Nope nope", "body": "Should not save"})
assert code == 401, denied

subprocess.check_call([
    "sudo", "-u", "postgres", "psql", "-d", "sailors_master", "-v", "ON_ERROR_STOP=1", "-c",
    """
    DELETE FROM public.user_sessions WHERE session_id IN ('dockside-verify-a','dockside-verify-b');
    INSERT INTO public.user_sessions (session_id, account_id, sas_id, login_method, expires_at, is_active)
    VALUES
      ('dockside-verify-a', 19, '27159', 'sas_id', NOW() + INTERVAL '20 minutes', true),
      ('dockside-verify-b', 20, '27159', 'sas_id', NOW() + INTERVAL '20 minutes', true);
    """
])
try:
    code, created = call("POST", "/api/dockside/topics", {"subject": "ZZ-DOCKSIDE-VERIFY line", "body": "Verify comment"}, "dockside-verify-a")
    assert code == 200 and created.get("topic_id"), created
    topic_id = created["topic_id"]
    first_id = created["posts"][0]["post_id"]
    code, notes = call("GET", "/api/dockside/notifications", cookie="dockside-verify-a")
    assert code == 200 and notes.get("unread") == 0, notes
    code, reply = call("POST", f"/api/dockside/topics/{topic_id}/posts", {"body": "Verify reply", "parent_post_id": first_id}, "dockside-verify-b")
    assert code == 200 and reply.get("notified") == 1, reply
    code, notes = call("GET", "/api/dockside/notifications", cookie="dockside-verify-a")
    assert code == 200 and notes.get("unread") == 1, notes
    assert notes["notifications"][0]["actor_name"]
    code, own = call("GET", "/api/dockside/notifications", cookie="dockside-verify-b")
    assert code == 200 and own.get("unread") == 0, own
    code, muted = call("POST", f"/api/dockside/topics/{topic_id}/follow", {"muted": True}, "dockside-verify-a")
    assert code == 200 and muted.get("muted") is True, muted
    code, again = call("POST", f"/api/dockside/topics/{topic_id}/posts", {"body": "Verify after mute"}, "dockside-verify-b")
    assert code == 200 and again.get("notified") == 0, again
    code, found = call("GET", "/api/dockside/topics?q=ZZ-DOCKSIDE-VERIFY")
    assert code == 200 and any(row["topic_id"] == topic_id for row in found.get("topics", [])), found
    print("HTTP_LOGIC_OK")
finally:
    subprocess.check_call([
        "sudo", "-u", "postgres", "psql", "-d", "sailors_master", "-v", "ON_ERROR_STOP=1", "-c",
        """
        DELETE FROM public.dockside_topics WHERE subject LIKE 'ZZ-DOCKSIDE-VERIFY%';
        DELETE FROM public.user_sessions WHERE session_id IN ('dockside-verify-a','dockside-verify-b');
        """
    ])
    code, current = call("GET", "/api/dockside/current")
    if code != 200 or current.get("topic") is not None:
        raise SystemExit(f"STOP verify rows still visible {current}")
    print("HTTP_CLEAN_OK")
PY
then
  echo "STOP_VERIFY_FAILED"
  bash "$BAK/ROLLBACK.sh"
  exit 1
fi

roundup_now="$(hash_of "$WEB/js/landing-roundup-cards.js")"
if [[ "$roundup_now" != "$EXPECTED_ROUNDUP" ]]; then
  echo "STOP_ROUNDUP_CHANGED"
  bash "$BAK/ROLLBACK.sh"
  exit 1
fi
echo "DEPLOY_FILES_OK $BAK"
