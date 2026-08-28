#!/bin/bash
echo '=== find live.py ==='
find /var/www/sailingsa -name 'lipton_dev_live.py' 2>/dev/null
echo '=== systemd ==='
systemctl cat sailingsa-api | head -80
echo '=== pyc ==='
find /var/www/sailingsa -name 'lipton_dev_live*.pyc' 2>/dev/null
echo '=== holding_last in files ==='
grep -n holding_last /var/www/sailingsa/sailingsa/scripts/lipton_dev_live.py /var/www/sailingsa/api/lipton_dev_live.py /var/www/sailingsa/*.py 2>/dev/null | head
echo '=== PYTHONPATH / WorkingDirectory ==='
systemctl show sailingsa-api -p Environment -p WorkingDirectory -p ExecStart -p User
