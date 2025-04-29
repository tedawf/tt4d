#!/bin/bash

set -e

echo "--- Starting deployment for tt4d ---"

echo "Getting latest changes"
git pull origin main

echo "Activating virtualenv"
source .venv/bin/activate || { echo "Failed to activate virtualenv"; exit 1; }

echo "Installing/updating python deps"
pip install -r requirements.txt

echo "Running db migrations"
alembic upgrade head

echo "Deactivating virtualenv"
deactivate

# Configured user to be able to run this without sudo
echo "Restarting tt4d service"
systemctl restart tt4d-api.service

echo "Checking service status..."
sleep 1
systemctl status tt4d-api.service --no-pager

echo "--- Finished deployment for tt4d ---"