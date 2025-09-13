#!/usr/bin/env python3

from pathlib import Path

from market_brief_generator import (
    fetch_news,
    filter_market_headlines,
    fetch_stock_prices,
    calculate_expected_range,
    fetch_gapping_stocks,
    generate_fallback_summary,
    generate_html_content_with_summary,
)


def main() -> None:
    headlines = filter_market_headlines(fetch_news())
    prices = fetch_stock_prices()
    expected = calculate_expected_range(prices)
    gappers = fetch_gapping_stocks()

    # Use fallback summary to avoid OpenAI calls and keep this deterministic
    summary = generate_fallback_summary(headlines, expected, gappers)
    site_html = generate_html_content_with_summary(summary, headlines, expected, gappers, None)

    out = Path('static/uploads/brief_latest.html')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(site_html, encoding='utf-8')
    print(f"WROTE {out}")


if __name__ == "__main__":
    main()


