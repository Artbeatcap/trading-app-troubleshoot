# Comprehensive Deployment Script
# Updates all local changes to the live trading analysis app.
#
# Covers the Polygon-only data-source migration:
#   - Syncs providers/, pipeline/, schemas/, daily_brief/ packages.
#   - Syncs all python modules touched by the migration/audit.
#   - Removes old/backup/remote files that are no longer in the repo.
#   - Smoke-tests gunicorn on the correct port (8000).

Write-Host "Starting Comprehensive Deployment to Live App..." -ForegroundColor Blue
Write-Host "==================================================" -ForegroundColor Blue

# Configuration
$REMOTE_HOST = "167.88.43.61"
$REMOTE_USER = "root"
$REMOTE_APP_DIR = "/home/tradingapp/trading-analysis"
$REMOTE_PORT = "8000"

function Write-Status { param([string]$Message); Write-Host "[INFO] $Message" -ForegroundColor Blue }
function Write-Success { param([string]$Message); Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message); Write-Host "[WARNING] $Message" -ForegroundColor Yellow }
function Write-Err { param([string]$Message); Write-Host "[ERROR] $Message" -ForegroundColor Red }

# Step 1: Backup current live app
Write-Status "Creating backup of current live app..."
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
ssh $REMOTE_USER@$REMOTE_HOST "tar -czf /home/tradingapp/trading-analysis.backup.$timestamp.tar.gz -C /home/tradingapp trading-analysis"
if ($LASTEXITCODE -eq 0) {
    Write-Success "Backup created: trading-analysis.backup.$timestamp.tar.gz"
} else {
    Write-Warn "Backup creation may have failed, but continuing..."
}

# Step 2: Upload main application files
Write-Status "Uploading main application files..."

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
    "brief_routes.py",
    "requirements.txt",
    "env_example.txt",
    "ai_analysis.py",
    "gpt_summary.py",
    "headline_summarizer.py",
    "daily_brief_schema.py",
    "weekly_brief_schema.py",
    "market_brief_generator.py",
    "market_brief_generator_fixed.py",
    "send_morning_brief.py",
    "send_weekly_brief.py",
    "send_manual_brief.py",
    "gen_site_brief.py",
    "gen_email_preview.py"
)

foreach ($file in $main_files) {
    if (Test-Path $file) {
        Write-Status "Uploading $file..."
        scp $file "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/$file" | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Success "$file uploaded" } else { Write-Warn "Failed to upload $file" }
    } else {
        Write-Warn "Skipping missing file: $file"
    }
}

# Step 3: Upload Python packages (new directories)
Write-Status "Uploading Python packages (providers/, pipeline/, schemas/, daily_brief/)..."
$pkg_dirs = @("providers", "pipeline", "schemas", "daily_brief")
foreach ($dir in $pkg_dirs) {
    if (Test-Path $dir) {
        Write-Status "Ensuring remote $dir exists..."
        ssh $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_APP_DIR/$dir" | Out-Null
        Write-Status "Syncing $dir/*.py..."
        scp "$dir/*.py" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/$dir/" | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Success "$dir/ uploaded" } else { Write-Warn "Failed to upload $dir/" }
    } else {
        Write-Warn "Skipping missing directory: $dir"
    }
}

