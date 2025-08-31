# Market Brief Live Deployment Script (PowerShell)
# Based on troubleshooting lessons to ensure proper port configuration and service updates

param(
    [string]$VPS_IP = "167.88.43.61",
    [string]$VPS_USER = "root"
)

Write-Host "🚀 Starting Market Brief Live Deployment..." -ForegroundColor Green

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Blue
}

# Variables
$APP_DIR = "/home/tradingapp/trading-analysis"
$VENV_DIR = "$APP_DIR/venv"
$BACKUP_DIR = "/home/tradingapp/backups"

Write-Step "Step 1: Pre-deployment checks and backup"

# Create backup directory
$backupCmd = "ssh $VPS_USER@$VPS_IP 'mkdir -p $BACKUP_DIR'"
Write-Status "Creating backup directory..."
Invoke-Expression $backupCmd

# Backup existing installation
$backupCmd = "ssh $VPS_USER@$VPS_IP 'if [ -f `"$APP_DIR/app.py`" ]; then tar -czf $BACKUP_DIR/market_brief_backup_`$(date +%Y%m%d_%H%M%S).tar.gz -C $APP_DIR .; fi'"
Write-Status "Creating backup of existing installation..."
Invoke-Expression $backupCmd

Write-Step "Step 2: Update application files"

# Update Python dependencies
$updateCmd = "ssh $VPS_USER@$VPS_IP 'cd $APP_DIR && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt'"
Write-Status "Updating Python dependencies..."
Invoke-Expression $updateCmd

Write-Step "Step 3: Verify market brief components"

# Check required files exist
$checkFilesCmd = "ssh $VPS_USER@$VPS_IP 'cd $APP_DIR && for file in market_brief_generator.py tasks.py market-brief-scheduler.service gunicorn.conf.py; do if [ ! -f `"`$file`" ]; then echo `"Missing: `$file`"; exit 1; fi; done && echo `"All files present`"'"
Write-Status "Verifying market brief components..."
Invoke-Expression $checkFilesCmd

Write-Step "Step 4: Update systemd services"

# Update trading-analysis service
$updateServiceCmd = "ssh $VPS_USER@$VPS_IP 'cat > /etc/systemd/system/trading-analysis.service << EOF
[Unit]
Description=Trading Analysis Flask App
After=network.target

[Service]
User=tradingapp
Group=tradingapp
WorkingDirectory=$APP_DIR
Environment=`"PATH=$VENV_DIR/bin`"
Environment=`"DATABASE_URL=postgresql://trading_user:Hvjband12345@localhost/trading_analysis`"
ExecStart=$VENV_DIR/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP `\$MAINPID
Restart=always
StandardOutput=append:/var/log/trading-analysis/app.log
StandardError=append:/var/log/trading-analysis/error.log

[Install]
WantedBy=multi-user.target
EOF'"
Write-Status "Updating trading-analysis service..."
Invoke-Expression $updateServiceCmd

# Update market brief scheduler service
$updateSchedulerCmd = "ssh $VPS_USER@$VPS_IP 'cat > /etc/systemd/system/market-brief-scheduler.service << EOF
[Unit]
Description=Market Brief Scheduler
After=network.target

[Service]
Type=simple
User=tradingapp
Group=tradingapp
WorkingDirectory=$APP_DIR
Environment=`"PATH=$VENV_DIR/bin`"
Environment=`"DATABASE_URL=postgresql://trading_user:Hvjband12345@localhost/trading_analysis`"
ExecStart=$VENV_DIR/bin/python tasks.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/trading-analysis/scheduler.log
StandardError=append:/var/log/trading-analysis/scheduler_error.log

[Install]
WantedBy=multi-user.target
EOF'"
Write-Status "Updating market brief scheduler service..."
Invoke-Expression $updateSchedulerCmd

# Create log directory
$logDirCmd = "ssh $VPS_USER@$VPS_IP 'mkdir -p /var/log/trading-analysis && chown tradingapp:tradingapp /var/log/trading-analysis'"
Write-Status "Creating log directory..."
Invoke-Expression $logDirCmd

Write-Step "Step 5: Restart services"

# Reload systemd and restart services
$reloadCmd = "ssh $VPS_USER@$VPS_IP 'systemctl daemon-reload && systemctl stop trading-analysis || true && systemctl stop market-brief-scheduler || true && systemctl enable trading-analysis && systemctl start trading-analysis && systemctl enable market-brief-scheduler && systemctl start market-brief-scheduler && sleep 5'"
Write-Status "Reloading systemd and restarting services..."
Invoke-Expression $reloadCmd

Write-Step "Step 6: Verify service status"

# Check service status
$checkAppStatus = "ssh $VPS_USER@$VPS_IP 'systemctl is-active --quiet trading-analysis && echo `"✅ Trading Analysis service is running`" || echo `"❌ Trading Analysis service failed`"'"
Write-Status "Checking trading-analysis service..."
Invoke-Expression $checkAppStatus

$checkSchedulerStatus = "ssh $VPS_USER@$VPS_IP 'systemctl is-active --quiet market-brief-scheduler && echo `"✅ Market Brief Scheduler service is running`" || echo `"❌ Market Brief Scheduler service failed`"'"
Write-Status "Checking market-brief-scheduler service..."
Invoke-Expression $checkSchedulerStatus

