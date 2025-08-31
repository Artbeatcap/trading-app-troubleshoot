# Market Brief Live Deployment Guide

## Overview
This guide provides step-by-step instructions to deploy the market brief system to the live VPS, ensuring proper port configuration and service management based on troubleshooting lessons learned.

## Prerequisites
- SSH access to VPS (167.88.43.61)
- Root or sudo access on VPS
- Market brief components ready for deployment

## Quick Deployment Options

### Option 1: PowerShell Deployment (Windows)
```powershell
# Run the PowerShell deployment script
.\deploy_market_brief_live.ps1

# Or with custom parameters
.\deploy_market_brief_live.ps1 -VPS_IP "167.88.43.61" -VPS_USER "root"
```

### Option 2: Manual SSH Deployment
```bash
# Copy the bash script to VPS and run
scp deploy_market_brief_live.sh root@167.88.43.61:/tmp/
ssh root@167.88.43.61 "chmod +x /tmp/deploy_market_brief_live.sh && /tmp/deploy_market_brief_live.sh"
```

### Option 3: Direct SSH Commands
Follow the step-by-step manual deployment below.

## Step-by-Step Manual Deployment

### Step 1: Pre-deployment Checks and Backup

```bash
# SSH into VPS
ssh root@167.88.43.61

# Create backup directory
mkdir -p /home/tradingapp/backups

# Backup existing installation
cd /home/tradingapp/trading-analysis
if [ -f "app.py" ]; then
    tar -czf /home/tradingapp/backups/market_brief_backup_$(date +%Y%m%d_%H%M%S).tar.gz .
fi
```

### Step 2: Update Application Files

```bash
# Navigate to app directory
cd /home/tradingapp/trading-analysis

# Activate virtual environment
source venv/bin/activate

# Update Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Verify Market Brief Components

```bash
# Check required files exist
required_files=(
    "market_brief_generator.py"
    "tasks.py"
    "market-brief-scheduler.service"
    "gunicorn.conf.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Missing: $file"
        exit 1
    fi
done
echo "All market brief components verified"
```

### Step 4: Update Systemd Services

```bash
# Update trading-analysis service
cat > /etc/systemd/system/trading-analysis.service << EOF
[Unit]
Description=Trading Analysis Flask App
After=network.target

[Service]
User=tradingapp
Group=tradingapp
WorkingDirectory=/home/tradingapp/trading-analysis
Environment="PATH=/home/tradingapp/trading-analysis/venv/bin"
Environment="DATABASE_URL=postgresql://trading_user:Hvjband12345@localhost/trading_analysis"
ExecStart=/home/tradingapp/trading-analysis/venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
StandardOutput=append:/var/log/trading-analysis/app.log
StandardError=append:/var/log/trading-analysis/error.log

[Install]
WantedBy=multi-user.target
EOF

# Update market brief scheduler service
cat > /etc/systemd/system/market-brief-scheduler.service << EOF
[Unit]
Description=Market Brief Scheduler
After=network.target

[Service]
Type=simple
User=tradingapp
Group=tradingapp
WorkingDirectory=/home/tradingapp/trading-analysis
Environment="PATH=/home/tradingapp/trading-analysis/venv/bin"
Environment="DATABASE_URL=postgresql://trading_user:Hvjband12345@localhost/trading_analysis"
ExecStart=/home/tradingapp/trading-analysis/venv/bin/python tasks.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/trading-analysis/scheduler.log
StandardError=append:/var/log/trading-analysis/scheduler_error.log

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
mkdir -p /var/log/trading-analysis
chown tradingapp:tradingapp /var/log/trading-analysis
```

### Step 5: Restart Services

```bash
# Reload systemd and restart services
systemctl daemon-reload

# Stop existing services
systemctl stop trading-analysis || true
systemctl stop market-brief-scheduler || true

# Start services
systemctl enable trading-analysis
systemctl start trading-analysis

systemctl enable market-brief-scheduler
systemctl start market-brief-scheduler

# Wait for services to start
sleep 5
```

### Step 6: Verify Service Status

```bash
# Check service status
if systemctl is-active --quiet trading-analysis; then
    echo "✅ Trading Analysis service is running"
else
    echo "❌ Trading Analysis service failed to start"
    systemctl status trading-analysis
    exit 1
fi

if systemctl is-active --quiet market-brief-scheduler; then
    echo "✅ Market Brief Scheduler service is running"
else
    echo "❌ Market Brief Scheduler service failed to start"
    systemctl status market-brief-scheduler
    exit 1
fi
```

### Step 7: Verify Port Configuration

```bash
# Check what port the app is actually running on
RUNNING_PORT=$(netstat -tlnp | grep gunicorn | awk '{print $4}' | cut -d: -f2 | head -1)

if [ -z "$RUNNING_PORT" ]; then
    echo "No gunicorn process found running"
    exit 1
fi

echo "Application is running on port: $RUNNING_PORT"

# Verify gunicorn config matches
GUNICORN_PORT=$(grep "bind" gunicorn.conf.py | cut -d'"' -f2 | cut -d: -f2)
echo "Gunicorn configured for port: $GUNICORN_PORT"

if [ "$RUNNING_PORT" != "$GUNICORN_PORT" ]; then
    echo "Port mismatch detected. Running on $RUNNING_PORT, configured for $GUNICORN_PORT"
fi
```

### Step 8: Update Nginx Configuration

```bash
# Update Nginx configuration to point to correct port
cat > /etc/nginx/sites-available/trading-analysis << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:$RUNNING_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias /home/tradingapp/trading-analysis/static;
        expires 30d;
    }

    location /uploads {
        alias /home/tradingapp/trading-analysis/static/uploads;
        expires 30d;
    }
}
EOF

