# Deploy dark mode fix and recent changes to live app (PowerShell version)

Write-Host "🚀 Deploying dark mode fix and recent changes to live app..." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

# Set variables
$REMOTE_HOST = "root@167.88.43.61"
$REMOTE_DIR = "/home/tradingapp/trading-analysis"
$LOCAL_DIR = "."

# Create timestamp for backup
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_NAME = "trading-analysis-backup-${TIMESTAMP}.tar.gz"

Write-Host "📦 Creating backup of current live app..." -ForegroundColor Yellow
ssh $REMOTE_HOST "cd $REMOTE_DIR; tar -czf $BACKUP_NAME --exclude='*.tar.gz' --exclude='venv*' --exclude='__pycache__' --exclude='.git' ."

Write-Host "✅ Backup created: $BACKUP_NAME" -ForegroundColor Green

# Files to update (focusing on dark mode and recent changes)
$FILES_TO_UPDATE = @(
    "app.py",
    "forms.py", 
    "models.py",
    "templates/base.html",
    "templates/settings.html",
    "migrate_user_settings.py",
    "requirements.txt"
)

Write-Host "📤 Uploading updated files..." -ForegroundColor Yellow

foreach ($file in $FILES_TO_UPDATE) {
    if (Test-Path $file) {
        Write-Host "  📄 Uploading $file..." -ForegroundColor Cyan
        scp $file "${REMOTE_HOST}:${REMOTE_DIR}/${file}"
    } else {
        Write-Host "  ⚠️  Warning: $file not found locally" -ForegroundColor Yellow
    }
}

Write-Host "🔧 Running database migrations..." -ForegroundColor Yellow
ssh $REMOTE_HOST "cd $REMOTE_DIR; source venv/bin/activate; python migrate_user_settings.py"

Write-Host "🔄 Restarting the application..." -ForegroundColor Yellow
ssh $REMOTE_HOST "systemctl restart trading-analysis"

Write-Host "⏳ Waiting for app to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "🔍 Checking application status..." -ForegroundColor Yellow
ssh $REMOTE_HOST "systemctl status trading-analysis --no-pager"

Write-Host "✅ Deployment completed!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Live app should now have dark mode functionality working correctly." -ForegroundColor Green
Write-Host "📝 To test:" -ForegroundColor Cyan
Write-Host "   1. Visit your live app" -ForegroundColor White
Write-Host "   2. Log in to your account" -ForegroundColor White
Write-Host "   3. Go to Settings page" -ForegroundColor White
Write-Host "   4. Toggle the 'Enable dark mode' checkbox" -ForegroundColor White
Write-Host "   5. Save changes and refresh to see dark mode applied" -ForegroundColor White
Write-Host ""
Write-Host "📦 Backup saved as: $BACKUP_NAME" -ForegroundColor Cyan
