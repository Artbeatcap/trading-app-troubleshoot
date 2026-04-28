# Manual Deployment Guide - Market Brief Optimization

## 🚀 Deploy Market Brief 90% Token Reduction Optimization to Live App

### **Server Details:**
- **Host**: 167.88.43.61
- **User**: root
- **App Directory**: /home/tradingapp/trading-analysis
- **Database**: postgresql://tradingapp:<DB_PASSWORD>@localhost/trading_journal

---

## **Step 1: Create Backup**

```bash
# SSH to server
ssh root@167.88.43.61

# Create backup with timestamp
cd /home/tradingapp
timestamp=$(date +%Y%m%d_%H%M%S)
tar -czf trading-analysis.backup.$timestamp.tar.gz trading-analysis
echo "Backup created: trading-analysis.backup.$timestamp.tar.gz"
```

---

## **Step 2: Upload Main Application Files**

From your local machine, upload the updated files:

```bash
# Upload main application files
scp app.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp config.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp models.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp forms.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp billing.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp emailer.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp emails.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp tasks.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp wsgi.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp market_brief_generator.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp send_morning_brief.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp requirements.txt root@167.88.43.61:/home/tradingapp/trading-analysis/
```

---

## **Step 3: Create Optimization Directories**

```bash
# SSH to server
ssh root@167.88.43.61

# Create new directories
cd /home/tradingapp/trading-analysis
mkdir -p schemas pipeline tests
echo "Optimization directories created"
```

---

## **Step 4: Upload New Optimization Files**

From your local machine:

```bash
# Upload new optimization files
scp schemas/brief_input.py root@167.88.43.61:/home/tradingapp/trading-analysis/schemas/
scp pipeline/prepare_inputs.py root@167.88.43.61:/home/tradingapp/trading-analysis/pipeline/
scp pipeline/write_brief.py root@167.88.43.61:/home/tradingapp/trading-analysis/pipeline/
scp tests/test_brief_shrink.py root@167.88.43.61:/home/tradingapp/trading-analysis/tests/
```

---

## **Step 5: Upload Templates and Static Files**

```bash
# Upload templates
scp -r templates/* root@167.88.43.61:/home/tradingapp/trading-analysis/templates/

# Upload static files
scp -r static/* root@167.88.43.61:/home/tradingapp/trading-analysis/static/

# Upload migrations
scp -r migrations/* root@167.88.43.61:/home/tradingapp/trading-analysis/migrations/
```

---

## **Step 6: Set File Permissions**

```bash
# SSH to server
ssh root@167.88.43.61

# Set correct permissions
cd /home/tradingapp/trading-analysis
chown -R tradingapp:tradingapp .
chmod -R 644 *.py *.txt *.md
chmod -R 755 templates static migrations schemas pipeline tests
echo "File permissions set correctly"
```

---

## **Step 7: Update Python Dependencies**

```bash
# SSH to server
ssh root@167.88.43.61

# Update dependencies
cd /home/tradingapp/trading-analysis
source venv/bin/activate
pip install -r requirements.txt --upgrade
echo "Python dependencies updated"
```

---

## **Step 8: Run Database Migrations**

```bash
# SSH to server
ssh root@167.88.43.61

# Run migrations
cd /home/tradingapp/trading-analysis
source venv/bin/activate
python -m flask db upgrade
echo "Database migrations completed"
```

---

## **Step 9: Update Scheduler Service**

```bash
# SSH to server
ssh root@167.88.43.61

# Create scheduler service file
cat > /etc/systemd/system/market-brief-scheduler.service << 'EOF'
[Unit]
Description=Market Brief Scheduler
After=network.target

[Service]
Type=simple
User=tradingapp
Group=tradingapp
WorkingDirectory=/home/tradingapp/trading-analysis
Environment="PATH=/home/tradingapp/trading-analysis/venv/bin"
Environment="DATABASE_URL=postgresql://tradingapp:<DB_PASSWORD>@localhost/trading_journal"
ExecStart=/home/tradingapp/trading-analysis/venv/bin/python tasks.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/trading-analysis/scheduler.log
StandardError=append:/var/log/trading-analysis/scheduler_error.log

[Install]
WantedBy=multi-user.target
EOF

echo "Scheduler service configuration updated"
```

---

## **Step 10: Reload Systemd and Restart Services**

```bash
# SSH to server
ssh root@167.88.43.61

# Reload systemd
systemctl daemon-reload

# Restart scheduler
systemctl restart market-brief-scheduler

# Restart main application
systemctl restart trading-analysis

echo "Services restarted"
```

---

## **Step 11: Verify Deployment**

```bash
# SSH to server
ssh root@167.88.43.61

# Check application status
systemctl status trading-analysis --no-pager -l

# Check scheduler status
systemctl status market-brief-scheduler --no-pager -l

# Test application response
curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/

# Check application logs
tail -20 /home/tradingapp/trading-analysis/app.log

# Check scheduler logs
tail -20 /var/log/trading-analysis/scheduler.log
```

---

## **Step 12: Test Optimization**

```bash
# SSH to server
ssh root@167.88.43.61

# Test the optimization pipeline
cd /home/tradingapp/trading-analysis
source venv/bin/activate

# Run a simple test
python -c "
import sys
sys.path.insert(0, '.')
try:
    from schemas.brief_input import BriefInput
    from pipeline.prepare_inputs import prepare_brief_input
    print('✅ Optimization pipeline imports successfully')
except Exception as e:
    print(f'❌ Import failed: {e}')
"
```

---

## **Expected Results**

### **✅ Success Indicators:**
- Application responds with HTTP 200
- Scheduler service is active and running
- No errors in application or scheduler logs
- Optimization pipeline imports successfully
- Token usage logs show `[TOKENS]` entries

### **📊 Optimization Benefits:**
- **90% token reduction** in brief generation
- **Faster processing** due to smaller payloads
- **Cost savings** on OpenAI API usage
- **Better reliability** with hard data caps
- **Token monitoring** with detailed logging

### **🔍 Monitoring:**
- Check logs for `[TOKENS]` entries to verify optimization
- Monitor OpenAI dashboard for reduced API usage
- Test brief generation functionality
- Verify scheduler is using correct database URL

---

## **Rollback Instructions**

If issues occur, restore from backup:

```bash
# SSH to server
ssh root@167.88.43.61

# Restore from backup (replace TIMESTAMP with actual backup timestamp)
cd /home/tradingapp
tar -xzf trading-analysis.backup.TIMESTAMP.tar.gz

# Restart services
systemctl restart trading-analysis market-brief-scheduler
```

---

## **Troubleshooting**

### **Common Issues:**

1. **Import Errors**: Check that all optimization files are uploaded correctly
2. **Permission Errors**: Ensure files are owned by `tradingapp:tradingapp`
3. **Service Failures**: Check logs with `journalctl -u service-name -f`
4. **Database Issues**: Verify DATABASE_URL is correct in scheduler service

### **Log Locations:**
- Application: `/home/tradingapp/trading-analysis/app.log`
- Scheduler: `/var/log/trading-analysis/scheduler.log`
- System: `journalctl -u trading-analysis -f`
- Scheduler System: `journalctl -u market-brief-scheduler -f`

---

**🎉 Deployment Complete! The Market Brief optimization is now live with 90% token reduction!**



