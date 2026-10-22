#!/bin/bash
# Retired: do not install a publisher on the SailingSA box.
# Generation stays on GoWifi. This script used to enable a duplicate
# sailing-roundup.timer on live; that timer is masked.
set -euo pipefail
echo "refusing to install a SailingSA-local publisher" >&2
echo "generate on GoWifi (/opt/rea/work/sailing-roundup) and publish issue-scoped files only" >&2
exit 1