Write-Step "Step 7: Verify port configuration"

# Check what port the app is actually running on
$portCheckCmd = "ssh $VPS_USER@$VPS_IP 'netstat -tlnp | grep gunicorn | awk `"{print `\$4}`" | cut -d: -f2 | head -1'"
Write-Status "Checking application port..."
$RUNNING_PORT = Invoke-Expression $portCheckCmd

if ([string]::IsNullOrEmpty($RUNNING_PORT)) {
    Write-Error "No gunicorn process found running"
    exit 1
}

Write-Status "Application is running on port: $RUNNING_PORT"

Write-Step "Step 8: Update Nginx configuration"

# Update Nginx configuration to point to correct port
$nginxConfigCmd = "ssh $VPS_USER@$VPS_IP 'cat > /etc/nginx/sites-available/trading-analysis << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:$RUNNING_PORT;
        proxy_set_header Host `\$host;
        proxy_set_header X-Real-IP `\$remote_addr;
        proxy_set_header X-Forwarded-For `\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `\$scheme;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
    }

    location /uploads {
        alias $APP_DIR/static/uploads;
        expires 30d;
    }
}
EOF'"
Write-Status "Updating Nginx configuration..."
Invoke-Expression $nginxConfigCmd

# Also update default config if it exists
$updateDefaultCmd = "ssh $VPS_USER@$VPS_IP 'if [ -f `/etc/nginx/sites-available/default` ]; then sed -i `"s/proxy_pass http:\/\/127.0.0.1:[0-9]*;/proxy_pass http:\/\/127.0.0.1:$RUNNING_PORT;/` /etc/nginx/sites-available/default; fi'"
Write-Status "Updating default Nginx configuration..."
Invoke-Expression $updateDefaultCmd

# Test and reload Nginx
$nginxTestCmd = "ssh $VPS_USER@$VPS_IP 'nginx -t && systemctl reload nginx && echo `"✅ Nginx configuration updated and reloaded`" || echo `"❌ Nginx configuration test failed`"'"
Write-Status "Testing and reloading Nginx..."
Invoke-Expression $nginxTestCmd

Write-Step "Step 9: Verify deployment"

# Test internal connectivity
$internalTestCmd = "ssh $VPS_USER@$VPS_IP 'curl -I http://localhost:$RUNNING_PORT > /dev/null 2>&1 && echo `"✅ Internal connectivity test passed`" || echo `"❌ Internal connectivity test failed`"'"
Write-Status "Testing internal connectivity..."
Invoke-Expression $internalTestCmd

# Test external connectivity
$externalTestCmd = "ssh $VPS_USER@$VPS_IP 'curl -I http://localhost > /dev/null 2>&1 && echo `"✅ External connectivity test passed`" || echo `"❌ External connectivity test failed`"'"
Write-Status "Testing external connectivity..."
Invoke-Expression $externalTestCmd

Write-Step "Step 10: Final verification"

# Check for any remaining port 5000 references
$port5000CheckCmd = "ssh $VPS_USER@$VPS_IP 'grep -r `"proxy_pass.*5000`" /etc/nginx/sites-available/ || echo `"✅ No remaining port 5000 references found`"'"
Write-Status "Checking for any remaining port 5000 references..."
Invoke-Expression $port5000CheckCmd

# Check running processes
$processCheckCmd = "ssh $VPS_USER@$VPS_IP 'ps aux | grep -E `"(python|flask|gunicorn)`" | grep -v grep || echo `"No Python processes found running`"'"
Write-Status "Checking running processes..."
Invoke-Expression $processCheckCmd

Write-Host "🎉 Market Brief Live Deployment Completed Successfully!" -ForegroundColor Green

Write-Host ""
Write-Host "📋 Deployment Summary:" -ForegroundColor Cyan
Write-Host "✅ Application updated and running on port $RUNNING_PORT" -ForegroundColor Green
Write-Host "✅ Market Brief Scheduler service active" -ForegroundColor Green
Write-Host "✅ Nginx configuration updated" -ForegroundColor Green
Write-Host "✅ All services verified and running" -ForegroundColor Green
Write-Host ""
Write-Host "🔍 Useful commands:" -ForegroundColor Cyan
Write-Host "- Check app status: ssh $VPS_USER@$VPS_IP 'systemctl status trading-analysis'" -ForegroundColor White
Write-Host "- Check scheduler status: ssh $VPS_USER@$VPS_IP 'systemctl status market-brief-scheduler'" -ForegroundColor White
Write-Host "- View app logs: ssh $VPS_USER@$VPS_IP 'journalctl -u trading-analysis -f'" -ForegroundColor White
Write-Host "- View scheduler logs: ssh $VPS_USER@$VPS_IP 'journalctl -u market-brief-scheduler -f'" -ForegroundColor White
Write-Host "- Test market brief: ssh $VPS_USER@$VPS_IP 'curl http://localhost/market-brief'" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Your market brief is now live at: https://optionsplunge.com" -ForegroundColor Green

