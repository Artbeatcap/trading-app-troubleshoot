# VPS Market Brief Testing Guide

## 🎯 Overview

This guide provides step-by-step instructions for testing the market brief system on your VPS at `167.88.43.61`.

## 📋 Prerequisites

1. **SSH Access**: You need SSH access to the VPS
2. **Current Code**: The VPS should have the latest version with market brief functionality
3. **Environment Variables**: Proper configuration in `.env` file

## 🔧 Step 1: Connect to VPS

```bash
# Connect as tradingapp user (recommended)
ssh tradingapp@167.88.43.61

# Or as root if needed
ssh root@167.88.43.61
```

## 📁 Step 2: Navigate to Application Directory

```bash
# Navigate to the trading analysis directory
cd /home/tradingapp/trading-analysis

# Or if using root
cd /var/www/optionsplunge
```

## 🧪 Step 3: Test Market Brief System

### Option A: Run the Simple Test Script

```bash
# Copy the test script to VPS (if not already there)
# Then run:
python3 test_vps_market_brief.py
```

### Option B: Test Individual Components

```bash
# 1. Test environment variables
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('FINNHUB_TOKEN:', 'SET' if os.getenv('FINNHUB_TOKEN') else 'NOT SET')"

# 2. Test Finnhub API
python3 -c "import os, requests; from dotenv import load_dotenv; load_dotenv(); token = os.getenv('FINNHUB_TOKEN'); response = requests.get('https://finnhub.io/api/v1/quote', params={'symbol': 'AAPL', 'token': token}); print('Status:', response.status_code)"

# 3. Test market brief generator
python3 -c "from market_brief_generator import fetch_news; headlines = fetch_news(); print(f'Retrieved {len(headlines)} headlines')"

# 4. Test file output
ls -la static/uploads/
```

### Option C: Run Full Newsletter Test

```bash
# Activate virtual environment (if needed)
source venv/bin/activate

# Run the full test suite
python3 test_newsletter.py
```

## 🚀 Step 4: Test Market Brief Generation

```bash
# Generate a market brief
python3 run_brief.py

# Check the generated files
ls -la static/uploads/brief_latest.html
cat static/uploads/brief_latest_date.txt
```

## 📊 Step 5: Check Service Status

```bash
# Check if the application service is running
sudo systemctl status trading-analysis

# View service logs
sudo journalctl -u trading-analysis -f

# Check if the application is accessible
curl http://localhost:8000/market_brief
```

## 🔍 Step 6: Verify Results

### Expected Output for Successful Test:

```
🚀 VPS Market Brief Test
==================================================
Test time: 2025-08-14 20:00:00
Current directory: /home/tradingapp/trading-analysis

🔧 Testing Environment
========================================
✅ FINNHUB_TOKEN: SET (length: 40)
✅ OPENAI_API_KEY: SET (length: 164)
✅ DATABASE_URL: SET (length: 65)

📊 Testing Finnhub API
========================================
✅ Finnhub API working - AAPL: $232.78

📰 Testing Market Brief Import
========================================
✅ Market brief generator imported successfully
✅ Retrieved 20 headlines
✅ Retrieved prices for 4 symbols

💾 Testing File Output
========================================
✅ Latest brief HTML: 5988 bytes
✅ Latest brief date: 2025-08-14

==================================================
📋 VPS TEST SUMMARY
==================================================
Environment: ✅ PASS
Finnhub API: ✅ PASS
Market Brief Import: ✅ PASS
File Output: ✅ PASS

Overall: 4/4 tests passed
🎉 All tests passed! Market brief system is working on VPS.
==================================================
```

## ⚠️ Troubleshooting

### Common Issues:

1. **SSH Connection Failed**
   ```bash
   # Check if VPS is accessible
   ping 167.88.43.61
   
   # Try different user
   ssh root@167.88.43.61
   ssh tradingapp@167.88.43.61
   ```

2. **Environment Variables Not Set**
   ```bash
   # Check .env file
   cat .env
   
   # Set missing variables
   export FINNHUB_TOKEN=your_token_here
   ```

3. **Python Dependencies Missing**
   ```bash
   # Install requirements
   pip3 install -r requirements.txt
   
   # Or activate virtual environment
   source venv/bin/activate
   ```

4. **Service Not Running**
   ```bash
   # Start the service
   sudo systemctl start trading-analysis
   
   # Check logs
   sudo journalctl -u trading-analysis -f
   ```

5. **Permission Issues**
   ```bash
   # Fix permissions
   sudo chown -R tradingapp:tradingapp /home/tradingapp/trading-analysis
   chmod +x test_vps_market_brief.py
   ```

## 📈 Success Indicators

✅ **Market brief system is working when:**
- All environment variables are set
- Finnhub API returns 200 status
- Market brief generator imports successfully
- HTML file is generated in static/uploads/
- Service is running and accessible

## 🔄 Next Steps

If the test passes:
1. **Monitor the system** for any issues
2. **Set up automated testing** if needed
3. **Configure alerts** for failures
4. **Document any VPS-specific configurations**

If the test fails:
1. **Check the error messages** above
2. **Verify environment variables**
3. **Update the code** if needed
4. **Restart services** if necessary

## 📞 Support

If you encounter issues:
1. Check the logs: `sudo journalctl -u trading-analysis -f`
2. Verify environment: `cat .env`
3. Test connectivity: `curl https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_TOKEN`
4. Check service status: `sudo systemctl status trading-analysis`
