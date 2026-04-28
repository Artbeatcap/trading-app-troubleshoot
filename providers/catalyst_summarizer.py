"""Anthropic Claude Haiku catalyst summarizer.

`summarize_catalyst(ticker, pct, headlines)` returns a 1-2 sentence
explanation of why a stock is moving, based on the supplied headlines.
Results are cached per (ticker, truncated headline set) for the life of
the process so the same ticker within a brief doesn't re-bill.

If `ANTHROPIC_API_KEY` is missing, Anthropic returns an error, or no
headlines are supplied, the function degrades gracefully to returning the
top headline title (or an empty string if no headlines).

Deliberately uses `requests` rather than the `anthropic` SDK to avoid
adding a hard dependency.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Iterable, Optional

import requests

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_HEADLINES = 5
MAX_TOKENS = 150
REQUEST_TIMEOUT = 15.0

_cache: dict[str, str] = {}
_cache_lock = threading.Lock()
_warned: set[str] = set()
_warn_lock = threading.Lock()


def _warn_once(tag: str, msg: str) -> None:
    with _warn_lock:
        if tag in _warned:
            return
        _warned.add(tag)
    logger.warning(msg)


def reset_summary_cache() -> None:
    """Test helper: clear the in-process summary cache."""
    with _cache_lock:
        _cache.clear()


def _normalize_headlines(headlines: Iterable) -> list[str]:
    out: list[str] = []
    for h in headlines or []:
        if isinstance(h, dict):
            title = (h.get("title") or "").strip()
        else:
            title = str(h).strip()
        if title:
            out.append(title)
        if len(out) >= MAX_HEADLINES:
            break
    return out


def _cache_key(ticker: str, headlines: list[str]) -> str:
    joined = " || ".join(headlines)
    return f"{ticker.upper()}::{joined[:400]}"


def summarize_catalyst(
    ticker: str,
    pct: Optional[float],
    headlines: Iterable,
    *,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: float = REQUEST_TIMEOUT,
) -> str:
    """Produce a 1-2 sentence catalyst summary for `ticker`.

    Returns an empty string if no headlines and no API response.
    Never raises on HTTP/network issues - always degrades gracefully.
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return ""
    norm_headlines = _normalize_headlines(headlines)
    if not norm_headlines:
        return ""

    key = _cache_key(ticker, norm_headlines)
    with _cache_lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        _warn_once(
            "no_anthropic_key",
            "catalyst_summarizer: ANTHROPIC_API_KEY not set; "
            "falling back to top headline.",
        )
        fallback = norm_headlines[0]
        with _cache_lock:
            _cache[key] = fallback
        return fallback

    pct_str = f"{pct:+.1f}" if isinstance(pct, (int, float)) else "an unknown amount"
    headlines_block = "\n".join(f"- {h}" for h in norm_headlines)
    prompt = (
        f"You are a trading desk analyst. {ticker} moved {pct_str}% today. "
        f"Here are recent headlines:\n{headlines_block}\n\n"
        "Write exactly 1-2 sentences explaining the specific catalyst and "
        "whether it's likely retail FOMO, a fundamental change, or an "
        "institutional event. Be direct."
    )
    body = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    http = session or requests
    try:
        resp = http.post(ANTHROPIC_URL, json=body, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        logger.info("catalyst_summarizer HTTP error for %s: %s", ticker, exc)
        fallback = norm_headlines[0]
        with _cache_lock:
            _cache[key] = fallback
        return fallback

    if resp.status_code >= 400:
        logger.info(
            "catalyst_summarizer HTTP %s for %s (body=%.200s)",
            resp.status_code,
            ticker,
            resp.text if resp.text else "",
        )
        fallback = norm_headlines[0]
        with _cache_lock:
            _cache[key] = fallback
        return fallback

    try:
        payload = resp.json()
    except ValueError:
        fallback = norm_headlines[0]
        with _cache_lock:
            _cache[key] = fallback
        return fallback

    content = payload.get("content")
    text = ""
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
        text = "".join(parts).strip()
    elif isinstance(content, str):
        text = content.strip()

    if not text:
        text = norm_headlines[0]

    with _cache_lock:
        _cache[key] = text
    return text
