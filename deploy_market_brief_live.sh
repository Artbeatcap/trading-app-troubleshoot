#!/bin/bash

# Market Brief Live Deployment Script
# Based on troubleshooting lessons to ensure proper port configuration and service updates

set -e  # Exit on any error

echo "🚀 Starting Market Brief Live Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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
APP_DIR="/home/tradingapp/trading-analysis"
VENV_DIR="$APP_DIR/venv"
BACKUP_DIR="/home/tradingapp/backups"
VPS_IP="167.88.43.61"

print_step "Step 1: Pre-deployment checks and backup"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as tradingapp user."
   exit 1
fi

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup existing installation
if [ -f "$APP_DIR/app.py" ]; then
    print_status "Creating backup of existing installation..."
    tar -czf $BACKUP_DIR/market_brief_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C $APP_DIR .
fi

print_step "Step 2: Update application files"

cd $APP_DIR

# Activate virtual environment
source venv/bin/activate

# Update Python dependencies
print_status "Updating Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

print_step "Step 3: Verify market brief components"

# Check market brief files exist
required_files=(
    "market_brief_generator.py"
    "tasks.py"
    "market-brief-scheduler.service"
    "gunicorn.conf.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file missing: $file"
        exit 1
    fi
done

print_status "All market brief components verified"

print_step "Step 4: Update systemd services"

# Update trading-analysis service
print_status "Updating trading-analysis service..."
sudo tee /etc/systemd/system/trading-analysis.service > /dev/null << EOF
[Unit]
Description=Trading Analysis Flask App
After=network.target

[Service]
User=tradingapp
Group=tradingapp
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="DATABASE_URL=postgresql://trading_user:Hvjband12345@localhost/trading_analysis"
ExecStart=$VENV_DIR/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
StandardOutput=append:/var/log/trading-analysis/app.log
StandardError=append:/var/log/trading-analysis/error.log

[Install]
WantedBy=multi-user.target
EOF

# Update market brief scheduler service
print_status "Updating market brief scheduler service..."
sudo tee /etc/systemd/system/market-brief-scheduler.service > /dev/null << EOF
[Unit]
Description=Market Brief Scheduler
After=network.target

[Service]
Type=simple
User=tradingapp
Group=tradingapp
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="DATABASE_URL=postgresql://trading_user:Hvjband12345@localhost/trading_analysis"
ExecStart=$VENV_DIR/bin/python tasks.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/trading-analysis/scheduler.log
StandardError=append:/var/log/trading-analysis/scheduler_error.log

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
sudo mkdir -p /var/log/trading-analysis
sudo chown tradingapp:tradingapp /var/log/trading-analysis

print_step "Step 5: Restart services"

# Reload systemd and restart services
print_status "Reloading systemd and restarting services..."
sudo systemctl daemon-reload

# Stop existing services
sudo systemctl stop trading-analysis || true
sudo systemctl stop market-brief-scheduler || true

# Start services
sudo systemctl enable trading-analysis
sudo systemctl start trading-analysis

sudo systemctl enable market-brief-scheduler
sudo systemctl start market-brief-scheduler

# Wait for services to start
sleep 5

print_step "Step 6: Verify service status"

# Check service status
if sudo systemctl is-active --quiet trading-analysis; then
    print_status "✅ Trading Analysis service is running"
else
    print_error "❌ Trading Analysis service failed to start"
    sudo systemctl status trading-analysis
    exit 1
fi

if sudo systemctl is-active --quiet market-brief-scheduler; then
    print_status "✅ Market Brief Scheduler service is running"
else
    print_error "❌ Market Brief Scheduler service failed to start"
    sudo systemctl status market-brief-scheduler
    exit 1
fi

print_step "Step 7: Verify port configuration"

# Check what port the app is actually running on
print_status "Checking application port..."
RUNNING_PORT=$(sudo netstat -tlnp | grep gunicorn | awk '{print $4}' | cut -d: -f2 | head -1)

if [ -z "$RUNNING_PORT" ]; then
    print_error "No gunicorn process found running"
    exit 1
fi

print_status "Application is running on port: $RUNNING_PORT"

# Verify gunicorn config matches
GUNICORN_PORT=$(grep "bind" gunicorn.conf.py | cut -d'"' -f2 | cut -d: -f2)
print_status "Gunicorn configured for port: $GUNICORN_PORT"

if [ "$RUNNING_PORT" != "$GUNICORN_PORT" ]; then
    print_warning "Port mismatch detected. Running on $RUNNING_PORT, configured for $GUNICORN_PORT"
fi

print_step "Step 8: Update Nginx configuration"

# Update Nginx configuration to point to correct port
print_status "Updating Nginx configuration..."
sudo tee /etc/nginx/sites-available/trading-analysis > /dev/null << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:$RUNNING_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
    }

    location /uploads {
        alias $APP_DIR/static/uploads;
        expires 30d;
    }
}
EOF

# Also update default config if it exists
if [ -f "/etc/nginx/sites-available/default" ]; then
    print_status "Updating default Nginx configuration..."
    sudo sed -i "s/proxy_pass http:\/\/127.0.0.1:[0-9]*;/proxy_pass http:\/\/127.0.0.1:$RUNNING_PORT;/" /etc/nginx/sites-available/default
fi

# Test and reload Nginx
if sudo nginx -t; then
    sudo systemctl reload nginx
    print_status "✅ Nginx configuration updated and reloaded"
else
    print_error "❌ Nginx configuration test failed"
    exit 1
fi

print_step "Step 9: Verify deployment"

# Test internal connectivity
print_status "Testing internal connectivity..."
if curl -I http://localhost:$RUNNING_PORT > /dev/null 2>&1; then
    print_status "✅ Internal connectivity test passed"
else
    print_error "❌ Internal connectivity test failed"
    exit 1
fi

# Test external connectivity
print_status "Testing external connectivity..."
if curl -I http://localhost > /dev/null 2>&1; then
    print_status "✅ External connectivity test passed"
else
    print_error "❌ External connectivity test failed"
    exit 1
fi

print_step "Step 10: Final verification"

# Check for any remaining port 5000 references
print_status "Checking for any remaining port 5000 references..."
PORT_5000_REFS=$(sudo grep -r "proxy_pass.*5000" /etc/nginx/sites-available/ || true)
if [ -n "$PORT_5000_REFS" ]; then
    print_warning "Found remaining port 5000 references:"
    echo "$PORT_5000_REFS"
else
    print_status "✅ No remaining port 5000 references found"
fi

# Check running processes
print_status "Checking running processes..."
RUNNING_PROCESSES=$(ps aux | grep -E "(python|flask|gunicorn)" | grep -v grep || true)
if [ -n "$RUNNING_PROCESSES" ]; then
    print_status "Running processes:"
    echo "$RUNNING_PROCESSES"
else
    print_warning "No Python processes found running"
fi

print_status "🎉 Market Brief Live Deployment Completed Successfully!"

echo ""
echo "📋 Deployment Summary:"
echo "✅ Application updated and running on port $RUNNING_PORT"
echo "✅ Market Brief Scheduler service active"
echo "✅ Nginx configuration updated"
echo "✅ All services verified and running"
echo ""
echo "🔍 Useful commands:"
echo "- Check app status: sudo systemctl status trading-analysis"
echo "- Check scheduler status: sudo systemctl status market-brief-scheduler"
echo "- View app logs: sudo journalctl -u trading-analysis -f"
echo "- View scheduler logs: sudo journalctl -u market-brief-scheduler -f"
echo "- Test market brief: curl http://localhost/market-brief"
echo ""
echo "🌐 Your market brief is now live at: https://optionsplunge.com"

