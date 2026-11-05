#!/bin/bash
# Sourced by deploy_api.sh and deploy_api_verified.sh on the server.
# Keeps the production-lineage api.py when a short branch file is uploaded.
# Does not restart the API. Returns 10 when the caller should restart.

ilca4_install_one() {
  local src="$1"
  local dest="$2"
  if [ ! -f "$src" ]; then
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
    echo "ILCA sidecar unchanged: $dest"
    return 0
  fi
  cp "$src" "$dest"
  chown www-data:www-data "$dest" 2>/dev/null || true
  echo "ILCA sidecar installed: $dest"
  ILCA4_CHANGED=1
}

ilca4_apply_patch_if_needed() {
  local live="$1"
  local patchf="/root/incoming/20261004_ilca4_live_api.patch"
  if grep -q 'EVENT_LOGO_ASSET_BUST = "20261004ilca4"' "$live"; then
    echo "ILCA 4 production patch already in live api.py"
    return 0
  fi
  if [ ! -f "$patchf" ]; then
    echo "ERROR: live api.py is missing the ILCA 4 patch and $patchf was not uploaded."
    return 1
  fi
  if ! patch --forward --dry-run --batch -p1 -d "$(dirname "$live")" < "$patchf"; then
    echo "ERROR: ILCA 4 patch does not apply. Live api.py was not modified."
    return 1
  fi
  patch --forward --batch -p1 -d "$(dirname "$live")" < "$patchf"
  echo "Applied ILCA 4 patch to $live"
  ILCA4_CHANGED=1
}

ilca4_fix_html_display() {
  local f
  for f in \
    /var/www/sailingsa/index.html \
    /var/www/sailingsa/index.sailor_spa.html \
    /var/www/sailingsa/index.sailorset.html
  do
    if [ -f "$f" ] && grep -q "'ilca 4.7':'ILCA 4.7'" "$f"; then
      sed -i "s/'ilca 4.7':'ILCA 4.7'/'ilca 4.7':'ILCA 4'/g" "$f"
      echo "ILCA 4 display map updated in $f"
    fi
  done
}

# Install sidecars, re-apply the ILCA 4 patch only when it is missing, and
# relock api.py. Historical fleet URL tails and class_original are not touched.
ilca4_preserve_live() {
  local live="$1"
  ILCA4_CHANGED=0
  ilca4_install_one /root/incoming/class_name_aliases.py /var/www/sailingsa/api/class_name_aliases.py
  if [ -d /var/www/sailingsa/deploy ]; then
    ilca4_install_one /root/incoming/class_name_aliases.py /var/www/sailingsa/deploy/class_name_aliases.py
  fi
  ilca4_install_one /root/incoming/ilca4_canonical.py /var/www/sailingsa/api/ilca4_canonical.py
  ilca4_install_one /root/incoming/regatta_host_code.py /var/www/sailingsa/api/regatta_host_code.py
  ilca4_apply_patch_if_needed "$live" || return 1
  ilca4_fix_html_display
  chattr +i "$live" 2>/dev/null || true
  if [ "${ILCA4_CHANGED}" = 1 ]; then
    return 10
  fi
  return 0
}
