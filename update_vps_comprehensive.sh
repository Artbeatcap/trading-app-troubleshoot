#!/bin/bash

# Comprehensive VPS update script for AI Trading Analysis App
# This script will copy the latest files from production-package and update the VPS

set -e

echo "🚀 Starting comprehensive VPS update..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Variables
VPS_HOST="root@167.88.43.61"
VPS_APP_DIR="/home/tradingapp/trading-analysis"
LOCAL_PRODUCTION_DIR="production-package"
BACKUP_DIR="/home/tradingapp/backups"

print_step "Step 1: Creating backup on VPS..."
ssh $VPS_HOST "cd $VPS_APP_DIR && mkdir -p $BACKUP_DIR && tar -czf $BACKUP_DIR/pre_update_backup_\$(date +%Y%m%d_%H%M%S).tar.gz ."

print_step "Step 2: Copying latest files to VPS..."
# Copy all files from production-package to VPS
rsync -avz --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' $LOCAL_PRODUCTION_DIR/ $VPS_HOST:$VPS_APP_DIR/

print_step "Step 3: Setting proper permissions on VPS..."
ssh $VPS_HOST "cd $VPS_APP_DIR && chown -R tradingapp:tradingapp . && chmod +x *.sh"

print_step "Step 4: Updating Python dependencies..."
ssh $VPS_HOST "cd $VPS_APP_DIR && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

print_step "Step 5: Running database migrations..."
ssh $VPS_HOST "cd $VPS_APP_DIR && source venv/bin/activate && flask db upgrade"

print_step "Step 6: Creating static directories if they don't exist..."
ssh $VPS_HOST "cd $VPS_APP_DIR && mkdir -p static/uploads static/css static/js static/images && chmod 755 static/uploads"

print_step "Step 7: Restarting the application service..."
ssh $VPS_HOST "sudo systemctl restart trading-analysis"

print_step "Step 8: Waiting for service to start..."
sleep 5

print_step "Step 9: Checking service status..."
if ssh $VPS_HOST "sudo systemctl is-active --quiet trading-analysis"; then
    print_status "✅ Application service is running successfully!"
else
    print_error "❌ Application service failed to start!"
    ssh $VPS_HOST "sudo systemctl status trading-analysis"
    exit 1
fi

print_step "Step 10: Testing application..."
# Test if the application responds
if ssh $VPS_HOST "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000" | grep -q "200\|302"; then
    print_status "✅ Application is responding correctly!"
else
    print_warning "⚠️  Application may not be responding correctly. Check logs for details."
fi

print_step "Step 11: Cleaning up old backups..."
ssh $VPS_HOST "cd $BACKUP_DIR && ls -t *.tar.gz | tail -n +6 | xargs -r rm"

print_status "🎉 Comprehensive VPS update completed successfully!"

echo ""
echo "📋 Update Summary:"
echo "- Backup created in $BACKUP_DIR"
echo "- Latest files copied from production-package"
echo "- Dependencies updated"
echo "- Database migrations applied"
echo "- Application service restarted"
echo "- Service status: RUNNING"
echo ""
echo "🔗 Your application should be available at: http://167.88.43.61"
echo ""
echo "📝 Useful commands for monitoring:"
echo "- Check service status: ssh $VPS_HOST 'sudo systemctl status trading-analysis'"
echo "- View logs: ssh $VPS_HOST 'sudo journalctl -u trading-analysis -f'"
echo "- Check application: ssh $VPS_HOST 'curl -I http://localhost:8000'"
