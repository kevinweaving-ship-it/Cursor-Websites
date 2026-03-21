#!/bin/bash
set -e

echo "=== SailingSA Deployment Guard ==="

CHANGED_FRONTEND=false
CHANGED_BACKEND=false

FILES=$(git status --porcelain)

for file in $FILES
do
    if [[ "$file" == *"frontend/"* ]]; then
        CHANGED_FRONTEND=true
    fi

    if [[ "$file" == *"api.py"* ]] || [[ "$file" == *"regatta_host_code.py"* ]]; then
        CHANGED_BACKEND=true
    fi
done

bash sailingsa/dev/check-layout.sh

if [ "$CHANGED_FRONTEND" = true ]; then
  echo "Deploying FRONTEND..."
  bash sailingsa/deploy/deploy-with-key.sh
fi

if [ "$CHANGED_BACKEND" = true ]; then
  echo "Deploying BACKEND..."
  scp -i ~/.ssh/sailingsa_live_key api.py root@102.218.215.253:/root/incoming/api.py
  if [ -f regatta_host_code.py ]; then
    scp -i ~/.ssh/sailingsa_live_key regatta_host_code.py root@102.218.215.253:/root/incoming/regatta_host_code.py
  fi
  ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "/root/deploy_api.sh"
fi

echo "Checking API..."
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "systemctl is-active sailingsa-api"

echo "=== Deployment Guard Completed ==="
