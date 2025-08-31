import json, os, pytz, datetime as dt
from pathlib import Path
from daily_brief_schema import MorningBrief  # type: ignore
from .movers import load_universe, top_ah_moves, top_premarket_moves

TZ = pytz.timezone(os.getenv("TZ", "America/New_York"))


def build_context(base_json_path: str | Path, *, include_movers: bool = True) -> dict:
    """Read base JSON, enrich with movers, validate, and return context dict."""
    with open(base_json_path, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    if include_movers:
        universe = load_universe()
        ctx["ah_moves"] = top_ah_moves(universe)
        ctx["premarket_moves"] = top_premarket_moves(universe)

    # Ensure required date string
    ctx.setdefault("date", dt.datetime.now(TZ).strftime("%B %d, %Y"))

    # Validate schema; will raise if invalid
    _ = MorningBrief(**ctx)
    return ctx
