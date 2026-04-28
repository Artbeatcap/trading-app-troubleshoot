# Manual Voice Layer Deployment Guide

## Files to Upload to Production

### 1. Main Implementation
- **`market_brief_generator.py`** → `/home/tradingapp/trading-analysis/market_brief_generator.py`

### 2. Voice Profile Directory
- **`style/`** → `/home/tradingapp/trading-analysis/style/`
  - Contains `brief_voice.md` with your voice samples

## Server Commands

### SSH to your server:
```bash
ssh root@167.88.43.61
cd /home/tradingapp/trading-analysis
```

### 1. Backup current files:
```bash
cp market_brief_generator.py market_brief_generator.py.backup.$(date +%Y%m%d_%H%M%S)
```

### 2. Upload new files (from your local machine):
```bash
# From your local project directory:
scp market_brief_generator.py root@167.88.43.61:/home/tradingapp/trading-analysis/
scp -r style root@167.88.43.61:/home/tradingapp/trading-analysis/
```

### 3. Set permissions on server:
```bash
ssh root@167.88.43.61
chown -R tradingapp:tradingapp /home/tradingapp/trading-analysis/style
chmod 644 /home/tradingapp/trading-analysis/market_brief_generator.py
chmod -R 644 /home/tradingapp/trading-analysis/style/*
```

### 4. Update environment variables:
```bash
# Edit the production .env file
nano /home/tradingapp/trading-analysis/.env

# Add or update these lines:
BRIEF_MODEL=gpt-4o-mini
BRIEF_VOICE_FILE=style/brief_voice.md
BRIEF_VOICE_STRENGTH=0.7
```

### 5. Restart services:
```bash
systemctl restart trading-analysis
systemctl restart weekly-brief-scheduler
```

### 6. Verify deployment:
```bash
# Check service status
systemctl status trading-analysis

# Check logs
journalctl -u trading-analysis -f

# Test the voice layer (optional)
curl -X POST http://localhost:5000/admin/generate/daily-noemail
```

## Key Changes Deployed

### ✅ Voice Layer Features:
- Two-pass generation (structure + voice rewrite)
- Voice profile loading from `style/brief_voice.md`
- Model compatibility fixes (gpt-4o-mini recommended)
- Temperature handling for different models
- Increased token limits for reasoning models

### ✅ Bug Fixes:
- Fixed empty content issue with gpt-5-nano
- Proper temperature parameter handling
- Improved error handling and fallbacks

## Testing the Deployment

### 1. Check voice profile is loaded:
```bash
# Should show your voice file exists
ls -la /home/tradingapp/trading-analysis/style/brief_voice.md
```

### 2. Test brief generation:
```bash
# Monitor logs while testing
journalctl -u trading-analysis -f &

# Trigger a test brief (if you have admin access)
# Or wait for the next scheduled brief
```

### 3. Verify no "empty content" warnings:
```bash
# Check recent logs for the warning
journalctl -u trading-analysis --since "1 hour ago" | grep -i "empty content"
```

## Rollback Instructions (if needed)

If something goes wrong:

```bash
# Restore backup
cd /home/tradingapp/trading-analysis
cp market_brief_generator.py.backup.YYYYMMDD_HHMMSS market_brief_generator.py

# Remove voice layer env vars from .env
nano .env
# Remove or comment out:
# BRIEF_MODEL=gpt-4o-mini
# BRIEF_VOICE_FILE=style/brief_voice.md  
# BRIEF_VOICE_STRENGTH=0.7

# Restart service
systemctl restart trading-analysis
```

## Success Indicators

- ✅ No "OpenAI returned empty content" warnings in logs
- ✅ Brief generation completes successfully  
- ✅ Generated briefs sound more natural/human
- ✅ All facts, numbers, and tickers preserved
- ✅ Services restart without errors
