"""After-hours / pre-market mover detection for the morning brief.

Sources of truth are `providers.DataProvider` (Polygon.io /
"Massive API") for price data and news, and `providers.catalyst_summarizer`
for a short Claude-Haiku-generated explanation of each move.

Historically this module looped over the S&P500+NDX100 universe pulling
1-minute bars from yfinance and company news from Finnhub. Polygon's
snapshot-gainers/losers endpoint already returns a liquid, pre-ranked
universe of overnight movers (pre-market in the AM, after-hours in the
PM), so we use that and just enrich each entry with news + catalyst
summary.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from providers import get_default_provider, summarize_catalyst

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _read_json(fname: str) -> list[str]:
    try:
        with open(DATA_DIR / fname, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def load_universe() -> list[str]:
    """Return combined S&P500 + NDX100 ticker universe (deduped).

    Retained for callers that want to scope news lookups or reporting
    filters, even though `top_ah_moves` / `top_premarket_moves` no longer
    iterate over it directly.
    """
    spx = _read_json("sp500.json")
    ndx = _read_json("ndx100.json")
    tickers = sorted(set(spx + ndx))
    return [t for t in tickers if "^" not in t and "." not in t]


def _build_mover_items(
    movers: Iterable[dict],
    session_label: str,
    max_n: int,
    universe: set[str] | None = None,
) -> list[dict]:
    out: list[dict] = []
    dp = get_default_provider()
    for m in movers:
        ticker = (m.get("ticker") or "").upper()
        if not ticker:
            continue
        if universe and ticker not in universe:
            continue
        pct = m.get("change_pct")
        if pct is None:
            continue
        news_items = dp.get_news(ticker, limit=5)
        top_title = (news_items[0].get("title") if news_items else "") or ""
        source_url = news_items[0].get("url") if news_items else None
        try:
            catalyst = summarize_catalyst(ticker, pct, news_items)
        except Exception:
            catalyst = top_title
        why = catalyst or top_title
        out.append(
            {
                "ticker": ticker,
                "move": f"{pct:+.2f}% {session_label}",
                "why": (why[:140] + "…") if why and len(why) > 140 else why,
                "source_url": source_url,
                "catalyst_summary": catalyst,
            }
        )
        if len(out) >= max_n:
            break
    return out


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def top_ah_moves(tickers: list[str] | None = None, max_n: int = 6) -> list[dict]:
    """Return mixed winners/losers from the current Polygon snapshot,
    labeled as after-hours moves.

    When the morning brief is generated before the open, Polygon's day-
    change snapshot reflects overnight (AH + pre-market) activity, which
    is what the original implementation approximated via yfinance
    1-minute bars.
    """
    dp = get_default_provider()
    universe = set(tickers) if tickers else None
    half = max(1, max_n // 2)
    winners = _build_mover_items(
        dp.get_gainers(limit=max_n * 3), "AH", half, universe
    )
    losers = _build_mover_items(
        dp.get_losers(limit=max_n * 3), "AH", half, universe
    )
    return winners + losers


def top_premarket_moves(tickers: list[str] | None = None, max_n: int = 8) -> list[dict]:
    """Same source as `top_ah_moves` but labeled for the pre-market block."""
    dp = get_default_provider()
    universe = set(tickers) if tickers else None
    half = max(1, max_n // 2)
    winners = _build_mover_items(
        dp.get_gainers(limit=max_n * 3), "pre", half, universe
    )
    losers = _build_mover_items(
        dp.get_losers(limit=max_n * 3), "pre", half, universe
    )
    return winners + losers
