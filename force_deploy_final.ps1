# Force deploy all files and restart service
$SERVER = "root@167.88.43.61"
$APP_DIR = "/home/tradingapp/trading-analysis"

Write-Host "Forcing full deployment..." -ForegroundColor Cyan

# Upload all files
Write-Host "Uploading files..." -ForegroundColor Yellow
scp app.py ${SERVER}:${APP_DIR}/
scp templates/register.html ${SERVER}:${APP_DIR}/templates/
scp templates/login.html ${SERVER}:${APP_DIR}/templates/
scp gunicorn.conf.py ${SERVER}:${APP_DIR}/

# Stop service completely
Write-Host "Stopping service..." -ForegroundColor Yellow
ssh $SERVER "systemctl stop trading-analysis.service"
Start-Sleep -Seconds 2

# Clear any cached bytecode
Write-Host "Clearing Python cache..." -ForegroundColor Yellow
ssh $SERVER "find $APP_DIR -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true"
ssh $SERVER "find $APP_DIR -name '*.pyc' -delete 2>/dev/null || true"

# Start service
Write-Host "Starting service..." -ForegroundColor Yellow
ssh $SERVER "systemctl start trading-analysis.service"
Start-Sleep -Seconds 7

# Check status
Write-Host "Checking status..." -ForegroundColor Yellow
ssh $SERVER "systemctl status trading-analysis.service --no-pager | head -15"

Write-Host "`nTesting..." -ForegroundColor Cyan
ssh $SERVER "curl -s http://localhost:8000/register | grep -c 'Sign up with Google'"

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green


