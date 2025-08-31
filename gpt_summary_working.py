import os
import textwrap
from typing import Dict, Any
import requests
import json

# Check if OpenAI is available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

MODEL = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")  # default

# Initialize client only if API key is available
CLIENT = None
if OPENAI_AVAILABLE:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            # Try to create client with minimal parameters to avoid proxy issues
            CLIENT = OpenAI(api_key=api_key)
            print("✅ OpenAI client initialized successfully")
        except Exception as e:
            print(f"⚠️ OpenAI client initialization failed: {e}")
            CLIENT = None

SYSTEM = (
    "You are a pro market writer. Summarize for retail traders at ~8th–10th grade "
    "reading level. Be concise, scannable, and actionable. Avoid penny/illiquid tickers."
)

def _prompt(brief: Dict[str, Any]) -> str:
    # Build a compact, structured context for the model
    ah = brief.get("ah_moves", [])[:8]
    pre = brief.get("premarket_moves", [])[:8]
    earnings = brief.get("earnings", [])[:6]

    return f"""
Write a short subscriber summary (120–180 words) for today's U.S. market brief.

Tone: calm, direct, trader-friendly. No fluff. 
Format:
- Today in one line
- AH & Premarket: 3–5 notable movers with the reason (tickers only)
- Why it matters (macro/sector)
- Levels to watch (SPY ladder from brief)
- Tomorrow (next catalyst in 1 line)

DATA:
Market overview: {brief.get('market_overview','')}
Macro/data: {brief.get('macro_data','')}

AH movers (top):
{[{'t':m['ticker'],'mv':m['move'],'why':m.get('why','')} for m in ah]}

Premarket movers (top):
{[{'t':m['ticker'],'mv':m['move'],'why':m.get('why','')} for m in pre]}

Earnings (bullets):
{[e['ticker']+': '+e['note'] for e in earnings]}

SPY levels: S1 {brief.get('spy_s1')} → {brief.get('spy_s2')} | R {brief.get('spy_r1')}, {brief.get('spy_r2')}, {brief.get('spy_r3')}

Constraints:
- Keep under 180 words
- Use bullets and short sentences
- Never include sub-$1 or illiquid tickers
"""

def call_openai_api_directly(api_key: str, messages: list, model: str = "gpt-4o-mini") -> str:
    """Call OpenAI API directly using requests to bypass client issues"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 500
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"OpenAI API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Direct API call failed: {e}")
        return None

def summarize_brief(brief: Dict[str, Any]) -> Dict[str, str]:
    """Returns {'subscriber_summary': markdown, 'preheader': str}"""
    # Check if OpenAI is available and API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        # Fallback: rule-based summary
        fallback_summary = (
            f"• Today: {brief.get('market_overview','')}\n"
            f"• Movers: " +
            ", ".join([m['ticker'] for m in (brief.get('premarket_moves') or [])[:4]]) +
            f"\n• SPY: S {brief.get('spy_s1')}→{brief.get('spy_s2')} | R {brief.get('spy_r1')},{brief.get('spy_r2')},{brief.get('spy_r3')}"
        )
        return {
            "subscriber_summary": fallback_summary,
            "preheader_ai": f"Market Brief: {brief.get('market_overview','')}"[:140]
        }
    
    # Try OpenAI client first
    if CLIENT:
        try:
            msg = _prompt(brief)
            resp = CLIENT.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": msg}
                ],
                temperature=0.5,
                max_tokens=500,
            )
            
            summary_text = resp.choices[0].message.content.strip()
            
            # Build a tight preheader from the first line
            first_line = summary_text.strip().splitlines()[0][:140]
            
            return {
                "subscriber_summary": summary_text,
                "preheader_ai": first_line
            }
        except Exception as e:
            print(f"OpenAI client failed, trying direct API: {e}")
    
    # Try direct API call as fallback
    try:
        msg = _prompt(brief)
        summary_text = call_openai_api_directly(
            api_key, 
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": msg}
            ],
            MODEL
        )
        
        if summary_text:
            # Build a tight preheader from the first line
            first_line = summary_text.strip().splitlines()[0][:140]
            
            return {
                "subscriber_summary": summary_text,
                "preheader_ai": first_line
            }
    except Exception as e:
        print(f"Direct API call failed: {e}")
    
    # Final fallback: rule-based summary
    fallback_summary = (
        f"• Today: {brief.get('market_overview','')}\n"
        f"• Movers: " +
        ", ".join([m['ticker'] for m in (brief.get('premarket_moves') or [])[:4]]) +
        f"\n• SPY: S {brief.get('spy_s1')}→{brief.get('spy_s2')} | R {brief.get('spy_r1')},{brief.get('spy_r2')},{brief.get('spy_r3')}"
    )
    return {
        "subscriber_summary": fallback_summary,
        "preheader_ai": f"Market Brief: {brief.get('market_overview','')}"[:140]
    }