# Also update default config if it exists
if [ -f "/etc/nginx/sites-available/default" ]; then
    sed -i "s/proxy_pass http:\/\/127.0.0.1:[0-9]*;/proxy_pass http:\/\/127.0.0.1:$RUNNING_PORT;/" /etc/nginx/sites-available/default
fi

# Test and reload Nginx
if nginx -t; then
    systemctl reload nginx
    echo "✅ Nginx configuration updated and reloaded"
else
    echo "❌ Nginx configuration test failed"
    exit 1
fi
```

### Step 9: Verify Deployment

```bash
# Test internal connectivity
if curl -I http://localhost:$RUNNING_PORT > /dev/null 2>&1; then
    echo "✅ Internal connectivity test passed"
else
    echo "❌ Internal connectivity test failed"
    exit 1
fi

# Test external connectivity
if curl -I http://localhost > /dev/null 2>&1; then
    echo "✅ External connectivity test passed"
else
    echo "❌ External connectivity test failed"
    exit 1
fi
```

### Step 10: Final Verification

```bash
# Check for any remaining port 5000 references
PORT_5000_REFS=$(grep -r "proxy_pass.*5000" /etc/nginx/sites-available/ || true)
if [ -n "$PORT_5000_REFS" ]; then
    echo "Found remaining port 5000 references:"
    echo "$PORT_5000_REFS"
else
    echo "✅ No remaining port 5000 references found"
fi

# Check running processes
RUNNING_PROCESSES=$(ps aux | grep -E "(python|flask|gunicorn)" | grep -v grep || true)
if [ -n "$RUNNING_PROCESSES" ]; then
    echo "Running processes:"
    echo "$RUNNING_PROCESSES"
else
    echo "No Python processes found running"
fi
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Port Mismatch (5000 vs 8000)
**Problem**: Nginx pointing to port 5000 but app running on 8000
**Solution**: Update Nginx configuration to point to correct port
```bash
# Check running port
netstat -tlnp | grep gunicorn

# Update Nginx config
sed -i 's/proxy_pass http:\/\/127.0.0.1:5000;/proxy_pass http:\/\/127.0.0.1:8000;/' /etc/nginx/sites-available/trading-analysis
systemctl reload nginx
```

