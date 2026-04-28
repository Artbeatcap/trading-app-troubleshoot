"""Small helper module for the daily market brief.

Historically this file was a 1.4k-line sibling of market_brief_generator.py
with copy-pasted Polygon/Alpha-Vantage/Finnhub/MarketWatch fetch logic,
deterministic sample-data fallbacks, and an inline ``generate_enhanced_html``
email renderer. As part of the data-source migration and the UI overhaul it
has been reduced to the two symbols still imported by
``market_brief_generator.py``:

    - CONVERSATIONAL_SYSTEM_PROMPT
    - fetch_gapping_stocks_enhanced()

Email HTML for the morning brief is now rendered via the shared Jinja
template ``templates/email/morning_brief.html.jinja`` (see
``emailer.render_morning_brief`` and
``market_brief_generator._build_morning_brief_context``). The previous
``generate_enhanced_html`` / ``_HTML_STYLES`` helpers were removed because
their output was a full ``<!DOCTYPE html>...</html>`` document that
``emails.send_daily_brief_direct`` then re-wrapped in a second ``<html>``
shell, which caused Gmail/Outlook to strip the inner ``<style>`` block.

All market data is sourced via ``providers.DataProvider`` (Polygon.io /
"Massive API"). No hardcoded sample movers are ever returned; when the
provider returns nothing the section simply renders an honest empty state.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

from providers import get_default_provider

logger = logging.getLogger(__name__)

NY = pytz.timezone("America/New_York")
MAX_MOVERS = int(os.getenv("GAPPING_MOVERS_LIMIT", "8"))


CONVERSATIONAL_SYSTEM_PROMPT = """You are a seasoned trader writing the morning brief for your trading desk.

Your style:
- Write like you're talking to fellow traders - casual but sharp
- Use short, punchy sentences that get to the point
- Include specific levels and setups traders can use
- Explain the "why" behind moves in plain English
- Sound like a human trader, not a news robot

Hard rules for levels (to avoid hallucinations):
- Treat provided support/resistance values as VIX-implied daily-move σ bands (±1σ, ±2σ, +3σ) from the data feed.
- Do NOT invent chart-based reasons (moving averages, prior highs/lows, VWAP, Fibonacci, "gap fill", etc.) for why these exact prices matter.
- If you reference the key levels, explain them only in terms of the σ band and rough historical probability (~68% for 1σ, ~95% for 2σ). Do not cite unprovided indicators.

Focus on:
1. What's moving and WHY (the story matters)
2. Key levels that actually matter for entries/exits
3. The setup - what kind of day are we looking at?
4. Specific trades to watch

Keep it conversational. No corporate speak. Make it something traders actually want to read at 6am."""


# ---------------------------------------------------------------------------
# Mover formatting + session split
# ---------------------------------------------------------------------------


def _now_et() -> datetime:
    return datetime.now(tz=NY)


def _format_move(
    ticker: str,
    change_pct: float,
    why: str,
    price: Optional[float] = None,
) -> Dict[str, Any]:
    if not ticker:
        ticker = "N/A"
    direction = "+" if change_pct >= 0 else ""
    price_fragment = ""
    if isinstance(price, (int, float)):
        price_fragment = f"@ ${price:.2f}"
    return {
        "ticker": ticker.upper(),
        "move": f"{direction}{change_pct:.2f}%",
        "why": (why or "Active flow").strip(),
        "price": price_fragment,
    }


def _split_session(movers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    movers = movers[: MAX_MOVERS * 2]
    if not movers:
        return {"premarket": [], "after_hours": []}
    now = _now_et()
    if now.hour < 9:
        return {"premarket": movers[:MAX_MOVERS], "after_hours": []}
    if now.hour >= 16:
        return {"premarket": [], "after_hours": movers[:MAX_MOVERS]}
    half = max(3, MAX_MOVERS // 2)
    return {
        "premarket": movers[:half],
        "after_hours": movers[half:half + MAX_MOVERS],
    }


def fetch_gapping_stocks_enhanced() -> Dict[str, List[Dict[str, Any]]]:
    """Return gapping movers split into premarket/after-hours buckets.

    Data source is Polygon's gainers+losers snapshots via
    `providers.DataProvider`. If no movers qualify we return empty
    buckets (no fabricated sample data).
    """
    dp = get_default_provider()
    gainers: List[Dict[str, Any]] = []
    losers: List[Dict[str, Any]] = []
    try:
        gainers = dp.get_gainers(limit=MAX_MOVERS * 2) or []
    except Exception as exc:
        logger.warning("get_gainers failed: %s", exc)
    try:
        losers = dp.get_losers(limit=MAX_MOVERS * 2) or []
    except Exception as exc:
        logger.warning("get_losers failed: %s", exc)

    seen: set[str] = set()
    movers: List[Dict[str, Any]] = []
    for item in list(gainers) + list(losers):
        tkr = (item.get("ticker") or "").upper()
        if not tkr or tkr in seen:
            continue
        seen.add(tkr)
        pct = item.get("change_pct")
        price = item.get("price")
        vol = item.get("volume") or 0
        if pct is None:
            continue
        reason = (
            f"Active flow ({int(vol):,} shares)"
            if isinstance(vol, (int, float)) and vol
            else "High participation"
        )
        movers.append(_format_move(tkr, float(pct), reason, price))

    return _split_session(movers)


__all__ = [
    "CONVERSATIONAL_SYSTEM_PROMPT",
    "fetch_gapping_stocks_enhanced",
]
