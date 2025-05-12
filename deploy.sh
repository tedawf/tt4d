#!/bin/bash

set -e
set -x  # debug

DEPLOY_TARGET="${1}"

echo "--- Starting deployment for tt4d ---"

if [ -z "${DEPLOY_TARGET}" ]; then
  DEPLOY_TARGET="origin/main"
  echo "No deployment commit provided, defaulting to ${DEPLOY_TARGET}"
fi

echo "Deploying commit: ${DEPLOY_TARGET}"
echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"

echo "Fetching latest changes"
git fetch origin

echo "Resetting workspace to ${DEPLOY_TARGET}"
git reset --hard "${DEPLOY_TARGET}"

echo "Activating virtualenv"
source .venv/bin/activate || {
  echo "Failed to activate virtualenv"
  exit 1
}

echo "Installing/updating python deps"
pip install -r requirements.txt

echo "Running db migrations"
alembic upgrade head

echo "Deactivating virtualenv"
deactivate

echo "Restarting tt4d service"
sudo -n /usr/bin/systemctl restart tt4d-api.service

echo "Checking service status..."
sleep 1
sudo -n /usr/bin/systemctl status tt4d-api.service --no-pager

echo "--- Finished deployment for tt4d ---"
