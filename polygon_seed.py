import os
import aiohttp
import logging

logger = logging.getLogger(__name__)

API = os.getenv("POLYGON_API_KEY")
BASE = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks"

async def top_movers(direction="gainers"):
    """Get top movers from Polygon to seed our scan and reduce API load"""
    if not API:
        logger.info("No Polygon API key available, skipping seed")
        return []
    
    url = f"{BASE}/{direction}"
    params = {"apiKey": API}
    
    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(url, params=params, timeout=10) as r:
                r.raise_for_status()
                js = await r.json()
                tickers = [it["ticker"] for it in (js.get("tickers") or [])]
                logger.info(f"Got {len(tickers)} {direction} from Polygon")
                return tickers
        except Exception as e:
            logger.warning(f"Failed to fetch {direction} from Polygon: {e}")
            return []
