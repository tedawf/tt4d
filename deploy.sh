#!/bin/bash

set -e

echo "--- Starting tt4d deployment ---"

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

echo "--- Deployed tt4d ---"
