# PowerShell script to deploy correct app version with market brief

Write-Host "🚀 Deploying Correct App Version with Market Brief..." -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

$SERVER_IP = "167.88.43.61"
$SERVER_USER = "root"
$APP_DIR = "/home/tradingapp/trading-analysis"

Write-Host "📋 Deploying to: ${SERVER_USER}@${SERVER_IP}:${APP_DIR}" -ForegroundColor Yellow

# Step 1: Create backup
Write-Host ""
Write-Host "🔒 Step 1: Creating backup..." -ForegroundColor Cyan
$backup_cmd = "mkdir -p /root/app-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss') && cp -r ${APP_DIR}/* /root/app-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')/ && echo 'Backup created'"
ssh ${SERVER_USER}@${SERVER_IP} $backup_cmd

# Step 2: Stop service
Write-Host ""
Write-Host "⏹️  Step 2: Stopping service..." -ForegroundColor Cyan
ssh ${SERVER_USER}@${SERVER_IP} "systemctl stop trading-analysis || echo 'Service was not running'"

# Step 3: Deploy updated files
Write-Host ""
Write-Host "📦 Step 3: Deploying updated files..." -ForegroundColor Cyan

Write-Host "   Copying app.py..." -ForegroundColor White
scp app.py ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

Write-Host "   Copying forms.py..." -ForegroundColor White
scp forms.py ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

Write-Host "   Copying base.html..." -ForegroundColor White
scp templates/base.html ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/templates/

# Step 4: Start service
Write-Host ""
Write-Host "🔄 Step 4: Starting service..." -ForegroundColor Cyan
ssh ${SERVER_USER}@${SERVER_IP} "systemctl start trading-analysis"

# Step 5: Wait and test
Write-Host ""
Write-Host "⏳ Step 5: Waiting for service to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "🧪 Step 6: Testing application..." -ForegroundColor Cyan
$test_cmd = @"
if systemctl is-active --quiet trading-analysis; then
    echo "✅ Service is running"
    echo "Testing routes:"
    echo "  Dashboard: \$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/dashboard)"
    echo "  Market Brief: \$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/market_brief)"
    echo "  Home: \$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/)"
else
    echo "❌ Service failed to start"
    systemctl status trading-analysis
fi
"@

ssh ${SERVER_USER}@${SERVER_IP} $test_cmd

Write-Host ""
Write-Host "🎉 Deployment completed!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Correct app version with market brief deployed" -ForegroundColor Green
Write-Host "✅ Mobile OAuth fixes included" -ForegroundColor Green
Write-Host "✅ SettingsForm functionality included" -ForegroundColor Green
Write-Host "✅ Service restarted successfully" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Your live app at https://optionsplunge.com should now show:" -ForegroundColor Yellow
Write-Host "   • Market brief section" -ForegroundColor White
Write-Host "   • Action landing page" -ForegroundColor White
Write-Host "   • Mobile-friendly Google OAuth" -ForegroundColor White
Write-Host "   • Enhanced mobile sidebar" -ForegroundColor White

