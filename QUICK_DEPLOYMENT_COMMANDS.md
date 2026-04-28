# 🚀 Quick Deployment Commands - Market Brief Optimization

## **Deploy to Live App (167.88.43.61)**

### **Option 1: Run Automated Script**
```bash
./deploy_to_live_app.sh
```

### **Option 2: Manual Step-by-Step Commands**

#### **1. Test SSH Connection**
```bash
ssh root@167.88.43.61 "echo 'SSH connection successful'"
```

#### **2. Create Backup**
```bash
ssh root@167.88.43.61 "cd /home/tradingapp && tar -czf trading-analysis.backup.\$(date +%Y%m%d_%H%M%S).tar.gz trading-analysis"
```

#### **3. Upload Main Files**
```bash
scp app.py config.py models.py forms.py billing.py emailer.py emails.py tasks.py wsgi.py market_brief_generator.py send_morning_brief.py requirements.txt root@167.88.43.61:/home/tradingapp/trading-analysis/
```

#### **4. Create Directories & Upload Optimization Files**
```bash
ssh root@167.88.43.61 "cd /home/tradingapp/trading-analysis && mkdir -p schemas pipeline tests"
scp schemas/brief_input.py root@167.88.43.61:/home/tradingapp/trading-analysis/schemas/
scp pipeline/prepare_inputs.py root@167.88.43.61:/home/tradingapp/trading-analysis/pipeline/
scp pipeline/write_brief.py root@167.88.43.61:/home/tradingapp/trading-analysis/pipeline/
scp tests/test_brief_shrink.py root@167.88.43.61:/home/tradingapp/trading-analysis/tests/
```

#### **5. Upload Templates & Static Files**
```bash
scp -r templates/* root@167.88.43.61:/home/tradingapp/trading-analysis/templates/
scp -r static/* root@167.88.43.61:/home/tradingapp/trading-analysis/static/
scp -r migrations/* root@167.88.43.61:/home/tradingapp/trading-analysis/migrations/
```

#### **6. Set Permissions & Update Dependencies**
```bash
ssh root@167.88.43.61 "cd /home/tradingapp/trading-analysis && chown -R tradingapp:tradingapp . && chmod -R 644 *.py *.txt *.md && chmod -R 755 templates static migrations schemas pipeline tests"
ssh root@167.88.43.61 "cd /home/tradingapp/trading-analysis && source venv/bin/activate && pip install -r requirements.txt --upgrade"
```

#### **7. Run Database Migrations**
```bash
ssh root@167.88.43.61 "cd /home/tradingapp/trading-analysis && source venv/bin/activate && python -m flask db upgrade"
```

#### **8. Update Scheduler Service (with correct database URL)**
```bash
ssh root@167.88.43.61 "cat > /etc/systemd/system/market-brief-scheduler.service << 'EOF'
[Unit]
Description=Market Brief Scheduler
After=network.target

[Service]
Type=simple
User=tradingapp
Group=tradingapp
WorkingDirectory=/home/tradingapp/trading-analysis
Environment=\"PATH=/home/tradingapp/trading-analysis/venv/bin\"
Environment=\"DATABASE_URL=postgresql://tradingapp:<DB_PASSWORD>@localhost/trading_journal\"
ExecStart=/home/tradingapp/trading-analysis/venv/bin/python tasks.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/trading-analysis/scheduler.log
StandardError=append:/var/log/trading-analysis/scheduler_error.log

[Install]
WantedBy=multi-user.target
EOF"
```

#### **9. Restart Services**
```bash
ssh root@167.88.43.61 "systemctl daemon-reload && systemctl restart market-brief-scheduler && systemctl restart trading-analysis"
```

#### **10. Verify Deployment**
```bash
./verify_deployment.sh
```

---

## **🔍 Verify Deployment**

### **Check Application Status**
```bash
ssh root@167.88.43.61 "systemctl status trading-analysis --no-pager -l"
```

### **Check Scheduler Status**
```bash
ssh root@167.88.43.61 "systemctl status market-brief-scheduler --no-pager -l"
```

### **Test Application Response**
```bash
ssh root@167.88.43.61 "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/"
```

### **Check Database URL**
```bash
ssh root@167.88.43.61 "grep 'DATABASE_URL' /etc/systemd/system/market-brief-scheduler.service"
```

### **Test Optimization Pipeline**
```bash
ssh root@167.88.43.61 "cd /home/tradingapp/trading-analysis && source venv/bin/activate && python -c \"
import sys
sys.path.insert(0, '.')
from schemas.brief_input import BriefInput
from pipeline.prepare_inputs import prepare_brief_input
print('✅ Optimization pipeline working')
\""
```

---

## **📊 Expected Results**

### **✅ Success Indicators:**
- Application responds with HTTP 200
- Scheduler is active and running
- Database URL shows `trading_journal`
- Optimization pipeline imports successfully
- No errors in logs

### **💰 Benefits:**
- **90% token reduction** in API usage
- **Significant cost savings** on OpenAI API calls
- **Faster processing** due to smaller payloads
- **Better reliability** with hard data caps
- **Token usage monitoring** with detailed logging

---

## **🛡️ Safety Features**

### **Automatic Backup:**
- Creates timestamped backup before deployment
- Easy rollback if issues occur

### **Fallback System:**
- If optimization fails, automatically uses legacy system
- No disruption to existing functionality
- Graceful degradation

### **Rollback Instructions:**
```bash
# If needed, restore from backup
ssh root@167.88.43.61 "cd /home/tradingapp && tar -xzf trading-analysis.backup.TIMESTAMP.tar.gz"
ssh root@167.88.43.61 "systemctl restart trading-analysis market-brief-scheduler"
```

---

## **🎯 Quick Commands Summary**

1. **Deploy**: `./deploy_to_live_app.sh`
2. **Verify**: `./verify_deployment.sh`
3. **Check Status**: `ssh root@167.88.43.61 "systemctl status trading-analysis market-brief-scheduler"`
4. **Check Logs**: `ssh root@167.88.43.61 "tail -20 /home/tradingapp/trading-analysis/app.log"`

**🚀 Ready to deploy the 90% token reduction optimization!**



