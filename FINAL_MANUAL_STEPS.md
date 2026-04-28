# Final Manual Steps to Complete Server Fix

## Current Status:
- ✅ market_brief_generator.py - Uploaded successfully
- ✅ emails.py - Uploaded successfully (attempted)
- ❌ Dependencies - Need to be installed manually
- ❌ Services - Need to be restarted

## Manual Steps Required:

### 1. Connect to Server
```bash
ssh root@167.88.43.61
```

### 2. Navigate to Project Directory
```bash
cd /home/tradingapp/trading-analysis
```

### 3. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 4. Install Missing Dependencies
```bash
pip install openai
pip install httpx
pip install python-dotenv
```

### 5. Verify Files Are Present
```bash
ls -la emails.py market_brief_generator.py
```

### 6. Test GPT Functionality
```bash
python3 -c "from market_brief_generator import fetch_news_with_gpt; result = fetch_news_with_gpt(); print(f'GPT Headlines: {len(result)} headlines')"
```

### 7. Test Email Functionality
```bash
python3 -c "from market_brief_generator import send_market_brief_to_subscribers; result = send_market_brief_to_subscribers(); print(f'Email result: {result}')"
```

### 8. Restart Services
```bash
systemctl restart trading-analysis
systemctl restart market-brief-scheduler
```

### 9. Check Service Status
```bash
systemctl status trading-analysis market-brief-scheduler
```

## Expected Results:
- ✅ GPT headlines should generate 7 headlines
- ✅ Email sending should work without Flask context errors
- ✅ Services should be running without errors

## Troubleshooting:
If you encounter any issues:
1. Check the logs: `journalctl -u trading-analysis -f`
2. Check the logs: `journalctl -u market-brief-scheduler -f`
3. Verify the virtual environment has the correct packages: `pip list | grep openai`
