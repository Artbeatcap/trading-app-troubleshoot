# Voice Layer Model Fix

## Issue Found
The `gpt-5-nano` model is using all completion tokens for internal reasoning and not producing any output content. This is causing the "OpenAI returned empty content" warnings.

**Debug Results:**
- `gpt-5-nano` uses all 4000 completion tokens for `reasoning_tokens`
- `finish_reason='length'` indicates it hits the token limit during reasoning
- No actual content is generated

## Recommended Fix

Update your `.env` file to use a more reliable model:

```bash
# Change from:
BRIEF_MODEL=gpt-5-nano

# To:
BRIEF_MODEL=gpt-4o-mini
```

## Why gpt-4o-mini is Better for This Use Case

1. **Reliable Output**: Doesn't use reasoning tokens that consume the entire budget
2. **Cost Effective**: Much cheaper than gpt-4o
3. **Fast**: Quick response times
4. **Proven**: Works well with structured prompts and voice rewriting
5. **Temperature Support**: Supports custom temperature values (unlike gpt-5-nano)

## Alternative Models (in order of recommendation)

1. **gpt-4o-mini** (recommended) - Fast, cheap, reliable
2. **gpt-4o** - Highest quality but more expensive  
3. **gpt-3.5-turbo** - Older but still reliable for this task

## After Changing the Model

1. Update your `.env` file with the new model
2. Restart your Flask application
3. Test the brief generation again

The voice layer should work perfectly with these models since they don't have the reasoning token consumption issue that gpt-5-nano has.
