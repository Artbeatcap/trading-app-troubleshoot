"""Unified synchronous market-data provider.

Sole data source: Polygon.io (Stocks Starter tier, referred to internally as
the "Massive API"). No secondary provider. Endpoints that are not available
on the current Polygon tier (earnings calendar, earnings surprises, economic
calendar, options chains) degrade gracefully by returning empty results and
warning once.

All external network access lives here. Every public method:
  - calls Polygon with an api-key-scoped GET,
  - on HTTP/JSON/empty-payload failure, logs once and returns a sensible
    empty value,
  - normalizes the response to a fixed internal schema before returning.

Schemas (all dicts, JSON-serializable):
  quote : {ticker, price, change_pct, volume, timestamp}
  bar   : {open, high, low, close, volume, timestamp}
  news  : {title, description, published, source, url}
  mover : {ticker, price, change_pct, volume}
  option_contract : {symbol, type, strike, expiration, bid, ask, last,
                     volume, open_interest, iv, delta}
  earnings_event : {ticker, date, eps_estimate, eps_actual,
                    revenue_estimate, revenue_actual}

All `timestamp` fields are ISO-8601 strings in UTC (Zulu) when available.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

_UNSET = object()

# Set of (tag,) already-warned events so we don't flood logs.
_WARNED: set[str] = set()
_WARNED_LOCK = threading.Lock()


def _warn_once(tag: str, msg: str) -> None:
    with _WARNED_LOCK:
        if tag in _WARNED:
            return
        _WARNED.add(tag)
    logger.warning(msg)


def _to_iso_utc(value: Any) -> Optional[str]:
    """Coerce a variety of timestamp representations to ISO-8601 UTC string."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # milliseconds
            ts = ts / 1000.0
        elif ts > 1e10:  # microseconds
            ts = ts / 1_000_000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        fmts = (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        )
        for fmt in fmts:
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            except ValueError:
                continue
        return s
    return None


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> Optional[int]:
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except (TypeError, ValueError):
        return None


