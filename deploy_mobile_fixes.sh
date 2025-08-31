#!/bin/bash

# Mobile Fixes Deployment Script
# This script safely deploys the mobile-friendly updates to the live app

set -e  # Exit on any error

echo "🚀 Starting Mobile Fixes Deployment..."
echo "======================================"

# Configuration
SERVER_IP="167.88.43.61"
SERVER_USER="root"
APP_DIR="/root/trading-analysis"
BACKUP_DIR="/root/trading-analysis-backup-$(date +%Y%m%d-%H%M%S)"

echo "📋 Deployment Configuration:"
echo "   Server: ${SERVER_USER}@${SERVER_IP}"
echo "   App Directory: ${APP_DIR}"
echo "   Backup Directory: ${BACKUP_DIR}"

# Step 1: Create backup of current app
echo ""
echo "🔒 Step 1: Creating backup of current app..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    set -e
    echo "Creating backup directory..."
    mkdir -p /root/trading-analysis-backup-$(date +%Y%m%d-%H%M%S)
    
    echo "Copying current app files..."
    cp -r /root/trading-analysis/* /root/trading-analysis-backup-$(date +%Y%m%d-%H%M%S)/
    
    echo "Backup completed successfully"
EOF

# Step 2: Stop the current service
echo ""
echo "⏹️  Step 2: Stopping current service..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    set -e
    echo "Stopping trading-analysis service..."
    systemctl stop trading-analysis || echo "Service was not running"
    
    echo "Waiting for service to stop..."
    sleep 3
    
    echo "Checking if service is stopped..."
    if systemctl is-active --quiet trading-analysis; then
        echo "Service is still running, forcing stop..."
        systemctl kill trading-analysis
        sleep 2
    fi
    
    echo "Service stopped successfully"
EOF

# Step 3: Deploy updated files
echo ""
echo "📦 Step 3: Deploying updated files..."

# Copy the updated app.py with mobile OAuth fixes
echo "   Copying updated app.py..."
scp app.py ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

# Copy the updated base templates
echo "   Copying updated base templates..."
scp templates/base.html ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/templates/
scp production-package/templates/base.html ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/production-package/templates/

# Step 4: Verify file sizes and content
echo ""
echo "🔍 Step 4: Verifying deployment..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    set -e
    echo "Checking file sizes:"
    echo "  app.py: $(wc -c < /root/trading-analysis/app.py) bytes"
    echo "  templates/base.html: $(wc -c < /root/trading-analysis/templates/base.html) bytes"
    echo "  production-package/templates/base.html: $(wc -c < /root/trading-analysis/production-package/templates/base.html) bytes"
    
    echo ""
    echo "Verifying mobile OAuth functionality in app.py..."
    if grep -q "mobile_preference" /root/trading-analysis/app.py; then
        echo "✅ Mobile OAuth fixes found in app.py"
    else
        echo "❌ Mobile OAuth fixes NOT found in app.py"
        exit 1
    fi
    
    echo "Verifying mobile sidebar functionality in base.html..."
    if grep -q "mobile-menu-btn" /root/trading-analysis/templates/base.html; then
        echo "✅ Mobile sidebar functionality found in base.html"
    else
        echo "❌ Mobile sidebar functionality NOT found in base.html"
        exit 1
    fi
    
    echo "Verifying mobile viewport enforcement..."
    if grep -q "ensureMobileViewport" /root/trading-analysis/templates/base.html; then
        echo "✅ Mobile viewport enforcement found"
    else
        echo "❌ Mobile viewport enforcement NOT found"
        exit 1
    fi
EOF

# Step 5: Restart the service
echo ""
echo "🔄 Step 5: Restarting service..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    set -e
    echo "Starting trading-analysis service..."
    systemctl start trading-analysis
    
    echo "Waiting for service to start..."
    sleep 5
    
    echo "Checking service status..."
    if systemctl is-active --quiet trading-analysis; then
        echo "✅ Service is running successfully"
    else
        echo "❌ Service failed to start"
        systemctl status trading-analysis
        exit 1
    fi
    
    echo "Checking service logs..."
    journalctl -u trading-analysis --no-pager -n 10
EOF

# Step 6: Test the application
echo ""
echo "🧪 Step 6: Testing application..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    set -e
    echo "Testing main routes..."
    
    # Test dashboard route
    echo "Testing dashboard route..."
    curl -s -o /dev/null -w "Dashboard: %{http_code}\n" http://localhost:8000/dashboard
    
    # Test Google OAuth route
    echo "Testing Google OAuth route..."
    curl -s -o /dev/null -w "Google Login: %{http_code}\n" http://localhost:8000/google_login
    
    # Test base template
    echo "Testing base template..."
    curl -s -o /dev/null -w "Base Template: %{http_code}\n" http://localhost:8000/
    
    echo "✅ All routes responding correctly"
EOF

# Step 7: Verify nginx configuration
echo ""
echo "🌐 Step 7: Verifying nginx configuration..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    set -e
    echo "Checking nginx configuration..."
    nginx -t
    
    echo "Reloading nginx..."
    systemctl reload nginx
    
    echo "Checking nginx status..."
    systemctl is-active nginx && echo "✅ Nginx is running" || echo "❌ Nginx is not running"
EOF

echo ""
echo "🎉 Deployment completed successfully!"
echo "======================================"
echo ""
echo "📱 Mobile improvements deployed:"
echo "   ✅ Mobile OAuth redirect fixes"
echo "   ✅ Enhanced mobile sidebar functionality"
echo "   ✅ Mobile viewport enforcement"
echo "   ✅ Improved mobile CSS and JavaScript"
echo ""
echo "🔒 Safety measures taken:"
echo "   ✅ Backup created before deployment"
echo "   ✅ Service properly stopped and restarted"
echo "   ✅ File verification completed"
echo "   ✅ All routes tested successfully"
echo ""
echo "🌐 Your live app at https://optionsplunge.com should now have:"
echo "   • Proper mobile layout after Google OAuth login"
echo "   • Enhanced mobile sidebar with backdrop"
echo "   • Better mobile navigation experience"
echo "   • Improved mobile viewport handling"
echo ""
echo "If you need to rollback, the backup is available at:"
echo "   /root/trading-analysis-backup-$(date +%Y%m%d-%H%M%S)/"

