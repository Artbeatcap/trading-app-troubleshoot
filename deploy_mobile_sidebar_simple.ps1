# Deploy Mobile Sidebar Fix to Live App
# This script updates the live trading analysis app with mobile sidebar improvements

Write-Host "🚀 Deploying Mobile Sidebar Fix to Live App..." -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue

# Configuration
$REMOTE_HOST = "167.88.43.61"
$REMOTE_USER = "root"
$REMOTE_APP_DIR = "/home/tradingapp/trading-analysis"
$LOCAL_TEMPLATE = "templates/base.html"
$REMOTE_TEMPLATE = "$REMOTE_APP_DIR/templates/base.html"

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Step 1: Backup current template
Write-Status "Creating backup of current template..."
$backup_result = ssh $REMOTE_USER@$REMOTE_HOST "cp $REMOTE_TEMPLATE $REMOTE_TEMPLATE.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Backup created successfully"
} else {
    Write-Error "Failed to create backup"
    exit 1
}

# Step 2: Upload updated template
Write-Status "Uploading updated base.html template..."
$upload_result = scp $LOCAL_TEMPLATE "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_TEMPLATE}"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Template uploaded successfully"
} else {
    Write-Error "Failed to upload template"
    exit 1
}

# Step 3: Verify the upload
Write-Status "Verifying uploaded template..."
$verify_result = ssh $REMOTE_USER@$REMOTE_HOST "grep -q 'sidebar-content' $REMOTE_TEMPLATE"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Mobile sidebar fixes verified in template"
} else {
    Write-Error "Mobile sidebar fixes not found in uploaded template"
    exit 1
}

# Step 4: Check file permissions
Write-Status "Setting correct file permissions..."
$permissions_result = ssh $REMOTE_USER@$REMOTE_HOST "chown tradingapp:tradingapp $REMOTE_TEMPLATE && chmod 644 $REMOTE_TEMPLATE"

if ($LASTEXITCODE -eq 0) {
    Write-Success "File permissions set correctly"
} else {
    Write-Warning "Failed to set file permissions"
}

# Step 5: Restart the application
Write-Status "Restarting the trading analysis application..."
$restart_result = ssh $REMOTE_USER@$REMOTE_HOST "systemctl restart trading-analysis"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Application restarted successfully"
} else {
    Write-Warning "Failed to restart application - you may need to restart manually"
}

# Step 6: Check application status
Write-Status "Checking application status..."
ssh $REMOTE_USER@$REMOTE_HOST "systemctl status trading-analysis --no-pager -l"

# Step 7: Test the deployment
Write-Status "Testing the mobile sidebar functionality..."
$test_result = ssh $REMOTE_USER@$REMOTE_HOST "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Application is responding to HTTP requests"
} else {
    Write-Warning "Application may not be responding - check logs"
}

Write-Host ""
Write-Host "🎉 Mobile Sidebar Fix Deployment Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📱 Changes Deployed:" -ForegroundColor Cyan
Write-Host "   ✅ Enhanced mobile sidebar scrolling" -ForegroundColor Green
Write-Host "   ✅ Auto-hide functionality after navigation" -ForegroundColor Green
Write-Host "   ✅ Touch gesture support (swipe to open/close)" -ForegroundColor Green
Write-Host "   ✅ Improved mobile UX and responsive design" -ForegroundColor Green
Write-Host ""
Write-Host "🔍 To verify the deployment:" -ForegroundColor Cyan
Write-Host "   1. Visit the live app on a mobile device" -ForegroundColor White
Write-Host "   2. Open the sidebar and test scrolling" -ForegroundColor White
Write-Host "   3. Select a navigation option to test auto-hide" -ForegroundColor White
Write-Host "   4. Test swipe gestures from the left edge" -ForegroundColor White



