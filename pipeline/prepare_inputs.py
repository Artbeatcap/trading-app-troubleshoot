"""
Transform raw market data into compact BriefInput format to reduce token usage by ~90%.
Applies hard caps, rounding, and minification to all data.
"""

import json
import logging
from dataclasses import asdict
from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz

from schemas.brief_input import BriefInput, Ticker, Event, Level

logger = logging.getLogger(__name__)

# Hard caps to prevent token bloat
MAX_INDICES = 6
MAX_RATES = 3
MAX_EVENTS = 5
MAX_MOVERS = 5
MAX_LEVELS = 10
MAX_HEADLINES = 5

# Precision limits
PRICE_DECIMALS = 2
CHANGE_DECIMALS = 1
VOLUME_ROUND = 1000
HEADLINE_MAX_LEN = 100
EVENT_MAX_LEN = 50


def round_to_decimals(value: float, decimals: int) -> float:
    """Round float to specified decimal places."""
    if value is None:
        return 0.0
    return round(float(value), decimals)


def round_volume(volume: int) -> int:
    """Round volume to nearest 1000."""
    if volume is None:
        return 0
    return int(round(volume / VOLUME_ROUND) * VOLUME_ROUND)


def truncate_string(text: str, max_len: int) -> str:
    """Truncate string to max length."""
    if not text:
        return ""
    return text[:max_len].strip()


def _coerce_positive_price(value: Any) -> Optional[float]:
    """Return value as float if it represents a positive price, else None."""
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num <= 0:
        return None
    return num


def prepare_ticker_data(symbol: str, data: Dict[str, Any]) -> Optional[Ticker]:
    """Convert raw ticker data to compact Ticker format.

    Returns ``None`` when the input has no usable price. Returning a zeroed
    ticker here is a known footgun: the LLM and downstream renderers have
    formatted those zeros as ``$0.00`` in published copy when the upstream
    provider was unavailable. Callers must filter out ``None`` entries.
    """
    if not isinstance(data, dict):
        return None

    price = _coerce_positive_price(
        data.get("current_price")
        if data.get("current_price") is not None
        else data.get("price")
    )
    if price is None:
        return None

    change = data.get("change")
    change_percent = data.get("change_percent")
    return Ticker(
        symbol=symbol.upper(),
        price=round_to_decimals(price, PRICE_DECIMALS),
        change=round_to_decimals(change, PRICE_DECIMALS) if change is not None else 0.0,
        change_percent=(
            round_to_decimals(change_percent, CHANGE_DECIMALS)
            if change_percent is not None
            else 0.0
        ),
        volume=round_volume(data.get("volume", 0)),
        levels=[],
    )


def prepare_event_data(event: Dict[str, Any]) -> Event:
    """Convert raw event data to compact Event format."""
    return Event(
        time=event.get("time", "00:00")[:5],  # HH:MM format
        event=truncate_string(event.get("event", ""), EVENT_MAX_LEN),
        impact=event.get("impact", "Low"),
        why=event.get("why", "Market impact")
    )


def prepare_level_data(price: float, strength: str = "Medium") -> Level:
    """Convert raw level data to compact Level format."""
    return Level(
        price=round_to_decimals(price, PRICE_DECIMALS),
        label=strength
    )


