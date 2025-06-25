#!/bin/bash

# Simple VPS update script for AI Trading Analysis App
# Run this script on your VPS to update the application

set -e

echo "🔄 Starting VPS update..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Variables
APP_DIR="/home/tradingapp/trading-analysis"
BACKUP_DIR="/home/tradingapp/backups"

# Check if running as correct user
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as tradingapp user."
   exit 1
fi

cd $APP_DIR

# Create backup
print_status "Creating backup..."
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/pre_update_backup_$(date +%Y%m%d_%H%M%S).tar.gz .

# Pull latest changes
print_status "Pulling latest changes from GitHub..."
git fetch origin
git reset --hard origin/main

# Activate virtual environment
source venv/bin/activate

# Update dependencies
print_status "Updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
print_status "Running database migrations..."
flask db upgrade

# Restart application
print_status "Restarting application..."
sudo systemctl restart trading-analysis

# Wait for service to start
sleep 3

# Check if service is running
if sudo systemctl is-active --quiet trading-analysis; then
    print_status "✅ Update successful! Application is running."
else
    print_error "❌ Update failed! Application is not running."
    sudo systemctl status trading-analysis
    exit 1
fi

# Clean up old backups (keep last 5)
print_status "Cleaning up old backups..."
cd $BACKUP_DIR
ls -t *.tar.gz | tail -n +6 | xargs -r rm

echo "🎉 VPS update completed successfully!" 