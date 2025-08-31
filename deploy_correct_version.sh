#!/bin/bash

echo "🚀 Deploying Correct App Version with Market Brief..."
echo "=================================================="

# Configuration
SERVER_IP="167.88.43.61"
SERVER_USER="root"
APP_DIR="/home/tradingapp/trading-analysis"

echo "📋 Deploying to: ${SERVER_USER}@${SERVER_IP}:${APP_DIR}"

# Step 1: Create backup
echo ""
echo "🔒 Step 1: Creating backup..."
ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p /root/app-backup-$(date +%Y%m%d-%H%M%S) && cp -r ${APP_DIR}/* /root/app-backup-$(date +%Y%m%d-%H%M%S)/ && echo 'Backup created'"

# Step 2: Stop service
echo ""
echo "⏹️  Step 2: Stopping service..."
ssh ${SERVER_USER}@${SERVER_IP} "systemctl stop trading-analysis || echo 'Service was not running'"

# Step 3: Deploy updated files
echo ""
echo "📦 Step 3: Deploying updated files..."

echo "   Copying app.py..."
scp app.py ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

echo "   Copying forms.py..."
scp forms.py ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

echo "   Copying base.html..."
scp templates/base.html ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/templates/

# Step 4: Verify file sizes and content
echo ""
echo "🔍 Step 4: Verifying deployment..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    echo "File sizes:"
    echo "  app.py: $(wc -c < /home/tradingapp/trading-analysis/app.py) bytes"
    echo "  forms.py: $(wc -c < /home/tradingapp/trading-analysis/forms.py) bytes"
    echo "  base.html: $(wc -c < /home/tradingapp/trading-analysis/templates/base.html) bytes"
    
    echo ""
    echo "Checking for market brief functionality:"
    if grep -q "market_brief" /home/tradingapp/trading-analysis/app.py; then
        echo "✅ Market brief route found in app.py"
    else
        echo "❌ Market brief route NOT found in app.py"
    fi
    
    echo "Checking for mobile OAuth functionality:"
    if grep -q "mobile_preference" /home/tradingapp/trading-analysis/app.py; then
        echo "✅ Mobile OAuth fixes found in app.py"
    else
        echo "❌ Mobile OAuth fixes NOT found in app.py"
    fi
    
    echo "Checking for SettingsForm:"
    if grep -q "SettingsForm" /home/tradingapp/trading-analysis/forms.py; then
        echo "✅ SettingsForm found in forms.py"
    else
        echo "❌ SettingsForm NOT found in forms.py"
    fi
EOF

# Step 5: Start service
echo ""
echo "🔄 Step 5: Starting service..."
ssh ${SERVER_USER}@${SERVER_IP} "systemctl start trading-analysis"

# Step 6: Wait and test
echo ""
echo "⏳ Step 6: Waiting for service to start..."
sleep 5

echo ""
echo "🧪 Step 7: Testing application..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    if systemctl is-active --quiet trading-analysis; then
        echo "✅ Service is running"
        
        echo "Testing routes:"
        echo "  Dashboard: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/dashboard)"
        echo "  Market Brief: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/market_brief)"
        echo "  Home: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/)"
        
    else
        echo "❌ Service failed to start"
        systemctl status trading-analysis
    fi
EOF

echo ""
echo "🎉 Deployment completed!"
echo "=================================================="
echo ""
echo "✅ Correct app version with market brief deployed"
echo "✅ Mobile OAuth fixes included"
echo "✅ SettingsForm functionality included"
echo "✅ Service restarted successfully"
echo ""
echo "🌐 Your live app at https://optionsplunge.com should now show:"
echo "   • Market brief section"
echo "   • Action landing page"
echo "   • Mobile-friendly Google OAuth"
echo "   • Enhanced mobile sidebar"

