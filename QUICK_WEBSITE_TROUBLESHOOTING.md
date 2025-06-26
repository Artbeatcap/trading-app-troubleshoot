# Quick Website Troubleshooting Guide

If your Flask app website is not loading, follow these steps in order:

## 1. Check Service Status

```bash
# Check if Flask service is running
sudo systemctl status trading-analysis

# If not running, start it
sudo systemctl start trading-analysis

# If it fails to start, check logs
sudo journalctl -u trading-analysis -f
```

## 2. Check Nginx Status

```bash
# Check if Nginx is running
sudo systemctl status nginx

# If not running, start it
sudo systemctl start nginx

# Check Nginx configuration
sudo nginx -t

# If config is valid, restart Nginx
sudo systemctl restart nginx
```

## 3. Check Port Binding

```bash
# Check if port 8000 is listening
sudo netstat -tlnp | grep :8000

# If not listening, the Flask app isn't running properly
```

## 4. Test Local Connection

```bash
# Test if you can connect to the app locally
curl http://localhost:8000

# If this fails, the issue is with the Flask app
# If this works, the issue is with Nginx or external access
```

## 5. Check Logs

```bash
# Flask app logs
sudo journalctl -u trading-analysis --no-pager -n 20

# Nginx error logs
sudo tail -n 20 /var/log/nginx/error.log

# Nginx access logs
sudo tail -n 20 /var/log/nginx/access.log
```

## 6. Check Environment

```bash
# Make sure you're in the right directory
cd /home/tradingapp/trading-analysis

# Check if .env file exists
ls -la .env

# Check if virtual environment exists
ls -la venv/

# Activate virtual environment and test
source venv/bin/activate
python -c "from app import app; print('App imports successfully')"
```

## 7. Common Issues and Fixes

### Issue: Service won't start
```bash
# Check if all dependencies are installed
source venv/bin/activate
pip install -r requirements.txt

# Check if .env file has correct values
cat .env

# Try running the app manually to see errors
python wsgi.py
```

### Issue: Port already in use
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill the process if needed
sudo kill -9 <PID>
```

### Issue: Permission denied
```bash
# Fix ownership
sudo chown -R tradingapp:tradingapp /home/tradingapp/trading-analysis

# Fix permissions
sudo chmod -R 755 /home/tradingapp/trading-analysis
```

### Issue: Database connection failed
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
psql -h localhost -U tradingapp -d trading_journal

# Check .env file has correct DATABASE_URL
grep DATABASE_URL .env
```

## 8. Test External Access

```bash
# Get your VPS IP address
curl ifconfig.me

# Test from another machine
curl http://YOUR_VPS_IP

# If this works but domain doesn't, it's a DNS issue
```

## 9. Firewall Check

```bash
# Check firewall status
sudo ufw status

# Make sure ports 80 and 443 are open
sudo ufw allow 80
sudo ufw allow 443
```

## 10. Quick Restart Everything

```bash
# Restart all services
sudo systemctl restart postgresql
sudo systemctl restart trading-analysis
sudo systemctl restart nginx

# Check all statuses
sudo systemctl status postgresql
sudo systemctl status trading-analysis
sudo systemctl status nginx
```

## 11. Run Automated Troubleshooting

```bash
# Upload and run the troubleshooting script
python3 troubleshoot_website.py
```

## Most Common Solutions

1. **Service not running**: `sudo systemctl start trading-analysis`
2. **Nginx not running**: `sudo systemctl start nginx`
3. **Wrong port**: Check `gunicorn.conf.py` and Nginx config
4. **Missing .env**: Copy from template and configure
5. **Database issues**: Check PostgreSQL and connection string
6. **Permission issues**: Fix ownership and permissions
7. **Firewall blocking**: Open ports 80 and 443

## Emergency Reset

If nothing else works:

```bash
# Stop all services
sudo systemctl stop trading-analysis
sudo systemctl stop nginx

# Remove and recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Restart services
sudo systemctl start trading-analysis
sudo systemctl start nginx
``` 