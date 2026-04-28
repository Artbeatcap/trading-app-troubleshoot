"""Tests for required-market-data guards and compact-input normalization.

These tests exercise the safeguards added after the deployed post-market
generator emitted ``SPY/QQQ at $0.00`` and ``VIX: 0.00`` because upstream
provider data was missing. The guarantees we want:

1. ``require_market_data`` raises ``BriefDataUnavailable`` when SPY/QQQ are
   missing or non-positive, so callers cannot publish a zero brief.
2. ``build_market_snapshot`` returns only symbols with valid positive
   prices so newsletter/post copy can omit unavailable values rather than
   render them as ``$0.00``.
3. ``prepare_brief_input`` drops indices and movers without a valid price
   instead of zero-padding them into the LLM input.
4. ``generate_fallback_summary`` formats missing required indices as
   ``n/a`` rather than ``$0.00``.
5. ``generate_daily_recap_markdown`` raises ``BriefDataUnavailable`` when
   the provider has no SPY/QQQ price.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

import pytest


def test_require_market_data_raises_when_spy_missing():
    from market_brief_generator import require_market_data, BriefDataUnavailable

    prices = {
        "spy": {"current_price": None},
        "qqq": {"current_price": 510.0},
    }
    with pytest.raises(BriefDataUnavailable) as excinfo:
        require_market_data(prices)
    assert "SPY" in str(excinfo.value)


def test_require_market_data_raises_when_price_zero():
    from market_brief_generator import require_market_data, BriefDataUnavailable

    prices = {
        "spy": {"current_price": 0.0},
        "qqq": {"current_price": 0.0},
    }
    with pytest.raises(BriefDataUnavailable) as excinfo:
        require_market_data(prices)
    msg = str(excinfo.value)
    assert "SPY" in msg and "QQQ" in msg


def test_require_market_data_passes_with_valid_prices():
    from market_brief_generator import require_market_data

    prices = {
        "spy": {"current_price": 644.95},
        "qqq": {"current_price": 579.89},
        "vix": {"current_price": 15.4},
    }
    require_market_data(prices)


def test_require_market_data_allows_missing_vix_by_default():
    from market_brief_generator import require_market_data

    prices = {
        "spy": {"current_price": 644.95},
        "qqq": {"current_price": 579.89},
        "vix": {"current_price": None},
    }
    require_market_data(prices)


def test_build_market_snapshot_omits_missing_symbols():
    from market_brief_generator import build_market_snapshot

    prices = {
        "spy": {"current_price": 644.95, "change": 1.2, "change_percent": 0.18},
        "qqq": {"current_price": None, "change": None, "change_percent": None},
        "iwm": {"current_price": 0.0},
        "vix": {"current_price": 15.4, "change": -0.3, "change_percent": -1.9},
    }
    snap = build_market_snapshot(prices)
    assert set(snap.keys()) == {"spy", "vix"}
    assert snap["spy"]["price"] == 644.95
    assert snap["spy"]["change_percent"] == 0.18
    assert snap["vix"]["price"] == 15.4


def test_build_market_snapshot_with_no_data():
    from market_brief_generator import build_market_snapshot

    assert build_market_snapshot({}) == {}


def test_prepare_brief_input_drops_invalid_indices():
    from pipeline.prepare_inputs import prepare_brief_input

    raw: Dict[str, Any] = {
        "expected_range": {
            "spy": {"current_price": 644.95, "change_percent": 0.18},
            "qqq": {"current_price": None, "change_percent": None},
            "iwm": {"current_price": 0},
            "vix": {"current_price": 15.4, "change_percent": -1.9},
        },
        "headlines": [],
        "gapping_stocks": [],
    }
    brief_input = prepare_brief_input(raw)
    symbols = [t.symbol for t in brief_input.indices]
    assert symbols == ["SPY", "VIX"]
    spy = next(t for t in brief_input.indices if t.symbol == "SPY")
    assert spy.price == 644.95


def test_prepare_brief_input_drops_invalid_movers():
    from pipeline.prepare_inputs import prepare_brief_input

    movers: List[Dict[str, Any]] = [
        {"symbol": "NVDA", "current_price": 950.0, "change_percent": 5.0},
        {"symbol": "BAD", "current_price": 0.0, "change_percent": -1.0},
        {"symbol": "ALSO_BAD", "current_price": None},
        {"ticker": "TSLA", "price": 240.0, "gap_pct": -3.0},
    ]
    raw: Dict[str, Any] = {
        "expected_range": {},
        "headlines": [],
        "gapping_stocks": movers,
    }
    brief_input = prepare_brief_input(raw)
    symbols = [t.symbol for t in brief_input.movers]
    assert symbols == ["NVDA", "TSLA"]
    tsla = next(t for t in brief_input.movers if t.symbol == "TSLA")
    assert tsla.price == 240.0
    assert tsla.change_percent == -3.0


def test_fallback_summary_renders_unavailable_when_data_missing():
    from market_brief_generator import generate_fallback_summary

    out = generate_fallback_summary(
        headlines=[],
        expected_range={"spy": {}, "qqq": {}, "vix": {}},
        gapping_stocks=[],
    )
    assert "$0.00" not in out
    assert "n/a" in out


def test_fallback_summary_renders_real_prices():
    from market_brief_generator import generate_fallback_summary

    out = generate_fallback_summary(
        headlines=[],
        expected_range={
            "spy": {"current_price": 644.95, "support": 631.0, "resistance": 658.0},
            "qqq": {"current_price": 579.89, "support": 565.0, "resistance": 595.0},
            "vix": {"current_price": 15.4},
        },
        gapping_stocks=[],
    )
    assert "$644.95" in out
    assert "$579.89" in out
    assert "15.40" in out
    assert "$0.00" not in out


def test_calculate_expected_range_returns_no_bands_without_vix():
    from market_brief_generator import calculate_expected_range

    ranges = calculate_expected_range(
        {
            "spy": {"current_price": 644.95},
            "qqq": {"current_price": 579.89},
            "vix": {"current_price": None},
        }
    )
    assert ranges == {}


def test_generate_daily_recap_raises_when_data_missing():
    import market_brief_generator as mbg

    empty_prices = {
        "spy": {"current_price": None},
        "qqq": {"current_price": None},
        "vix": {"current_price": None},
    }
    with mock.patch.object(mbg, "fetch_stock_prices", return_value=empty_prices):
        with mock.patch.object(mbg, "fetch_news") as fetch_news_mock:
            with mock.patch.object(mbg, "summarize_news") as summarize_mock:
                with pytest.raises(mbg.BriefDataUnavailable):
                    mbg.generate_daily_recap_markdown()
    fetch_news_mock.assert_not_called()
    summarize_mock.assert_not_called()


def test_generate_daily_recap_continues_without_vix_but_no_ranges():
    import market_brief_generator as mbg

    soft_vix_missing = {
        "spy": {"current_price": 644.95, "change": 1.2, "change_percent": 0.18},
        "qqq": {"current_price": 579.89, "change": -0.3, "change_percent": -0.05},
        "vix": {"current_price": None, "change": None, "change_percent": None},
    }
    with mock.patch.object(mbg, "fetch_stock_prices", return_value=soft_vix_missing):
        with mock.patch.object(mbg, "fetch_news", return_value=[]):
            with mock.patch.object(mbg, "filter_market_headlines", return_value=[]):
                with mock.patch.object(mbg, "fetch_gapping_stocks", return_value={}):
                    with mock.patch.object(mbg, "summarize_news", return_value="recap") as summarize_mock:
                        out = mbg.generate_daily_recap_markdown()
    assert out == "recap"
    summarize_mock.assert_called_once()
    assert summarize_mock.call_args.args[1] == {}


def _render_context(market_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "subject_theme": "Test Brief",
        "date": "April 24, 2026",
        "preheader": "Test preheader",
        "market_overview": "Market data is being validated.",
        "market_snapshot": market_snapshot,
        "llm_daily_recap_md": "",
        "llm_daily_recap_html": "",
        "ah_moves": [],
        "premarket_moves": [],
        "spy_s1": "n/a",
        "spy_s2": "n/a",
        "spy_r1": "n/a",
        "spy_r2": "n/a",
        "spy_r3": "n/a",
        "extra_levels": "",
        "levels_methodology": {},
        "news_headlines": [],
        "macro_data": "",
        "earnings": [],
        "sectors": "",
        "day_plan": [],
        "swing_plan": [],
        "on_deck": "",
        "unsubscribe_url": "#",
        "preferences_url": "#",
    }


def test_render_morning_brief_does_not_emit_synthetic_market_values():
    from emailer import render_morning_brief

    html, text = render_morning_brief(_render_context({}))
    rendered = html + text
    forbidden = ["$0.00", "$400.00", "$300.00", "$200.00", "vix=20", "VIX: 20.00"]
    for token in forbidden:
        assert token not in rendered


def test_render_morning_brief_emits_real_market_snapshot_values():
    from emailer import render_morning_brief

    html, text = render_morning_brief(
        _render_context(
            {
                "spy": {"price": 644.95, "change": 1.2, "change_percent": 0.18},
                "qqq": {"price": 579.89, "change": -0.3, "change_percent": -0.05},
                "vix": {"price": 15.4, "change": -0.2, "change_percent": -1.3},
            }
        )
    )
    rendered = html + text
    assert "$644.95" in rendered
    assert "$579.89" in rendered
    assert "$15.40" in rendered
    assert "$0.00" not in rendered


def test_write_brief_unavailable_sentinel(tmp_path, monkeypatch):
    import market_brief_generator as mbg

    fake_module = tmp_path / "market_brief_generator.py"
    fake_module.write_text("# fake module path", encoding="utf-8")
    monkeypatch.setattr(mbg, "__file__", str(fake_module))

    path = mbg._write_brief_unavailable_sentinel("Market data unavailable: missing SPY")
    latest_file = Path(path)
    latest_date_file = latest_file.with_name("brief_latest_date.txt")

    assert latest_file.exists()
    assert "Today's brief is delayed - market data provider unavailable." in latest_file.read_text(
        encoding="utf-8"
    )
    assert latest_date_file.read_text(encoding="utf-8").startswith("unavailable:")


def test_write_brief_unavailable_sentinel_swallows_write_errors(tmp_path, monkeypatch):
    import market_brief_generator as mbg

    fake_module = tmp_path / "market_brief_generator.py"
    fake_module.write_text("# fake module path", encoding="utf-8")
    monkeypatch.setattr(mbg, "__file__", str(fake_module))
    monkeypatch.setattr(Path, "write_text", mock.Mock(side_effect=OSError("disk full")))

    assert mbg._write_brief_unavailable_sentinel("missing SPY") == ""


def test_read_brief_date_accepts_unavailable_status(tmp_path):
    from app import _read_brief_date

    date_file = tmp_path / "brief_latest_date.txt"
    date_file.write_text("unavailable:2026-04-24:provider-outage", encoding="utf-8")

    assert _read_brief_date(date_file).isoformat() == "2026-04-24"


def test_gpt5_headline_summarizer_omits_custom_temperature():
    import headline_summarizer

    assert headline_summarizer._supports_custom_temperature("gpt-4o-mini")
    assert not headline_summarizer._supports_custom_temperature("gpt-5-nano")


def test_repo_has_no_synthetic_market_price_defaults():
    repo_root = Path(__file__).resolve().parents[1]
    forbidden_plain = ("default_prices",)
    suspect_literals = ("400.0", "300.0", "200.0")
    vix_fallback = "vix = 20.0"

    for path in repo_root.rglob("*.py"):
        rel = path.relative_to(repo_root)
        rel_parts = set(rel.parts)
        ignored = {"tests", ".git", "__pycache__", "venv", ".venv", "env"}
        if rel_parts & ignored:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_plain:
            assert token not in text, f"{rel} contains forbidden synthetic default {token}"
        lower = text.lower()
        has_index_literal = any(lit in text for lit in suspect_literals)
        mentions_indices = any(sym in lower for sym in ("spy", "qqq", "iwm"))
        assert not (has_index_literal and mentions_indices), (
            f"{rel} appears to pair index symbols with synthetic price defaults"
        )
        assert vix_fallback not in lower, f"{rel} contains forbidden missing-VIX fallback"
