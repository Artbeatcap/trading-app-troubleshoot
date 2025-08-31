#!/bin/bash
set -e

echo ">>> Setting up Git safe directory"
git config --global --add safe.directory /home/tradingapp/trading-analysis

echo ">>> Changing to app directory"
cd /home/tradingapp/trading-analysis

echo ">>> pulling latest code"
git pull origin main

echo ">>> activating venv"
source venv/bin/activate

echo ">>> installing deps"
pip install --no-cache-dir -r requirements.txt

echo ">>> applying migrations"
flask db upgrade

echo ">>> restarting app via supervisor"
supervisorctl reread
supervisorctl update
supervisorctl restart stockapp

echo ">>> reloading nginx (just in case)"
systemctl reload nginx

echo "✓ Deploy completed." 