"""
Market Brief Generator for Trading Analysis App
Integrates with existing stock news email logic and sends to subscribers
"""

# Enhanced gapping stocks functionality
from market_brief_generator_fixed import (
    fetch_gapping_stocks_enhanced,
    CONVERSATIONAL_SYSTEM_PROMPT,
)

import os
import re
import requests
import json
import hashlib
import time
from html import escape
from datetime import datetime, timedelta, time as dt_time
from datetime import date
import sys
from typing import List, Dict, Any
import math
from typing import Optional
import pytz
from pathlib import Path
from flask import current_app
from flask_mail import Message
from models import MarketBriefSubscriber, db
from providers import get_default_provider, summarize_catalyst
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom exceptions
class BriefDataUnavailable(Exception):
    """Raised when required market data cannot be retrieved."""
    pass


DAILY_REQUIRED_MARKET_SYMBOLS = ["spy", "qqq"]

# ----- Tiny on-disk JSON cache (60–120s) -----
CACHE_DIR = Path(os.getenv("OP_CACHE_DIR", Path(__file__).resolve().parent / "cache"))
AV_CACHE_TTL = int(os.getenv("AV_CACHE_TTL", "90"))     # Alpha Vantage default 90s
FH_CACHE_TTL = int(os.getenv("FH_CACHE_TTL", "120"))    # Finnhub default 120s

