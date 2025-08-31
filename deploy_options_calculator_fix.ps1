#!/usr/bin/env pwsh
# Deploy Options Calculator Fix to Live App
# This script updates the live trading analysis app with the latest changes

Write-Host "🚀 Deploying Options Calculator Fix to Live App..." -ForegroundColor Green

# Configuration
$SERVER_IP = "167.88.43.61"
$REMOTE_PATH = "/home/tradingapp/trading-analysis"
$LOCAL_PATH = "."

# Step 1: Create a backup of the current live app
Write-Host "📦 Creating backup of current live app..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup_name = "trading-analysis-backup-$timestamp.tar.gz"

$backup_cmd = "cd $REMOTE_PATH; tar -czf $backup_name --exclude='venv*' --exclude='__pycache__' --exclude='*.log' ."
ssh root@$SERVER_IP $backup_cmd

# Step 2: Copy the updated .env file
Write-Host "🔧 Updating environment configuration..." -ForegroundColor Yellow
scp .env root@${SERVER_IP}:${REMOTE_PATH}/.env

# Step 3: Copy the main application files
Write-Host "📁 Copying updated application files..." -ForegroundColor Yellow

# Core application files
$core_files = @(
    "app.py",
    "config.py", 
    "models.py",
    "forms.py",
    "tasks.py",
    "wsgi.py",
    "requirements.txt"
)

foreach ($file in $core_files) {
    if (Test-Path $file) {
        Write-Host "  Copying $file..." -ForegroundColor Cyan
        scp $file root@${SERVER_IP}:${REMOTE_PATH}/
    }
}

# Step 4: Copy templates
Write-Host "🎨 Copying updated templates..." -ForegroundColor Yellow
if (Test-Path "templates") {
    scp -r templates root@${SERVER_IP}:${REMOTE_PATH}/
}

# Step 5: Copy static files
Write-Host "📄 Copying static files..." -ForegroundColor Yellow
if (Test-Path "static") {
    scp -r static root@${SERVER_IP}:${REMOTE_PATH}/
}

# Step 6: Restart the application
Write-Host "🔄 Restarting the application..." -ForegroundColor Yellow
ssh root@$SERVER_IP "systemctl restart trading-analysis"

# Step 7: Check application status
Write-Host "✅ Checking application status..." -ForegroundColor Yellow
ssh root@$SERVER_IP "systemctl status trading-analysis --no-pager"

# Step 8: Test the options calculator
Write-Host "🧪 Testing options calculator..." -ForegroundColor Yellow
$test_cmd = "cd $REMOTE_PATH; python3 -c 'import os; from dotenv import load_dotenv; load_dotenv(); token = os.getenv(\"TRADIER_API_TOKEN\"); print(\"TRADIER_API_TOKEN configured: \" + (\"Yes\" if token else \"No\")); print(\"Token preview: \" + token[:10] + \"...\" if token else \"No token\")'"
ssh root@$SERVER_IP $test_cmd

Write-Host "🎉 Deployment completed!" -ForegroundColor Green
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Visit https://optionsplunge.com/tools/options-calculator" -ForegroundColor White
Write-Host "   2. Test with a stock symbol (e.g., AAPL)" -ForegroundColor White
Write-Host "   3. Verify the 500 error is resolved" -ForegroundColor White
