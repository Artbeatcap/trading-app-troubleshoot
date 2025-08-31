import os
import asyncio
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Import our providers
try:
    from tradier_provider import TradierProvider
except ImportError:
    logger.error("TradierProvider not available")
    TradierProvider = None

# Optional seed
try:
    from polygon_seed import top_movers
except ImportError:
    async def top_movers(direction="gainers"):
        return []

# Configuration
MIN_PRICE = 1            # per your latest rule
MIN_ADV = 500_000        # 20D avg shares (apply in your universe builder)
PRE_VOL_FLOOR = 80_000   # window total volume guard
AH_MOVE = 6.0           # % threshold
PRE_MOVE = 4.0          # % threshold

provider = TradierProvider() if TradierProvider else None

def pct(a, b):
    """Calculate percentage change"""
    try:
        return round((a - b) / b * 100, 2)
    except:
        return None

async def _window(kind: str, symbols: List[str], start_ts: int, end_ts: int,
                  vol_floor: int, move_threshold: float) -> List[Dict]:
    """Scan a time window for movers"""
    if not provider:
        logger.error("TradierProvider not available")
        return []
    
    logger.info(f"Scanning {len(symbols)} symbols for {kind} movers")
    
    minutes = await provider.minute_window(symbols, start_ts, end_ts, prepost=True)
    prev = await provider.prev_close(symbols)
    movers: List[Dict] = []
    
    for sym, bars in minutes.items():
        if not bars:
            continue
        
        vol = sum(b["v"] for b in bars)
        if kind == "PRE" and vol < PRE_VOL_FLOOR:
            continue
        
        last = bars[-1]["c"]
        base = prev.get(sym)
        if base is None:
            continue
        
        gap = pct(last, base)
        if gap is None or abs(gap) < move_threshold:
            continue
        
        # Get one-line reason from news
        news = await provider.news(sym, since_hours=24)
        why = ((news[0].get("headline") if news else "") or "")[:140]
        
        movers.append({
            "ticker": sym,
            "move": f"{'+' if gap >= 0 else ''}{gap}% {'pre' if kind=='PRE' else 'AH'}",
            "why": why,
            "abs": abs(gap)
        })
    
    result = sorted(movers, key=lambda x: x["abs"], reverse=True)
    logger.info(f"Found {len(result)} {kind} movers")
    return result

async def scan_premarket(universe: List[str], start_ts: int, end_ts: int) -> List[Dict]:
    """Scan premarket for movers"""
    # Optional: seed with Polygon movers to cut load
    seed = list(set((await top_movers("gainers")) + (await top_movers("losers"))))[:40]
    batch = [s for s in seed if s in universe] or universe
    
    return await _window("PRE", batch, start_ts, end_ts, PRE_VOL_FLOOR, PRE_MOVE)

async def scan_afterhours(universe: List[str], start_ts: int, end_ts: int) -> List[Dict]:
    """Scan after-hours for movers"""
    return await _window("AH", universe, start_ts, end_ts, 0, AH_MOVE)

async def scan_all_movers(universe: List[str], ah_start_ts: int, ah_end_ts: int, 
                         pre_start_ts: int, pre_end_ts: int) -> Dict[str, List[Dict]]:
    """Scan both after-hours and premarket windows"""
    logger.info("Starting comprehensive mover scan")
    
    # Run both scans concurrently
    ah_task = scan_afterhours(universe, ah_start_ts, ah_end_ts)
    pre_task = scan_premarket(universe, pre_start_ts, pre_end_ts)
    
    ah_moves, pre_moves = await asyncio.gather(ah_task, pre_task)
    
    return {
        "after_hours": ah_moves[:12],  # Top 12 AH movers
        "premarket": pre_moves[:12]    # Top 12 premarket movers
    }
