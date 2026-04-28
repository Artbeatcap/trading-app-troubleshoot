# Voice Layer Setup Guide

The voice layer has been successfully implemented! Here's what you need to do to activate it:

## Environment Variables to Add

Add these variables to your `.env` file:

```bash
# Voice Layer Configuration
BRIEF_MODEL=gpt-5-nano
BRIEF_VOICE_FILE=style/brief_voice.md
BRIEF_VOICE_STRENGTH=0.7
```

### Variable Descriptions:

- **BRIEF_MODEL**: The OpenAI model to use for both content generation and voice rewriting (default: "gpt-5-nano")
- **BRIEF_VOICE_FILE**: Path to your voice profile file (default: "style/brief_voice.md")
- **BRIEF_VOICE_STRENGTH**: Controls how strongly the voice rewrite adheres to your style (0.0-1.0, default: 0.7)
  - Higher values = more faithful to your voice, lower temperature
  - Lower values = more creative, but less consistent with your style

## Files Created:

1. ✅ **style/brief_voice.md** - Your voice profile with writing samples
2. ✅ **market_brief_generator.py** - Updated with voice layer functionality

## What's Changed:

### In market_brief_generator.py:
- Added voice configuration variables
- Added `_load_voice_profile()` function to read your voice file
- Added `_rewrite_in_voice()` function for the second-pass voice rewrite
- Updated `summarize_news()` to use the voice layer
- Updated `summarize_news_weekly()` to use the voice layer
- Changed model references to use `BRIEF_MODEL` variable
- Lowered temperature from 1.0 to 0.8 for more consistent results

### Two-Pass Generation Process:
1. **First pass**: Uses your existing BRIEF_SYSTEM prompt with strict structure/fact requirements
2. **Second pass**: Rewrites the content to match your voice while preserving all facts, numbers, tickers, and headers

## How to Test:

1. Add the environment variables to your `.env` file
2. Restart your application to load the new environment variables
3. Test with no-email generation:
   - **Daily**: POST to `/admin/generate/daily-noemail` → writes `static/uploads/brief_latest.html`
   - **Weekly**: POST to `/admin/generate/weekly-noemail?force=1` → writes `static/uploads/brief_weekly_latest.html`
4. Check the generated HTML files to verify the voice sounds more like you while keeping all facts intact

## Safety Features:

- If the voice file is missing or empty, the system falls back to the original content
- If the voice rewrite fails, the system returns the original structured content
- All factual data (tickers, numbers, dates, levels, headers) are explicitly preserved
- The voice hint is added to the first pass but doesn't override the strict BRIEF_SYSTEM rules

## Customizing Your Voice:

Edit `style/brief_voice.md` anytime to adjust your voice profile. The file is read at runtime, so changes take effect immediately without restarting the application.

## Optional: Apply to "What's Moving" Section

If you want to apply the voice layer to the gapping stocks section as well, you can wrap the return statement in `generate_gapping_stocks_summary()` with `_rewrite_in_voice()`.
