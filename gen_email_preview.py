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

    # Use fallback summary for determinism; include a sample subscriber summary
    summary = generate_fallback_summary(headlines, expected, gappers)
    subscriber_summary = (
        "**Today in one line**\n"
        "- **SPY/QQQ** firm after mixed data; watch opening drive.\n\n"
        "**AH & Premarket**\n"
        "- **NVDA**: +2.1% — AI demand tailwind\n"
        "- **TSLA**: -1.3% — margin concerns\n\n"
        "**Levels to watch**\n"
        "- Support: SPY S1/S2 from brief\n"
        "- Resistance: SPY R1/R2 from brief\n\n"
        "**Tomorrow**: Initial claims"
    )
    email_html = generate_html_content_with_summary(summary, headlines, expected, gappers, subscriber_summary)

    out = Path('static/uploads/brief_email_preview.html')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(email_html, encoding='utf-8')
    print(f"WROTE {out}")


if __name__ == "__main__":
    main()


