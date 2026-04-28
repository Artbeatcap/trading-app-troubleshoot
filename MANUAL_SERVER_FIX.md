# Manual Server Fix Instructions

## Issues Found:
1. ❌ Missing `openai` module on server
2. ❌ `emails.py` file not uploaded to server
3. ❌ SSH connection issues preventing automated fixes

## Manual Steps to Fix:

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

### 5. Upload emails.py File
From your local machine:
```bash
scp emails.py root@167.88.43.61:/home/tradingapp/trading-analysis/
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

## Files That Need to Be on Server:
- `market_brief_generator.py` ✅ (already uploaded)
- `emails.py` ❌ (needs to be uploaded)
- Dependencies: `openai`, `httpx`, `python-dotenv` ❌ (need to be installed)
