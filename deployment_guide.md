# Manual Deployment Guide

## Pre-Deployment Checklist
- [ ] Test all changes locally
- [ ] Commit changes to git
- [ ] Review files to be deployed
- [ ] Notify users of potential downtime (if major changes)

## Manual Deployment Steps

### 1. Connect to Server

```bash
ssh root@167.88.43.61
```

### 2. Navigate to App Directory

```bash
cd /home/tradingapp/trading-analysis
```

### 3. Create Backup

```bash
# Create backup directory with timestamp
BACKUP_DIR="/home/tradingapp/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup current files
cp app.py $BACKUP_DIR/
cp -r templates $BACKUP_DIR/
```

### 4. Upload Modified Files from Local Machine

**From your local machine (in a new terminal):**

```bash
# Upload app.py
scp app.py root@167.88.43.61:/home/tradingapp/trading-analysis/

# Upload index.html
scp templates/index.html root@167.88.43.61:/home/tradingapp/trading-analysis/templates/

# Upload NEW welcome.html
scp templates/welcome.html root@167.88.43.61:/home/tradingapp/trading-analysis/templates/

# Upload any other modified templates
scp templates/view_trade.html root@167.88.43.61:/home/tradingapp/trading-analysis/templates/
scp templates/trades.html root@167.88.43.61:/home/tradingapp/trading-analysis/templates/
```

### 5. Verify Files on Server

**Back on the server:**

```bash
# Check if files were uploaded
ls -lh app.py
ls -lh templates/welcome.html
ls -lh templates/index.html

# Optional: Check file contents
head -20 templates/welcome.html
```

### 6. Restart Application

```bash
# Restart the Flask app service
systemctl restart trading-analysis.service

# Check status
systemctl status trading-analysis.service

# Watch logs for errors
journalctl -u trading-analysis.service -f
```

Press Ctrl+C to stop watching logs once you confirm it's running.

### 7. Test the Live Site

1. Visit https://optionsplunge.com
2. Test registration flow → Should see new welcome page
3. Test login → Returning users should see dashboard
4. Test adding a trade → Should see confirmation message
5. Check that landing page shows new stats

### 8. Rollback (if something breaks)

```bash
# Stop the service
systemctl stop trading-analysis.service

# Restore from backup (use the timestamp from step 3)
cp /home/tradingapp/backups/YYYYMMDD_HHMMSS/app.py /home/tradingapp/trading-analysis/
cp -r /home/tradingapp/backups/YYYYMMDD_HHMMSS/templates/* /home/tradingapp/trading-analysis/templates/

# Restart
systemctl start trading-analysis.service
systemctl status trading-analysis.service
```

## Post-Deployment Verification

- [ ] Homepage loads correctly
- [ ] Registration redirects to welcome page
- [ ] Welcome page displays properly
- [ ] Adding trades shows confirmation message
- [ ] No errors in logs: `journalctl -u trading-analysis.service -n 100`
- [ ] Check for Python errors: Look for traceback in logs

## Troubleshooting

### If service won't start:

```bash
# Check for Python syntax errors
cd /home/tradingapp/trading-analysis
python3 -m py_compile app.py

# Check logs
journalctl -u trading-analysis.service -n 50 --no-pager
```

### If templates not found:

```bash
# Verify templates directory structure
ls -la /home/tradingapp/trading-analysis/templates/

# Check file permissions
chmod 644 /home/tradingapp/trading-analysis/templates/*.html
```

### If 500 errors occur:

```bash
# Watch logs in real-time
journalctl -u trading-analysis.service -f
```

Then visit the page that's causing the error and watch the logs for Python tracebacks.
