import json, os, pytz, datetime as dt
from pathlib import Path
from daily_brief_schema import MorningBrief  # type: ignore
from .movers import load_universe, top_ah_moves, top_premarket_moves

TZ = pytz.timezone(os.getenv("TZ", "America/New_York"))


def build_context(base_json_path: str | Path, *, include_movers: bool = True, include_news: bool = True) -> dict:
    """Read base JSON, enrich with movers and news, validate, and return context dict."""
    with open(base_json_path, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    if include_movers:
        universe = load_universe()
        ctx["ah_moves"] = top_ah_moves(universe)
        ctx["premarket_moves"] = top_premarket_moves(universe)

    if include_news:
        # Import here to avoid circular imports
        from market_brief_generator import fetch_news
        try:
            news_data = fetch_news()
            # Convert to NewsItem format for schema validation
            ctx["news_headlines"] = [
                {
                    "headline": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "datetime": item.get("datetime")
                }
                for item in news_data[:5]  # Limit to top 5 headlines
            ]
        except Exception as e:
            print(f"Warning: Failed to fetch news headlines: {e}")
            ctx["news_headlines"] = []

    # Ensure required date string
    ctx.setdefault("date", dt.datetime.now(TZ).strftime("%B %d, %Y"))

    # Validate schema; will raise if invalid
    _ = MorningBrief(**ctx)
    return ctx
