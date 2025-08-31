#!/bin/bash

# Deploy Mobile Sidebar Fix to Live App
# This script updates the live trading analysis app with mobile sidebar improvements

echo "🚀 Deploying Mobile Sidebar Fix to Live App..."
echo "================================================"

# Configuration
REMOTE_HOST="167.88.43.61"
REMOTE_USER="root"
REMOTE_APP_DIR="/home/tradingapp/trading-analysis"
LOCAL_TEMPLATE="templates/base.html"
REMOTE_TEMPLATE="$REMOTE_APP_DIR/templates/base.html"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Backup current template
print_status "Creating backup of current template..."
ssh $REMOTE_USER@$REMOTE_HOST "cp $REMOTE_TEMPLATE $REMOTE_TEMPLATE.backup.$(date +%Y%m%d_%H%M%S)"

if [ $? -eq 0 ]; then
    print_success "Backup created successfully"
else
    print_error "Failed to create backup"
    exit 1
fi

# Step 2: Upload updated template
print_status "Uploading updated base.html template..."
scp $LOCAL_TEMPLATE $REMOTE_USER@$REMOTE_HOST:$REMOTE_TEMPLATE

if [ $? -eq 0 ]; then
    print_success "Template uploaded successfully"
else
    print_error "Failed to upload template"
    exit 1
fi

# Step 3: Verify the upload
print_status "Verifying uploaded template..."
ssh $REMOTE_USER@$REMOTE_HOST "grep -q 'sidebar-content' $REMOTE_TEMPLATE"

if [ $? -eq 0 ]; then
    print_success "Mobile sidebar fixes verified in template"
else
    print_error "Mobile sidebar fixes not found in uploaded template"
    exit 1
fi

# Step 4: Check file permissions
print_status "Setting correct file permissions..."
ssh $REMOTE_USER@$REMOTE_HOST "chown tradingapp:tradingapp $REMOTE_TEMPLATE && chmod 644 $REMOTE_TEMPLATE"

if [ $? -eq 0 ]; then
    print_success "File permissions set correctly"
else
    print_warning "Failed to set file permissions"
fi

# Step 5: Restart the application
print_status "Restarting the trading analysis application..."
ssh $REMOTE_USER@$REMOTE_HOST "systemctl restart trading-analysis"

if [ $? -eq 0 ]; then
    print_success "Application restarted successfully"
else
    print_warning "Failed to restart application - you may need to restart manually"
fi

# Step 6: Check application status
print_status "Checking application status..."
ssh $REMOTE_USER@$REMOTE_HOST "systemctl status trading-analysis --no-pager -l"

# Step 7: Test the deployment
print_status "Testing the mobile sidebar functionality..."
ssh $REMOTE_USER@$REMOTE_HOST "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/"

if [ $? -eq 0 ]; then
    print_success "Application is responding to HTTP requests"
else
    print_warning "Application may not be responding - check logs"
fi

echo ""
echo "🎉 Mobile Sidebar Fix Deployment Complete!"
echo "=========================================="
echo ""
echo "📱 Changes Deployed:"
echo "   ✅ Enhanced mobile sidebar scrolling"
echo "   ✅ Auto-hide functionality after navigation"
echo "   ✅ Touch gesture support (swipe to open/close)"
echo "   ✅ Improved mobile UX and responsive design"
echo ""
echo "🔍 To verify the deployment:"
echo "   1. Visit the live app on a mobile device"
echo "   2. Open the sidebar and test scrolling"
echo "   3. Select a navigation option to test auto-hide"
echo "   4. Test swipe gestures from the left edge"
echo ""
echo "📋 Rollback Instructions:"
echo "   If needed, restore from backup:"
echo "   ssh $REMOTE_USER@$REMOTE_HOST \"cp $REMOTE_TEMPLATE.backup.* $REMOTE_TEMPLATE\""