# Step 4: Upload templates
Write-Status "Updating templates..."
scp -r templates/* "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/templates/" | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Success "Templates updated" } else { Write-Warn "Template update had issues" }

# Step 5: Upload static files
Write-Status "Updating static files..."
if (Test-Path "static") {
    scp -r static/* "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/static/" | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Success "Static files updated" } else { Write-Warn "Static files update had issues" }
}

# Step 6: Upload migrations
Write-Status "Updating migrations..."
if (Test-Path "migrations") {
    scp -r migrations/* "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/migrations/" | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Success "Migrations updated" } else { Write-Warn "Migrations update had issues" }
}

# Step 7: Upload style/
Write-Status "Updating style/ (brief_voice.md etc.)..."
if (Test-Path "style") {
    ssh $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_APP_DIR/style" | Out-Null
    scp style/* "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/style/" | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Success "style/ updated" } else { Write-Warn "style/ update had issues" }
}

# Step 8: Remove old / deprecated files that no longer exist locally
Write-Status "Cleaning up removed / backup files on server..."
$cleanup_cmd = @"
cd $REMOTE_APP_DIR && rm -f \
  tradier_provider.py \
  polygon_seed.py \
  movers_scan.py \
  fix_users_without_settings.py \
  app_backup_.py \
  app.remote.py \
  config.remote.py \
  create_admin.remote.py \
  gunicorn.remote.conf.py \
  gpt_summary_backup.py \
  gpt_summary_fixed.py \
  market_brief_generator_backup_20251115_032208.py \
  market_brief_generator_improved.py \
  test_gapping_stocks_fix.py
"@
ssh $REMOTE_USER@$REMOTE_HOST $cleanup_cmd | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Success "Old files removed" } else { Write-Warn "Cleanup had issues (non-fatal)" }

# Step 9: File permissions
Write-Status "Setting correct file permissions..."
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_APP_DIR && chown -R tradingapp:tradingapp . && find . -type f -name '*.py' -exec chmod 644 {} \; && find . -type d -exec chmod 755 {} \;" | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Success "Permissions set" } else { Write-Warn "Permissions may not be correct" }

# Step 10: Update Python dependencies
Write-Status "Updating Python dependencies..."
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_APP_DIR && source venv/bin/activate && pip install -r requirements.txt --upgrade"
if ($LASTEXITCODE -eq 0) { Write-Success "Dependencies updated" } else { Write-Warn "Dependency update had issues" }

# Step 11: Database migrations
Write-Status "Running database migrations..."
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_APP_DIR && source venv/bin/activate && python -m flask db upgrade"
if ($LASTEXITCODE -eq 0) { Write-Success "Migrations complete" } else { Write-Warn "Migrations had issues" }

# Step 12: Restart the application
Write-Status "Restarting trading-analysis service..."
ssh $REMOTE_USER@$REMOTE_HOST "systemctl restart trading-analysis"
if ($LASTEXITCODE -eq 0) { Write-Success "Application restarted" } else { Write-Warn "Failed to restart application" }

# Step 13: Service status
Write-Status "Service status..."
ssh $REMOTE_USER@$REMOTE_HOST "systemctl is-active trading-analysis && systemctl status trading-analysis --no-pager -l | head -20"

# Step 14: Smoke test on gunicorn port 8000
Write-Status "Smoke-testing gunicorn on port $REMOTE_PORT..."
Start-Sleep -Seconds 5
$http_code = ssh $REMOTE_USER@$REMOTE_HOST "curl -s -o /dev/null -w '%{http_code}' http://localhost:$REMOTE_PORT/"
Write-Status "HTTP code: $http_code"
if ($http_code -match '^(200|301|302|307|308)$') {
    Write-Success "App responding on port $REMOTE_PORT (HTTP $http_code)"
} else {
    Write-Warn "App may not be responding correctly (HTTP $http_code) - check logs"
}

# Step 15: Tail recent logs
Write-Status "Recent app log (last 20 lines)..."
ssh $REMOTE_USER@$REMOTE_HOST "tail -20 /var/log/trading-analysis/app.log 2>/dev/null || tail -20 $REMOTE_APP_DIR/app.log 2>/dev/null || echo '(no log file found)'"
Write-Status "Recent error log (last 20 lines)..."
ssh $REMOTE_USER@$REMOTE_HOST "tail -20 /var/log/trading-analysis/error.log 2>/dev/null || echo '(no error log file found)'"

Write-Host ""
Write-Host "Comprehensive Deployment Complete" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""
Write-Host "Changes Deployed:" -ForegroundColor Cyan
Write-Host "  * Main Python files (app, config, models, billing, emails, tasks, etc.)" -ForegroundColor Green
Write-Host "  * providers/, pipeline/, schemas/, daily_brief/ packages" -ForegroundColor Green
Write-Host "  * templates/, static/, migrations/, style/" -ForegroundColor Green
Write-Host "  * Python dependencies reinstalled" -ForegroundColor Green
Write-Host "  * Legacy/backup/.remote files removed" -ForegroundColor Green
Write-Host "  * Database migrations applied" -ForegroundColor Green
Write-Host "  * Service restarted and smoke-tested on port $REMOTE_PORT" -ForegroundColor Green
Write-Host ""
Write-Host "Backup Info:" -ForegroundColor Yellow
Write-Host "  trading-analysis.backup.$timestamp.tar.gz" -ForegroundColor Gray
Write-Host ""
Write-Host "Rollback:" -ForegroundColor Yellow
Write-Host "  ssh $REMOTE_USER@$REMOTE_HOST 'cd /home/tradingapp && tar -xzf trading-analysis.backup.$timestamp.tar.gz'" -ForegroundColor Gray
Write-Host "  ssh $REMOTE_USER@$REMOTE_HOST 'systemctl restart trading-analysis'" -ForegroundColor Gray
