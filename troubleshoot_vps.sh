#!/bin/bash

echo "=== VPS TROUBLESHOOTING SCRIPT ==="
echo "Checking for multiple services and cached content..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_step "Step 1: Checking all Python processes..."
echo "Python processes:"
ps aux | grep python | grep -v grep || echo "No Python processes found"

print_step "Step 2: Checking for multiple gunicorn instances..."
echo "Gunicorn processes:"
ps aux | grep gunicorn | grep -v grep || echo "No gunicorn processes found"

print_step "Step 3: Checking for multiple app.py files..."
echo "Found app.py files:"
find /home -name "app.py" 2>/dev/null || echo "No app.py files found in /home"

print_step "Step 4: Checking for multiple application directories..."
echo "Found trading-related directories:"
find /home -name "*trading*" -type d 2>/dev/null || echo "No trading directories found"

print_step "Step 5: Checking all services..."
echo "Trading-related services:"
sudo systemctl list-units --type=service | grep -i trading || echo "No trading services found"

print_step "Step 6: Checking application file timestamps..."
echo "Current app.py timestamp:"
ls -la /home/tradingapp/trading-analysis/app.py 2>/dev/null || echo "app.py not found"

print_step "Step 7: Checking for Python cache files..."
echo "Python cache files found:"
find /home/tradingapp/trading-analysis -name "*.pyc" 2>/dev/null | wc -l
find /home/tradingapp/trading-analysis -name "__pycache__" -type d 2>/dev/null | wc -l

print_step "Step 8: Checking Nginx configuration..."
echo "Enabled Nginx sites:"
ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "No enabled sites found"

print_step "Step 9: Checking for other web servers..."
echo "Processes listening on ports 80, 443, 8000:"
sudo netstat -tlnp | grep -E ":(80|443|8000)" 2>/dev/null || echo "No processes found on these ports"

print_step "Step 10: Testing application locally..."
echo "Local application test:"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000 2>/dev/null || echo "Local test failed"

print_step "Step 11: Checking application logs..."
echo "Recent application logs:"
sudo journalctl -u trading-analysis --no-pager -n 10 2>/dev/null || echo "No application logs found"

print_step "Step 12: Checking service configuration..."
echo "Trading analysis service configuration:"
sudo systemctl cat trading-analysis 2>/dev/null | grep -E "(WorkingDirectory|ExecStart)" || echo "Service config not found"

echo ""
echo "=== TROUBLESHOOTING COMPLETE ==="
echo ""
echo "If you see multiple app.py files or multiple services, that's likely the issue."
echo "If you see many .pyc files, clearing the cache might help."
echo ""
echo "To force restart everything, run:"
echo "sudo systemctl stop trading-analysis && sudo pkill -f gunicorn && cd /home/tradingapp/trading-analysis && find . -name '*.pyc' -delete && sudo systemctl start trading-analysis"