#### 2. Service Not Starting
**Problem**: Market brief scheduler service fails to start
**Solution**: Check logs and dependencies
```bash
# Check service status
systemctl status market-brief-scheduler

# View logs
journalctl -u market-brief-scheduler -f

# Check Python dependencies
cd /home/tradingapp/trading-analysis
source venv/bin/activate
python -c "import schedule, pytz; print('Dependencies OK')"
```

#### 3. Database Connection Issues
**Problem**: Market brief can't connect to database
**Solution**: Verify database configuration
```bash
# Test database connection
cd /home/tradingapp/trading-analysis
source venv/bin/activate
python -c "from models import db; print('Database connection OK')"
```

#### 4. Nginx Configuration Errors
**Problem**: Nginx fails to reload
**Solution**: Test and fix configuration
```bash
# Test Nginx config
nginx -t

# Check syntax errors
cat /etc/nginx/sites-available/trading-analysis

# Reload Nginx
systemctl reload nginx
```

## Verification Commands

### Service Status
```bash
# Check all services
systemctl status trading-analysis
systemctl status market-brief-scheduler
systemctl status nginx

# Check if services are enabled
systemctl is-enabled trading-analysis
systemctl is-enabled market-brief-scheduler
```

### Port Verification
```bash
# Check what's running on each port
netstat -tlnp | grep :8000
netstat -tlnp | grep :5000
netstat -tlnp | grep gunicorn
```

### Connectivity Tests
```bash
# Internal tests
curl -I http://localhost:8000
curl -I http://localhost

# External tests
curl -I https://optionsplunge.com
```

### Log Monitoring
```bash
# Real-time log monitoring
journalctl -u trading-analysis -f
journalctl -u market-brief-scheduler -f
tail -f /var/log/trading-analysis/app.log
tail -f /var/log/trading-analysis/scheduler.log
```

## Market Brief Testing

### Manual Test
```bash
# Test market brief generation
cd /home/tradingapp/trading-analysis
source venv/bin/activate
python -c "from market_brief_generator import send_market_brief_to_subscribers; print(send_market_brief_to_subscribers())"
```

### Schedule Test
```bash
# Test scheduler
cd /home/tradingapp/trading-analysis
source venv/bin/activate
python tasks.py
```

### Web Interface Test
```bash
# Test market brief page
curl http://localhost/market-brief
curl https://optionsplunge.com/market-brief
```

## Rollback Procedure

If deployment fails, rollback to previous version:

```bash
# Stop services
systemctl stop trading-analysis
systemctl stop market-brief-scheduler

# Restore from backup
cd /home/tradingapp/trading-analysis
rm -rf *
tar -xzf /home/tradingapp/backups/market_brief_backup_YYYYMMDD_HHMMSS.tar.gz

# Restart services
systemctl start trading-analysis
systemctl start market-brief-scheduler
```

## Success Criteria

Deployment is successful when:
- ✅ Trading Analysis service is running
- ✅ Market Brief Scheduler service is running
- ✅ Nginx is proxying to correct port
- ✅ Internal connectivity tests pass
- ✅ External connectivity tests pass
- ✅ Market brief page is accessible
- ✅ No port 5000 references remain

## Post-Deployment Checklist

- [ ] All services running
- [ ] Port configuration correct
- [ ] Nginx configuration updated
- [ ] Market brief accessible via web
- [ ] Scheduler running and enabled
- [ ] Logs being written correctly
- [ ] Backup created successfully
- [ ] External domain accessible

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review service logs: `journalctl -u service-name -f`
3. Verify port configuration: `netstat -tlnp`
4. Test connectivity: `curl -I http://localhost:8000`
5. Check Nginx configuration: `nginx -t`

