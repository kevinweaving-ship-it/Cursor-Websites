#!/bin/bash
# Re-apply Lipton 2026 unique-string patches to live api.py.
# NEVER copy repo api.py over /var/www/sailingsa/api/api.py.
set -u
API="${1:-/var/www/sailingsa/api/api.py}"
DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ ! -f "$API" ]]; then
  echo "missing $API" >&2
  exit 1
fi

PATCHERS=(
  patch_lipton_day_close_17.py
  patch_lipton_overnight_ui.py
  patch_lipton_overnight_r5_chip.py
  patch_lipton_live_keep_last_rn.py
  patch_lipton_tracker_overnight_guard.py
  patch_lipton_next_rn_max.py
  patch_lipton_official_identity_overlay.py
  patch_lipton_asat_db_only.py
  patch_lipton_overnight_put_guard.py
  patch_lipton_pre_wake_close.py
  patch_lipton_no_heal_overnight.py
  patch_lipton_apply_asat.py
  patch_lipton_js_pre_wake_close.py
  patch_lipton_apply_overnight_skip.py
  patch_lipton_race_times_merge.py
  patch_lipton_pre_arm_put.py
  patch_lipton_pre_arm_wake.py
  patch_lipton_live_button_rk.py
  patch_lipton_apply_late_finish.py
  patch_lipton_icons_merge_read.py
  patch_lipton_allers_name_links.py
  patch_lipton_public_not_dev.py
  patch_lipton_public_not_dev_v2.py
  patch_lipton_public_not_dev_v3.py
  patch_lipton_keep_last_rn_db.py
  patch_lipton_schedule_keep_last_db.py
)

echo "api $API"
for p in "${PATCHERS[@]}"; do
  f="$DIR/$p"
  if [[ ! -f "$f" ]]; then
    echo "SKIP missing $p"
    continue
  fi
  out="$(python3 "$f" "$API" 2>&1)" || true
  echo "$p: $out"
done

REQUIRED=(
  LIPTON_NO_GUN_LIVE_OVERRIDE_V1
  LIPTON_OVERNIGHT_UI_V1
  LIPTON_OVERNIGHT_R5_CHIP_V1
  LIPTON_LIVE_KEEP_LAST_RN_V1
  LIPTON_TRACKER_OVERNIGHT_GUARD_V1
  LIPTON_NEXT_RN_MAX_V1
  LIPTON_OFFICIAL_IDENTITY_V1
  LIPTON_ASAT_DB_ONLY_V1
  LIPTON_OVERNIGHT_PUT_GUARD_V1
  LIPTON_PRE_WAKE_CLOSE_V1
  LIPTON_NO_HEAL_OVERNIGHT_V1
  LIPTON_APPLY_ASAT_V1
  LIPTON_JS_PRE_WAKE_CLOSE_V1
  LIPTON_APPLY_OVERNIGHT_SKIP_V1
  LIPTON_RACE_TIMES_MERGE_V1
  LIPTON_PRE_ARM_PUT_V1
  LIPTON_PRE_ARM_WAKE_V1
  LIPTON_LIVE_BUTTON_RK_V1
  LIPTON_APPLY_LATE_FINISH_V1
  LIPTON_ICONS_MERGE_READ_V1
  LIPTON_ALLERS_NAME_LINKS_V2
  LIPTON_PUBLIC_NOT_DEV_V1
  LIPTON_PUBLIC_NOT_DEV_V2
  LIPTON_PUBLIC_NOT_DEV_V3
  LIPTON_KEEP_LAST_RN_DB_V1
  LIPTON_SCHEDULE_KEEP_LAST_DB_V1
)
miss=0
for m in "${REQUIRED[@]}"; do
  if grep -q "$m" "$API"; then
    echo "OK $m"
  else
    echo "MISSING $m" >&2
    miss=1
  fi
done
if [[ "$miss" -ne 0 ]]; then
  echo "FAIL required markers missing" >&2
  exit 1
fi
echo "OK all required Lipton live markers"
echo "After overnight/leftover-gun restart: python3 /usr/local/sbin/restore_lipton_live_overnight.py"
echo "Do NOT run overnight restore while race_armed / waiting for a start (it pins day_close + last filled Rn)."
