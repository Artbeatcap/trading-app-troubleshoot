#!/usr/bin/env python3
"""
CLI script to send morning brief emails.
Usage: python send_morning_brief.py [json_file] [--dry-run]
"""

import json
import os
import re
import sys
import argparse
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from html import escape

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_brief.build import build_context
from emailer import render_morning_brief, send_morning_brief_direct

# Movers, catalysts, and recap helpers
from market_brief_generator import (
    fetch_top_movers_av,
    fetch_economic_calendar_today,
    generate_daily_recap_markdown,
    fetch_stock_prices,
    build_market_snapshot,
    require_market_data,
    BriefDataUnavailable,
    _write_brief_unavailable_sentinel,
)
from pytz import timezone
NY = timezone("America/New_York")
logger = logging.getLogger(__name__)
ENV_BYPASS_DEPRECATION_DATE = date(2026, 5, 24)

# Deprecated loader removed; handled by build_context

def save_dry_run_output(html_content: str, text_content: str, date_str: str):
    """Save dry-run output to files."""
    # Create output directory
    output_dir = Path("out/emails") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save HTML file
    html_file = output_dir / "morning_brief.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Save text file
    text_file = output_dir / "morning_brief.txt"
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    print(f"Dry-run output saved to:")
    print(f"  HTML: {html_file}")
    print(f"  Text: {text_file}")

_RECAP_BOLD_LINE = re.compile(r"^\s*\*{2}([^*\n]+?)\*{2}\s*:?\s*$")
_RECAP_INLINE_BOLD = re.compile(r"\*{2}(.+?)\*{2}")
_RECAP_INLINE_ITALIC = re.compile(r"(?<!\*)\*(?!\s)([^*\n]+?)\*(?!\*)")


def _render_recap_inline(text: str) -> str:
    """Escape ``text`` then convert inline markdown emphasis to HTML.

    Kept in sync with ``market_brief_generator._render_recap_inline``.
    """
    out = escape(text)
    out = _RECAP_INLINE_BOLD.sub(r"<strong>\1</strong>", out)
    out = _RECAP_INLINE_ITALIC.sub(r"<em>\1</em>", out)
    return out.replace("**", "")