def prepare_brief_input(raw_data: Dict[str, Any]) -> BriefInput:
    """
    Transform raw market data into compact BriefInput format.
    
    Args:
        raw_data: Raw data dict from AV/Tradier/etc containing:
            - expected_range: Dict with ticker data
            - headlines: List of news headlines
            - gapping_stocks/movers: List of stock data
            - economic_catalysts/events: List of economic events
            - support/resistance levels
            - weekly_data: Dict with weekly-specific data (for weekly briefs)
    
    Returns:
        BriefInput: Compact, token-optimized data structure
    """
    logger.info("Preparing compact brief input from raw data")
    
    # Get current date
    ny_tz = pytz.timezone("America/New_York")
    date_str = datetime.now(ny_tz).strftime("%Y-%m-%d")
    
    # Prepare indices (SPY, QQQ, IWM, DIA, VIX, TLT)
    indices = []
    expected_range = raw_data.get("expected_range", {})
    index_symbols = ["spy", "qqq", "iwm", "dia", "vix", "tlt"]
    
    for symbol in index_symbols[:MAX_INDICES]:
        if symbol in expected_range:
            ticker_data = prepare_ticker_data(symbol, expected_range[symbol])
            if ticker_data is not None:
                indices.append(ticker_data)
            else:
                logger.warning(
                    "Dropping index %s from brief input - no valid price", symbol.upper()
                )
    
    # Prepare rates (10Y, 2Y, DXY) - these might be in expected_range or separate
    rates = []
    rate_symbols = ["10y", "2y", "dxy"]
    for symbol in rate_symbols[:MAX_RATES]:
        if symbol in expected_range:
            ticker_data = prepare_ticker_data(symbol, expected_range[symbol])
            if ticker_data is not None:
                rates.append(ticker_data)
    
    # Prepare economic events
    events = []
    economic_events = raw_data.get("economic_catalysts", []) or raw_data.get("catalysts", [])
    for event in economic_events[:MAX_EVENTS]:
        if isinstance(event, dict):
            events.append(prepare_event_data(event))
    
    # Prepare movers (gapping stocks)
    movers = []
    gapping_stocks = raw_data.get("gapping_stocks", []) or raw_data.get("movers", [])
    if isinstance(gapping_stocks, dict):
        flattened: List[Dict[str, Any]] = []
        for bucket in ("premarket", "after_hours"):
            flattened.extend(gapping_stocks.get(bucket, []) or [])
        gapping_stocks = flattened
    for stock in gapping_stocks[:MAX_MOVERS]:
        if not isinstance(stock, dict):
            continue
        symbol = stock.get("symbol") or stock.get("ticker") or "UNKNOWN"
        # Mover dicts use a few different shapes across providers; normalize
        # to the keys ``prepare_ticker_data`` understands.
        normalized = dict(stock)
        if normalized.get("current_price") is None:
            normalized["current_price"] = stock.get("price")
        if normalized.get("change_percent") is None:
            normalized["change_percent"] = stock.get("gap_pct")
        ticker_data = prepare_ticker_data(symbol, normalized)
        if ticker_data is not None:
            movers.append(ticker_data)
    
    # Prepare support/resistance levels
    levels = []
    # Extract levels from expected_range
    for symbol, data in expected_range.items():
        if isinstance(data, dict):
            # Support levels
            for level_key in ["support", "support2", "support3"]:
                if level_key in data and data[level_key]:
                    levels.append(prepare_level_data(data[level_key], "Strong"))
            
            # Resistance levels  
            for level_key in ["resistance", "resistance2", "resistance3"]:
                if level_key in data and data[level_key]:
                    levels.append(prepare_level_data(data[level_key], "Strong"))
    
    # Limit levels to MAX_LEVELS
    levels = levels[:MAX_LEVELS]
    
    # Prepare headlines
    headlines = []
    raw_headlines = raw_data.get("headlines", [])
    
    # Handle weekly brief headlines differently
    weekly_data = raw_data.get("weekly_data", {})
    if weekly_data:
        # For weekly briefs, use weekly-specific headlines
        weekly_headlines = weekly_data.get("weekly_headlines", "")
        if weekly_headlines:
            # Split by newlines and take first MAX_HEADLINES
            weekly_headline_list = [h.strip() for h in weekly_headlines.split('\n') if h.strip()]
            raw_headlines = [{"headline": h} for h in weekly_headline_list]
    
    for headline in raw_headlines[:MAX_HEADLINES]:
        if isinstance(headline, dict):
            text = headline.get("headline", headline.get("title", ""))
        else:
            text = str(headline)
        headlines.append(truncate_string(text, HEADLINE_MAX_LEN))
    
    brief_input = BriefInput(
        date=date_str,
        indices=indices,
        rates=rates,
        events=events,
        movers=movers,
        levels=levels,
        headlines=headlines,
        market_session="premarket"
    )
    
    # Log statistics
    logger.info(f"Brief input prepared: {len(indices)} indices, {len(rates)} rates, "
                f"{len(events)} events, {len(movers)} movers, {len(levels)} levels, "
                f"{len(headlines)} headlines")
    
    return brief_input


def minify_brief_input(brief_input: BriefInput) -> str:
    """
    Convert BriefInput to minified JSON string for LLM consumption.
    
    Args:
        brief_input: BriefInput object
        
    Returns:
        str: Minified JSON string
    """
    return json.dumps(asdict(brief_input), separators=(',', ':'))


def get_brief_input_stats(brief_input: BriefInput) -> Dict[str, Any]:
    """Get statistics about the brief input for logging."""
    data = asdict(brief_input)
    mini_json = json.dumps(data, separators=(',', ':'))
    
    return {
        "indices_count": len(brief_input.indices),
        "rates_count": len(brief_input.rates),
        "events_count": len(brief_input.events),
        "movers_count": len(brief_input.movers),
        "levels_count": len(brief_input.levels),
        "headlines_count": len(brief_input.headlines),
        "minified_json_length": len(mini_json),
        "total_symbols": (
            len(brief_input.indices)
            + len(brief_input.rates)
            + len(brief_input.movers)
        ),
        "total_arrays": 6  # indices, rates, events, movers, levels, headlines
    }