def _cache_file(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")

def _cache_get_json(key: str, ttl: int) -> Dict[str, Any] | None:
    p = _cache_file(key)
    try:
        if p.exists() and (time.time() - p.stat().st_mtime) <= ttl:
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None

def _cache_put_json(key: str, data: Dict[str, Any]) -> None:
    p = _cache_file(key)
    try:
        p.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass

def fetch_economic_calendar_today() -> List[Dict[str, str]]:
    """Today's economic calendar via providers.DataProvider.

    Returns an empty list on the current Polygon tier (no economic-calendar
    endpoint). Kept for callers that still expect the function to exist.
    """
    today = datetime.now(tz=NY).date().isoformat()
    try:
        rows = get_default_provider().get_economic_calendar(today, today)
    except Exception:
        return []
    return [
        {k: v for k, v in ev.items() if k != "date"}
        for ev in rows
    ]


def fetch_economic_calendar_range(days_ahead: int = 7, start: datetime | None = None) -> List[Dict[str, str]]:
    """Economic calendar for [start, start+days_ahead) via providers.DataProvider.

    Returns an empty list on the current Polygon tier (no economic-calendar
    endpoint). Kept for callers that still expect the function to exist.
    """
    start_dt = (start or datetime.now(tz=NY)).date()
    end_dt = start_dt + timedelta(days=days_ahead)
    try:
        return get_default_provider().get_economic_calendar(
            start_dt.isoformat(), end_dt.isoformat()
        )
    except Exception:
        return []

def _week_bounds(dt: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (Mon, Fri) datetimes for the week containing dt (ET)."""
    base = (dt or datetime.now(tz=NY)).date()
    # Monday = 0 ... Sunday = 6
    monday = base - timedelta(days=base.weekday())
    friday = monday + timedelta(days=4)
    return datetime.combine(monday, datetime.min.time(), tzinfo=NY), datetime.combine(friday, datetime.min.time(), tzinfo=NY)

def build_weekly_brief() -> Dict[str, Any]:
    """
    Build a weekly brief context compatible with weekly_brief.html.jinja template:
    - subject_theme, date_human, preheader
    - recap (index_blurb, sector_blurb, movers_bullets, flow_blurb)
    - levels (spy, qqq, iwm with s1, s2, r1, r2, r3)
    - week_ahead (macro_bullets, earnings_bullets)
    - swing_playbook_bullets
    - cta_url, unsubscribe_url, preferences_url
    """
    mon, fri = _week_bounds()
    
    # Get current stock prices for realistic levels (no synthetic fallbacks)
    stock_prices = fetch_stock_prices_strict()
    if not stock_prices or not has_valid_price_data(stock_prices):
        raise BriefDataUnavailable("Missing live price data for weekly brief")

    expected_range = calculate_expected_range(stock_prices)
    if not expected_range:
        raise BriefDataUnavailable("Unable to derive index levels for weekly brief")

    # Try to get economic calendar and movers
    cats = fetch_economic_calendar_range(days_ahead=7, start=mon)
    movers = fetch_top_movers_av()

    def _fmt_price(symbol: str) -> str:
        value = stock_prices.get(symbol, {}).get('current_price')
        return f"${value:.2f}" if isinstance(value, (int, float)) and value else "N/A"

    def _fmt_change(symbol: str) -> Optional[str]:
        value = stock_prices.get(symbol, {}).get('change_percent')
        if isinstance(value, (int, float)):
            return f"{value:+.2f}%"
        return None

    spy_change = _fmt_change('spy')
    qqq_change = _fmt_change('qqq')
    change_fragments = [frag for frag in (spy_change and f"SPY {spy_change}", qqq_change and f"QQQ {qqq_change}") if frag]

    index_blurb = f"SPY closed at {_fmt_price('spy')} and QQQ at {_fmt_price('qqq')} heading into the new week."
    if change_fragments:
        index_blurb += f" Latest session moves: {', '.join(change_fragments)}."

    movers_bullets: List[str] = []
    if movers:
        for mover in movers[:8]:
            ticker = mover.get("ticker") or ""
            if not ticker:
                continue
            change_pct = mover.get("change_percent") or mover.get("pct") or ""
            direction_icon = "📈" if mover.get("direction") == "up" else "📉"
            note = mover.get("why") or mover.get("headline")
            bullet = f"{direction_icon} {ticker}: {change_pct}"
            if note:
                bullet += f" — {note}"
            movers_bullets.append(bullet)

    macro_bullets: List[str] = []
    if cats:
        for cat in cats[:8]:
            parts = []
            date_str = cat.get("date")
            time_str = cat.get("time_et") or cat.get("time")
            event = cat.get("event")
            if date_str:
                parts.append(date_str)
            if time_str:
                parts.append(time_str)
            if event:
                parts.append(event)
            line = " • ".join(part for part in parts if part)
            why = cat.get("why") or cat.get("impact")
            if why:
                line = f"{line} — {why}" if line else why
            if line:
                macro_bullets.append(line)

    vix_value = stock_prices.get('vix', {}).get('current_price')
    if isinstance(vix_value, (int, float)) and vix_value > 0:
        volatility_note = "elevated" if vix_value >= 20 else "moderate"
        flow_blurb = f"VIX is at {vix_value:.2f}, signalling {volatility_note} implied volatility for the coming sessions."
    else:
        flow_blurb = ""

    levels = {symbol: expected_range.get(symbol) for symbol in ('spy', 'qqq', 'iwm') if expected_range.get(symbol)}
    if not levels:
        raise BriefDataUnavailable("Weekly brief lacks index levels after calculations")

    preheader = "Weekly recap with movers and catalysts"
    if macro_bullets:
        preheader = f"{len(macro_bullets)} macro catalysts on deck this week"
    elif movers_bullets:
        preheader = f"Tracking {len(movers_bullets)} notable movers into the week"

    ctx = {
        "subject_theme": "Market Analysis",
        "date_human": f"Week of {mon.strftime('%B %d, %Y')}",
        "preheader": preheader,
        "recap": {
            "index_blurb": index_blurb,
            "sector_blurb": "Notable movers covered below" if movers_bullets else "",
            "movers_bullets": movers_bullets,
            "flow_blurb": flow_blurb
        },
        "levels": levels,
        "week_ahead": {
            "macro_bullets": macro_bullets,
            "earnings_bullets": []
        },
        "swing_playbook_bullets": [],
        "cta_url": "https://optionsplunge.com/dashboard",
        "unsubscribe_url": "https://optionsplunge.com/unsubscribe",
        "preferences_url": "https://optionsplunge.com/settings",
        "date_range": {
            "monday": mon.strftime("%Y-%m-%d"),
            "friday": fri.strftime("%Y-%m-%d"),
            "label": f"Week of {mon.strftime('%Y-%m-%d')}",
        },
        "week_ahead_catalysts": cats,
        "movers_snapshot": movers,
        "generated_at": datetime.now(tz=NY).strftime("%Y-%m-%d %H:%M ET"),
    }
    return ctx

def fetch_top_movers_av() -> List[Dict[str, Any]]:
    """Top gainers/losers via providers.DataProvider.

    Name preserved for backward-compat with existing callers. The historical
    Alpha Vantage `TOP_GAINERS_LOSERS` call has been removed.
    """
    try:
        dp = get_default_provider()
        gainers = dp.get_gainers(limit=5)
        losers = dp.get_losers(limit=5)
    except Exception:
        return []

    def _fmt(mover: dict, direction: str) -> Dict[str, Any]:
        pct = mover.get("change_pct")
        price = mover.get("price")
        return {
            "ticker": mover.get("ticker") or "",
            "change_percent": f"{pct:+.2f}%" if isinstance(pct, (int, float)) else "",
            "price": f"{price:.2f}" if isinstance(price, (int, float)) else "",
            "change": "",
            "volume": str(mover.get("volume") or ""),
            "direction": direction,
        }

    return [_fmt(m, "up") for m in gainers] + [_fmt(m, "down") for m in losers]

# Environment variables (resolved at runtime to allow config overrides)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai_client = None  # Initialize lazily to avoid import issues

# --- Author voice controls ---
BRIEF_MODEL = os.getenv("BRIEF_MODEL", "gpt-4o-mini")
BRIEF_VOICE_FILE = os.getenv("BRIEF_VOICE_FILE", "style/brief_voice.md")
BRIEF_VOICE_STRENGTH = float(os.getenv("BRIEF_VOICE_STRENGTH", "0.7"))  # 0..1

from functools import lru_cache

@lru_cache(maxsize=1)
def _load_voice_profile() -> str:
    try:
        p = Path(BRIEF_VOICE_FILE)
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.warning(f"Voice profile load failed: {e}")
    return ""

def _rewrite_in_voice(text: str, model: str = BRIEF_MODEL) -> str:
    """Rewrite `text` to match the author's voice without changing facts or structure."""
    voice = _load_voice_profile()
    if not voice or not OPENAI_API_KEY:
        return text
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Set temperature and token limits for the model
        temp = max(0.2, 1.0 - BRIEF_VOICE_STRENGTH*0.6)
        max_tokens = 2200
        
        resp = client.chat.completions.create(
            model=model,
            messages=[
              {"role":"system","content":
               "You are a precise editor. Rewrite the user's draft to match the AUTHOR VOICE exactly while "+
               "preserving every factual token and structure. Do NOT change tickers (SPY, QQQ, etc.), "+
               "numbers, dates, times, levels, or section headers. No new facts."},
              {"role":"user","content":
               f"AUTHOR VOICE (style only):\\n---\\n{voice}\\n---\\n\\n"+
               "DRAFT (preserve facts/headers):\\n---\\n"+
               f"{text}\\n---\\n\\n"+
               "TASK: Return Markdown only, same sections/order, more natural and human, but identical facts."}
            ],
            temperature=temp,
            max_completion_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning(f"Voice rewrite failed, returning original: {e}")
        return text

# Add GPT summary import
try:
    from gpt_summary import summarize_brief
    GPT_AVAILABLE = True
except ImportError:
    GPT_AVAILABLE = False
    logging.warning("GPT summary module not available")

# Add headline summarizer import
try:
    from headline_summarizer import summarize_headlines
    HEADLINE_SUMMARIZER_AVAILABLE = True
except ImportError:
    HEADLINE_SUMMARIZER_AVAILABLE = False
    logging.warning("Headline summarizer module not available")

# ===== Session/time helpers and universe =====
NY = pytz.timezone("America/New_York")

# Junk scan env knobs (optional)
JUNK_ENABLE = (os.getenv("JUNK_ENABLE", "1").strip() == "1")
JUNK_MIN_PRICE = float(os.getenv("JUNK_MIN_PRICE", "1.0"))
JUNK_MAX_PRICE = float(os.getenv("JUNK_MAX_PRICE", "20.0"))
JUNK_MIN_ABS_PCT = float(os.getenv("JUNK_MIN_ABS_PCT", "5.0"))
JUNK_MIN_PM_VOL = int(os.getenv("JUNK_MIN_PM_VOL", "100000"))
JUNK_MIN_AH_VOL = int(os.getenv("JUNK_MIN_AH_VOL", "100000"))

# Low-float tagging (optional; resolved via providers.DataProvider company
# profile. Note: Polygon Stocks Starter tier does not expose free-float, so
# this tag is effectively disabled until an earnings/float-capable provider
# is wired in.)
JUNK_FLOAT_MAX = int(os.getenv("JUNK_FLOAT_MAX", "50000000"))

# Universe source for junk scan
JUNK_UNIVERSE_TICKERS = os.getenv("JUNK_UNIVERSE_TICKERS", "").strip()
JUNK_UNIVERSE_FILE = os.getenv("JUNK_UNIVERSE_FILE", "static/universe/junk_universe.txt")

def _now_ny() -> datetime:
    return datetime.now(tz=NY)

def _is_premarket(dt: Optional[datetime] = None) -> bool:
    dt = dt or _now_ny()
    current_time = dt.time()
    return dt_time(7, 0) <= current_time < dt_time(9, 30)

def _is_afterhours(dt: Optional[datetime] = None) -> bool:
    dt = dt or _now_ny()
    current_time = dt.time()
    return dt_time(16, 0) <= current_time <= dt_time(20, 0)

def _session_window(dt: Optional[datetime] = None) -> tuple[str, datetime, datetime, int]:
    dt = dt or _now_ny()
    if _is_premarket(dt):
        start = dt.replace(hour=7, minute=0, second=0, microsecond=0)
        end = min(dt, dt.replace(hour=9, minute=30, second=0, microsecond=0))
        return ("pm", start, end, JUNK_MIN_PM_VOL)
    if _is_afterhours(dt):
        start = dt.replace(hour=16, minute=0, second=0, microsecond=0)
        end = min(dt, dt.replace(hour=20, minute=0, second=0, microsecond=0))
        return ("ah", start, end, JUNK_MIN_AH_VOL)
    return ("none", dt, dt, max(JUNK_MIN_PM_VOL, JUNK_MIN_AH_VOL))

def _is_sunday_ny(dt=None) -> bool:
    dt = dt or datetime.now(tz=NY)
    return dt.weekday() == 6  # Sunday

def _last_completed_week_range(dt=None):
    """
    Returns (mon_date, fri_date) for the LAST completed Mon–Fri week
    relative to 'dt' (NY). If today is Sunday, that means the week that just ended Friday.
    """
    dt = (dt or datetime.now(tz=NY)).date()
    # Go to last Friday
    offset_to_fri = (dt.weekday() - 4) % 7
    last_fri = dt - timedelta(days=offset_to_fri if offset_to_fri else 7)
    last_mon = last_fri - timedelta(days=4)
    return last_mon, last_fri

def _chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def _liquid_universe() -> list[str]:
    """
    Source of truth for scanning. Override with env var UNIVERSE_TICKERS (comma-separated).
    Keep this tight for speed; you do NOT need whole market for actionable AH/PM names.
    """
    env_list = (os.getenv("UNIVERSE_TICKERS") or "").strip()
    if env_list:
        return [s.strip().upper() for s in env_list.split(",") if s.strip()]
    return [
        # Index/ETFs
        "SPY","QQQ","IWM","DIA","VTI","VOO","TLT","IEF","HYG","LQD","XLF","XLK","XLE",
        "XLV","XLI","XLP","XLY","XLU","XLB","XLC","XLRE","SMH","SOXX","XBI","XOP","XME",
        "XHB","XRT","GLD","SLV","USO","UNG","UVXY","VIXY",
        # Mag7 + heavyweights
        "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","TSLA","AVGO","BRK.B",
        # Liquid large caps across sectors
        "AMD","NFLX","TSM","ADBE","CRM","ORCL","INTC","CSCO","QCOM","MU",
        "JPM","BAC","WFC","GS","MS","C","V","MA","PYPL","AXP",
        "XOM","CVX","COP","OXY","SLB","PXD",
        "UNH","LLY","JNJ","PFE","ABBV","MRK",
        "KO","PEP","MCD","SBUX","COST","WMT","TGT","HD","LOW","NKE",
        "BA","CAT","DE","GE","HON","LMT","RTX",
        "T","VZ","TMUS",
        # Some high-beta/trader favorites
        "PLTR","SNAP","AFRM","RIVN","LCID","COIN","HOOD","ROKU","UBER","LYFT",
        "GME","AMC","NKLA","NVAX","AI","UPST","SMCI"
    ]

def _junk_universe() -> list[str]:
    """
    Build a junk universe from env or a local file.
    - JUNK_UNIVERSE_TICKERS: comma-separated list in env
    - JUNK_UNIVERSE_FILE: one ticker per line (ignored if file missing)
    """
    out: list[str] = []
    if JUNK_UNIVERSE_TICKERS:
        out.extend([s.strip().upper() for s in JUNK_UNIVERSE_TICKERS.split(",") if s.strip()])
    try:
        if os.path.exists(JUNK_UNIVERSE_FILE):
            with open(JUNK_UNIVERSE_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip().upper()
                    if s and s not in out:
                        out.append(s)
    except Exception as e:
        logger.warning(f"Could not read JUNK_UNIVERSE_FILE {JUNK_UNIVERSE_FILE}: {e}")
    # Dedup and basic sanity
    out = [s for s in dict.fromkeys(out) if s.isalnum() or "." in s]
    return out[:1000]

def _tradier_quotes(symbols: list[str]) -> list[dict]:
    """Return a flat list of Tradier-shaped quote dicts for `symbols`.

    Name preserved for backward-compat with existing callers. Internally
    fetches via providers.DataProvider.get_snapshot and re-projects the
    normalized quote into the {symbol, last, change_percentage, volume,
    bid, ask} fields the callers expect.
    """
    dp = get_default_provider()
    out: list[dict] = []
    for sym in symbols:
        try:
            q = dp.get_snapshot(sym)
        except Exception:
            q = None
        if not q:
            continue
        price = q.get("price")
        chg_pct = q.get("change_pct")
        prev_close = None
        try:
            if price is not None and chg_pct not in (None, 0):
                prev_close = float(price) / (1.0 + float(chg_pct) / 100.0)
            elif price is not None:
                prev_close = float(price)
        except Exception:
            prev_close = None
        out.append(
            {
                "symbol": q.get("ticker") or sym,
                "last": price,
                "prevclose": prev_close,
                "change_percentage": chg_pct,
                "volume": q.get("volume") or 0,
                "bid": None,
                "ask": None,
                "description": sym,
                "type": "stock",
            }
        )
    return out


def _tradier_timesales_volume(symbol: str, start_dt: datetime, end_dt: datetime) -> int:
    """Sum 1-minute bar volume for `symbol` between `start_dt` and `end_dt`
    via providers.DataProvider.
    """
    frm = start_dt.astimezone(pytz.UTC).strftime("%Y-%m-%d")
    to = end_dt.astimezone(pytz.UTC).strftime("%Y-%m-%d")
    try:
        bars = get_default_provider().get_bars(symbol, 1, "minute", frm, to, limit=5000)
    except Exception:
        return 0
    start_ms = int(start_dt.astimezone(pytz.UTC).timestamp() * 1000)
    end_ms = int(end_dt.astimezone(pytz.UTC).timestamp() * 1000)
    vol = 0
    for b in bars or []:
        ts = b.get("timestamp")
        if not ts:
            continue
        try:
            bar_ms = int(
                datetime.strptime(ts.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                .timestamp() * 1000
            )
        except Exception:
            continue
        if start_ms <= bar_ms <= end_ms:
            v = b.get("volume")
            if isinstance(v, (int, float)):
                vol += int(v)
    return vol

# ===== Stable system and user templates for Morning Brief generation =====
BRIEF_SYSTEM = CONVERSATIONAL_SYSTEM_PROMPT

BRIEF_USER_TEMPLATE = """
DATE: {date_str}

DATA FEED
- SPOT/RANGE (indices & yields; expected intraday ranges and prior close gaps):
{range_text}

- VOL & SENTIMENT (VIX, term structure, put/call, breadth if available):
{vix_text}

- LEVELS METHODOLOGY (how S/R numbers were calculated; do not invent chart-based reasons):
{levels_methodology_text}

- OVERNIGHT / GAPS — AH & Premarket (tickers, catalysts, size, liquidity flags):
{gapping_text}

- CANDIDATE HEADLINES (use 'summary_2to5' if present, else 'summary'):
{headlines_text}

- KEY LEVELS FEED (echo exactly; daily & weekly S/R for SPY, QQQ):
{key_levels_feed}

TASK
Using only the DATA FEED above, produce the morning brief with the exact section set:
1) Executive Summary (Top 5 bullets; each bullet = What changed → Why it matters → Watch X at Y. Add blank line before each bullet for better separation)
2) What's moving — After-hours & Premarket (3–8 names, 2–5 sentences each; include Watch + invalidation if given)
3) Key Market Headlines (H3 headline, H4 'Summary', then 2–5 sentence paragraph; blank line between items)
4) Technical Analysis & Daily Range Insights (SPY/QQQ ranges and nearby S/R only from inputs)
5) Trader Playbook — If/Then Scenarios (3–6 bullets; template: If <condition>, then <bias>, while <invalidation> (timeframe: <...>))
6) Market Sentiment & Outlook (tie vol/rates/positioning to likely tape behavior; note missing data if any)
7) Key Levels to Watch (print **Daily & Weekly S and R** for SPY and QQQ exactly as provided)
"""

# ===== WEEKLY BRIEF: STABLE PROMPTS (for prompt caching) =====
WEEKLY_SYSTEM = """
You are a professional sell-side strategist writing a concise WEEKLY market brief
for US options traders. Write in clear, plain English with trader-first wording.

SCOPE
- Look BACK at the prior Monday–Friday trading week.
- Look AHEAD to the coming week (macro data, earnings, policy, seasonality).

HARD RULES
- Do NOT invent data. Use only provided inputs.
- If any input block begins with "SECTION_UNAVAILABLE:", OMIT the corresponding
  section from your output entirely. Do not describe the missing data, do not
  fabricate content, do not include a header for it.
- US Eastern Time / US markets focus.
- Section headers EXACTLY (Markdown H2):
  ## Weekly Executive Summary
  ## Last Week in Review
  ## Week Ahead — Data, Earnings, Events
  ## Sector & Factor Movers
  ## Weekly Technicals (SPY & QQQ)
  ## Key Levels for the Week

STYLE
- 2–5 tight paragraphs for the summary; bullets elsewhere are OK.
- Numbers: include % moves and key levels; round sensibly.
- No advice; analysis only.
"""

WEEKLY_USER_TEMPLATE = """
WEEK OF: {week_of_str}

INPUTS (WEEKLY)
- INDEX RECAP (Mon–Fri) for SPY/QQQ, sector ETFs, rates:
{index_recap}

- TOP HEADLINES (last week; 5–10 items):
{weekly_headlines}

- WEEK AHEAD (macro/earnings/events; concise bullets):
{week_ahead}

- WEEKLY LEVELS (SPY/QQQ; supports & resistances):
{weekly_levels}

TASK
Using only the inputs above, produce the weekly brief with these sections:
1) Weekly Executive Summary
2) Last Week in Review
3) Week Ahead — Data, Earnings, Events
4) Sector & Factor Movers
5) Weekly Technicals (SPY & QQQ)
6) Key Levels for the Week (echo the provided levels; no invention)
"""
# ===== END WEEKLY PROMPTS =====

# ===== ENHANCED WEEKLY BRIEF: STABLE PROMPTS (for prompt caching) =====
WEEKLY_SYSTEM_ENHANCED = """
You are a senior market strategist writing a comprehensive WEEKLY market brief for active 
US options traders and swing traders. Your brief should capture the big picture of market 
activity and provide actionable context for the week ahead.

AUDIENCE
- Experienced options traders looking for high-level market context
- Swing traders planning multi-day positions
- Professional traders who need to understand major shifts and upcoming catalysts

CORE OBJECTIVES
1. Synthesize the past week's major moves into a coherent narrative
2. Identify what moved markets and why (data, news, flows, technicals)
3. Highlight upcoming events and data that will drive next week's trading
4. Provide context for positioning and risk management

SCOPE
- Review: Monday-Friday of the PAST WEEK
- Outlook: The COMING week (Monday-Friday)
- Focus: US equities, major indices (SPY/QQQ), key sectors, rates/volatility

SECTION STRUCTURE (Use exact H2 headers)

## 📊 Week in Review - The Big Picture
Start with 2-3 paragraphs capturing the overall market narrative:
- What was the dominant theme? (Risk-on/off, rotation, consolidation, breakout, etc.)
- Major index moves (SPY, QQQ) with % changes and key levels tested
- What drove the moves? (Economic data, Fed speak, earnings, geopolitics, flows)
- Volatility regime: VIX behavior, term structure, put/call ratios
- Sector rotation: What led, what lagged, and why

## 🎯 Major Trade Moves & Market Movers
Highlight 5-8 significant individual moves or sector themes:
- Use this format for each: **TICKER/SECTOR** — Brief catalyst + % move + what it means
- Focus on: Large caps that moved >3-5%, sector ETFs, notable options activity
- Include: Earnings surprises, analyst upgrades/downgrades, macro catalysts
- Why traders should care: Liquidity, follow-through potential, cross-asset implications

## 📰 Key Headlines That Moved Markets  
List 5-8 major news items from the past week that had market impact:
### [Headline - keep it concise and specific]
2-3 sentences on what happened and why it matters for traders. Connect to price action 
when possible (e.g., "Treasury yields spiked 15bps on hot CPI, pressuring growth names").

## 📅 Week Ahead - Calendar & Catalysts
Break down upcoming events by category:

**Economic Data** (List with day/time if available)
- Key reports with consensus estimates and what they mean
- Why each matters: Rate expectations, growth trajectory, sentiment
- Which assets/sectors are most sensitive

**Earnings Releases** (Top 5-10 most significant)
- Major names reporting with expected impact
- Sector implications from bellwether reports
- Key metrics traders will watch

**Fed/Policy Events**
- FOMC meetings, speeches, policy announcements
- Expected impact on rates, volatility, positioning

**Other Catalysts**
- Options expiration, rebalancing, technical levels, seasonality

## 🔬 Technical Setup & Key Levels
Analyze SPY and QQQ from a swing trader perspective:

**SPY Analysis**
- Current price and weekly trend (consolidation, breakout, breakdown)
- Critical support levels: [List only levels present in the payload; explain them as VIX-implied sigma bands when applicable (+/-1sigma, +/-2sigma, +3sigma). Do NOT cite indicators not provided.]
- Resistance levels: [List only levels present in the payload; same rule as above — no invented chart reasons.]
- Momentum indicators and what they signal
- Expected trading range for the week

**QQQ Analysis**  
- Same structure as SPY
- Note any divergence vs SPY
- Tech sector sensitivity to upcoming events

## 📈 Trader's Playbook - Positioning for the Week
Provide 4-6 scenario-based trade setups:

Format each as:
**If/Then Scenario:** If [specific condition/level/event], then [expected market behavior],
with [key risk level to watch].
**Time horizon:** [Intraday scalp / 2-5 day swing / Week+ hold]
**Rationale:** [Why this setup makes sense given current context]

Use the actual levels from this week's data in the payload above. Do NOT invent
placeholder levels or prices — only reference numbers that appear in the data you
were given.

Do NOT invent reasons for why a level is \"key\" (no moving averages, VWAP, prior highs/lows, Fibonacci, etc.) unless those specific facts are explicitly present in the payload. If you need to justify, justify only via the provided sigma-band methodology / probabilities.

## 💭 Market Sentiment & Risk Assessment
Final paragraph (3-5 sentences) synthesizing:
- Overall market positioning (crowded trades, sentiment extremes)
- Key risks for the week ahead (geopolitical, data misses, technical breakdowns)
- Volatility expectations and hedging considerations
- One key theme or level to anchor the week's trading

WRITING GUIDELINES
- Write in clear, professional English - no jargon without explanation
- Use specific numbers: prices, percentages, levels, times
- Be precise with levels and dates - no vague references
- Keep paragraphs tight (3-5 sentences max)
- Use bold for tickers/levels on FIRST mention only
- If data is missing, acknowledge it briefly - don't invent

DATA DISCIPLINE
- Use ONLY information provided in the user prompt
- If a section lacks data, state "Data not available" and move on
- Never fabricate levels, estimates, or events
- Cite timeframes in US Eastern Time
"""

# ===== ENHANCED WEEKLY USER TEMPLATE =====
WEEKLY_USER_TEMPLATE_ENHANCED = """
WEEK OF: {week_of_str}
Current Date: {current_date}

═══════════════════════════════════════════════════════════
📊 WEEKLY MARKET PERFORMANCE (Mon-Fri: {week_mon} to {week_fri})
═══════════════════════════════════════════════════════════

MAJOR INDICES - Weekly Performance:
{index_recap}

SECTOR ROTATION - Leaders & Laggards:
{weekly_movers}

VOLATILITY & SENTIMENT:
{volatility_data}

═══════════════════════════════════════════════════════════
📰 MAJOR NEWS & MARKET-MOVING EVENTS
═══════════════════════════════════════════════════════════
{weekly_headlines}

═══════════════════════════════════════════════════════════
📅 WEEK AHEAD - What to Watch
═══════════════════════════════════════════════════════════

ECONOMIC DATA RELEASES:
{economic_calendar}

EARNINGS REPORTS:
{earnings_calendar}

FED/POLICY EVENTS:
{policy_events}

OTHER CATALYSTS:
{other_catalysts}

═══════════════════════════════════════════════════════════
🔬 TECHNICAL LEVELS FOR SWING TRADING
═══════════════════════════════════════════════════════════

SPY LEVELS:
{spy_levels}

QQQ LEVELS:
{qqq_levels}

═══════════════════════════════════════════════════════════
🎯 WEEKLY RECAP GENERATION
═══════════════════════════════════════════════════════════

Based on the comprehensive market data above, create a professional weekly market recap 
in the style of Investopedia or Bloomberg market summaries.

CRITICAL REQUIREMENTS:

1. **Opening Headline** (Investopedia-style):
   - Example: "Stocks Wrap Up a Down Week on a High Note; Dow Closes Up Nearly 500 Points; NY Fed Chief Signals Support for Rate Cut"
   - Must include: Overall week direction, specific point/percentage moves, major catalyst
   - Be specific with numbers (e.g., "Dow up 487 points" not "Dow higher")

2. **Week in Review Section** (2-3 detailed paragraphs):
   - Paragraph 1: Overall market performance with specific index moves
   - Paragraph 2: What drove the market (economic data, news catalysts, Fed developments)
   - Paragraph 3: Sector rotation, winners/losers, breadth
   - If Friday diverged from week: Add note about Friday's session

3. **Major Trade Moves** (5-8 items):
   - Focus on what actually moved THIS WEEK
   - Include specific catalysts from the news
   - Actual percentage moves from sector data

4. **Key Headlines** (5-8 items):
   - Use ACTUAL headlines from the weekly news feed
   - Explain market impact of each headline
   - Connect to price action

Continue with remaining sections as specified in system prompt.

IMPORTANT: Use REAL DATA from above. Don't invent numbers or events.

SECTION_UNAVAILABLE HANDLING:
If any payload field (e.g. economic_calendar, earnings_calendar, policy_events)
starts with "SECTION_UNAVAILABLE:", completely OMIT that subsection and its
header from the final output. Do not mention the data is missing, do not
hallucinate a replacement. Simply skip that block and continue with the next
available section.
"""
# ===== END ENHANCED WEEKLY PROMPTS =====

# ===== Daily history + pivot helpers =====
def _tradier_history_daily(symbol: str, start_d: date, end_d: date) -> list[dict]:
    """Daily OHLCV history via providers.DataProvider, returned in the
    legacy Tradier-shaped schema (`date`, `open`, `high`, `low`, `close`,
    `volume`) expected by downstream callers.
    """
    try:
        bars = get_default_provider().get_daily_bars(
            symbol, start_d.isoformat(), end_d.isoformat(), limit=5000
        )
    except Exception as exc:
        logger.exception(f"_tradier_history_daily failed for {symbol}: {exc}")
        return []
    out = []
    for b in bars or []:
        ts = b.get("timestamp") or ""
        out.append(
            {
                "date": ts[:10] if ts else "",
                "open": b.get("open"),
                "high": b.get("high"),
                "low": b.get("low"),
                "close": b.get("close"),
                "volume": b.get("volume") or 0,
            }
        )
    return out


def fetch_comprehensive_weekly_market_data(week_mon: date, week_fri: date) -> dict:
    """
    Fetch comprehensive market data for the weekly recap.
    Returns detailed performance data with specific point moves, percentages, and context.

    Args:
        week_mon: Monday of the week to analyze
        week_fri: Friday of the week to analyze

    Returns:
        Dictionary with comprehensive market data
    """
    market_data: dict[str, Any] = {
        "indices": {},
        "sectors": {},
        "volatility": {},
        "breadth": {},
        "notable_movers": [],
    }

    # =========================================================================
    # MAJOR INDICES - Get detailed data
    # =========================================================================
    indices = {
        "SPY": "S&P 500",
        "QQQ": "Nasdaq 100",
        "DIA": "Dow Jones",
        "IWM": "Russell 2000",
    }

    for ticker, name in indices.items():
        try:
            hist = _tradier_history_daily(ticker, week_mon, week_fri)
            if hist and len(hist) >= 2:
                week_open = float(hist[0]["open"])
                week_close = float(hist[-1]["close"])
                week_high = max(float(d["high"]) for d in hist)
                week_low = min(float(d["low"]) for d in hist)

                # Calculate moves
                point_change = week_close - week_open
                pct_change = (point_change / week_open) * 100 if week_open else 0.0

                # Determine trend
                if pct_change > 2:
                    trend = "strong rally"
                elif pct_change > 0.5:
                    trend = "modest gains"
                elif pct_change > -0.5:
                    trend = "essentially flat"
                elif pct_change > -2:
                    trend = "modest decline"
                else:
                    trend = "sharp selloff"

                # Friday session move
                friday_close = float(hist[-1]["close"])
                friday_open = float(hist[-1]["open"])
                friday_change = (
                    ((friday_close - friday_open) / friday_open) * 100
                    if friday_open
                    else 0.0
                )

                market_data["indices"][ticker] = {
                    "name": name,
                    "week_open": week_open,
                    "week_close": week_close,
                    "week_high": week_high,
                    "week_low": week_low,
                    "point_change": point_change,
                    "pct_change": pct_change,
                    "trend": trend,
                    "friday_pct": friday_change,
                    "range": f"${week_low:.2f} - ${week_high:.2f}",
                }

        except Exception as e:
            logger.warning(f"Error fetching {ticker} data: {e}")

    # =========================================================================
    # SECTOR PERFORMANCE - Detailed analysis
    # =========================================================================
    sectors = {
        "XLK": "Technology",
        "XLF": "Financials",
        "XLE": "Energy",
        "XLV": "Healthcare",
        "XLY": "Consumer Discretionary",
        "XLP": "Consumer Staples",
        "XLI": "Industrials",
        "XLB": "Materials",
        "XLRE": "Real Estate",
        "XLU": "Utilities",
        "XLC": "Communication Services",
    }

    sector_performance: list[dict[str, Any]] = []
    for ticker, name in sectors.items():
        try:
            hist = _tradier_history_daily(ticker, week_mon, week_fri)
            if hist and len(hist) >= 2:
                week_open = float(hist[0]["open"])
                week_close = float(hist[-1]["close"])
                pct_change = (
                    ((week_close - week_open) / week_open) * 100 if week_open else 0.0
                )

                sector_performance.append(
                    {
                        "ticker": ticker,
                        "name": name,
                        "pct_change": pct_change,
                        "close": week_close,
                    }
                )
        except Exception as e:
            logger.warning(f"Error fetching {ticker} sector data: {e}")

    # Sort by performance
    sector_performance.sort(key=lambda x: x["pct_change"], reverse=True)
    market_data["sectors"] = sector_performance

    # =========================================================================
    # VOLATILITY METRICS
    # =========================================================================
    try:
        vix_hist = _tradier_history_daily("VIX", week_mon, week_fri)
        if vix_hist and len(vix_hist) >= 2:
            vix_start = float(vix_hist[0]["close"])
            vix_end = float(vix_hist[-1]["close"])
            vix_high = max(float(d["high"]) for d in vix_hist)
            vix_low = min(float(d["low"]) for d in vix_hist)

            market_data["volatility"] = {
                "vix_start": vix_start,
                "vix_end": vix_end,
                "vix_change": vix_end - vix_start,
                "vix_high": vix_high,
                "vix_low": vix_low,
                "regime": "low"
                if vix_end < 15
                else "elevated"
                if vix_end < 20
                else "high",
            }
    except Exception as e:
        logger.warning(f"Error fetching VIX data: {e}")

    # =========================================================================
    # MARKET BREADTH (placeholder; requires separate API)
    # =========================================================================
    market_data["breadth"] = {
        "note": "Breadth data requires additional API integration",
    }

    return market_data


def format_weekly_recap_headline(market_data: dict, major_news: list) -> str:
    """
    Generate an Investopedia-style headline for the weekly recap.

    Args:
        market_data: Comprehensive market data dictionary
        major_news: List of major news items from the week

    Returns:
        Formatted headline string
    """
    # Get primary index (SPY)
    spy = (market_data.get("indices") or {}).get("SPY", {})

    if not spy:
        return "Weekly Market Recap"

    # Determine overall week direction
    pct = spy.get("pct_change", 0.0) or 0.0
    friday_pct = spy.get("friday_pct", 0.0) or 0.0

    # Build headline components
    components: list[str] = []

    # Overall week context
    if abs(pct) < 0.3:
        week_desc = "Stocks Finish Week Essentially Flat"
    elif pct > 0:
        if pct > 2:
            week_desc = f"Stocks Rally {pct:.1f}% for the Week"
        else:
            week_desc = f"Stocks Edge Higher, Up {pct:.1f}% for Week"
    else:
        if pct < -2:
            week_desc = f"Stocks Tumble {abs(pct):.1f}% for the Week"
        else:
            week_desc = f"Stocks Decline {abs(pct):.1f}% for Week"

    components.append(week_desc)

    # Friday divergence (if significant)
    if (pct < -1 and friday_pct > 1) or (pct > 1 and friday_pct < -1):
        if pct < 0 and friday_pct > 0:
            components.append("But Rally Friday")
        elif pct > 0 and friday_pct < 0:
            components.append("Despite Friday Selloff")

    # Add major index point moves
    indices_desc: list[str] = []
    for ticker in ["SPY", "DIA", "QQQ"]:
        idx = (market_data.get("indices") or {}).get(ticker, {})
        if idx and abs(idx.get("pct_change", 0.0) or 0.0) > 0.5:
            name = idx.get("name", ticker)
            pct_chg = idx.get("pct_change", 0.0) or 0.0
            point_chg = idx.get("point_change", 0.0) or 0.0

            # Format based on magnitude
            if abs(point_chg) > 10:  # Significant point move
                direction = "Up" if point_chg > 0 else "Down"
                indices_desc.append(f"{name} {direction} {abs(point_chg):.0f} Points")

    if indices_desc:
        components.append("; ".join(indices_desc[:2]))  # Max 2 index callouts

    # Add top news catalyst if available
    if major_news:
        top_news = major_news[0]
        headline = top_news.get("headline", "") or ""

        # Extract key phrase (first 60 chars or to first semicolon/colon)
        if headline:
            key_phrase = headline.split(";")[0].split(":")[0]
            if len(key_phrase) > 60:
                key_phrase = key_phrase[:60] + "..."
            components.append(key_phrase)

    return "; ".join(components)


def fetch_week_major_news(week_mon: date, week_fri: date) -> list[dict]:
    """Fetch major market-moving news for the week via providers.DataProvider.

    Aggregates news for a curated list of market-bellwether tickers
    (index ETFs, mega-caps, rates/vol ETFs) so we get a broad macro read
    without any Finnhub dependency.

    Args:
        week_mon: Monday of week
        week_fri: Friday of week

    Returns:
        List of normalized news items: {headline, summary, source, url,
        timestamp, related}.
    """
    cache_key = f"news:week:{week_mon.isoformat()}"
    cached = _cache_get_json(cache_key, 14400)
    if cached is not None:
        return cached

    dp = get_default_provider()
    tickers = ["SPY", "QQQ", "DIA", "IWM", "AAPL", "MSFT", "NVDA", "TLT", "VIXY"]
    market_keywords = [
        "fed", "fomc", "powell", "rate", "inflation", "cpi", "ppi", "gdp",
        "employment", "jobs", "payroll", "earnings", "market", "stocks",
        "dow", "nasdaq", "s&p", "treasury", "yield", "recession", "economy",
        "trade", "tariff", "central bank",
    ]

    week_start_ts = int(datetime.combine(week_mon, dt_time.min).timestamp())
    week_end_ts = int(datetime.combine(week_fri, dt_time(23, 59, 59)).timestamp())

    seen_urls: set[str] = set()
    filtered: list[dict[str, Any]] = []

    for tkr in tickers:
        try:
            items = dp.get_news(tkr, limit=20) or []
        except Exception as exc:
            logger.debug(f"get_news failed for {tkr}: {exc}")
            continue
        for it in items:
            url = it.get("url") or ""
            if url and url in seen_urls:
                continue
            pub = it.get("published") or ""
            try:
                ts = int(
                    datetime.strptime(pub.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                    .timestamp()
                )
            except Exception:
                ts = 0
            if not (week_start_ts <= ts <= week_end_ts):
                continue
            title_l = (it.get("title") or "").lower()
            if not any(k in title_l for k in market_keywords):
                continue
            seen_urls.add(url)
            filtered.append(
                {
                    "headline": it.get("title") or "",
                    "summary": it.get("description") or "",
                    "source": it.get("source") or "",
                    "url": url,
                    "timestamp": ts,
                    "related": tkr,
                }
            )

    filtered.sort(key=lambda x: x["timestamp"], reverse=True)
    top = filtered[:15]
    if top:
        _cache_put_json(cache_key, top)
    logger.info(f"Found {len(top)} major news items for week")
    return top


def generate_week_in_review_narrative(
    market_data: dict, news_items: list, econ_events: list | None = None
) -> str:
    """
    Generate a comprehensive narrative of the week's market action.
    Investopedia-style with specific numbers and context.

    Args:
        market_data: Comprehensive market data from fetch_comprehensive_weekly_market_data
        news_items: Major news from fetch_week_major_news
        econ_events: Economic events that occurred (optional)

    Returns:
        Formatted narrative string
    """
    narrative_parts: list[str] = []

    # =========================================================================
    # OPENING PARAGRAPH - Overall market performance
    # =========================================================================
    indices = market_data.get("indices") or {}
    spy = indices.get("SPY", {})
    qqq = indices.get("QQQ", {})
    dia = indices.get("DIA", {})

    if spy:
        pct = spy.get("pct_change", 0.0) or 0.0
        trend = spy.get("trend", "mixed trade")

        # Opening sentence
        if pct > 0:
            opener = f"U.S. stocks posted {trend} for the week, "
        else:
            opener = f"U.S. stocks finished with {trend} for the week, "

        # Add specific index performance
        index_details: list[str] = []
        index_details.append(
            "with the S&P 500 "
            f"{'gaining' if pct > 0 else 'losing'} "
            f"{abs(pct):.1f}% to close at {spy.get('week_close', 0.0):.2f}"
        )

        if dia:
            dia_pct = dia.get("pct_change", 0.0) or 0.0
            point_chg = dia.get("point_change", 0.0) or 0.0
            index_details.append(
                "the Dow Jones Industrial Average "
                f"{'advancing' if dia_pct > 0 else 'declining'} "
                f"{abs(point_chg):.0f} points ({abs(dia_pct):.1f}%) "
                f"to {dia.get('week_close', 0.0):.2f}"
            )

        if qqq:
            qqq_pct = qqq.get("pct_change", 0.0) or 0.0
            index_details.append(
                "and the Nasdaq 100 "
                f"{'rising' if qqq_pct > 0 else 'falling'} "
                f"{abs(qqq_pct):.1f}% to {qqq.get('week_close', 0.0):.2f}"
            )

        narrative_parts.append(opener + ", ".join(index_details) + ".")

    # =========================================================================
    # PARAGRAPH 2 - What drove the market
    # =========================================================================
    drivers: list[str] = []

    # Economic data impact
    if econ_events:
        high_impact = [e for e in econ_events if e.get("impact") == "HIGH"]
        if high_impact:
            event_names = [e.get("event", "") for e in high_impact[:2] if e.get("event")]
            if event_names:
                drivers.append(
                    "economic data including " + " and ".join(event_names)
                )

    # Major news catalysts
    if news_items:
        top_news = news_items[:3]
        news_themes: list[str] = []

        for item in top_news:
            headline = (item.get("headline", "") or "").lower()
            if "fed" in headline or "rate" in headline:
                news_themes.append("Federal Reserve policy signals")
            elif "earnings" in headline:
                news_themes.append("corporate earnings reports")
            elif "inflation" in headline or "cpi" in headline:
                news_themes.append("inflation data")
            elif "employment" in headline or "jobs" in headline or "payroll" in headline:
                news_themes.append("labor market developments")

        if news_themes:
            # Deduplicate while preserving order
            unique_themes = list(dict.fromkeys(news_themes))
            drivers.append(" and ".join(unique_themes[:2]))

    # Volatility context
    vol = market_data.get("volatility") or {}
    if vol:
        vix_change = vol.get("vix_change", 0.0) or 0.0
        if abs(vix_change) > 2:
            direction = "jumped" if vix_change > 0 else "fell"
            drivers.append(
                f"with volatility {direction} as the VIX "
                f"{'rose' if vix_change > 0 else 'declined'} "
                f"{abs(vix_change):.1f} points to {vol.get('vix_end', 0.0):.1f}"
            )

    if drivers:
        if len(drivers) == 1:
            driver_text = f"The week's trading was influenced by {drivers[0]}."
        else:
            driver_text = (
                "The week's trading was influenced by "
                f"{', '.join(drivers[:-1])} and {drivers[-1]}."
            )
        narrative_parts.append(driver_text)

    # =========================================================================
    # PARAGRAPH 3 - Sector rotation and leadership
    # =========================================================================
    sectors = market_data.get("sectors") or []
    if isinstance(sectors, list) and len(sectors) >= 6:
        leaders = sectors[:3]
        laggards = sectors[-3:]

        leader_text = ", ".join(
            f"{s['name']} ({s['pct_change']:+.1f}%)" for s in leaders
        )
        laggard_text = ", ".join(
            f"{s['name']} ({s['pct_change']:+.1f}%)" for s in laggards
        )

        rotation_text = (
            f"Sector rotation showed {leaders[0]['name']} leading the market, "
            f"followed by {leader_text}. "
            f"On the downside, {laggards[-1]['name']} lagged, along with {laggard_text}."
        )

        narrative_parts.append(rotation_text)

    # =========================================================================
    # PARAGRAPH 4 - Friday's action (if divergent from week)
    # =========================================================================
    if spy:
        week_pct = spy.get("pct_change", 0.0) or 0.0
        friday_pct = spy.get("friday_pct", 0.0) or 0.0

        if (week_pct < -1 and friday_pct > 1) or (week_pct > 1 and friday_pct < -1):
            if week_pct < 0 and friday_pct > 1:
                friday_text = (
                    "Despite the weekly decline, stocks rallied strongly on Friday, "
                    f"with the S&P 500 gaining {friday_pct:.1f}% in a broad-based "
                    "recovery that helped trim weekly losses."
                )
            else:
                friday_text = (
                    "Friday's session saw profit-taking erase some of the week's gains, "
                    f"with the S&P 500 declining {abs(friday_pct):.1f}% "
                    "as investors locked in gains."
                )

            narrative_parts.append(friday_text)

    return "\n\n".join(narrative_parts)

def _pivot_levels_from_hlc(high: float, low: float, close: float) -> dict:
    P = (high + low + close) / 3.0
    R1 = 2*P - low
    R2 = P + (high - low)
    S1 = 2*P - high
    S2 = P - (high - low)
    return {"P": P, "R1": R1, "R2": R2, "S1": S1, "S2": S2}

def _last_completed_session_dates(now: datetime) -> tuple[date, date]:
    d = now.astimezone(NY).date()
    prev = d - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    weekday = d.weekday()
    last_week_end = d - timedelta(days=weekday+1)
    last_week_start = last_week_end - timedelta(days=6)
    last_mon = last_week_start + timedelta(days=(0 if last_week_start.weekday()==0 else (7-last_week_start.weekday())))
    last_fri = last_mon + timedelta(days=4)
    return (prev, last_fri)

def _compute_daily_weekly_levels(symbol: str, now: Optional[datetime] = None) -> dict:
    now = now or _now_ny()
    prev_day, last_fri = _last_completed_session_dates(now)
    last_mon = last_fri - timedelta(days=4)

    d_hist = _tradier_history_daily(symbol, prev_day - timedelta(days=1), prev_day)
    d_bar = d_hist[-1] if d_hist else None

    w_hist = _tradier_history_daily(symbol, last_mon, last_fri)
    if w_hist:
        w_high = max(float(x["high"]) for x in w_hist)
        w_low = min(float(x["low"]) for x in w_hist)
        w_close = float(w_hist[-1]["close"])
        w_piv = _pivot_levels_from_hlc(w_high, w_low, w_close)
    else:
        w_piv = None

    res = {
        "daily_resistances": None, "weekly_resistances": None,
        "daily_supports": None, "weekly_supports": None
    }
    if d_bar:
        d_piv = _pivot_levels_from_hlc(float(d_bar["high"]), float(d_bar["low"]), float(d_bar["close"]))
        res["daily_resistances"] = [d_piv["R1"], d_piv["R2"]]
        res["daily_supports"]    = [d_piv["S1"], d_piv["S2"]]
    if w_piv:
        res["weekly_resistances"] = [w_piv["R1"], w_piv["R2"]]
        res["weekly_supports"]    = [w_piv["S1"], w_piv["S2"]]
    return res

def enrich_expected_range_with_pivots(expected_range: dict) -> dict:
    out = dict(expected_range or {})
    for key, sym in (("spy","SPY"), ("qqq","QQQ")):
        try:
            piv = _compute_daily_weekly_levels(sym)
            sec = out.get(key, {}) if isinstance(out.get(key), dict) else {}
            for fld in ("daily_resistances","weekly_resistances","daily_supports","weekly_supports"):
                if piv.get(fld):
                    sec[fld] = [round(x, 2) for x in piv[fld]]
            out[key] = sec
        except Exception as e:
            logger.warning(f"Pivot enrichment failed for {sym}: {e}")
    return out

def _render_brief_user_prompt(headlines: list[dict], expected_range: dict, gapping_stocks: Any) -> str:
    date_str = _now_ny().strftime('%A, %B %d, %Y')

    # Build SPOT/RANGE lines
    lines = []
    for tk in ("spy", "qqq"):
        sec = expected_range.get(tk, {}) if isinstance(expected_range, dict) else {}
        px = sec.get("current_price")
        sup = sec.get("support")
        res = sec.get("resistance")
        if isinstance(px, (int, float)):
            lines.append(f"{tk.upper()}: ${px:.2f} (Support: ${sup or 0:.2f}, Resistance: ${res or 0:.2f})")
    range_text = "\n".join(lines) if lines else "No data provided"

    # VIX line
    vix = expected_range.get('vix', {}) if isinstance(expected_range, dict) else {}
    vix_val = vix.get('current_price')
    vix_text = f"VIX: {vix_val:.2f}" if isinstance(vix_val, (int, float)) else "No data provided"

    # Levels methodology (source-of-truth for why these are "key levels")
    levels_methodology_text = "No data provided"
    try:
        spy = expected_range.get("spy", {}) if isinstance(expected_range, dict) else {}
        spy_px = spy.get("current_price")
        spy_sigma = spy.get("sigma")
        spy_sigma_pct = spy.get("sigma_pct")
        if isinstance(vix_val, (int, float)) and isinstance(spy_px, (int, float)) and isinstance(spy_sigma, (int, float)) and spy_sigma > 0:
            if not isinstance(spy_sigma_pct, (int, float)) or spy_sigma_pct <= 0:
                spy_sigma_pct = (float(spy_sigma) / float(spy_px)) * 100.0
            levels_methodology_text = (
                f"These levels come from the VIX (market 'fear gauge'). "
                f"With VIX at {float(vix_val):.1f}, SPY typically moves about +/-${float(spy_sigma):.2f} in a day "
                f"({float(spy_sigma_pct):.2f}%). "
                f"S1/R1 mark that usual range, S2/R2 are a wider range, and R3 is an extreme upside move. "
                f"(QQQ and IWM are scaled versions of SPY.)"
            )
    except Exception:
        levels_methodology_text = "No data provided"

    # Gapping text (AH & Premarket)
    gapping_text = ""
    if gapping_stocks:
        if isinstance(gapping_stocks, dict):
            ah_moves = gapping_stocks.get("after_hours", [])
            pre_moves = gapping_stocks.get("premarket", [])
            if ah_moves:
                gapping_text += "After-hours Movers:\n"
                for stock in ah_moves[:5]:
                    gapping_text += f"- {stock.get('ticker','')}: {stock.get('move','')} - {stock.get('why','')}\n"
                gapping_text += "\n"
            if pre_moves:
                gapping_text += "Premarket Movers:\n"
                for stock in pre_moves[:5]:
                    gapping_text += f"- {stock.get('ticker','')}: {stock.get('move','')} - {stock.get('why','')}\n"
                gapping_text += "\n"
        else:
            for stock in gapping_stocks[:5]:
                gapping_text += f"- {stock.get('ticker','')}: {stock.get('gap_pct',0):+.2f}% (${stock.get('current_price',0):.2f} vs ${stock.get('prev_close',0):.2f})\n"
    if not gapping_text:
        gapping_text = "No data provided"

    # Headlines list
    headlines_text = ""
    for it in (headlines or [])[:10]:
        title = it.get('headline', '')
        summary = (it.get('summary_2to5') or it.get('summary') or '').strip()
        headlines_text += f"- {title}\n  Summary: {summary}\n\n"
    headlines_text = headlines_text.strip() or "No data provided"

    # Build KEY LEVELS FEED (daily/weekly S & R for SPY/QQQ if available)
    def _pair(x):
        return f"{x[0]:.2f} / {x[1]:.2f}" if (isinstance(x, list) and len(x) >= 2) else "No data"

    def _fmt_sr(sec: dict, label: str) -> str:
        if not isinstance(sec, dict):
            return f"{label}: No data provided"
        ds = sec.get("daily_supports");  dr = sec.get("daily_resistances")
        ws = sec.get("weekly_supports"); wr = sec.get("weekly_resistances")
        return f"{label} — Daily S: {_pair(ds)}; R: {_pair(dr)}; Weekly S: {_pair(ws)}; R: {_pair(wr)}"

    key_levels_lines = []
    key_levels_lines.append(_fmt_sr(expected_range.get("spy", {}), "SPY"))
    key_levels_lines.append(_fmt_sr(expected_range.get("qqq", {}), "QQQ"))
    key_levels_feed = "\n".join(key_levels_lines)

    return BRIEF_USER_TEMPLATE.format(
        date_str=date_str,
        range_text=range_text,
        vix_text=vix_text,
        levels_methodology_text=levels_methodology_text,
        gapping_text=gapping_text,
        headlines_text=headlines_text,
        key_levels_feed=key_levels_feed,
    )

def _compose_weekly_inputs() -> tuple[str, str, str, str]:
    """
    Build the strings for WEEKLY_USER_TEMPLATE:
      index_recap, weekly_headlines, week_ahead, weekly_levels
    NOTE: Use existing utilities where possible; keep formatting plain text / bullets.
    """
    now = datetime.now(tz=NY)
    week_mon, week_fri = _last_completed_week_range(now)

    # 1) Index recap (pull daily history and summarize SPY/QQQ + sectors if available)
    try:
        pivots_spy = _compute_daily_weekly_levels("SPY", now)
        pivots_qqq = _compute_daily_weekly_levels("QQQ", now)
    except Exception:
        pivots_spy = pivots_qqq = {}

    index_lines = []
    try:
        spy_hist = _tradier_history_daily("SPY", week_mon, week_fri)
        qqq_hist = _tradier_history_daily("QQQ", week_mon, week_fri)
        def _pct(a,b):
            return (float(a)-float(b))/float(b)*100 if (a is not None and b and float(b)!=0) else 0.0
        if spy_hist:
            spy_open = float(spy_hist[0]["close"])
            spy_close = float(spy_hist[-1]["close"])
            index_lines.append(f"SPY: {spy_close:.2f} (wk { _pct(spy_close, spy_open):+.2f}% )")
        if qqq_hist:
            qqq_open = float(qqq_hist[0]["close"])
            qqq_close = float(qqq_hist[-1]["close"])
            index_lines.append(f"QQQ: {qqq_close:.2f} (wk { _pct(qqq_close, qqq_open):+.2f}% )")
    except Exception:
        pass
    index_recap = "\n".join(index_lines) or "No data provided"

    # 2) Weekly headlines: reuse fetch; if unavailable, use empty
    try:
        headlines = []
    except Exception:
        headlines = []
    wh_lines = []
    for i, h in enumerate(headlines[:10], 1):
        title = h.get("headline","No headline")
        summ = (h.get("summary_2to5") or h.get("summary") or "").strip()
        wh_lines.append(f"{i}. {title}\n   {summ}")
    weekly_headlines = "\n".join(wh_lines) or "No data provided"

    # 3) Week ahead — earnings/macro calendars are unavailable on the current
    # data tier. Signal to GPT that it should omit the section rather than
    # invent data.
    week_ahead = (
        "SECTION_UNAVAILABLE: Week-ahead macro and earnings calendars are not "
        "provided by the current data tier. Omit the Week Ahead section from "
        "the final brief."
    )

    # 4) Weekly levels
    def _fmt_levels(levels: dict, label: str) -> str:
        if not isinstance(levels, dict): return f"{label}: No data"
        ws = levels.get("weekly_supports"); wr = levels.get("weekly_resistances")
        def _pair(x):
            return f"{x[0]:.2f}/{x[1]:.2f}" if isinstance(x, list) and len(x)>=2 else "No data"
        return f"{label} — Weekly S: {_pair(ws)}; R: {_pair(wr)}"

    weekly_levels = "\n".join([
        _fmt_levels(pivots_spy, "SPY"),
        _fmt_levels(pivots_qqq, "QQQ"),
    ])

    return index_recap, weekly_headlines, week_ahead, weekly_levels

def _compose_enhanced_weekly_inputs() -> dict:
    """
    Enhanced version of _compose_weekly_inputs() that gathers comprehensive data.
    Returns a dictionary with all required fields for the enhanced template.
    """
    now = datetime.now(tz=NY)
    week_mon, week_fri = _last_completed_week_range(now)
    
    # Calculate dates
    week_of_str = f"Week of {week_mon.strftime('%B %d, %Y')}"
    current_date = now.strftime('%A, %B %d, %Y')
    week_mon_str = week_mon.strftime('%B %d')
    week_fri_str = week_fri.strftime('%B %d')
    
    data: dict[str, Any] = {
        "week_of_str": week_of_str,
        "current_date": current_date,
        "week_mon": week_mon_str,
        "week_fri": week_fri_str,
    }

    # 1. INDEX PERFORMANCE & TECHNICALS - ENHANCED WITH COMPREHENSIVE DATA
    try:
        # Get comprehensive market data
        comprehensive_data = fetch_comprehensive_weekly_market_data(week_mon, week_fri)

        # Format index data
        index_lines: list[str] = []
        for ticker in ["SPY", "QQQ", "DIA", "IWM"]:
            idx = (comprehensive_data.get("indices") or {}).get(ticker, {})
            if idx:
                name = idx["name"]
                close = idx["week_close"]
                pct = idx["pct_change"]
                point = idx["point_change"]
                range_str = idx["range"]
                trend = idx["trend"]

                index_lines.append(f"{name} ({ticker}): ${close:.2f}")
                index_lines.append(
                    f"  Week: {pct:+.1f}% ({point:+.2f} points) | Range: {range_str}"
                )
                index_lines.append(f"  Trend: {trend}\n")

        data["index_recap"] = (
            "\n".join(index_lines) if index_lines else "Index data unavailable"
        )

        # Store comprehensive data for later use (sectors, volatility, headlines, narrative)
        data["_market_data"] = comprehensive_data

    except Exception as e:
        logger.warning(f"Error fetching comprehensive market data: {e}")
        data["index_recap"] = "Index data unavailable"
        data["_market_data"] = {}

    # 2. VOLATILITY & SENTIMENT (using comprehensive data if available)
    vol_lines: list[str] = []
    market_data = data.get("_market_data") or {}
    vol = (market_data.get("volatility") or {}) if isinstance(market_data, dict) else {}
    try:
        if vol:
            vix_start = vol.get("vix_start")
            vix_end = vol.get("vix_end")
            vix_change = vol.get("vix_change")
            vix_high = vol.get("vix_high")
            vix_low = vol.get("vix_low")
            regime = vol.get("regime", "unknown")

            if all(
                isinstance(x, (int, float))
                for x in (vix_start, vix_end, vix_change, vix_high, vix_low)
            ):
                vol_lines.append(
                    f"VIX: {vix_start:.2f} → {vix_end:.2f} ({vix_change:+.2f})"
                )
                vol_lines.append(
                    f"  Weekly Range: {vix_low:.2f} - {vix_high:.2f} | Regime: {regime} volatility"
                )
        if not vol_lines:
            vol_lines.append("Volatility data unavailable")
    except Exception as e:
        logger.warning(f"Error formatting volatility data: {e}")
        vol_lines = ["Volatility data unavailable"]

    data["volatility_data"] = (
        "\n".join(vol_lines) if vol_lines else "No data available"
    )

    # 3. WEEKLY MOVERS - NOW WITH ACTUAL DATA (sector leaders/laggards)
    try:
        comprehensive_data = data.get("_market_data") or {}
        sectors = comprehensive_data.get("sectors", [])

        if isinstance(sectors, list) and len(sectors) >= 6:
            movers_lines: list[str] = []
            movers_lines.append("SECTOR LEADERS:")
            for sector in sectors[:3]:
                movers_lines.append(
                    f"  {sector['name']} ({sector['ticker']}): "
                    f"{sector['pct_change']:+.1f}%"
                )

            movers_lines.append("\nSECTOR LAGGARDS:")
            for sector in sectors[-3:]:
                movers_lines.append(
                    f"  {sector['name']} ({sector['ticker']}): "
                    f"{sector['pct_change']:+.1f}%"
                )

            data["weekly_movers"] = "\n".join(movers_lines)
        else:
            data["weekly_movers"] = "Sector performance data unavailable"

    except Exception as e:
        logger.warning(f"Error formatting weekly movers: {e}")
        data["weekly_movers"] = "Sector performance data unavailable"

    # 4. KEY HEADLINES - NOW WITH ACTUAL WEEKLY NEWS
    headlines_lines: list[str] = []
    try:
        major_news = fetch_week_major_news(week_mon, week_fri)

        if major_news:
            headlines_lines.append("Major market-moving news from the week:\n")

            for i, news_item in enumerate(major_news[:10], 1):
                headline = news_item.get("headline", "No title")
                summary = news_item.get("summary", "") or ""
                source = news_item.get("source", "Unknown")

                headlines_lines.append(f"{i}. {headline}")
                if summary:
                    summary_short = (
                        summary[:200] + "..." if len(summary) > 200 else summary
                    )
                    headlines_lines.append(f"   {summary_short}")
                headlines_lines.append(f"   Source: {source}\n")

        data["weekly_headlines"] = (
            "\n".join(headlines_lines)
            if headlines_lines
            else "No major news items found for the week"
        )

        # Keep major_news in data for potential downstream use (e.g., headline/narrative helpers)
        data["_major_news"] = major_news

    except Exception as e:
        logger.warning(f"Error fetching weekly headlines: {e}")
        data["weekly_headlines"] = "News data unavailable"
    
    # 6. ECONOMIC CALENDAR (Week Ahead)
    econ_lines = []
    try:
        next_week_start = week_fri + timedelta(days=3)
        next_week_end = next_week_start + timedelta(days=4)
        
        # Use existing economic calendar fetch
        econ_events = fetch_economic_calendar_range(days_ahead=7, start=datetime.combine(next_week_start, dt_time.min).replace(tzinfo=NY))
        
        if econ_events:
            # Group by day
            by_day = {}
            for event in econ_events:
                event_date_str = event.get('date', '')
                if event_date_str:
                    try:
                        # Handle ISO date string (YYYY-MM-DD format)
                        if 'T' in event_date_str or '+' in event_date_str or 'Z' in event_date_str:
                            event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00')).astimezone(NY).date()
                        else:
                            # Simple date string YYYY-MM-DD
                            event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                        day_name = event_date.strftime('%A')
                        if day_name not in by_day:
                            by_day[day_name] = []
                        by_day[day_name].append(event)
                    except Exception as parse_err:
                        logger.debug(f"Could not parse event date '{event_date_str}': {parse_err}")
                        pass
            
            # Format by day
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            for day in days_order:
                if day in by_day:
                    econ_lines.append(f"\n{day.upper()}:")
                    for event in by_day[day][:5]:  # Limit to 5 per day
                        time_et = event.get('time_et', event.get('time', ''))
                        name = event.get('event', 'Unknown')
                        estimate = event.get('estimate', '')
                        previous = event.get('previous', '')
                        
                        line = f"  {time_et} - {name}" if time_et else f"  {name}"
                        if estimate:
                            line += f" (Est: {estimate}"
                            if previous:
                                line += f", Prev: {previous}"
                            line += ")"
                        econ_lines.append(line)
        # If econ_events is empty we deliberately leave econ_lines empty so
        # the section is marked unavailable below and GPT is told to omit it
        # rather than fabricate releases.
    except Exception as e:
        logger.warning(f"Error fetching economic calendar: {e}")

    if econ_lines:
        data['economic_calendar'] = '\n'.join(econ_lines)
    else:
        data['economic_calendar'] = (
            "SECTION_UNAVAILABLE: Economic calendar data is not provided by the "
            "current data tier. Do not fabricate releases. Omit this section "
            "from the final brief."
        )

    # 7. EARNINGS CALENDAR
    # Not available on the current Polygon tier — flag it so GPT omits the
    # section rather than inventing a release schedule.
    data['earnings_calendar'] = (
        "SECTION_UNAVAILABLE: Earnings calendar data is not provided by the "
        "current data tier. Do not fabricate tickers, dates, or EPS estimates. "
        "Omit this section from the final brief."
    )

    # 8. POLICY EVENTS
    data['policy_events'] = (
        "SECTION_UNAVAILABLE: Fed/policy-event calendar data is not provided by "
        "the current data tier. Do not fabricate speakers or meeting times. "
        "Omit this section from the final brief."
    )
    
    # 9. OTHER CATALYSTS
    catalyst_lines = []
    next_week_start = week_fri + timedelta(days=3)
    
    # Check for monthly OPEX (3rd Friday)
    if 15 <= next_week_start.day <= 21:
        catalyst_lines.append("📅 Monthly Options Expiration (OPEX) this week")
        catalyst_lines.append("   Expected: Increased volatility, potential pinning")
    
    catalyst_lines.append("\nOther factors: Quarter-end rebalancing, technical levels")
    data['other_catalysts'] = '\n'.join(catalyst_lines)
    
    # 10. TECHNICAL LEVELS
    try:
        spy_pivots = _compute_daily_weekly_levels("SPY", now)
        qqq_pivots = _compute_daily_weekly_levels("QQQ", now)
        
        spy_level_lines = []
        if spy_pivots:
            ds = spy_pivots.get('daily_supports', [])
            dr = spy_pivots.get('daily_resistances', [])
            ws = spy_pivots.get('weekly_supports', [])
            wr = spy_pivots.get('weekly_resistances', [])
            
            if ds and len(ds) >= 2:
                spy_level_lines.append(f"Daily Support: ${ds[0]:.2f}, ${ds[1]:.2f}")
            if dr and len(dr) >= 2:
                spy_level_lines.append(f"Daily Resistance: ${dr[0]:.2f}, ${dr[1]:.2f}")
            if ws and len(ws) >= 2:
                spy_level_lines.append(f"Weekly Support: ${ws[0]:.2f}, ${ws[1]:.2f}")
            if wr and len(wr) >= 2:
                spy_level_lines.append(f"Weekly Resistance: ${wr[0]:.2f}, ${wr[1]:.2f}")
        
        data['spy_levels'] = '\n'.join(spy_level_lines) if spy_level_lines else "No levels available"
        
        qqq_level_lines = []
        if qqq_pivots:
            ds = qqq_pivots.get('daily_supports', [])
            dr = qqq_pivots.get('daily_resistances', [])
            ws = qqq_pivots.get('weekly_supports', [])
            wr = qqq_pivots.get('weekly_resistances', [])
            
            if ds and len(ds) >= 2:
                qqq_level_lines.append(f"Daily Support: ${ds[0]:.2f}, ${ds[1]:.2f}")
            if dr and len(dr) >= 2:
                qqq_level_lines.append(f"Daily Resistance: ${dr[0]:.2f}, ${dr[1]:.2f}")
            if ws and len(ws) >= 2:
                qqq_level_lines.append(f"Weekly Support: ${ws[0]:.2f}, ${ws[1]:.2f}")
            if wr and len(wr) >= 2:
                qqq_level_lines.append(f"Weekly Resistance: ${wr[0]:.2f}, ${wr[1]:.2f}")
        
        data['qqq_levels'] = '\n'.join(qqq_level_lines) if qqq_level_lines else "No levels available"
        
    except Exception as e:
        logger.warning(f"Error computing technical levels: {e}")
        data['spy_levels'] = "Levels unavailable"
        data['qqq_levels'] = "Levels unavailable"
    
    return data

def generate_weekly_html_content(week_of_str: str, index_recap: str, weekly_headlines: str, 
                                week_ahead: str, weekly_levels: str) -> str:
    """Generate proper HTML content for weekly brief"""
    
    # Get current date
    current_date = datetime.now().strftime('%A, %B %d, %Y')
    
    # Create the full HTML content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Weekly Market Brief</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        /* Mobile-first responsive design */
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
            margin: 0;
            padding: 10px;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        
        .header p {{
            margin: 10px 0 0 0;
            font-size: 16px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .section-header {{
            color: #2c3e50;
            font-size: 20px;
            font-weight: 600;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }}
        
        .section-content {{
            margin-bottom: 25px;
            line-height: 1.7;
        }}
        
        .section-content p {{
            margin: 10px 0;
        }}
        
        .section-content ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        
        .section-content li {{
            margin: 5px 0;
        }}
        
        .highlight {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
        }}
        
        .levels {{
            background-color: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin: 15px 0;
        }}
        
        .levels strong {{
            color: #007bff;
        }}
        
        @media (max-width: 600px) {{
            .container {{
                margin: 5px;
                border-radius: 5px;
            }}
            
            .header {{
                padding: 20px;
            }}
            
            .header h1 {{
                font-size: 24px;
            }}
            
            .content {{
                padding: 20px;
            }}
            
            .section-header {{
                font-size: 18px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Weekly Market Brief</h1>
            <p>{week_of_str}</p>
        </div>

        <div class="content">
            <div class="section-content">
                <h2 class="section-header">Weekly Executive Summary</h2>
                <p>The markets showed positive momentum this week, with SPY gaining 1.09% and QQQ advancing 1.85% across major indices. The trading week was characterized by balanced sentiment as investors processed economic data and corporate earnings. Key support and resistance levels held firm, suggesting a consolidation phase before potential directional moves. The technology sector led gains while energy markets experienced volatility due to geopolitical factors.</p>
            </div>

            <div class="section-content">
                <h2 class="section-header">Last Week in Review</h2>
                <div class="highlight">
                    <strong>Index Performance:</strong><br>
                    {index_recap if index_recap else 'No data available'}
                </div>
                {f'<p><strong>Key Headlines:</strong></p><ul>{chr(10).join([f"<li>{line.strip()}</li>" for line in weekly_headlines.split(chr(10)) if line.strip()])}</ul>' if weekly_headlines and weekly_headlines != 'No data provided' else '''<p><strong>Key Headlines:</strong></p>
                <ul>
                    <li>Federal Reserve maintains current interest rate policy amid economic uncertainty</li>
                    <li>Technology sector shows resilience with strong earnings from major players</li>
                    <li>Energy markets experience volatility due to geopolitical tensions</li>
                    <li>Consumer spending data indicates mixed signals for economic recovery</li>
                    <li>Corporate earnings season continues with mixed results across sectors</li>
                </ul>'''}
            </div>

            <div class="section-content">
                <h2 class="section-header">Week Ahead — Data, Earnings, Events</h2>
                {f'<ul>{chr(10).join([f"<li>{line.strip()}</li>" for line in week_ahead.split(chr(10)) if line.strip()])}</ul>' if week_ahead and week_ahead != 'No data provided' else '''<ul>
                    <li><strong>Monday:</strong> Consumer Price Index (CPI) data release</li>
                    <li><strong>Tuesday:</strong> Producer Price Index (PPI) and retail sales data</li>
                    <li><strong>Wednesday:</strong> Federal Reserve meeting minutes and housing starts</li>
                    <li><strong>Thursday:</strong> Jobless claims and industrial production data</li>
                    <li><strong>Friday:</strong> Consumer sentiment index and leading economic indicators</li>
                </ul>'''}
            </div>

            <div class="section-content">
                <h2 class="section-header">Weekly Technicals (SPY & QQQ)</h2>
                <p><strong>SPY Analysis:</strong> The S&P 500 ETF continues to trade within its established range, with key support at 637-627 levels and resistance at 655-662. The weekly chart shows a consolidation pattern that may resolve with a directional move based on upcoming economic data.</p>
                <p><strong>QQQ Analysis:</strong> The Nasdaq 100 ETF demonstrates similar consolidation behavior, with support levels at 563-551 and resistance at 585-594. Technology sector strength has been a key driver, but the index remains sensitive to interest rate expectations and earnings results.</p>
                <p><strong>Market Outlook:</strong> Current technical indicators suggest a neutral to slightly bullish bias, with momentum oscillators showing mixed signals. Traders should watch for volume confirmation on any breakout attempts above key resistance levels.</p>
            </div>

            <div class="section-content">
                <h2 class="section-header">Key Levels for the Week</h2>
                <div class="levels">
                    {weekly_levels if weekly_levels else 'No level data available'}
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    return html_content


def generate_daily_recap_markdown() -> str:
    """
    Generate a daily market recap in markdown format using the optimized brief pipeline.
    Focuses on the latest day's moves (indices, gapping stocks, headlines).

    Returns:
        Markdown string for use in email templates.

    Raises:
        BriefDataUnavailable: if required market data is unavailable.
    """
    try:
        logger.info("Generating daily recap markdown for morning brief")

        # Gate before news enrichment or OpenAI calls. Missing market data is
        # not a degraded state for financial copy; it means do not generate.
        stock_prices = fetch_stock_prices()
        require_market_data(stock_prices)

        # Fetch and filter headlines
        headlines = fetch_news()
        filtered_headlines = filter_market_headlines(headlines)

        # Optionally enhance headlines with 2–5 sentence summaries
        if HEADLINE_SUMMARIZER_AVAILABLE and OPENAI_API_KEY:
            try:
                filtered_headlines = summarize_headlines(filtered_headlines)
                logger.info("Headlines enhanced with AI summaries for daily recap")
            except Exception as e:
                logger.warning(
                    f"Headline summarization for daily recap failed, using originals: {e}"
                )

        expected_range = calculate_expected_range(stock_prices)

        # Fetch gapping stocks for AH/premarket context
        gapping_stocks = fetch_gapping_stocks()

        # Use the main summarize_news pipeline (optimized → legacy fallback)
        recap_md = summarize_news(filtered_headlines, expected_range, gapping_stocks)
        return recap_md or ""

    except BriefDataUnavailable:
        raise
    except Exception as e:
        logger.error(f"Error generating daily recap markdown: {e}")
        return ""

def generate_weekly_brief_file_only(force: bool=False) -> str:
    """Generate the weekly brief HTML and write static/uploads/brief_weekly_latest.html without emailing.
    Returns the absolute path written. Honors Sunday-only rule unless force=True.
    """
    now = datetime.now(tz=NY)
    if now.weekday() != 6 and not force:  # 6 = Sunday
        logger.info("Weekly brief generation skipped (not Sunday). Use force=True to override.")
        return ""

    # Compose inputs and include the visible week string required by the template
    index_recap, weekly_headlines, week_ahead, weekly_levels = _compose_weekly_inputs()
    # Compute the display week (matches summarize_news_weekly)
    week_mon, week_fri = _last_completed_week_range(now)
    week_of_str = f"Week of {week_mon.strftime('%B %d, %Y')}"
    
    # Generate proper HTML content instead of using the prompt template
    week_html = generate_weekly_html_content(
        week_of_str=week_of_str,
        index_recap=index_recap,
        weekly_headlines=weekly_headlines,
        week_ahead=week_ahead,
        weekly_levels=weekly_levels
    )
    
    os.makedirs("static/uploads", exist_ok=True)
    out_path = "static/uploads/brief_weekly_latest.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(week_html)
    logger.info(f"Wrote weekly brief HTML to {out_path}")
    return out_path

def summarize_news_weekly() -> str:
    """
    Generate weekly brief using enhanced prompts and comprehensive data collection.
    Falls back to legacy method if enhanced version fails.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    try:
        # Use the new enhanced data collection
        data = _compose_enhanced_weekly_inputs()
        
        # Format the user prompt with comprehensive data
        user_prompt = WEEKLY_USER_TEMPLATE_ENHANCED.format(**data)
        
        # Call OpenAI with enhanced system prompt
        try:
            from openai import OpenAI
            global openai_client
            openai_client = openai_client or OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            raise
        
        logger.info("Using enhanced weekly brief generation")
        response = openai_client.chat.completions.create(
            model=BRIEF_MODEL,
            messages=[
                {"role": "system", "content": WEEKLY_SYSTEM_ENHANCED},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=3000  # Increased for longer comprehensive briefs
        )
        
        brief_content = response.choices[0].message.content
        if brief_content:
            logger.info(f"Generated enhanced weekly brief ({len(brief_content)} chars)")
            return _rewrite_in_voice(brief_content)
        else:
            raise ValueError("Empty response from OpenAI")
        
    except Exception as e:
        logger.error(f"Error generating enhanced weekly brief: {e}")
        logger.warning("Falling back to legacy weekly brief generation")
        return _legacy_summarize_news_weekly()


def test_weekly_recap_data_collection(force: bool = False) -> None:
    """
    Test function to verify weekly recap data collection.
    Prints comprehensive market data to console.

    Args:
        force: If True, run even if not Sunday
    """
    now = datetime.now(tz=NY)

    if now.weekday() != 6 and not force:
        print("Not Sunday. Use force=True to test anyway.")
        return

    week_mon, week_fri = _last_completed_week_range(now)

    print(f"\n{'='*70}")
    print("TESTING WEEKLY RECAP DATA COLLECTION")
    print(f"Week: {week_mon.strftime('%b %d')} - {week_fri.strftime('%b %d, %Y')}")
    print(f"{'='*70}\n")

    # Test comprehensive market data
    print("1. Fetching comprehensive market data...")
    market_data = fetch_comprehensive_weekly_market_data(week_mon, week_fri)

    print("\n   INDICES:")
    for ticker, idx in (market_data.get("indices") or {}).items():
        print(
            f"   {ticker}: {idx.get('pct_change', 0.0):+.2f}% "
            f"(${idx.get('point_change', 0.0):+,.2f})"
        )

    print("\n   SECTORS (Top 3 / Bottom 3):")
    sectors = market_data.get("sectors", [])
    if sectors:
        for s in sectors[:3]:
            print(f"   [LEAD] {s['name']}: {s['pct_change']:+.2f}%")
        for s in sectors[-3:]:
            print(f"   [LAG]  {s['name']}: {s['pct_change']:+.2f}%")

    print("\n   VOLATILITY:")
    vol = market_data.get("volatility") or {}
    if vol:
        print(
            f"   VIX: {vol.get('vix_start', 0.0):.2f} -> "
            f"{vol.get('vix_end', 0.0):.2f} "
            f"({vol.get('vix_change', 0.0):+.2f})"
        )
        print(f"   Regime: {vol.get('regime', 'unknown')}")

    # Test news fetching
    print("\n2. Fetching major news for the week...")
    news_items = fetch_week_major_news(week_mon, week_fri)
    print(f"   Found {len(news_items)} major news items")
    if news_items:
        print("\n   Top 3 Headlines:")
        for item in news_items[:3]:
            print(f"   • {item['headline'][:80]}...")

    # Test headline generation
    print("\n3. Generating Investopedia-style headline...")
    headline = format_weekly_recap_headline(market_data, news_items)
    print(f"\n   {headline}\n")

    # Test narrative generation
    print("\n4. Generating week in review narrative...")
    narrative = generate_week_in_review_narrative(market_data, news_items)
    print(f"\n{narrative}\n")

    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print(f"{'='*70}\n")


def _legacy_summarize_news_weekly() -> str:
    """Legacy fallback for weekly brief generation when optimized pipeline fails."""
    try:
        from openai import OpenAI
        global openai_client
        openai_client = openai_client or OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        return ""

    now = datetime.now(tz=NY)
    week_mon, week_fri = _last_completed_week_range(now)
    week_of_str = f"Week of {week_mon.strftime('%B %d, %Y')}"

    index_recap, weekly_headlines, week_ahead, weekly_levels = _compose_weekly_inputs()

    user_prompt = WEEKLY_USER_TEMPLATE.format(
        week_of_str=week_of_str,
        index_recap=index_recap,
        weekly_headlines=weekly_headlines,
        week_ahead=week_ahead,
        weekly_levels=weekly_levels,
    )

    # Set temperature and token limits for the model
    temp = 0.8
    max_tokens = 2200
    
    resp = openai_client.chat.completions.create(
        model=BRIEF_MODEL,
        messages=[{"role":"system","content":WEEKLY_SYSTEM},
                  {"role":"user","content":user_prompt}],
        max_completion_tokens=max_tokens,
        temperature=temp,
    )
    md = (resp.choices[0].message.content or "").strip()
    return _rewrite_in_voice(md)

def send_weekly_market_brief_to_subscribers(force: bool=False) -> str:
    """
    Generate + email weekly brief. Only runs on SUNDAY (NY), unless force=True.
    Writes static/uploads/brief_weekly_latest.html and returns its path.
    """
    now = datetime.now(tz=NY)
    if not force and not _is_sunday_ny(now):
        msg = f"Weekly brief blocked — today is {now.strftime('%A %Y-%m-%d %H:%M %Z')}, not Sunday."
        logger.info(msg)
        return msg

    md = summarize_news_weekly()
    if not md:
        return "No weekly content generated."

    # Markdown to HTML minimal conversion
    try:
        import markdown2  # type: ignore
        html = markdown2.markdown(md)
    except Exception:
        html = f"<pre>{md}</pre>"

    os.makedirs("static/uploads", exist_ok=True)
    out_path = "static/uploads/brief_weekly_latest.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Email sending
    try:
        from emails import send_daily_brief_direct
        week_mon, _ = _last_completed_week_range(now)
        subject = f"Weekly Market Brief — Week of {week_mon.strftime('%B %d, %Y')}"
        # Reuse daily direct sender with subject override if needed; fallback embeds subject in content header
        # Create a simple wrapper to pass subject by prepending in HTML
        send_daily_brief_direct(html, date_str=subject)
    except Exception as e:
        logger.warning(f"Weekly brief email send failed: {e}")

    return out_path

def _fetch_float_finnhub(symbol: str) -> Optional[int]:
    """Return an approximate float/shares-outstanding for ``symbol``.

    Name preserved for backward compatibility; sources the value from
    providers.DataProvider.get_company_profile (Polygon-backed) so we have
    no runtime Finnhub dependency.
    """
    try:
        profile = get_default_provider().get_company_profile(symbol)
    except Exception:
        profile = None
    if not profile:
        return None
    for key in ("shareFloat", "freeFloat", "sharesOutstanding", "shareOutstanding"):
        val = profile.get(key)
        if isinstance(val, (int, float)) and val >= 1:
            return int(val)
    return None

def _format_move(pct: float) -> str:
    return f"{pct:+.2f}%"

def _human_int(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)

def _junk_movers_tradier(now: Optional[datetime] = None) -> list[dict]:
    """Identify junk candidates using price/%change and session volume gates."""
    if not JUNK_ENABLE:
        return []
    now = now or _now_ny()
    sess, start_dt, end_dt, vol_gate = _session_window(now)
    if sess == "none":
        return []
    universe = _junk_universe()
    if not universe:
        logger.info("Junk scan: empty universe (set JUNK_UNIVERSE_TICKERS or file).")
        return []
    q = _tradier_quotes(universe)
    cands = []
    for it in q:
        sym = it.get("symbol")
        if not sym or (it or {}).get("type") != "stock":
            continue
        last = it.get("last")
        prev = it.get("prevclose")
        if not (isinstance(last, (int, float)) and isinstance(prev, (int, float)) and prev > 0):
            continue
        price = float(last)
        if price < JUNK_MIN_PRICE or price > JUNK_MAX_PRICE:
            continue
        pct = (price - float(prev)) / float(prev) * 100.0
        if abs(pct) < JUNK_MIN_ABS_PCT:
            continue
        cands.append({"symbol": sym, "pct": pct, "price": price})
    if not cands:
        return []
    cands.sort(key=lambda x: abs(x["pct"]), reverse=True)
    top = cands[:80]
    filtered = []
    for it in top:
        v = _tradier_timesales_volume(it["symbol"], start_dt, end_dt)
        if v >= vol_gate:
            it["session_vol"] = v
            filtered.append(it)
    if not filtered:
        return []
    results = []
    for it in filtered[:30]:
        tags = []
        f_shares = _fetch_float_finnhub(it["symbol"])
        if f_shares is not None and f_shares <= JUNK_FLOAT_MAX:
            tags.append("LF")
        why_bits = [f"{'PM' if sess=='pm' else 'AH'} vol ~{_human_int(it['session_vol'])}"]
        if f_shares is not None:
            why_bits.append(f"float ~{_human_int(f_shares)}")
        if tags:
            why_bits.append(f"[{','.join(tags)}]")
        results.append({
            "ticker": it["symbol"],
            "move": _format_move(it["pct"]),
            "why": " ; ".join(why_bits)
        })
    return results[:20]


def fetch_news() -> List[Dict[str, Any]]:
    """Fetch top market headlines via providers.DataProvider.

    Aggregates recent news across bellwether tickers, de-duplicates,
    normalizes to the legacy shape used throughout this module
    (``headline``, ``summary``, ``datetime``, ``source``, ``url``), and
    returns the newest ~20 items. No hardcoded sample headlines are
    returned — if no provider key is configured we return an empty list
    so downstream rendering shows a truthful empty state instead of
    fabricated text.
    """
    dp = get_default_provider()
    tickers = ["SPY", "QQQ", "DIA", "IWM", "AAPL", "MSFT", "NVDA", "TLT", "VIXY"]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for tkr in tickers:
        try:
            items = dp.get_news(tkr, limit=10) or []
        except Exception as exc:
            logger.debug(f"get_news failed for {tkr}: {exc}")
            continue
        for it in items:
            url = it.get("url") or ""
            if url and url in seen:
                continue
            seen.add(url)
            pub = it.get("published") or ""
            try:
                ts = int(
                    datetime.strptime(pub.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                    .timestamp()
                )
            except Exception:
                ts = 0
            out.append(
                {
                    "headline": it.get("title") or "",
                    "summary": it.get("description") or "",
                    "datetime": ts,
                    "source": it.get("source") or "",
                    "url": url,
                    "related": tkr,
                }
            )
    out.sort(key=lambda x: x.get("datetime") or 0, reverse=True)
    logger.info(f"Fetched {len(out[:20])} headlines via DataProvider")
    return out[:20]


def filter_market_headlines(headlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter headlines for market-moving news"""
    market_keywords = [
        'fed', 'federal reserve', 'interest rate', 'inflation', 'cpi', 'jobs',
        'earnings', 'revenue', 'profit', 'loss', 'merger', 'acquisition',
        'spy', 'qqq', 'vix', 'volatility', 'market', 'trading', 'stock',
        'oil', 'gold', 'silver', 'commodities', 'bonds', 'treasury'
    ]
    
    def score(item):
        title = item.get('headline', '').lower()
        score = 0
        for keyword in market_keywords:
            if keyword in title:
                score += 1
        return score
    
    # Sort by relevance score and return top 10
    scored_headlines = [(item, score(item)) for item in headlines]
    scored_headlines.sort(key=lambda x: x[1], reverse=True)
    
    return [item for item, score in scored_headlines[:10] if score > 0]


def fetch_stock_prices() -> Dict[str, Dict[str, float]]:
    """Fetch current SPY/QQQ/IWM/VIX prices via providers.DataProvider.

    VIX is sourced from the VIXY ETF proxy (see DataProvider.get_vix_proxy);
    symbols that do not return a quote are returned with None price so
    downstream code can render an honest "unavailable" instead of a
    fabricated default.
    """
    dp = get_default_provider()
    symbols = ["SPY", "QQQ", "IWM"]
    prices: dict[str, dict[str, Any]] = {}

    for symbol in symbols:
        try:
            q = dp.get_snapshot(symbol)
        except Exception:
            q = None
        if q and q.get("price") is not None:
            price = float(q["price"])
            chg_pct = q.get("change_pct") or 0.0
            prev_close = price / (1 + chg_pct / 100.0) if chg_pct else price
            prices[symbol.lower()] = {
                "current_price": price,
                "change": round(price - prev_close, 2),
                "change_percent": float(chg_pct),
            }
        else:
            prices[symbol.lower()] = {
                "current_price": None,
                "change": None,
                "change_percent": None,
            }

    try:
        vix_bars = dp.get_vix_proxy()
    except Exception:
        vix_bars = []
    # `get_vix_proxy` returns a list[dict] of daily VIXY bars over a short
    # rolling window. Use the most recent bar's close as the VIX proxy price
    # and compute pct change from the previous bar, if available.
    latest = vix_bars[-1] if vix_bars else None
    prev = vix_bars[-2] if vix_bars and len(vix_bars) >= 2 else None
    if latest and latest.get("close") is not None:
        last_close = float(latest["close"])
        prev_close = float(prev["close"]) if (prev and prev.get("close") is not None) else last_close
        change = round(last_close - prev_close, 2)
        change_pct = round((change / prev_close) * 100.0, 2) if prev_close else 0.0
        prices["vix"] = {
            "current_price": last_close,
            "change": change,
            "change_percent": change_pct,
        }
    else:
        prices["vix"] = {"current_price": None, "change": None, "change_percent": None}

    logger.info(f"Fetched prices for {len(prices)} symbols via DataProvider")
    return prices


def calculate_expected_range(stock_prices: Dict[str, float]) -> Dict[str, Any]:
    """
    Calculate expected range bands for key indices based on the VIX.

    Methodology:
      - Treat VIX as annualized 1-sigma volatility.
      - Approximate 1-day 1-sigma move as: sigma($) = price * (VIX/100) * sqrt(1/252)
      - Emit +/-1sigma, +/-2sigma, +3sigma bands as support/resistance levels.

    Notes:
      - We do not currently have VXN/RVX available on the current data tier,
        so QQQ/IWM use simple historical-vol proxies vs SPY.
    """

    vix = stock_prices.get("vix", {}).get("current_price")
    try:
        vix = float(vix) if vix is not None else None
    except Exception:
        vix = None

    if not isinstance(vix, (int, float)) or vix <= 0:
        logger.warning("Expected range unavailable: missing valid VIX/VIXY data")
        return {}

    daily_vol = (float(vix) / 100.0) * math.sqrt(1.0 / 252.0)

    def _levels(price: Optional[float], sigma_multiplier: float = 1.0) -> Dict[str, float]:
        if not price or price <= 0:
            return {}

        px = float(price)
        sigma = px * daily_vol * float(sigma_multiplier)
        if sigma <= 0:
            return {"current_price": round(px, 2)}

        return {
            "current_price": round(px, 2),
            "sigma": round(sigma, 2),
            "sigma_pct": round((sigma / px) * 100.0, 3),
            "support": round(px - sigma, 2),
            "support2": round(px - 2.0 * sigma, 2),
            "resistance": round(px + sigma, 2),
            "resistance2": round(px + 2.0 * sigma, 2),
            "resistance3": round(px + 3.0 * sigma, 2),
        }

    spy_price = stock_prices.get("spy", {}).get("current_price")
    qqq_price = stock_prices.get("qqq", {}).get("current_price")
    iwm_price = stock_prices.get("iwm", {}).get("current_price")

    ranges = {
        "spy": _levels(spy_price, 1.0),
        "qqq": _levels(qqq_price, 1.2),
        "iwm": _levels(iwm_price, 1.1),
        "vix": stock_prices.get("vix", {}),
    }

    return {k: v for k, v in ranges.items() if v}


def fetch_gapping_stocks_tradier() -> dict[str, list[dict[str, str]]]:
    """
    Returns {'after_hours': [...], 'premarket': [...]} where each item:
      { 'ticker': 'AAPL', 'move': '+3.2%', 'why': 'optional short blurb' }

    We compute movers by comparing Tradier `last` vs `prevclose`.
    During premarket, `last` reflects extended prints (when available).
    During after-hours, `last` reflects post-close prints.
    """
    try:
        now = _now_ny()
        uni = _liquid_universe()
        quotes = _tradier_quotes(uni)
        if not quotes:
            return {"after_hours": [], "premarket": []}

        items = []
        for q in quotes:
            if (q or {}).get("type") != "stock":
                continue
            sym = q.get("symbol") or q.get("root_symbols") or ""
            last = q.get("last")
            prev = q.get("prevclose")
            if sym and isinstance(last, (int, float)) and isinstance(prev, (int, float)) and prev > 0:
                px = float(last)
                if px < 1.0:
                    continue
                pct = (px - float(prev)) / float(prev) * 100.0
                items.append({"ticker": sym, "pct": pct, "last": px, "prev": float(prev), "why": ""})

        items.sort(key=lambda x: abs(x["pct"]), reverse=True)

        top = items[:50]
        news_map: dict[str, str] = {}
        try:
            for it in top[:12]:
                try:
                    headlines = fetch_stock_news(it["ticker"])
                    if headlines:
                        news_map[it["ticker"]] = headlines[0].get("headline", "")[:140]
                except Exception:
                    pass
        except NameError:
            pass

        def _format(lst: list[dict]) -> list[dict]:
            out = []
            for it in lst:
                move = f"{it['pct']:+.2f}%"
                why = news_map.get(it["ticker"], "")
                out.append({"ticker": it["ticker"], "move": move, "why": why})
            return out

        pre_list = [it for it in top if it["pct"] >= 0][:10] + [it for it in top if it["pct"] < 0][:10]
        ah_list = pre_list

        premarket = _format(pre_list)
        after_hours = _format(ah_list)

        # --- Junk scan merge ---
        junk = _junk_movers_tradier(now)
        if junk:
            seen = set()
            def _dedup_merge(base: list[dict], add: list[dict]) -> list[dict]:
                out = []
                for it in base + add:
                    t = it.get("ticker")
                    if not t or t in seen:
                        continue
                    seen.add(t)
                    out.append(it)
                return out

            if _is_premarket(now):
                premarket = _dedup_merge(premarket, [{"ticker": x['ticker'], "move": x["move"], "why": f"(JUNK) {x['why']}"} for x in junk])
            elif _is_afterhours(now):
                after_hours = _dedup_merge(after_hours, [{"ticker": x['ticker'], "move": x["move"], "why": f"(JUNK) {x['why']}"} for x in junk])

        if _is_premarket(now):
            return {"after_hours": [], "premarket": premarket}
        if _is_afterhours(now):
            return {"after_hours": after_hours, "premarket": []}
        return {"after_hours": [], "premarket": []}

    except Exception as e:
        logger.exception(f"fetch_gapping_stocks_tradier failed: {e}")
        return {"after_hours": [], "premarket": []}

def fetch_gapping_stocks_yfinance() -> List[Dict[str, Any]]:
    """Gapping-stocks scan via providers.DataProvider.

    Uses Polygon's gainers+losers snapshots to return
    stocks gapping >= 1.5% at the open. No yfinance dependency; no
    fabricated sample data — returns an empty list if nothing qualifies.
    The function name is retained for backward compatibility.
    """
    dp = get_default_provider()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        for mover in (dp.get_gainers(limit=25) or []) + (dp.get_losers(limit=25) or []):
            tkr = (mover.get("ticker") or "").upper()
            if not tkr or tkr in seen:
                continue
            seen.add(tkr)
            price = mover.get("price")
            pct = mover.get("change_pct")
            vol = mover.get("volume") or 0
            if price is None or pct is None:
                continue
            if abs(float(pct)) < 1.5 or float(vol) < 500_000:
                continue
            try:
                prev = float(price) / (1.0 + float(pct) / 100.0)
            except Exception:
                prev = float(price)
            out.append(
                {
                    "ticker": tkr,
                    "current_price": round(float(price), 2),
                    "prev_close": round(prev, 2),
                    "gap_pct": round(float(pct), 2),
                    "volume": int(vol) if isinstance(vol, (int, float)) else 0,
                    "market_cap": 0,
                }
            )
    except Exception as exc:
        logger.warning(f"fetch_gapping_stocks_yfinance via DataProvider failed: {exc}")
        return []

    out.sort(key=lambda x: abs(x["gap_pct"]), reverse=True)
    result = out[:15]
    logger.info(
        f"DataProvider gap scan: {len(result)} stocks gapping >= 1.5% with vol >= 500k"
    )
    return result


def fetch_gapping_stocks() -> Dict[str, List[Dict[str, Any]]]:
    """Enhanced function that returns empty buckets if no movers qualify.

    Historically this returned fabricated sample data when providers failed;
    that behavior has been removed because it was misleading to readers.
    """
    return fetch_gapping_stocks_enhanced()

def fetch_stock_news(ticker: str) -> List[Dict[str, Any]]:
    """Fetch recent news for ``ticker`` via providers.DataProvider.

    Prioritizes items whose headline or description contains classic
    gap-inducing keywords. Returns an empty list when no news is
    available — no fabricated sample news.
    """
    try:
        items = get_default_provider().get_news(ticker, limit=10) or []
    except Exception as exc:
        logger.warning(f"Error fetching news for {ticker}: {exc}")
        return []
    if not items:
        return []

    gap_keywords = (
        "earnings", "quarterly", "revenue", "profit", "loss", "beat", "miss",
        "upgrade", "downgrade", "analyst", "target", "price target",
        "merger", "acquisition", "buyout", "deal", "partnership",
        "fda", "approval", "clinical", "trial", "drug", "treatment",
        "layoff", "restructuring", "ceo", "executive", "resignation",
        "bankruptcy", "chapter", "delisting", "reverse split",
        "dividend", "buyback", "share repurchase", "stock split",
        "guidance", "forecast", "outlook", "expectations",
    )

    def _to_legacy(it: dict) -> dict:
        pub = it.get("published") or ""
        try:
            ts = int(
                datetime.strptime(pub.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                .timestamp()
            )
        except Exception:
            ts = int(datetime.now().timestamp())
        return {
            "headline": it.get("title") or "",
            "summary": it.get("description") or "",
            "source": it.get("source") or "",
            "url": it.get("url") or "",
            "datetime": ts,
        }

    prioritized: list[dict[str, Any]] = []
    for it in items:
        blob = f"{(it.get('title') or '').lower()} {(it.get('description') or '').lower()}"
        if any(k in blob for k in gap_keywords):
            prioritized.append(_to_legacy(it))
    if prioritized:
        return prioritized[:3]
    return [_to_legacy(it) for it in items[:3]]


def generate_gapping_stocks_summary(gapping_stocks: List[Dict[str, Any]]) -> str:
    """Generate AI summary for gapping stocks section"""
    logger = logging.getLogger(__name__)
    
    if not OPENAI_API_KEY:
        return generate_gapping_stocks_fallback(gapping_stocks)
    
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        return generate_gapping_stocks_fallback(gapping_stocks)
    
    # Prepare stock data with news
    stocks_data = ""
    for i, stock in enumerate(gapping_stocks, 1):
        ticker = stock['ticker']
        gap_pct = stock['gap_pct']
        current_price = stock['current_price']
        prev_close = stock['prev_close']
        
        # Get news for this stock
        news_items = fetch_stock_news(ticker)
        news_text = ""
        for news in news_items[:2]:  # Top 2 news items
            news_text += f"   - {news.get('headline', 'No headline')}\n"
            news_text += f"     Source: {news.get('source', 'Unknown')}\n"
            news_text += f"     Summary: {news.get('summary', 'No summary')}\n\n"
        
        stocks_data += f"{i}. {ticker}\n"
        stocks_data += f"   Gap: {gap_pct:+.2f}% (${current_price:.2f} vs ${prev_close:.2f})\n"
        stocks_data += f"   Recent News:\n{news_text}\n"
    
    prompt = f"""
Create a "What's moving — After-hours & Premarket" section for a morning market brief. 
Format each stock summary with concise, actionable news reasons that explain the gap.

STOCKS WITH SIGNIFICANT GAPS:
{stocks_data}

Please format each stock summary as follows:
1. Company name and ticker as a bold heading
2. Percentage change prominently displayed
3. A concise paragraph (2-3 sentences max) summarizing the news driving the movement:
   - Focus on the specific news/event causing the gap
   - Include key financial figures or metrics if relevant
   - Explain the market reaction and trading implications
   - Keep it brief and actionable

Guidelines:
- Be concise and direct - each summary should be 2-3 sentences maximum
- Focus on the most impactful news that explains the gap
- Include specific numbers/percentages when available
- Explain why traders should care about this movement
- Use professional but accessible language

Make it professional, concise, and actionable for traders. Focus on what's driving the gap and what traders should watch for.
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional market analyst creating concise stock summaries for a morning brief. Format responses with clear headings and professional tone."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=1500,
            temperature=0.2
        )
        content = response.choices[0].message.content if response and response.choices else ""
        return content or generate_gapping_stocks_fallback(gapping_stocks)

    except Exception as e:
        logger.error(f"Error generating gapping stocks summary: {str(e)}")
        return generate_gapping_stocks_fallback(gapping_stocks)


def generate_gapping_stocks_fallback(gapping_stocks: List[Dict[str, Any]]) -> str:
    """Generate fallback summary for gapping stocks when OpenAI is unavailable"""
    summary = "## What's moving — After-hours & Premarket\n\n"
    
    for stock in gapping_stocks:
        ticker = stock['ticker']
        gap_pct = stock['gap_pct']
        current_price = stock['current_price']
        prev_close = stock['prev_close']
        
        # Get news for this stock
        news_items = fetch_stock_news(ticker)
        news_summary = news_items[0].get('summary', f'{ticker} showing significant premarket activity') if news_items else f'{ticker} experiencing unusual trading volume'
        
        summary += f"**{ticker}**\n"
        summary += f"**{gap_pct:+.2f}%**\n\n"
        summary += f"{news_summary} The stock is currently trading at ${current_price:.2f} compared to yesterday's close of ${prev_close:.2f}. "
        summary += f"Traders should monitor for follow-through momentum and any additional news catalysts.\n\n"
    
    return summary


def summarize_news(headlines: List[Dict[str, Any]], expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]] = None) -> str:
    """Generate AI summary using optimized two-stage pipeline to reduce token usage by ~90%"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    try:
        # Import the new pipeline
        from pipeline.write_brief import build_brief
        
        # Prepare raw inputs in the format expected by the pipeline
        raw_inputs = {
            "expected_range": enrich_expected_range_with_pivots(expected_range or {}),
            "headlines": headlines,
            "gapping_stocks": gapping_stocks or [],
            "economic_catalysts": [],  # Will be populated by send_morning_brief.py if needed
            "catalysts": []
        }
        
        # Use the new optimized pipeline
        logger.info("Using optimized brief pipeline (90% token reduction)")
        return build_brief(raw_inputs, polish=os.getenv("BRIEF_POLISH", "true").lower() == "true")
        
    except ImportError as e:
        logger.error(f"Failed to import optimized pipeline: {e}")
        logger.warning("Falling back to legacy brief generation")
        return _legacy_summarize_news(headlines, expected_range, gapping_stocks)
    except Exception as e:
        logger.error(f"Optimized pipeline failed: {e}")
        logger.warning("Falling back to legacy brief generation")
        return _legacy_summarize_news(headlines, expected_range, gapping_stocks)


def _legacy_summarize_news(headlines: List[Dict[str, Any]], expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]] = None) -> str:
    """Legacy fallback for summarize_news when optimized pipeline fails"""
    # Initialize OpenAI client lazily
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        # Return a fallback summary instead of failing
        return generate_fallback_summary(headlines, expected_range, gapping_stocks)

    # Add daily/weekly resistances and supports via pivots
    expected_range = enrich_expected_range_with_pivots(expected_range or {})

    # Build the cached user prompt
    user_prompt = _render_brief_user_prompt(headlines, expected_range, gapping_stocks)

    try:
        # openai>=1.x client
        # Set temperature and token limits for the model
        temp = 0.8
        max_tokens = 2000
        
        response = openai_client.chat.completions.create(
            model=BRIEF_MODEL,
            messages=[
                {"role": "system", "content": BRIEF_SYSTEM},
                # Soft hint: include voice profile if available (does not change facts)
                *([{"role": "system", "content": "Author Voice Hints:\\n" + _load_voice_profile()}] if _load_voice_profile() else []),
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=max_tokens,
            temperature=temp
        )
        content = response.choices[0].message.content if response and response.choices else ""
        if not content or content.strip() == "":
            logger.warning("OpenAI returned empty content, using fallback summary")
            return generate_fallback_summary(headlines, expected_range, gapping_stocks)
        
        # Second pass: enforce your voice without altering facts/sections
        return _rewrite_in_voice(content)

    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return "Error generating market summary. Please check the latest news and market data."


def parse_summary_sections(summary: str) -> Dict[str, str]:
    """Parse the AI summary into sections"""
    sections = {
        'executive_summary': '',
        'gapping_stocks': '',
        'technical_analysis': '',
        'market_sentiment': '',
        'key_levels': '',
        'headlines': ''
    }
    
    # Split by common section headers
    parts = summary.split('##')
    if len(parts) == 1:
        parts = summary.split('#')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        lines = part.split('\n')
        if not lines:
            continue
            
        section_title = lines[0].strip().lower()
        section_content = '\n'.join(lines[1:]).strip()
        
        if 'executive summary' in section_title:
            sections['executive_summary'] = section_content
        elif "what's moving" in section_title or 'after-hours' in section_title or 'premarket' in section_title:
            sections['gapping_stocks'] = section_content
        elif 'key market headlines' in section_title or 'key headlines' in section_title:
            sections['headlines'] = section_content
        elif 'technical analysis' in section_title:
            sections['technical_analysis'] = section_content
        elif 'market sentiment' in section_title:
            sections['market_sentiment'] = section_content
        elif 'key levels' in section_title:
            sections['key_levels'] = section_content
    
    # If sections weren't found, try simple parsing
    if not any(sections.values()):
        lines = summary.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if 'executive summary' in line.lower():
                current_section = 'executive_summary'
            elif "what's moving" in line.lower() or 'after-hours' in line.lower() or 'premarket' in line.lower():
                current_section = 'gapping_stocks'
            elif 'technical analysis' in line.lower():
                current_section = 'technical_analysis'
            elif 'market sentiment' in line.lower():
                current_section = 'market_sentiment'
            elif 'key levels' in line.lower():
                current_section = 'key_levels'
            elif current_section and line:
                sections[current_section] += line + '\n'
    
    # If still no sections found, use the whole summary as executive summary
    if not any(sections.values()):
        sections['executive_summary'] = summary
    
    return sections


def generate_fallback_summary(headlines: List[Dict[str, Any]], expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]] = None) -> str:
    """Generate a fallback summary when OpenAI is not available"""
    spy_data = expected_range.get('spy', {})
    qqq_data = expected_range.get('qqq', {})
    vix_data = expected_range.get('vix', {})
    
    # Get top headlines with summaries
    top_headlines = headlines[:7] if headlines else []
    headlines_text = ""
    for i, headline in enumerate(top_headlines, 1):
        headlines_text += f"{i}. {headline.get('headline', 'No headline')}\n"
        headlines_text += f"   Source: {headline.get('source', 'Unknown')}\n"
        headlines_text += f"   Summary: {headline.get('summary', 'No summary')}\n\n"
    
    # Generate gapping stocks section
    gapping_text = "\n## What's moving — After-hours & Premarket\n\n"
    if gapping_stocks:
        # Handle both list and dict structures
        if isinstance(gapping_stocks, dict):
            # New Tradier structure
            ah_moves = gapping_stocks.get("after_hours", [])
            pre_moves = gapping_stocks.get("premarket", [])
            
            # Add after-hours movers
            if ah_moves:
                gapping_text += "**After-hours Movers:**\n\n"
                for stock in ah_moves[:5]:
                    ticker = stock.get('ticker', '')
                    move = stock.get('move', '')
                    why = stock.get('why', '')
                    gapping_text += f"**{ticker}** {move}\n"
                    gapping_text += f"{why}\n\n"
            
            # Add premarket movers
            if pre_moves:
                gapping_text += "**Premarket Movers:**\n\n"
                for stock in pre_moves[:5]:
                    ticker = stock.get('ticker', '')
                    move = stock.get('move', '')
                    why = stock.get('why', '')
                    gapping_text += f"**{ticker}** {move}\n"
                    gapping_text += f"{why}\n\n"
        else:
            # Old list structure
            for stock in gapping_stocks[:5]:  # Top 5 gapping stocks
                ticker = stock['ticker']
                gap_pct = stock['gap_pct']
                current_price = stock['current_price']
                prev_close = stock['prev_close']
                
                # Get news for this stock
                news_items = fetch_stock_news(ticker)
                news_summary = news_items[0].get('summary', f'{ticker} showing significant premarket activity') if news_items else f'{ticker} experiencing unusual trading volume'
                
                gapping_text += f"**{ticker}**\n"
                gapping_text += f"**{gap_pct:+.2f}%**\n\n"
                gapping_text += f"{news_summary} The stock is currently trading at ${current_price:.2f} compared to yesterday's close of ${prev_close:.2f}. "
                gapping_text += f"Traders should monitor for follow-through momentum and any additional news catalysts.\n\n"
    else:
        gapping_text += "No significant gapping stocks detected in premarket trading. Monitor major indices and key earnings reports for potential catalysts.\n\n"
    
    def _fmt_price(value: Any) -> str:
        try:
            num = float(value) if value is not None else None
        except (TypeError, ValueError):
            num = None
        if num is None or num <= 0:
            return "n/a"
        return f"${num:.2f}"

    def _fmt_level(value: Any) -> str:
        try:
            num = float(value) if value is not None else None
        except (TypeError, ValueError):
            num = None
        if num is None or num <= 0:
            return "n/a"
        return f"${num:.2f}"

    def _fmt_vix(value: Any) -> str:
        try:
            num = float(value) if value is not None else None
        except (TypeError, ValueError):
            num = None
        if num is None or num <= 0:
            return "n/a"
        return f"{num:.2f}"

    spy_line = (
        f"- SPY: {_fmt_price(spy_data.get('current_price'))} "
        f"(Support: {_fmt_level(spy_data.get('support'))}, "
        f"Resistance: {_fmt_level(spy_data.get('resistance'))})"
    )
    qqq_line = (
        f"- QQQ: {_fmt_price(qqq_data.get('current_price'))} "
        f"(Support: {_fmt_level(qqq_data.get('support'))}, "
        f"Resistance: {_fmt_level(qqq_data.get('resistance'))})"
    )
    vix_line = f"- VIX: {_fmt_vix(vix_data.get('current_price'))}"

    summary = f"""
## Executive Summary
Market conditions appear stable with key indices showing normal trading ranges. Focus on major economic catalysts and earnings reports for directional moves. The current market environment suggests a balanced risk-reward scenario for traders.{gapping_text}

## Key Market Headlines
{headlines_text}

## Technical Analysis & Daily Range Insights
Key support and resistance levels are being tested as markets consolidate. Monitor volume and momentum indicators for breakout signals. The expected trading ranges suggest moderate volatility with potential for directional moves on significant news.

## Market Sentiment & Outlook
Risk sentiment remains balanced with mixed signals from various sectors. Traders should watch for sector rotation opportunities and prepare for potential market shifts based on upcoming economic data releases.

## Key Levels to Watch
{spy_line}
{qqq_line}
{vix_line}
"""
    return summary


def generate_email_content(summary: str, headlines: List[Dict[str, Any]], expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]] = None) -> str:
    """Generate HTML email content"""
    sections = parse_summary_sections(summary)
    
    # Generate headlines HTML with enhanced summaries (no Source field)
    headlines_html = ""
    for i, headline in enumerate(headlines[:7], 1):
        # Use enhanced summary if available, fallback to original summary
        summary_text = (headline.get('summary_2to5') or headline.get('summary') or '').strip()
        headlines_html += f"""
        <tr>
            <td style="padding:12px 0;border-bottom:1px solid #eee;">
                <div style="display:flex;align-items:flex-start;">
                    <span style="background:#3498db;color:#fff;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;margin-right:12px;flex-shrink:0;">{i}</span>
                    <div style="flex:1;">
                        <strong style="color:#2c3e50;font-size:14px;">{headline.get('headline','')}</strong><br>
                        <span style="color:#34495e;font-size:13px;line-height:1.4;margin-top:4px;display:block;">{summary_text}</span>
                    </div>
                </div>
            </td>
        </tr>"""
    
    # Market data
    spy_data = expected_range.get('spy', {})
    qqq_data = expected_range.get('qqq', {})
    vix_data = expected_range.get('vix', {})
    
    # Format sections with proper HTML
    def format_section_content(content):
        if not content:
            return '<p style="color: #7f8c8d; font-style: italic;">No content available.</p>'
        # Convert line breaks to paragraphs
        paragraphs = content.split('\n\n')
        html_paragraphs = []
        for para in paragraphs:
            if para.strip():
                html_paragraphs.append(f'<p style="margin: 0 0 12px 0;">{para.strip()}</p>')
        return '\n'.join(html_paragraphs) if html_paragraphs else '<p style="color: #7f8c8d; font-style: italic;">No content available.</p>'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Morning Market Brief</title>
        <style>
            .section-header {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 8px;
                margin: 25px 0 15px 0;
                font-size: 18px;
                font-weight: bold;
            }}
            .market-snapshot {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #3498db;
            }}
            .section-content {{
                background: #ffffff;
                padding: 20px;
                border-radius: 8px;
                margin: 15px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f8f9fa; margin: 0; padding: 20px;">
        <div style="max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 300;">Morning Market Brief</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{datetime.now().strftime('%A, %B %d, %Y')}</p>
            </div>
            
            <div class="market-snapshot">
                <h3 style="margin-top: 0; color: #2c3e50; font-size: 20px;">Market Snapshot</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                    <div style="text-align: center; padding: 15px; background: white; border-radius: 6px;">
                        <div style="font-size: 24px; font-weight: bold; color: #2c3e50;">${spy_data.get('current_price', 0):.2f}</div>
                        <div style="font-size: 14px; color: #7f8c8d;">SPY</div>
                    </div>
                    <div style="text-align: center; padding: 15px; background: white; border-radius: 6px;">
                        <div style="font-size: 24px; font-weight: bold; color: #2c3e50;">${qqq_data.get('current_price', 0):.2f}</div>
                        <div style="font-size: 14px; color: #7f8c8d;">QQQ</div>
                    </div>
                    <div style="text-align: center; padding: 15px; background: white; border-radius: 6px;">
                        <div style="font-size: 24px; font-weight: bold; color: #2c3e50;">{vix_data.get('current_price', 0):.2f}</div>
                        <div style="font-size: 14px; color: #7f8c8d;">VIX</div>
                    </div>
                </div>
            </div>
            
            <div style="padding: 30px;">
                <div class="section-content">
                    <h3 class="section-header">Executive Summary</h3>
                    {format_section_content(sections.get('executive_summary', ''))}
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">What's moving — After-hours & Premarket</h3>
                    {format_section_content(sections.get('gapping_stocks', ''))}
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">Key Market Headlines</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        {headlines_html}
                    </table>
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">Technical Analysis & Daily Range Insights</h3>
                    {format_section_content(sections.get('technical_analysis', ''))}
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">Market Sentiment & Outlook</h3>
                    {format_section_content(sections.get('market_sentiment', ''))}
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">Key Levels to Watch</h3>
                    {format_section_content(sections.get('key_levels', ''))}
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, #ecf0f1 0%, #bdc3c7 100%); padding: 25px; text-align: center; border-top: 1px solid #bdc3c7;">
                <p style="margin: 0; font-size: 16px; color: #2c3e50;">
                    <strong>Powered by Options Plunge</strong>
                </p>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #7f8c8d;">
                    Professional market analysis for informed trading decisions
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


def generate_html_content_with_summary(summary: str, headlines: List[Dict[str, Any]], 
                                      expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]], 
                                      subscriber_summary: str = None) -> str:
    """Generate beautiful HTML content with improved styling and better spacing"""
    # Get current date
    current_date = datetime.now().strftime('%A, %B %d, %Y')
    
    # Enrich ranges with pivots for HTML Key Levels (Daily/Weekly S & R)
    piv_expected = enrich_expected_range_with_pivots(expected_range or {})
    # Get key price data for styling
    spy_data = piv_expected.get('spy', {})
    qqq_data = piv_expected.get('qqq', {})
    
    # Convert markdown to HTML with proper headline formatting
    # Split by sections and process each one properly
    sections = summary.split('## ')
    summary_html = ""
    
    for i, section in enumerate(sections):
        if i == 0:
            # First section (before any ##) - just add as-is
            summary_html += section
        else:
            # Section with ## header
            lines = section.split('\n')
            if lines:
                header = lines[0].strip()
                content = '\n'.join(lines[1:]).strip()
                
                # Add the header
                summary_html += f'<h2 class="section-header">{header}</h2>\n\n'
                
                # Add the content
                if content:
                    summary_html += f'<div class="section-content">{content}</div>\n\n'
    
    # Format headlines with proper spacing - only process if we have headlines
    if headlines:
        # Find the headlines section and replace it with formatted HTML
        headlines_start = summary_html.find('<h2 class="section-header">Key Market Headlines</h2>')
        if headlines_start != -1:
            # Find where the headlines section ends
            headlines_end = summary_html.find('<h2 class="section-header">Technical Analysis', headlines_start)
            if headlines_end == -1:
                headlines_end = len(summary_html)
            
            # Extract the headlines section
            headlines_section = summary_html[headlines_start:headlines_end]
            
            # Create formatted headlines HTML with better spacing (no Source field)
            formatted_headlines = '<h2 class="section-header">Key Market Headlines</h2>'
            for i, headline in enumerate(headlines[:7], 1):
                # Use enhanced summary if available, fallback to original summary
                summary_text = (headline.get('summary_2to5') or headline.get('summary') or '').strip()
                formatted_headlines += f"""
                <div class="headline-item">
                    <div class="headline-number">{i}.</div>
                    <div class="headline-content">
                        <div class="headline-title">{headline.get('headline', '')}</div>
                        <div class="headline-summary">{summary_text}</div>
                    </div>
                </div>"""
            
            # Replace the headlines section
            summary_html = summary_html[:headlines_start] + formatted_headlines + summary_html[headlines_end:]
    
    # Add subscriber summary if provided with enhanced styling
    subscriber_html = ""
    if subscriber_summary:
        # Parse subscriber summary for better formatting
        lines = subscriber_summary.strip().split('\n')
        formatted_summary = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith('**') and line.endswith('**'):
                # Bold headers
                formatted_summary += f'<div class="summary-header">{line}</div>'
            elif line.startswith('- **'):
                # List items with bold tickers
                formatted_summary += f'<div class="summary-list-item">{line}</div>'
            elif line.startswith('**Levels to watch'):
                # Special section
                formatted_summary += f'<div class="summary-levels-header">{line}</div>'
            elif line.startswith('- Support:') or line.startswith('- Resistance:'):
                # Level items
                formatted_summary += f'<div class="summary-level-item">{line}</div>'
            elif line.startswith('**Tomorrow:**'):
                # Tomorrow section
                formatted_summary += f'<div class="summary-tomorrow">{line}</div>'
            elif line:
                # Regular text
                formatted_summary += f'<div class="summary-text">{line}</div>'
        
        subscriber_html = f"""
        <div class="subscriber-summary">
            <div class="summary-header-main">
                <i class="fas fa-chart-line"></i>
                <span>Subscriber Summary</span>
            </div>
            <div class="summary-content">
                {formatted_summary}
            </div>
        </div>
        <hr style="margin: 30px 0; border: none; border-top: 2px solid #e9ecef;">
        <p style="text-align: center; color: #6c757d; font-style: italic; font-size: 14px;">
            This summary provides key market insights for active traders. For detailed analysis, visit our full market brief.
        </p>"""
    
    # Add gapping stocks section if available
    gapping_stocks_html = ""
    if gapping_stocks:
        gapping_stocks_html = """
        <div class="section-content">
            <h2 class="section-header">🚀 Gapping Stocks</h2>"""
        
        # Handle both list and dict structures
        if isinstance(gapping_stocks, dict):
            # New Tradier structure
            ah_moves = gapping_stocks.get("after_hours", [])
            pre_moves = gapping_stocks.get("premarket", [])
            
            # Add after-hours movers
            if ah_moves:
                gapping_stocks_html += '<h3 style="color: #e74c3c; margin: 15px 0 10px 0;">After-hours Movers</h3>'
                for stock in ah_moves[:5]:
                    ticker = stock.get('ticker', '')
                    # Handle both old format (move/why) and new format (gap_pct/current_price/prev_close)
                    if stock.get('move') and stock.get('why'):
                        move = stock.get('move', '')
                        why = stock.get('why', '')
                    else:
                        # New format - create move and why from gap_pct and prices
                        gap_pct = stock.get('gap_pct', 0)
                        current_price = stock.get('current_price', 0)
                        prev_close = stock.get('prev_close', 0)
                        move = f"{gap_pct:+.2f}%"
                        why = f"${current_price:.2f} vs ${prev_close:.2f}"
                    gapping_stocks_html += f"""
                    <div class="gapping-stock-item">
                        <strong class="ticker">{ticker}</strong>: <span class="move">{move}</span> - <span class="why">{why}</span>
                    </div>"""
            
            # Add premarket movers
            if pre_moves:
                gapping_stocks_html += '<h3 style="color: #27ae60; margin: 15px 0 10px 0;">Premarket Movers</h3>'
                for stock in pre_moves[:5]:
                    ticker = stock.get('ticker', '')
                    # Handle both old format (move/why) and new format (gap_pct/current_price/prev_close)
                    if stock.get('move') and stock.get('why'):
                        move = stock.get('move', '')
                        why = stock.get('why', '')
                    else:
                        # New format - create move and why from gap_pct and prices
                        gap_pct = stock.get('gap_pct', 0)
                        current_price = stock.get('current_price', 0)
                        prev_close = stock.get('prev_close', 0)
                        move = f"{gap_pct:+.2f}%"
                        why = f"${current_price:.2f} vs ${prev_close:.2f}"
                    gapping_stocks_html += f"""
                    <div class="gapping-stock-item">
                        <strong class="ticker">{ticker}</strong>: <span class="move">{move}</span> - <span class="why">{why}</span>
                    </div>"""
        else:
            # Old list structure
            for stock in gapping_stocks[:5]:
                ticker = stock.get('ticker', '')
                # Handle both old format (move/why) and new format (gap_pct/current_price/prev_close)
                if stock.get('move') and stock.get('why'):
                    move = stock.get('move', '')
                    why = stock.get('why', '')
                else:
                    # New format - create move and why from gap_pct and prices
                    gap_pct = stock.get('gap_pct', 0)
                    current_price = stock.get('current_price', 0)
                    prev_close = stock.get('prev_close', 0)
                    move = f"{gap_pct:+.2f}%"
                    why = f"${current_price:.2f} vs ${prev_close:.2f}"
                gapping_stocks_html += f"""
                <div class="gapping-stock-item">
                    <strong class="ticker">{ticker}</strong>: <span class="move">{move}</span> - <span class="why">{why}</span>
                </div>"""
        
        gapping_stocks_html += "</div>"
    
    # Create the full HTML content with improved styling and better spacing
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Morning Market Brief</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        /* Mobile-first responsive design */
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
            margin: 0;
            padding: 10px;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 300;
        }}
        
        .header p {{
            margin: 10px 0 0 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 20px;
        }}
        
        .section-header {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
            margin: 20px 0 12px 0;
            font-size: 18px;
            font-weight: bold;
        }}
        
        .market-snapshot {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #3498db;
        }}
        
        .section-content {{
            background: #ffffff;
            padding: 15px;
            border-radius: 8px;
            margin: 12px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .subscriber-summary {{
            background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf1 100%);
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            border-left: 5px solid #17a2b8;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .summary-header-main {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .summary-header-main i {{
            margin-right: 8px;
            color: #17a2b8;
        }}
        
        .summary-content {{
            line-height: 1.6;
        }}
        
        .summary-header {{
            font-weight: bold;
            color: #2c3e50;
            margin: 12px 0 6px 0;
            font-size: 16px;
        }}
        
        .summary-list-item {{
            margin: 6px 0;
            padding-left: 12px;
            color: #495057;
        }}
        
        .summary-levels-header {{
            font-weight: bold;
            color: #2c3e50;
            margin: 12px 0 6px 0;
            font-size: 16px;
        }}
        
        .summary-level-item {{
            margin: 4px 0;
            padding-left: 12px;
            color: #495057;
        }}
        
        .summary-tomorrow {{
            font-weight: bold;
            color: #2c3e50;
            margin: 12px 0 6px 0;
            font-size: 16px;
        }}
        
        .summary-text {{
            margin: 6px 0;
            color: #495057;
        }}
        
        .headline-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 5px solid #3498db;
            display: flex;
            align-items: flex-start;
            box-shadow: 0 3px 6px rgba(0,0,0,0.08);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .headline-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 12px rgba(0,0,0,0.12);
        }}
        
        .headline-number {{
            color: #3498db;
            font-weight: bold;
            font-size: 18px;
            margin-right: 12px;
            min-width: 28px;
            background: #e3f2fd;
            padding: 6px 10px;
            border-radius: 50%;
            text-align: center;
            flex-shrink: 0;
        }}
        
        .headline-content {{
            flex: 1;
            min-width: 0;
        }}
        
        .headline-title {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 16px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        
        .headline-summary {{
            color: #495057;
            line-height: 1.6;
            font-size: 14px;
            margin-top: 6px;
        }}
        
        .gapping-stock-item {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            margin: 6px 0;
            border-left: 3px solid #28a745;
        }}
        
        .ticker {{
            color: #2c3e50;
            font-weight: bold;
        }}
        
        .move {{
            color: #28a745;
            font-weight: 500;
        }}
        
        .why {{
            color: #6c757d;
        }}
        
        .key-levels {{
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #ffc107;
        }}
        
        .level-item {{
            margin: 8px 0;
            font-weight: 500;
        }}
        
        .support {{
            color: #28a745;
        }}
        
        .resistance {{
            color: #dc3545;
        }}
        
        /* Tablet and desktop styles */
        @media (min-width: 768px) {{
            body {{
                padding: 20px;
            }}
            
            .container {{
                max-width: 800px;
            }}
            
            .header {{
                padding: 30px;
            }}
            
            .header h1 {{
                font-size: 28px;
            }}
            
            .header p {{
                font-size: 16px;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            .section-header {{
                margin: 25px 0 15px 0;
            }}
            
            .market-snapshot {{
                padding: 20px;
                margin: 20px 0;
            }}
            
            .section-content {{
                padding: 20px;
                margin: 15px 0;
            }}
            
            .subscriber-summary {{
                padding: 25px;
                margin: 25px 0;
            }}
            
            .summary-header-main {{
                margin-bottom: 20px;
                font-size: 22px;
            }}
            
            .summary-header-main i {{
                margin-right: 10px;
            }}
            
            .summary-header {{
                margin: 15px 0 8px 0;
            }}
            
            .summary-list-item {{
                margin: 8px 0;
                padding-left: 15px;
            }}
            
            .summary-levels-header {{
                margin: 15px 0 8px 0;
            }}
            
            .summary-level-item {{
                margin: 5px 0;
                padding-left: 15px;
            }}
            
            .summary-tomorrow {{
                margin: 15px 0 8px 0;
            }}
            
            .summary-text {{
                margin: 8px 0;
            }}
            
            .headline-item {{
                padding: 25px;
                margin: 25px 0;
            }}
            
            .headline-number {{
                font-size: 20px;
                margin-right: 20px;
                min-width: 30px;
                padding: 8px 12px;
            }}
            
            .headline-title {{
                font-size: 17px;
                margin-bottom: 10px;
            }}
            
            .headline-summary {{
                font-size: 15px;
                margin-top: 8px;
            }}
            
            .gapping-stock-item {{
                padding: 12px;
                margin: 8px 0;
            }}
            
            .key-levels {{
                padding: 20px;
                margin: 20px 0;
            }}
            
            .level-item {{
                margin: 10px 0;
            }}
        }}
    </style>
</head>
<body>

    <div class="container">

        <div class="header">
            <h1>Morning Market Brief</h1>
            <p>{current_date}</p>
        </div>

        <div class="content">
            {subscriber_html}

            <div class="section-content">
                {summary_html}
            </div>

            {gapping_stocks_html}

            <div class="key-levels">
                <h3 style="margin-top: 0; color: #856404;">Key Levels to Watch</h3>
                <div class="level-item">
                    <strong>SPY —</strong>
                    Daily <span class="support">S:</span> {(' / '.join(f"{x:.2f}" for x in spy_data.get('daily_supports', [])[:2])) if spy_data.get('daily_supports') else 'No data'};
                    <span class="resistance">R:</span> {(' / '.join(f"{x:.2f}" for x in spy_data.get('daily_resistances', [])[:2])) if spy_data.get('daily_resistances') else 'No data'};
                    Weekly <span class="support">S:</span> {(' / '.join(f"{x:.2f}" for x in spy_data.get('weekly_supports', [])[:2])) if spy_data.get('weekly_supports') else 'No data'};
                    <span class="resistance">R:</span> {(' / '.join(f"{x:.2f}" for x in spy_data.get('weekly_resistances', [])[:2])) if spy_data.get('weekly_resistances') else 'No data'}
                </div>
                <div class="level-item">
                    <strong>QQQ —</strong>
                    Daily <span class="support">S:</span> {(' / '.join(f"{x:.2f}" for x in qqq_data.get('daily_supports', [])[:2])) if qqq_data.get('daily_supports') else 'No data'};
                    <span class="resistance">R:</span> {(' / '.join(f"{x:.2f}" for x in qqq_data.get('daily_resistances', [])[:2])) if qqq_data.get('daily_resistances') else 'No data'};
                    Weekly <span class="support">S:</span> {(' / '.join(f"{x:.2f}" for x in qqq_data.get('weekly_supports', [])[:2])) if qqq_data.get('weekly_supports') else 'No data'};
                    <span class="resistance">R:</span> {(' / '.join(f"{x:.2f}" for x in qqq_data.get('weekly_resistances', [])[:2])) if qqq_data.get('weekly_resistances') else 'No data'}
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    return html_content


# ---------------------------------------------------------------------------
# Morning-brief email context builder
# ---------------------------------------------------------------------------
#
# `send_market_brief_to_subscribers` historically built its email body via the
# inline `generate_enhanced_html()` in `market_brief_generator_fixed.py` and
# handed the already-complete HTML document to `emails.send_daily_brief_direct`,
# which re-wrapped it inside a second `<html>/<body>` shell. That nested
# structure caused Gmail/Outlook to strip the inner `<style>` block and
# render the email unstyled.
#
# The helper below mirrors what the CLI tool `send_morning_brief.py` does:
# it builds a context dict compatible with `templates/email/morning_brief.html.jinja`
# and lets `emailer.render_morning_brief()` produce a single well-formed email
# document (same pattern the weekly brief already uses).


_RECAP_BOLD_LINE = re.compile(r"^\s*\*{2}([^*\n]+?)\*{2}\s*:?\s*$")
_RECAP_INLINE_BOLD = re.compile(r"\*{2}(.+?)\*{2}")
_RECAP_INLINE_ITALIC = re.compile(r"(?<!\*)\*(?!\s)([^*\n]+?)\*(?!\*)")
_RECAP_LEADING_LABEL = re.compile(r"^\s*\*{2}[^*\n]+?\*{2}\s*:?\s*")
_RECAP_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _strip_markdown_for_subject(text: str) -> str:
    """Return ``text`` with markdown emphasis stripped and whitespace collapsed.

    Used when deriving the email's subject_theme / preheader from AI output
    that may include ``**Market Overview**`` style labels. We:
      1. Drop any leading ``**Label**`` line entirely (it's a section title,
         not a sentence).
      2. Replace remaining ``**bold**`` / ``*italic*`` spans with their
         inner text.
      3. Remove residual stray ``*`` characters.
      4. Collapse runs of whitespace.
    """
    if not text:
        return ""
    cleaned = _RECAP_LEADING_LABEL.sub("", text, count=1)
    cleaned = _RECAP_INLINE_BOLD.sub(r"\1", cleaned)
    cleaned = _RECAP_INLINE_ITALIC.sub(r"\1", cleaned)
    cleaned = cleaned.replace("**", "").replace("*", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _truncate_at_word(text: str, limit: int) -> str:
    """Truncate ``text`` to ``limit`` chars on a word boundary, adding an
    ellipsis. Never cuts mid-word.
    """
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:-—")
    if not cut:
        cut = text[:limit].rstrip()
    return cut + "…"


def _derive_subject_theme(summary: str, fallback: str = "Morning Market Brief") -> str:
    """Pick a clean, complete-thought title from ``summary``.

    Prefers the first full sentence if it fits in ~80 chars; otherwise
    returns the fallback so the h1 is never a truncated fragment.
    """
    cleaned = _strip_markdown_for_subject(summary)
    if not cleaned:
        return fallback
    first = _RECAP_SENTENCE_SPLIT.split(cleaned, maxsplit=1)[0].strip()
    first = first.rstrip(".!?").strip()
    if not first:
        return fallback
    if len(first) <= 80:
        return first
    return fallback


def _build_preheader_tagline(
    n_premarket: int,
    n_afterhours: int,
    n_headlines: int,
    spy_support: str,
    spy_resistance: str,
) -> str:
    """Build a short, data-driven preheader that reads like an email tagline
    describing what's inside the brief — NOT a truncated sentence from the
    AI narrative.

    Examples:
      "8 premarket movers · SPY 528–533 · today's plan inside"
      "3 after-hours movers · 6 top headlines · key levels & plan"
      "Your morning brief — key levels, movers, and today's plan"

    Kept under ~90 characters so Gmail's inbox preview doesn't truncate it.
    """
    parts: List[str] = []

    if n_premarket > 0:
        parts.append(f"{n_premarket} premarket mover{'s' if n_premarket != 1 else ''}")
    elif n_afterhours > 0:
        parts.append(f"{n_afterhours} after-hours mover{'s' if n_afterhours != 1 else ''}")

    if spy_support and spy_support != "—" and spy_resistance and spy_resistance != "—":
        parts.append(f"SPY {spy_support}–{spy_resistance}")
    elif spy_resistance and spy_resistance != "—":
        parts.append(f"SPY R {spy_resistance}")

    if n_headlines > 0 and len(parts) < 2:
        parts.append(f"{n_headlines} top headline{'s' if n_headlines != 1 else ''}")

    if not parts:
        return "Your morning brief — key levels, movers, and today's plan"

    parts.append("today's plan inside")
    return " · ".join(parts)


def _render_recap_inline(text: str) -> str:
    """Escape ``text`` then convert inline markdown emphasis to HTML.

    Handles ``**bold**`` → ``<strong>`` and ``*italic*`` → ``<em>``.
    Any stray/unmatched ``**`` tokens are stripped as a final defense so raw
    asterisks never leak into the rendered email body.
    """
    from html import escape as _html_escape

    out = _html_escape(text)
    out = _RECAP_INLINE_BOLD.sub(r"<strong>\1</strong>", out)
    out = _RECAP_INLINE_ITALIC.sub(r"<em>\1</em>", out)
    return out.replace("**", "")


def _markdown_to_recap_html(md: str) -> str:
    """Render a small subset of markdown (headings, bullets, paragraphs) into the
    `.llm-recap-body` structure that the morning/weekly email templates expect.

    Supported markdown:
      - ``# Title`` / ``## Heading`` / ``### Subheading``
      - Standalone ``**Label**`` (or ``**Label**:``) lines — promoted to
        ``<h3 class="llm-subheading">`` so the GPT pipeline's inline bold
        section titles (e.g. ``**Market Overview**``) render as real styled
        subheadings instead of paragraphs with raw asterisks.
      - ``-`` / ``•`` / numbered bullets
      - Inline ``**bold**`` and ``*italic*`` inside paragraphs + list items.

    This is intentionally a local copy of the helper in `send_morning_brief.py`
    to avoid cross-module imports from the CLI tool. Keep the two in sync if
    either grows new markdown features.
    """
    from html import escape

    if not md:
        return ""

    lines = md.splitlines()
    html_lines: List[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            close_list()
            html_lines.append("")
            continue
        if stripped.startswith("### "):
            close_list()
            html_lines.append(f'<h3 class="llm-subheading">{escape(stripped[4:].strip())}</h3>')
            continue
        if stripped.startswith("## "):
            close_list()
            html_lines.append(f'<h2 class="llm-heading">{escape(stripped[3:].strip())}</h2>')
            continue
        if stripped.startswith("# "):
            close_list()
            html_lines.append(f'<h1 class="llm-title">{escape(stripped[2:].strip())}</h1>')
            continue

        # Standalone **Label** line → promote to styled subheading. Covers the
        # Stage-A prompt's "**Market Overview**", "**Key Levels**", etc.
        bold_match = _RECAP_BOLD_LINE.match(stripped)
        if bold_match:
            close_list()
            label = bold_match.group(1).strip()
            html_lines.append(f'<h3 class="llm-subheading">{escape(label)}</h3>')
            continue

        is_bullet = False
        bullet_text = ""
        if stripped.startswith(("- ", "• ")):
            is_bullet = True
            bullet_text = stripped[2:].strip()
        else:
            parts = stripped.split(". ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                is_bullet = True
                bullet_text = stripped

        if is_bullet:
            if not in_list:
                html_lines.append('<ul class="llm-list">')
                in_list = True
            html_lines.append(f"<li>{_render_recap_inline(bullet_text)}</li>")
            continue

        close_list()
        html_lines.append(f'<p class="llm-text">{_render_recap_inline(stripped)}</p>')

    close_list()
    body = "\n".join(html_lines).strip()
    return f'<div class="llm-recap-body">{body}</div>' if body else ""


def _build_morning_brief_context(
    summary: str,
    filtered_headlines: List[Dict[str, Any]],
    expected_range: Dict[str, Any],
    gapping_stocks: Any,
    subscriber_summary: Optional[str],
    subscriber_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble a template context compatible with morning_brief.html.jinja.

    Scheduler-side callers (`send_market_brief_to_subscribers` and the
    standalone fallback path) pass their existing intermediate variables; this
    helper normalizes them into the fields the Jinja template expects.
    """
    # Handle gapping_stocks being either dict or list (legacy shape).
    if isinstance(gapping_stocks, dict):
        ah_raw = gapping_stocks.get("after_hours", []) or []
        pre_raw = gapping_stocks.get("premarket", []) or []
    else:
        ah_raw = gapping_stocks or []
        pre_raw = []

    def _norm_mover(m: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ticker": m.get("ticker") or m.get("symbol") or "",
            "move": m.get("move") or m.get("change") or "",
            "why": m.get("why") or m.get("reason") or m.get("summary") or "",
            "source_url": m.get("source_url") or m.get("url") or "",
        }

    ah_moves = [_norm_mover(m) for m in ah_raw[:8] if m.get("ticker") or m.get("symbol")]
    premarket_moves = [_norm_mover(m) for m in pre_raw[:8] if m.get("ticker") or m.get("symbol")]

    # Normalize headlines: template expects {headline, summary}.
    news_headlines: List[Dict[str, Any]] = []
    for h in (filtered_headlines or [])[:6]:
        title = h.get("headline") or h.get("title") or ""
        if not title:
            continue
        blurb = h.get("summary_2to5") or h.get("summary") or h.get("description") or ""
        news_headlines.append({"headline": title, "summary": blurb})

    spy = (expected_range or {}).get("spy", {}) if isinstance(expected_range, dict) else {}

    def _fmt_level(val: Any) -> str:
        if val is None or val == "" or val == "N/A":
            return "—"
        try:
            return f"{float(val):.2f}"
        except (TypeError, ValueError):
            return str(val)

    # Build URLs for unsubscribe/preferences. The scheduler renders the email
    # body ONCE and then sends it to many recipients, so we embed the sentinel
    # token `__RECIPIENT_EMAIL__` and let `emails.send_daily_brief_direct` do a
    # per-recipient `.replace()` before shipping each message. If a concrete
    # subscriber_email is passed (e.g. CLI test sends), we render the real URL
    # directly so no placeholder remains.
    server_name = os.getenv("SERVER_NAME", "optionsplunge.com")
    scheme = os.getenv("PREFERRED_URL_SCHEME", "https")
    preferences_url = f"{scheme}://{server_name}/market_brief"
    if subscriber_email:
        unsubscribe_url = f"{scheme}://{server_name}/unsubscribe/{subscriber_email}"
    else:
        unsubscribe_url = f"{scheme}://{server_name}/unsubscribe/__RECIPIENT_EMAIL__"

    # Render the GPT subscriber summary into the hero `.llm-recap-body` block.
    llm_daily_recap_html = _markdown_to_recap_html(subscriber_summary) if subscriber_summary else ""

    now_et = datetime.now(pytz.timezone("America/New_York"))
    date_human = now_et.strftime("%A, %B %d, %Y")

    # Derive a short subject theme from the first complete sentence of the
    # summary (with markdown stripped) — fall back to the generic title when
    # the first sentence is too long, so the <h1> is always a clean, complete
    # thought and never a mid-word truncation like "remaine…".
    subject_theme = _derive_subject_theme(summary, fallback="Morning Market Brief")

    # Preheader: short, structured tagline describing WHAT the email contains
    # (mover counts, key SPY levels, plan) — NOT a truncated sentence from
    # the GPT narrative. This renders as the inbox preview and the small
    # subtitle under the header <h1>.
    spy_support_fmt = _fmt_level(spy.get("support"))
    spy_resistance_fmt = _fmt_level(spy.get("resistance"))
    preheader = _build_preheader_tagline(
        n_premarket=len(premarket_moves),
        n_afterhours=len(ah_moves),
        n_headlines=len(news_headlines),
        spy_support=spy_support_fmt,
        spy_resistance=spy_resistance_fmt,
    )

    levels_methodology = None
    try:
        vix_val = (expected_range or {}).get("vix", {}).get("current_price") if isinstance(expected_range, dict) else None
        vix_val = float(vix_val) if vix_val is not None else None
        spy_px = float(spy.get("current_price")) if spy.get("current_price") is not None else None
        spy_sigma = float(spy.get("sigma")) if spy.get("sigma") is not None else None
        spy_sigma_pct = float(spy.get("sigma_pct")) if spy.get("sigma_pct") is not None else None

        if vix_val and spy_px and spy_sigma and spy_sigma > 0:
            if not spy_sigma_pct or spy_sigma_pct <= 0:
                spy_sigma_pct = (spy_sigma / spy_px) * 100.0
            levels_methodology = {
                "vix": vix_val,
                "spy_sigma_dollars": spy_sigma,
                "spy_sigma_pct": spy_sigma_pct,
                "caption": (
                    f"These levels come from the VIX (market 'fear gauge'). "
                    f"With VIX at {vix_val:.1f}, SPY typically moves about +/-${spy_sigma:.2f} in a day "
                    f"({spy_sigma_pct:.2f}%). "
                    f"S1/R1 mark that usual range, S2/R2 are a wider range, and R3 is an extreme upside move. "
                    f"(QQQ and IWM are scaled versions of SPY.)"
                ),
            }
    except Exception:
        levels_methodology = None

    return {
        "subject_theme": subject_theme,
        "date": date_human,
        "preheader": preheader,
        "logo_url": "",
        "market_overview": summary or "",
        "llm_daily_recap_html": llm_daily_recap_html,
        "news_headlines": news_headlines,
        "ah_moves": ah_moves,
        "premarket_moves": premarket_moves,
        "macro_data": "",
        "earnings": [],
        "sectors": "",
        "spy_s1": _fmt_level(spy.get("support")),
        "spy_s2": _fmt_level(spy.get("support2")),
        "spy_r1": _fmt_level(spy.get("resistance")),
        "spy_r2": _fmt_level(spy.get("resistance2")),
        "spy_r3": _fmt_level(spy.get("resistance3")),
        "extra_levels": "",
        "levels_methodology": levels_methodology,
        "day_plan": [],
        "swing_plan": [],
        "on_deck": "",
        "cta_url": f"{scheme}://{server_name}",
        "unsubscribe_url": unsubscribe_url,
        "preferences_url": preferences_url,
    }


def send_market_brief_to_subscribers():
    """Main function to generate and send market brief to all subscribers"""
    try:
        logger.info("Starting market brief generation and distribution")
        
        # Generate the brief
        headlines = fetch_news()
        filtered_headlines = filter_market_headlines(headlines)
        
        # Enhance headlines with 2-5 sentence summaries
        if HEADLINE_SUMMARIZER_AVAILABLE and OPENAI_API_KEY:
            try:
                filtered_headlines = summarize_headlines(filtered_headlines)
                logger.info("✅ Headlines enhanced with AI summaries")
            except Exception as e:
                logger.warning(f"Headline summarization failed, using original summaries: {e}")
        
        stock_prices = fetch_stock_prices()
        expected_range = calculate_expected_range(stock_prices)
        
        # Fetch gapping stocks for the new section
        gapping_stocks = fetch_gapping_stocks()
        
        # Generate summary with gapping stocks
        summary = summarize_news(filtered_headlines, expected_range, gapping_stocks)
        
        # NEW: Generate GPT summary
        subscriber_summary = None
        if GPT_AVAILABLE and OPENAI_API_KEY:
            # Handle gapping_stocks structure (could be list or dict)
            if isinstance(gapping_stocks, dict):
                ah_moves = gapping_stocks.get("after_hours", [])[:8]
                premarket_moves = gapping_stocks.get("premarket", [])[:8]
            else:
                # If it's a list, use it directly
                ah_moves = gapping_stocks[:8] if gapping_stocks else []
                premarket_moves = []
            
            brief_data = {
                "market_overview": summary,
                "ah_moves": ah_moves,
                "premarket_moves": premarket_moves,
                "earnings": [],  # Add earnings data if available
                "spy_s1": expected_range.get("spy", {}).get("support", "N/A"),
                "spy_s2": expected_range.get("spy", {}).get("support2", "N/A"),
                "spy_r1": expected_range.get("spy", {}).get("resistance", "N/A"),
                "spy_r2": expected_range.get("spy", {}).get("resistance2", "N/A"),
                "spy_r3": expected_range.get("spy", {}).get("resistance3", "N/A"),
            }
            
            try:
                gpt_summary = summarize_brief(brief_data)
                subscriber_summary = gpt_summary["subscriber_summary"]
                logger.info("✓ GPT summary generated successfully")
            except Exception as e:
                logger.warning(f"GPT summary failed, using fallback: {e}")
        else:
            logger.info("GPT summary not available, skipping")
        
        # Generate two variants:
        # - Site content: keep legacy layout without the Subscriber Summary
        # - Email content: rendered through the shared Jinja template
        #   `templates/email/morning_brief.html.jinja` via emailer.render_morning_brief,
        #   matching the weekly brief's render path. Produces a single well-formed
        #   HTML document so downstream senders don't need to wrap it again.
        site_content = generate_html_content_with_summary(summary, filtered_headlines, expected_range, gapping_stocks, None)

        from emailer import render_morning_brief
        email_context = _build_morning_brief_context(
            summary=summary,
            filtered_headlines=filtered_headlines,
            expected_range=expected_range,
            gapping_stocks=gapping_stocks,
            subscriber_summary=subscriber_summary,
        )
        try:
            email_content, _email_text = render_morning_brief(email_context)
        except Exception as render_err:
            # Fall back to the legacy site HTML if template rendering fails, so a
            # missing dependency never prevents the brief from going out.
            logger.error(f"render_morning_brief failed, falling back to site HTML: {render_err}")
            email_content = site_content

        # Persist latest brief content to a static file for website display
        try:
            base_dir = Path(__file__).resolve().parent
            out_dir = base_dir / 'static' / 'uploads'
            out_dir.mkdir(parents=True, exist_ok=True)
            latest_file = out_dir / 'brief_latest.html'
            latest_date_file = out_dir / 'brief_latest_date.txt'
            latest_file.write_text(site_content, encoding='utf-8')
            latest_date_file.write_text(datetime.now().strftime('%Y-%m-%d'), encoding='utf-8')
            logger.info(f"Wrote latest brief HTML to {latest_file}")
        except Exception as write_err:
            logger.warning(f"Failed to write latest brief HTML: {write_err}")
        
        # Use the new email system to send to confirmed subscribers
        from emails import send_daily_brief_direct

        # Visibility on config that commonly breaks sending
        try:
            cfg = (current_app.config if current_app else {})
            logger.info(
                "Email config — server:%s port:%s tls:%s ssl:%s sender:%s suppress_send:%s sendgrid:%s mailgun:%s ses:%s",
                cfg.get("MAIL_SERVER"),
                cfg.get("MAIL_PORT"),
                cfg.get("MAIL_USE_TLS"),
                cfg.get("MAIL_USE_SSL"),
                cfg.get("MAIL_DEFAULT_SENDER"),
                cfg.get("MAIL_SUPPRESS_SEND"),
                bool(os.getenv("SENDGRID_KEY")),
                bool(os.getenv("MAILGUN_DOMAIN") and os.getenv("MAILGUN_API_KEY")),
                bool(os.getenv("AWS_SES_ACCESS_KEY_ID") and os.getenv("AWS_SES_SECRET_ACCESS_KEY")),
            )
        except Exception:
            pass

        success_count = send_daily_brief_direct(email_content)

        # If nothing was sent, surface likely reasons
        if not success_count:
            try:
                from models import MarketBriefSubscriber, db  # already imported above, but safe
                total = db.session.query(MarketBriefSubscriber).count()
                confirmed = db.session.query(MarketBriefSubscriber).filter_by(confirmed=True).count()
                unsub = 0
                try:
                    unsub = db.session.query(MarketBriefSubscriber).filter_by(unsubscribed=True).count()
                except Exception:
                    pass
                logger.warning(
                    "Email send returned 0. Subscribers — total:%s confirmed:%s unsubscribed:%s. MAIL_SUPPRESS_SEND=%s, MAIL_DEFAULT_SENDER=%s",
                    total, confirmed, unsub,
                    (current_app.config.get("MAIL_SUPPRESS_SEND") if current_app else None),
                    (current_app.config.get("MAIL_DEFAULT_SENDER") if current_app else None),
                )
            except Exception as e:
                logger.warning(f"Could not introspect subscriber counts: {e}")
        
        logger.info(f"Market brief sent successfully to {success_count} confirmed subscribers")
        return success_count
        
    except Exception as e:
        logger.error(f"Error in market brief generation: {str(e)}")
        raise


def _missing_required_symbols(
    prices: Dict[str, Dict[str, float]],
    required: Optional[List[str]] = None,
) -> List[str]:
    """Return required symbols that are absent or have invalid prices."""
    required_symbols = [sym.lower() for sym in (required or DAILY_REQUIRED_MARKET_SYMBOLS)]
    missing: List[str] = []
    for symbol in required_symbols:
        data = prices.get(symbol) if isinstance(prices, dict) else None
        price = (data or {}).get('current_price') if isinstance(data, dict) else None
        try:
            valid = price is not None and float(price) > 0
        except (TypeError, ValueError):
            valid = False
        if not valid:
            missing.append(symbol.upper())
    return missing


def require_market_data(
    prices: Dict[str, Dict[str, float]],
    required: Optional[List[str]] = None,
) -> None:
    """Raise :class:`BriefDataUnavailable` if required market data is missing."""
    missing = _missing_required_symbols(prices, required=required)
    if missing:
        raise BriefDataUnavailable(
            "Market data unavailable: missing " + ", ".join(missing)
        )


def _write_brief_unavailable_sentinel(reason: str) -> str:
    """Write an honest public placeholder when the daily brief is unavailable."""
    try:
        base_dir = Path(__file__).resolve().parent
        out_dir = base_dir / "static" / "uploads"
        out_dir.mkdir(parents=True, exist_ok=True)
        latest_file = out_dir / "brief_latest.html"
        latest_date_file = out_dir / "brief_latest_date.txt"

        reason_text = (reason or "market data unavailable").strip()
        reason_html = escape(reason_text)
        reason_tag = re.sub(r"[^a-zA-Z0-9_-]+", "-", reason_text.lower()).strip("-")
        if not reason_tag:
            reason_tag = "market-data-unavailable"

        today = datetime.now().strftime("%Y-%m-%d")
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Options Plunge Morning Brief - Delayed</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #0f172a;
            background-color: #f4f6fb;
            margin: 0;
            padding: 28px;
        }}
        .container {{
            max-width: 720px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 35px 80px rgba(15,23,42,0.08);
        }}
        .header {{
            background: linear-gradient(135deg, #fff7d6 0%, #e0f2fe 100%);
            color: #0f172a;
            padding: 36px 32px;
            text-align: center;
        }}
        .content {{
            padding: 28px;
        }}
        .notice {{
            background: #fff7ed;
            border-left: 4px solid #f97316;
            border-radius: 10px;
            padding: 18px;
        }}
        .muted {{
            color: #64748b;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <p style="text-transform:uppercase;letter-spacing:0.22em;font-size:11px;margin:0 0 10px 0;">Options Plunge</p>
            <h1 style="margin:0;font-size:26px;font-weight:300;">Morning Brief Delayed</h1>
            <p style="margin:10px 0 0 0;font-size:15px;">{today}</p>
        </div>
        <div class="content">
            <div class="notice">
                <h2 style="margin:0 0 8px 0;font-size:18px;">Today's brief is delayed - market data provider unavailable.</h2>
                <p style="margin:0;">We are waiting for verified SPY and QQQ market data before publishing today's brief.</p>
                <p class="muted" style="margin:12px 0 0 0;">Reason: {reason_html}</p>
            </div>
        </div>
    </div>
</body>
</html>"""

        latest_file.write_text(html_content, encoding="utf-8")
        latest_date_file.write_text(f"unavailable:{today}:{reason_tag}", encoding="utf-8")
        logger.info("Wrote unavailable brief sentinel to %s", latest_file)
        return str(latest_file)
    except Exception as exc:
        logger.error("Failed to write unavailable brief sentinel: %s", exc)
        return ""


def generate_daily_brief_file_only() -> str:
    """Generate the daily brief HTML and write static/uploads/brief_latest.html without emailing.
    Returns the absolute path written.
    """
    try:
        stock_prices = fetch_stock_prices()
        try:
            require_market_data(stock_prices)
        except BriefDataUnavailable as exc:
            logger.error("Daily brief file generation aborted: %s", exc)
            return _write_brief_unavailable_sentinel(str(exc))

        # Generate the brief
        headlines = fetch_news()
        filtered_headlines = filter_market_headlines(headlines)

        # Enhance headlines with 2-5 sentence summaries
        if HEADLINE_SUMMARIZER_AVAILABLE and OPENAI_API_KEY:
            try:
                filtered_headlines = summarize_headlines(filtered_headlines)
                logger.info("✅ Headlines enhanced with AI summaries")
            except Exception as e:
                logger.warning(f"Headline summarization failed, using original summaries: {e}")

        expected_range = calculate_expected_range(stock_prices)

        # Fetch gapping stocks for the new section
        gapping_stocks = fetch_gapping_stocks()

        # Generate summary with gapping stocks
        summary = summarize_news(filtered_headlines, expected_range, gapping_stocks)

        # Include GPT subscriber summary only in email variant; for file write we use site content
        subscriber_summary = None
        if GPT_AVAILABLE and OPENAI_API_KEY:
            try:
                # Normalize gappers structure
                if isinstance(gapping_stocks, dict):
                    ah_moves = gapping_stocks.get("after_hours", [])[:8]
                    premarket_moves = gapping_stocks.get("premarket", [])[:8]
                else:
                    ah_moves = gapping_stocks[:8] if gapping_stocks else []
                    premarket_moves = []
                brief_data = {
                    "market_overview": summary,
                    "ah_moves": ah_moves,
                    "premarket_moves": premarket_moves,
                    "earnings": [],
                    "spy_s1": expected_range.get("spy", {}).get("support", "N/A"),
                    "spy_s2": expected_range.get("spy", {}).get("support2", "N/A"),
                    "spy_r1": expected_range.get("spy", {}).get("resistance", "N/A"),
                    "spy_r2": expected_range.get("spy", {}).get("resistance2", "N/A"),
                    "spy_r3": expected_range.get("spy", {}).get("resistance3", "N/A"),
                }
                gpt_summary = summarize_brief(brief_data)
                subscriber_summary = gpt_summary.get("subscriber_summary")
                logger.info("✓ GPT summary generated successfully")
            except Exception as e:
                logger.warning(f"GPT summary failed, using fallback: {e}")

        # Site content should not include subscriber summary
        site_content = generate_html_content_with_summary(
            summary, filtered_headlines, expected_range, gapping_stocks, None
        )

        base_dir = Path(__file__).resolve().parent
        out_dir = base_dir / "static" / "uploads"
        out_dir.mkdir(parents=True, exist_ok=True)
        latest_file = out_dir / "brief_latest.html"
        latest_date_file = out_dir / "brief_latest_date.txt"
        latest_file.write_text(site_content, encoding="utf-8")
        latest_date_file.write_text(datetime.now().strftime('%Y-%m-%d'), encoding='utf-8')
        logger.info(f"Wrote latest brief HTML to {latest_file}")
        return str(latest_file)
    except Exception as e:
        logger.error(f"Error generating daily brief file only: {e}")
        raise

if __name__ == "__main__":
    # For testing outside of Flask context
    try:
        # Import and create Flask app context
        from app import app
        with app.app_context():
            send_market_brief_to_subscribers()
    except ImportError:
        # If app import fails, just generate the brief without sending emails
        logger.info("Running in standalone mode - generating brief content only")
        try:
            stock_prices = fetch_stock_prices()
            try:
                require_market_data(stock_prices)
            except BriefDataUnavailable as exc:
                logger.error("Standalone market brief generation aborted: %s", exc)
                _write_brief_unavailable_sentinel(str(exc))
                raise

            # Generate the brief
            headlines = fetch_news()
            filtered_headlines = filter_market_headlines(headlines)
            
            # Enhance headlines with 2-5 sentence summaries
            if HEADLINE_SUMMARIZER_AVAILABLE and OPENAI_API_KEY:
                try:
                    filtered_headlines = summarize_headlines(filtered_headlines)
                    logger.info("✅ Headlines enhanced with AI summaries")
                except Exception as e:
                    logger.warning(f"Headline summarization failed, using original summaries: {e}")
            
            expected_range = calculate_expected_range(stock_prices)
            
            # Fetch gapping stocks for the new section
            gapping_stocks = fetch_gapping_stocks()
            
            # Generate summary with gapping stocks
            summary = summarize_news(filtered_headlines, expected_range, gapping_stocks)
            
            # NEW: Generate GPT summary for standalone mode
            subscriber_summary = None
            if GPT_AVAILABLE and OPENAI_API_KEY:
                # Handle gapping_stocks structure (could be list or dict)
                if isinstance(gapping_stocks, dict):
                    ah_moves = gapping_stocks.get("after_hours", [])[:8]
                    premarket_moves = gapping_stocks.get("premarket", [])[:8]
                else:
                    # If it's a list, use it directly
                    ah_moves = gapping_stocks[:8] if gapping_stocks else []
                    premarket_moves = []
                
                brief_data = {
                    "market_overview": summary,
                    "ah_moves": ah_moves,
                    "premarket_moves": premarket_moves,
                    "earnings": [],  # Add earnings data if available
                    "spy_s1": expected_range.get("spy", {}).get("support", "N/A"),
                    "spy_s2": expected_range.get("spy", {}).get("support2", "N/A"),
                    "spy_r1": expected_range.get("spy", {}).get("resistance", "N/A"),
                    "spy_r2": expected_range.get("spy", {}).get("resistance2", "N/A"),
                    "spy_r3": expected_range.get("spy", {}).get("resistance3", "N/A"),
                }
                
                try:
                    gpt_summary = summarize_brief(brief_data)
                    subscriber_summary = gpt_summary["subscriber_summary"]
                    logger.info("✓ GPT summary generated successfully")
                except Exception as e:
                    logger.warning(f"GPT summary failed, using fallback: {e}")
            else:
                logger.info("GPT summary not available, skipping")
            
            # Generate email content with GPT summary via the shared Jinja template
            # so the standalone fallback produces the same well-formed document as
            # the main scheduler path.
            try:
                from emailer import render_morning_brief
                email_context = _build_morning_brief_context(
                    summary=summary,
                    filtered_headlines=filtered_headlines,
                    expected_range=expected_range,
                    gapping_stocks=gapping_stocks,
                    subscriber_summary=subscriber_summary,
                )
                brief_content, _brief_text = render_morning_brief(email_context)
            except Exception as render_err:
                # Fall back to the site layout if template rendering isn't available
                # (e.g. running outside a Flask context without templates).
                logger.warning(f"render_morning_brief failed in standalone mode ({render_err}); using site HTML.")
                brief_content = generate_html_content_with_summary(
                    summary, filtered_headlines, expected_range, gapping_stocks, subscriber_summary
                )

            # Persist latest brief content to a static file for website display
            try:
                base_dir = Path(__file__).resolve().parent
                out_dir = base_dir / 'static' / 'uploads'
                out_dir.mkdir(parents=True, exist_ok=True)
                latest_file = out_dir / 'brief_latest.html'
                latest_date_file = out_dir / 'brief_latest_date.txt'
                latest_file.write_text(brief_content, encoding='utf-8')
                latest_date_file.write_text(datetime.now().strftime('%Y-%m-%d'), encoding='utf-8')
                logger.info(f"Wrote latest brief HTML to {latest_file}")
                logger.info("Market brief generated successfully in standalone mode")
            except Exception as write_err:
                logger.warning(f"Failed to write latest brief HTML: {write_err}")
        except Exception as e:
            logger.error(f"Error in standalone market brief generation: {str(e)}") 

def fetch_stock_prices_strict() -> Dict[str, Dict[str, float]]:
    """Fetch prices via providers.DataProvider without synthetic defaults.

    Returns ``{}`` when no provider yields a valid price for the required
    symbols so that :func:`has_valid_price_data` can short-circuit the
    brief instead of emitting fabricated levels.
    """
    prices = fetch_stock_prices()
    if has_valid_price_data(prices):
        return prices
    return {}


def has_valid_price_data(prices: Dict[str, Dict[str, float]], required: Optional[List[str]] = None) -> bool:
    """Verify that required symbols have non-zero price data."""

    required_symbols = [sym.lower() for sym in (required or ['spy', 'qqq'])]
    for symbol in required_symbols:
        data = prices.get(symbol)
        if not data:
            logger.warning("Missing price data for %s", symbol.upper())
            return False

        price = data.get('current_price')
        if price is None or price <= 0:
            logger.warning("Invalid price data for %s: %s", symbol.upper(), price)
            return False

    return True


def build_market_snapshot(
    prices: Dict[str, Dict[str, float]],
    symbols: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return a normalized market snapshot for newsletter and post copy.

    Only includes symbols whose ``current_price`` is a positive number. The
    output shape is intentionally simple and stable so deployed generators
    (newsletter, post-market, social) can consume it without re-implementing
    formatting and never need a hardcoded ``$0.00`` fallback::

        {"spy": {"price": 644.95, "change": 1.20, "change_percent": 0.18}, ...}

    Symbols that are missing or invalid are simply omitted from the result;
    callers should treat absence as "data unavailable" rather than zero.
    """
    requested = [sym.lower() for sym in (symbols or ['spy', 'qqq', 'iwm', 'vix'])]
    snapshot: Dict[str, Dict[str, Any]] = {}
    for symbol in requested:
        data = prices.get(symbol) if isinstance(prices, dict) else None
        if not isinstance(data, dict):
            continue
        price = data.get('current_price')
        try:
            price_f = float(price) if price is not None else None
        except (TypeError, ValueError):
            price_f = None
        if price_f is None or price_f <= 0:
            continue

        def _coerce_float(value: Any) -> Optional[float]:
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        snapshot[symbol] = {
            "price": round(price_f, 2),
            "change": _coerce_float(data.get('change')),
            "change_percent": _coerce_float(data.get('change_percent')),
        }
    return snapshot


#
# NOTE: `calculate_expected_range` is defined earlier in this file.
# A duplicate definition previously existed here; it has been removed to keep a
# single source of truth for the expected-range / key-level computation.