def _render_markdown_to_html(md: str) -> str:
    """
    Lightweight markdown-to-HTML renderer for daily recap content.
    Mirrors the weekly recap styling: headings, bullets, and paragraphs.

    Kept structurally identical to
    ``market_brief_generator._markdown_to_recap_html`` — any change here
    should be mirrored there (and vice versa).
    """
    lines = (md or "").splitlines()
    html_lines: list[str] = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if not stripped:
            close_list()
            html_lines.append("")
            continue

        # Headings
        if stripped.startswith("### "):
            close_list()
            text = escape(stripped[4:].strip())
            html_lines.append(f'<h3 class="llm-subheading">{text}</h3>')
            continue
        if stripped.startswith("## "):
            close_list()
            text = escape(stripped[3:].strip())
            html_lines.append(f'<h2 class="llm-heading">{text}</h2>')
            continue
        if stripped.startswith("# "):
            close_list()
            text = escape(stripped[2:].strip())
            html_lines.append(f'<h1 class="llm-title">{text}</h1>')
            continue

        # Standalone **Label** line → promote to styled subheading. Covers the
        # Stage-A prompt's "**Market Overview**", "**Key Levels**", etc.
        bold_match = _RECAP_BOLD_LINE.match(stripped)
        if bold_match:
            close_list()
            label = bold_match.group(1).strip()
            html_lines.append(f'<h3 class="llm-subheading">{escape(label)}</h3>')
            continue

        # Bullets
        is_bullet = False
        bullet_text = ""

        if stripped.startswith(("- ", "• ")):
            is_bullet = True
            bullet_text = stripped[2:].strip()
        else:
            parts = stripped.split(". ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                is_bullet = True
                bullet_text = stripped

        if is_bullet:
            if not in_list:
                html_lines.append('<ul class="llm-list">')
                in_list = True
            html_lines.append(f"<li>{_render_recap_inline(bullet_text)}</li>")
            continue

        # Paragraph
        close_list()
        html_lines.append(f'<p class="llm-text">{_render_recap_inline(stripped)}</p>')

    close_list()
    body = "\n".join(html_lines).strip()
    return f'<div class="llm-recap-body">{body}</div>' if body else ""


def main():
    parser = argparse.ArgumentParser(description="Build and send Options Plunge Morning Brief")
    parser.add_argument("--source", required=True, help="Base JSON file for brief")
    parser.add_argument("--dry-run", action="store_true", help="Write files to out/emails/YYYY-MM-DD but do not send")
    parser.add_argument("--skip-movers", action="store_true", help="Skip building mover lists (faster, offline)")
    parser.add_argument("--test-email", help="Email address for a single test send (overrides subscriber list)")
    parser.add_argument(
        "--allow-missing-data",
        action="store_true",
        help="Bypass the strict market-data gate for this run only (not recommended)",
    )

    args = parser.parse_args()

    # Build context (validation inside build_context)
    include_movers = not args.skip_movers
    print(f"Building context from {args.source} (include movers: {include_movers})")
    context = build_context(args.source, include_movers=include_movers, include_news=True)

    # Attach a normalized market snapshot to the brief context so newsletter
    # rendering and downstream generators (e.g. post-market / social) can
    # rely on a single consistent shape instead of fabricating ``$0.00``
    # placeholders when the upstream provider fails. If required market
    # data is unavailable we abort instead of producing empty copy.
    try:
        live_prices = fetch_stock_prices()
    except Exception as exc:
        print(f"Error fetching market data: {exc}")
        sys.exit(1)

    env_bypass = os.getenv("BRIEF_REQUIRE_MARKET_DATA") == "0"
    if env_bypass and date.today() > ENV_BYPASS_DEPRECATION_DATE:
        logger.error(
            "BRIEF_REQUIRE_MARKET_DATA=0 bypass expired on %s",
            ENV_BYPASS_DEPRECATION_DATE.isoformat(),
        )
        print(
            "Error: BRIEF_REQUIRE_MARKET_DATA=0 bypass expired on "
            f"{ENV_BYPASS_DEPRECATION_DATE.isoformat()}; use --allow-missing-data."
        )
        sys.exit(2)
    if args.allow_missing_data:
        logger.error("Strict market-data gate bypassed by --allow-missing-data")
        print("Warning: strict market-data gate bypassed by --allow-missing-data")
    if env_bypass:
        logger.error(
            "Deprecated BRIEF_REQUIRE_MARKET_DATA=0 bypass is active; "
            "use --allow-missing-data for a single invocation instead."
        )
        print(
            "Warning: BRIEF_REQUIRE_MARKET_DATA=0 is deprecated; "
            "use --allow-missing-data for one-off bypasses."
        )
    require_strict = not (args.allow_missing_data or env_bypass)
    snapshot = build_market_snapshot(live_prices)
    context["market_snapshot"] = snapshot

    if require_strict:
        try:
            require_market_data(live_prices)
        except BriefDataUnavailable as exc:
            print(f"Aborting morning brief: {exc}")
            _write_brief_unavailable_sentinel(str(exc))
            print("Use --allow-missing-data to bypass for one run (not recommended).")
            sys.exit(2)

    # ---- Alpha Vantage fallbacks (no-cost) ---------------------------------
    # If the upstream builder didn't populate movers/catalysts, enrich here.
    # Movers: support either 'gapping_stocks' or 'movers' keys used across the app.
    try:
        if not context.get("gapping_stocks") and not context.get("movers"):
            av_moves = fetch_top_movers_av()
            # prefer the newer key
            context["movers"] = av_moves
            context.setdefault("gapping_stocks", av_moves)
            print("Added Alpha Vantage movers fallback (TOP_GAINERS_LOSERS).")
    except Exception as e:
        print(f"Warning: Alpha Vantage movers fallback failed: {e}")

    try:
        # Economic calendar is not available on the current Polygon tier; the
        # helper below returns [] so the section is omitted gracefully.
        if not context.get("economic_catalysts") and not context.get("catalysts"):
            cats = fetch_economic_calendar_today()
            context["economic_catalysts"] = cats
            context.setdefault("catalysts", cats)
            if cats:
                print(f"Added {len(cats)} economic catalysts.")
    except Exception as e:
        print(f"Warning: Economic catalysts fetch failed: {e}")
    
    # Ensure economic catalysts are available for the optimized pipeline
    if not context.get("economic_catalysts") and not context.get("catalysts"):
        context["economic_catalysts"] = []
        context["catalysts"] = []
    # ------------------------------------------------------------------------

    # Optional: show cache configuration during runs when debugging
    if os.getenv("OP_CACHE_DEBUG") == "1":
        print("Cache:", {
            "OP_CACHE_DIR": os.getenv("OP_CACHE_DIR", "<default ./cache>"),
            "AV_CACHE_TTL": os.getenv("AV_CACHE_TTL", "90"),
            "FH_CACHE_TTL": os.getenv("FH_CACHE_TTL", "120"),
        })

    # Optional: enhanced daily recap (Investopedia-style layout)
    try:
        daily_md = generate_daily_recap_markdown()
    except BriefDataUnavailable as e:
        logger.warning("Daily recap unavailable: %s", e)
        print(f"Warning: Daily recap skipped: {e}")
        daily_md = ""
    except Exception as e:
        print(f"Warning: Daily recap generation failed: {e}")
        daily_md = ""

    if daily_md:
        daily_html = _render_markdown_to_html(daily_md)
        context["llm_daily_recap_md"] = daily_md
        context["llm_daily_recap_html"] = daily_html

    subject = f"Options Plunge Morning Brief — {context['subject_theme']} ({context['date']})"
    
    try:
        # Render email templates
        print("Rendering email templates...")
        html_content, text_content = render_morning_brief(context)
        print("Templates rendered successfully")
        
        if args.dry_run:
            date_str = datetime.now().strftime("%Y-%m-%d")
            save_dry_run_output(html_content, text_content, date_str)
            print("Dry-run completed successfully")
            return
        
        # Determine recipients
        if args.test_email:
            recipients = [args.test_email]
            print(f"Sending test email to: {args.test_email}")
        else:
            # Get recipients from environment
            newsletter_to = os.getenv("NEWSLETTER_TO")
            if not newsletter_to:
                print("Error: NEWSLETTER_TO environment variable not set")
                sys.exit(1)
            
            recipients = [email.strip() for email in newsletter_to.split(',')]
            print(f"Sending to {len(recipients)} recipients")
        
        # Check for confirmation if not test email
        if not args.test_email:
            confirm_send = os.getenv('CONFIRM_SEND')
            if confirm_send != '1':
                print("Error: CONFIRM_SEND=1 environment variable required for production sends")
                print("Set CONFIRM_SEND=1 to confirm you want to send to all subscribers")
                sys.exit(1)
        
        # Send email
        print("Sending email...")
        success = send_morning_brief_direct(html_content, text_content, subject, recipients)
        
        if success:
            print("Morning brief sent successfully")
        else:
            print("Failed to send morning brief")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
