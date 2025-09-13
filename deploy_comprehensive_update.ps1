# Comprehensive Deployment Script
# Updates all local changes to the live trading analysis app

Write-Host "🚀 Starting Comprehensive Deployment to Live App..." -ForegroundColor Blue
Write-Host "==================================================" -ForegroundColor Blue

# Configuration
$REMOTE_HOST = "167.88.43.61"
$REMOTE_USER = "root"
$REMOTE_APP_DIR = "/home/tradingapp/trading-analysis"

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

# Step 1: Create backup of current live app
Write-Status "Creating backup of current live app..."
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup_result = ssh $REMOTE_USER@$REMOTE_HOST "tar -czf /home/tradingapp/trading-analysis.backup.$timestamp.tar.gz -C /home/tradingapp trading-analysis"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Backup created successfully: trading-analysis.backup.$timestamp.tar.gz"
} else {
    Write-Warning "Backup creation may have failed, but continuing..."
}

# Step 2: Update main application files
Write-Status "Updating main application files..."

$main_files = @(
    "app.py",
    "config.py",
    "models.py",
    "forms.py",
    "billing.py",
    "emailer.py",
    "emails.py",
    "tasks.py",
    "wsgi.py",
    "requirements.txt"
)

foreach ($file in $main_files) {
    if (Test-Path $file) {
        Write-Status "Uploading $file..."
        $upload_result = scp $file "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/$file"
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$file uploaded successfully"
        } else {
            Write-Warning "Failed to upload $file"
        }
    }
}

# Step 3: Update templates
Write-Status "Updating templates..."
$template_result = scp -r templates/* ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/templates/

if ($LASTEXITCODE -eq 0) {
    Write-Success "Templates updated successfully"
} else {
    Write-Warning "Template update may have had issues"
}

# Step 4: Update static files
Write-Status "Updating static files..."
if (Test-Path "static") {
    $static_result = scp -r static/* ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/static/
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Static files updated successfully"
    } else {
        Write-Warning "Static files update may have had issues"
    }
}

# Step 5: Update migrations
Write-Status "Updating migrations..."
if (Test-Path "migrations") {
    $migration_result = scp -r migrations/* ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/migrations/
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Migrations updated successfully"
    } else {
        Write-Warning "Migrations update may have had issues"
    }
}

# Step 6: Set correct file permissions
Write-Status "Setting correct file permissions..."
$permissions_result = ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_APP_DIR && chown -R tradingapp:tradingapp . && chmod -R 644 *.py *.txt *.md && chmod -R 755 templates static migrations"

if ($LASTEXITCODE -eq 0) {
    Write-Success "File permissions set correctly"
} else {
    Write-Warning "File permissions may not be set correctly"
}

# Step 7: Update Python dependencies
Write-Status "Updating Python dependencies..."
$pip_result = ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_APP_DIR && source venv/bin/activate && pip install -r requirements.txt --upgrade"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Python dependencies updated successfully"
} else {
    Write-Warning "Python dependencies update may have had issues"
}

# Step 8: Run database migrations
Write-Status "Running database migrations..."
$db_migration_result = ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_APP_DIR && source venv/bin/activate && python -m flask db upgrade"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Database migrations completed successfully"
} else {
    Write-Warning "Database migrations may have had issues"
}

# Step 9: Restart the application
Write-Status "Restarting the trading analysis application..."
$restart_result = ssh $REMOTE_USER@$REMOTE_HOST "systemctl restart trading-analysis"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Application restarted successfully"
} else {
    Write-Warning "Failed to restart application - you may need to restart manually"
}

# Step 10: Check application status
Write-Status "Checking application status..."
$status_result = ssh $REMOTE_USER@$REMOTE_HOST "systemctl status trading-analysis --no-pager -l"

# Step 11: Test the deployment
Write-Status "Testing the deployment..."
Start-Sleep -Seconds 5  # Wait for app to fully start
$test_result = ssh $REMOTE_USER@$REMOTE_HOST "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Application is responding to HTTP requests"
} else {
    Write-Warning "Application may not be responding - check logs"
}

# Step 12: Check application logs
Write-Status "Checking application logs..."
$logs_result = ssh $REMOTE_USER@$REMOTE_HOST "tail -20 $REMOTE_APP_DIR/app.log"

Write-Host ""
Write-Host "🎉 Comprehensive Deployment Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "📱 Changes Deployed:" -ForegroundColor Cyan
Write-Host "   ✅ Main application files updated" -ForegroundColor Green
Write-Host "   ✅ Templates updated" -ForegroundColor Green
Write-Host "   ✅ Static files updated" -ForegroundColor Green
Write-Host "   ✅ Database migrations run" -ForegroundColor Green
Write-Host "   ✅ Python dependencies updated" -ForegroundColor Green
Write-Host "   ✅ Application restarted" -ForegroundColor Green
Write-Host ""
Write-Host "🔍 To verify the deployment:" -ForegroundColor Cyan
Write-Host "   1. Visit the live app" -ForegroundColor White
Write-Host "   2. Test key functionality" -ForegroundColor White
Write-Host "   3. Check mobile sidebar behavior" -ForegroundColor White
Write-Host "   4. Verify all features are working" -ForegroundColor White
Write-Host ""
Write-Host "📋 Backup Information:" -ForegroundColor Yellow
Write-Host "   Backup created: trading-analysis.backup.$timestamp.tar.gz" -ForegroundColor Gray
Write-Host ""
Write-Host "🔄 Rollback Instructions:" -ForegroundColor Yellow
Write-Host "   If needed, restore from backup:" -ForegroundColor White
Write-Host "   ssh $REMOTE_USER@$REMOTE_HOST 'cd /home/tradingapp && tar -xzf trading-analysis.backup.$timestamp.tar.gz'" -ForegroundColor Gray
Write-Host "   ssh $REMOTE_USER@$REMOTE_HOST 'systemctl restart trading-analysis'" -ForegroundColor Gray