class DataProvider:
    """Synchronous data provider backed by Polygon.io only."""

    DEFAULT_POLYGON_BASE = "https://api.polygon.io"

    CACHE_TTL = {
        "quote": 30,
        "bars": 300,
        "daily_bars": 600,
        "gainers": 60,
        "losers": 60,
        "news": 300,
        "vix": 300,
        "options": 300,
        "profile": 86400,
    }

    def __init__(
        self,
        polygon_key: Any = _UNSET,
        rate_limit_delay: Optional[float] = None,
        polygon_base: Optional[str] = None,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
    ) -> None:
        if polygon_key is _UNSET:
            polygon_key = os.environ.get("MASSIVE_API_KEY") or os.environ.get(
                "POLYGON_API_KEY"
            )
        self.polygon_key = polygon_key or None
        self.polygon_base = (
            polygon_base or os.environ.get("POLYGON_BASE_URL") or self.DEFAULT_POLYGON_BASE
        ).rstrip("/")
        if rate_limit_delay is None:
            try:
                rate_limit_delay = float(os.environ.get("RATE_LIMIT_DELAY", "0.05"))
            except ValueError:
                rate_limit_delay = 0.05
        self.rate_limit_delay = max(0.0, float(rate_limit_delay))
        self.timeout = float(timeout)
        self.session = session or requests.Session()
        self._last_call_ts = 0.0
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_lock = threading.Lock()

        if not self.polygon_key:
            _warn_once(
                "no_polygon_key",
                "DataProvider: MASSIVE_API_KEY / POLYGON_API_KEY not set; "
                "all market-data calls will return empty.",
            )

    # ---------------------------------------------------------------- cache
    def _cache_get(self, key: str, ttl: float) -> Optional[Any]:
        with self._cache_lock:
            item = self._cache.get(key)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > ttl:
            return None
        return value

    def _cache_set(self, key: str, value: Any) -> None:
        with self._cache_lock:
            self._cache[key] = (time.time(), value)

    # ------------------------------------------------------------ rate limit
    def _rate_limit(self) -> None:
        if self.rate_limit_delay <= 0:
            return
        now = time.time()
        elapsed = now - self._last_call_ts
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_call_ts = time.time()

    # ------------------------------------------------------------ http core
    def _http_get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Optional[dict]:
        self._rate_limit()
        try:
            resp = self.session.get(
                url, params=params or {}, headers=headers or {}, timeout=self.timeout
            )
        except requests.RequestException as exc:
            logger.info("HTTP error calling %s: %s", url, exc)
            return None
        if resp.status_code >= 400:
            logger.info(
                "HTTP %s from %s (body=%.200s)",
                resp.status_code,
                url,
                resp.text if resp.text else "",
            )
            return None
        try:
            return resp.json()
        except (ValueError, json.JSONDecodeError):
            logger.info("Non-JSON response from %s", url)
            return None

    def _polygon_get(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        if not self.polygon_key:
            return None
        url = f"{self.polygon_base}{path}"
        merged = dict(params or {})
        merged["apiKey"] = self.polygon_key
        return self._http_get(url, params=merged)

    # ============================================================== QUOTES
    def get_snapshot(self, ticker: str) -> Optional[dict]:
        """Return normalized quote dict for `ticker`, or None if Polygon fails."""
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return None
        cache_key = f"quote:{ticker}"
        cached = self._cache_get(cache_key, self.CACHE_TTL["quote"])
        if cached is not None:
            return cached

        quote = self._polygon_snapshot(ticker)
        if quote is None:
            _warn_once(f"quote_fail_{ticker}", f"DataProvider: no quote for {ticker}")
            return None
        self._cache_set(cache_key, quote)
        return quote

    def _polygon_snapshot(self, ticker: str) -> Optional[dict]:
        data = self._polygon_get(
            f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        )
        if not data:
            return None
        t = data.get("ticker") or {}
        if not t:
            return None
        day = t.get("day") or {}
        prev = t.get("prevDay") or {}
        last_trade = t.get("lastTrade") or {}
        last_quote = t.get("lastQuote") or {}
        minute = t.get("min") or {}
        price = (
            _safe_float(last_trade.get("p"))
            or _safe_float(day.get("c"))
            or _safe_float(minute.get("c"))
            or _safe_float((last_quote.get("P") or last_quote.get("p")))
        )
        change_pct = _safe_float(t.get("todaysChangePerc"))
        if change_pct is None and price is not None:
            prev_close = _safe_float(prev.get("c"))
            if prev_close:
                change_pct = (price - prev_close) / prev_close * 100.0
        volume = _safe_int(day.get("v")) or _safe_int(minute.get("av"))
        ts_ns = last_trade.get("t") or t.get("updated") or minute.get("t")
        ts_iso = None
        if ts_ns:
            ts_num = float(ts_ns)
            if ts_num > 1e15:
                ts_num = ts_num / 1e9
            elif ts_num > 1e12:
                ts_num = ts_num / 1e3
            try:
                ts_iso = (
                    datetime.fromtimestamp(ts_num, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )
            except (OverflowError, OSError, ValueError):
                ts_iso = None
        if price is None:
            return None
        return {
            "ticker": ticker,
            "price": price,
            "change_pct": change_pct,
            "volume": volume,
            "timestamp": ts_iso,
        }

    # ================================================================ BARS
    def get_bars(
        self,
        ticker: str,
        multiplier: int,
        timespan: str,
        frm: str,
        to: str,
        adjusted: bool = True,
        limit: int = 500,
    ) -> list[dict]:
        """Return list of normalized bar dicts ordered ascending by time."""
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return []
        cache_key = f"bars:{ticker}:{multiplier}:{timespan}:{frm}:{to}:{adjusted}:{limit}"
        ttl_key = "daily_bars" if timespan == "day" else "bars"
        cached = self._cache_get(cache_key, self.CACHE_TTL[ttl_key])
        if cached is not None:
            return cached

        bars = self._polygon_bars(ticker, multiplier, timespan, frm, to, adjusted, limit)
        bars = bars or []
        self._cache_set(cache_key, bars)
        return bars

    def get_daily_bars(self, ticker: str, frm: str, to: str, limit: int = 500) -> list[dict]:
        return self.get_bars(ticker, 1, "day", frm, to, adjusted=True, limit=limit)

    def _polygon_bars(
        self,
        ticker: str,
        multiplier: int,
        timespan: str,
        frm: str,
        to: str,
        adjusted: bool,
        limit: int,
    ) -> list[dict]:
        data = self._polygon_get(
            f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{frm}/{to}",
            params={
                "adjusted": "true" if adjusted else "false",
                "sort": "asc",
                "limit": limit,
            },
        )
        if not data:
            return []
        results = data.get("results") or []
        out = []
        for r in results:
            ts_ms = r.get("t")
            ts_iso = _to_iso_utc(ts_ms)
            out.append(
                {
                    "open": _safe_float(r.get("o")),
                    "high": _safe_float(r.get("h")),
                    "low": _safe_float(r.get("l")),
                    "close": _safe_float(r.get("c")),
                    "volume": _safe_int(r.get("v")),
                    "timestamp": ts_iso,
                }
            )
        return out

    # ============================================================== MOVERS
    def get_gainers(self, limit: int = 10) -> list[dict]:
        return self._movers("gainers", limit)

    def get_losers(self, limit: int = 10) -> list[dict]:
        return self._movers("losers", limit)

    def _movers(self, direction: str, limit: int) -> list[dict]:
        cache_key = f"{direction}:{limit}"
        cached = self._cache_get(cache_key, self.CACHE_TTL[direction])
        if cached is not None:
            return cached

        out = self._polygon_movers(direction)
        out = (out or [])[:limit]
        self._cache_set(cache_key, out)
        return out

    def _polygon_movers(self, direction: str) -> list[dict]:
        data = self._polygon_get(
            f"/v2/snapshot/locale/us/markets/stocks/{direction}"
        )
        if not data:
            return []
        tickers = data.get("tickers") or []
        out = []
        for t in tickers:
            sym = (t.get("ticker") or "").upper()
            if not sym:
                continue
            day = t.get("day") or {}
            price = _safe_float(day.get("c")) or _safe_float((t.get("min") or {}).get("c"))
            out.append(
                {
                    "ticker": sym,
                    "price": price,
                    "change_pct": _safe_float(t.get("todaysChangePerc")),
                    "volume": _safe_int(day.get("v")),
                }
            )
        return out

    # ================================================================ NEWS
    def get_news(self, ticker: str, limit: int = 10) -> list[dict]:
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return []
        cache_key = f"news:{ticker}:{limit}"
        cached = self._cache_get(cache_key, self.CACHE_TTL["news"])
        if cached is not None:
            return cached

        items = self._polygon_news(ticker, limit)
        items = (items or [])[:limit]
        self._cache_set(cache_key, items)
        return items

    def _polygon_news(self, ticker: str, limit: int) -> list[dict]:
        data = self._polygon_get(
            "/v2/reference/news",
            params={
                "ticker": ticker,
                "limit": limit,
                "order": "desc",
                "sort": "published_utc",
            },
        )
        if not data:
            return []
        results = data.get("results") or []
        out = []
        for r in results:
            out.append(
                {
                    "title": (r.get("title") or "").strip(),
                    "description": (r.get("description") or "").strip(),
                    "published": _to_iso_utc(r.get("published_utc")),
                    "source": (r.get("publisher") or {}).get("name")
                    or r.get("author")
                    or "Polygon",
                    "url": r.get("article_url") or r.get("url") or "",
                }
            )
        return [x for x in out if x["title"]]

    # ============================================================ VIX PROXY
    def get_vix_proxy(
        self,
        multiplier: int = 1,
        timespan: str = "day",
        frm: Optional[str] = None,
        to: Optional[str] = None,
    ) -> list[dict]:
        """Return bars for the VIX proxy ETF (VIXY). Stocks-Starter compatible.

        Defaults to a small rolling window ending today (today-3 .. today)
        rather than today-only. On the Stocks Starter tier, Polygon's daily
        aggregate for the current trading day is not available until after
        market close and otherwise returns 403 NOT_AUTHORIZED; pulling a
        short lookback guarantees we get the most recent closed bar with no
        noisy 403s, and callers that only need the latest bar can still use
        the last element of the returned list.
        """
        today_dt = datetime.now(timezone.utc).date()
        if not to:
            to = today_dt.isoformat()
        if not frm:
            frm = (today_dt - timedelta(days=3)).isoformat()
        return self.get_bars("VIXY", multiplier, timespan, frm, to)

    # ============================================================= OPTIONS
    def get_option_chain(
        self, underlying: str, expiration_date: Optional[str] = None
    ) -> list[dict]:
        """Return normalized options contracts for `underlying`.

        `expiration_date` (optional, YYYY-MM-DD) filters server-side when
        supplied. On Stocks Starter tier this endpoint returns 401/403 -
        that's caught and logged once, and an empty list is returned so
        callers can render an "options unavailable" state.
        """
        underlying = (underlying or "").strip().upper()
        if not underlying:
            return []
        cache_key = f"options:{underlying}:{expiration_date or ''}"
        cached = self._cache_get(cache_key, self.CACHE_TTL["options"])
        if cached is not None:
            return cached
        params: dict[str, Any] = {"limit": 250}
        if expiration_date:
            params["expiration_date"] = expiration_date
        data = self._polygon_get(f"/v3/snapshot/options/{underlying}", params=params)
        if not data:
            _warn_once(
                f"options_unavailable_{underlying}",
                f"DataProvider: option chain unavailable for {underlying} "
                "(likely Polygon plan does not include options).",
            )
            self._cache_set(cache_key, [])
            return []
        results = data.get("results") or []
        out = []
        for r in results:
            details = r.get("details") or {}
            day = r.get("day") or {}
            last_quote = r.get("last_quote") or {}
            greeks = r.get("greeks") or {}
            out.append(
                {
                    "symbol": details.get("ticker") or r.get("ticker"),
                    "type": details.get("contract_type"),
                    "strike": _safe_float(details.get("strike_price")),
                    "expiration": details.get("expiration_date"),
                    "bid": _safe_float(last_quote.get("bid")),
                    "ask": _safe_float(last_quote.get("ask")),
                    "last": _safe_float(day.get("close")) or _safe_float(r.get("fair_market_value")),
                    "volume": _safe_int(day.get("volume")),
                    "open_interest": _safe_int(r.get("open_interest")),
                    "iv": _safe_float(r.get("implied_volatility")),
                    "delta": _safe_float(greeks.get("delta")),
                }
            )
        self._cache_set(cache_key, out)
        return out

    def get_option_expirations(self, underlying: str) -> list[str]:
        """Return sorted list of unique expiration-date strings for an
        underlying, derived from the full option-chain snapshot. Empty on
        auth failure or unsupported plan."""
        chain = self.get_option_chain(underlying)
        seen: set[str] = set()
        for c in chain:
            exp = c.get("expiration")
            if exp:
                seen.add(exp)
        return sorted(seen)

    # ============================================================ EARNINGS
    # The Polygon Stocks Starter tier does not include earnings calendar,
    # earnings surprises, or economic calendar endpoints. These stubs keep
    # callers working but warn once so it's clear why those sections are
    # empty. Upgrade to Stocks Advanced (or add a dedicated earnings/macro
    # provider) and replace the bodies here.
    def get_earnings_calendar(self, frm: str, to: str) -> list[dict]:
        _warn_once(
            "no_earnings_calendar",
            "DataProvider: earnings calendar is unavailable on the current "
            "Polygon plan; returning [].",
        )
        return []

    def get_earnings_surprises(self, ticker: str) -> list[dict]:
        _warn_once(
            "no_earnings_surprises",
            "DataProvider: earnings surprises are unavailable on the current "
            "Polygon plan; returning [].",
        )
        return []

    def get_economic_calendar(self, frm: str, to: str) -> list[dict]:
        _warn_once(
            "no_economic_calendar",
            "DataProvider: economic calendar is unavailable on the current "
            "Polygon plan; returning [].",
        )
        return []

    # =========================================================== PROFILE
    def get_company_profile(self, ticker: str) -> Optional[dict]:
        """Minimal company profile via Polygon /v3/reference/tickers/{ticker}.

        Returns a normalized dict or None on failure. Fields: {ticker, name,
        shares_outstanding, float_shares, market_cap, industry, sector,
        description, homepage_url}. ``float_shares`` is not provided by
        Polygon on this tier and is always None.
        """
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return None
        cache_key = f"profile:{ticker}"
        cached = self._cache_get(cache_key, self.CACHE_TTL["profile"])
        if cached is not None:
            return cached
        data = self._polygon_get(f"/v3/reference/tickers/{ticker}")
        if not data:
            self._cache_set(cache_key, None)
            return None
        results = data.get("results")
        if isinstance(results, list):
            results = results[0] if results else None
        if not isinstance(results, dict):
            self._cache_set(cache_key, None)
            return None
        out = {
            "ticker": ticker,
            "name": results.get("name"),
            "shares_outstanding": _safe_int(
                results.get("share_class_shares_outstanding")
                or results.get("weighted_shares_outstanding")
            ),
            # Polygon does not surface float on this tier.
            "float_shares": None,
            "market_cap": _safe_float(results.get("market_cap")),
            # Polygon uses SIC codes; surface both the human description
            # (sic_description) and leave sector unset since it's not a
            # direct field.
            "industry": results.get("sic_description"),
            "sector": None,
            "description": results.get("description"),
            "homepage_url": results.get("homepage_url"),
        }
        self._cache_set(cache_key, out)
        return out


# ---------------------------------------------------------- singleton helper
_default_provider: Optional[DataProvider] = None
_default_lock = threading.Lock()


def get_default_provider() -> DataProvider:
    """Return a process-wide singleton DataProvider built from env vars."""
    global _default_provider
    with _default_lock:
        if _default_provider is None:
            _default_provider = DataProvider()
        return _default_provider


def _reset_default_provider() -> None:
    """Test helper: drop the singleton so env changes take effect."""
    global _default_provider
    with _default_lock:
        _default_provider = None
