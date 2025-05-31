# Tradier API Setup Instructions

This application now integrates with the Tradier API for more reliable options data. Follow these steps to set up your Tradier API access:

## Step 1: Get a Tradier Account

1. Sign up for a free Tradier account at [tradier.com](https://tradier.com)
2. Complete the account verification process
3. Navigate to your account dashboard

## Step 2: Generate API Token

1. In your Tradier dashboard, go to "Preferences" > "API Access"
2. Create a new application
3. Generate an API token
4. Copy your token (keep it secure!)

## Step 3: Configure the Application

### Option A: Environment Variable (Recommended)
Set the environment variable before running the app:

**Windows:**
```cmd
set TRADIER_API_TOKEN=your_actual_token_here
python app.py
```

**Mac/Linux:**
```bash
export TRADIER_API_TOKEN=your_actual_token_here
python app.py
```

### Option B: Direct Code Modification
Edit `app.py` and replace:
```python
TRADIER_TOKEN = os.getenv('TRADIER_API_TOKEN', 'your_tradier_token_here')
```

With your actual token:
```python
TRADIER_TOKEN = "your_actual_token_here"
```

## Step 4: Switch to Production (Optional)

By default, the app uses Tradier's sandbox environment for testing. To use live market data:

1. In `app.py`, change:
```python
TRADIER_API_BASE = "https://sandbox.tradier.com/v1"
```

To:
```python
TRADIER_API_BASE = "https://api.tradier.com/v1"
```

## Fallback Behavior

If Tradier API is not configured or fails, the application will automatically fall back to Yahoo Finance for options data. However, Tradier provides more reliable and accurate options data.

## Benefits of Tradier Integration

- More reliable options chains
- Better data accuracy
- Proper market hours handling
- Professional-grade market data
- Real-time quotes (with appropriate account)

## Troubleshooting

- If you see "Tradier API token not configured" messages, your token setup needs attention
- Check that your token has the necessary permissions for market data
- Ensure your Tradier account is approved for options data access
- Verify you're using the correct API endpoint (sandbox vs production)

## Support

For Tradier API specific issues, consult the [Tradier API Documentation](https://documentation.tradier.com/). 