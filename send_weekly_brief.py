#!/usr/bin/env python3
"""
Weekly Market Brief Sender (Hybrid)

If a source JSON is provided, uses it. Otherwise builds a Weekly Brief with:
 - Week of <Mon–Fri> date range
 - Week-ahead catalysts (returns [] on the current Polygon Starter tier)
 - Movers snapshot via providers.DataProvider (Polygon gainers/losers)
Sends the email and writes a preview HTML for /brief/weekly.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pytz import timezone
NY = timezone("America/New_York")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from emailer import render_weekly_brief, send_weekly_brief_direct, send_weekly_brief
from market_brief_generator import build_weekly_brief, BriefDataUnavailable, summarize_news_weekly
from html import escape

logger = logging.getLogger("weekly_brief_sender")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _render_markdown_to_html(md: str) -> str:
    """
    Lightweight markdown-to-HTML renderer for weekly recap content.
    Supports headings (#, ##, ###), basic bullet lists, and paragraphs.
    Designed to match app typography (no monospace blocks).
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

        # Blank line → paragraph break
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

        # Bullets (unordered)
        is_bullet = False
        bullet_text = ""

        if stripped.startswith(("- ", "• ")):
            is_bullet = True
            bullet_text = stripped[2:].strip()
        else:
            # Simple ordered list pattern: "1. text"
            parts = stripped.split(". ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                is_bullet = True
                bullet_text = stripped

        if is_bullet:
            if not in_list:
                html_lines.append('<ul class="llm-list">')
                in_list = True
            html_lines.append(f"<li>{escape(bullet_text)}</li>")
            continue

        # Plain paragraph
        close_list()
        html_lines.append(f'<p class="llm-text">{escape(stripped)}</p>')

    close_list()
    body = "\n".join(html_lines).strip()
    return f'<div class="llm-recap-body">{body}</div>' if body else ""

def load_weekly_context_from_json(path: Path) -> dict:
    """Load weekly context from a JSON file if present"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_weekly_subscribers() -> List[str]:
    """Get weekly subscriber list from database (Pro users + weekly subscribers) or environment fallback"""
    try:
        # Try to get subscribers from database first
        from app import app, db
        from models import User
        
        with app.app_context():
            # Get Pro users (active or trialing) + users with weekly subscription enabled
            subscribers = User.query.filter(
                db.or_(
                    # Pro users should get weekly brief
                    User.subscription_status.in_(['active', 'trialing']),
                    # Users who explicitly subscribed to weekly
                    User.is_subscribed_weekly == True
                ),
                User.email_verified == True
            ).all()
            
            emails = [user.email for user in subscribers if user.email]
            logger.info(f"📧 Found {len(emails)} weekly subscribers (Pro users + weekly subscribers)")
            return emails
            
    except Exception as e:
        logger.warning(f"Database query failed ({e}), falling back to environment variables")
        
        # Fallback to environment variable
        weekly_to = os.getenv("WEEKLY_TO") or os.getenv("NEWSLETTER_TO")
        if not weekly_to:
            logger.error("No WEEKLY_TO or NEWSLETTER_TO configured")
            return []
        return [e.strip() for e in weekly_to.split(',') if e.strip()]

def render_weekly_email(context: dict) -> tuple[str, str]:
    """Render weekly email HTML and text via weekly templates (fallback to morning if needed)."""
    try:
        return render_weekly_brief(context)
    except Exception as e:
        logger.warning(f"render_weekly_brief failed ({e}); falling back to morning templates.")
        from emailer import render_morning_brief
        return render_morning_brief(context)

def save_preview(html_content: str, label: str = "Weekly"):
    """Save latest weekly brief for the Flask preview route"""
    try:
        base = Path(__file__).resolve().parent
        upload = base / "static" / "uploads"
        upload.mkdir(parents=True, exist_ok=True)
        (upload / "brief_weekly_latest.html").write_text(html_content, encoding="utf-8")
        # Write a weekly-specific date file so the daily freshness banner
        # on /brief/latest is not driven by the weekly send.
        (upload / "brief_weekly_latest_date.txt").write_text(
            datetime.now(tz=NY).strftime("%Y-%m-%d %H:%M ET"), encoding="utf-8"
        )
        try:
            from tasks import mark_weekly_sent

            mark_weekly_sent()
        except Exception:
            # Scheduler persistence is best-effort; failures shouldn't break the send.
            logger.debug("Could not update weekly scheduler state", exc_info=True)
        logger.info(f"Saved {label} preview to {upload}")
    except Exception as e:
        logger.warning(f"Could not save preview: {e}")

def main():
    parser = argparse.ArgumentParser(description="Send Weekly Market Brief")
    parser.add_argument("--source", help="Path to weekly JSON file (optional)", required=False)
    parser.add_argument("--dry-run", action="store_true", help="Write files but do not send")
    parser.add_argument("--test-email", help="Send to a single email for testing")
    args = parser.parse_args()

    # -------------------------------------------------------------------
    # Real-send safety gate.
    # A production send to the full subscriber list is only permitted when
    # WEEKLY_ALLOW_REAL_SEND=1 is set. That flag is set ONLY by the systemd
    # weekly scheduler unit (via Environment= in its override.conf), so any
    # ad-hoc invocation (shell, python REPL, cron, test harness) is
    # automatically forced into --dry-run mode — even if CONFIRM_SEND=1 is
    # already in the environment and even if the caller forgot --dry-run.
    # Single-recipient `--test-email ...` runs are still allowed because they
    # cannot blast the subscriber list.
    # -------------------------------------------------------------------
    allow_real = os.getenv("WEEKLY_ALLOW_REAL_SEND") == "1"
    if not args.dry_run and not args.test_email and not allow_real:
        logger.warning(
            "WEEKLY_ALLOW_REAL_SEND is not set; forcing --dry-run to prevent "
            "an accidental subscriber blast. Only the systemd weekly "
            "scheduler service should set this flag."
        )
        args.dry_run = True

    context: dict
    if args.source:
        src = Path(args.source)
        if not src.exists():
            logger.error(f"Source file not found: {src}")
            sys.exit(1)
        context = load_weekly_context_from_json(src)
        logger.info(f"Loaded weekly context from {src}")
    else:
        logger.info("No --source provided; building weekly brief with hybrid pipeline.")
        try:
            context = build_weekly_brief()
        except BriefDataUnavailable as err:
            logger.error(f"Weekly brief aborted: {err}")
            sys.exit(1)

    # Optional: generate enhanced LLM weekly recap for inclusion in the email
    try:
        weekly_md = summarize_news_weekly()
    except Exception as e:
        logger.warning(f"Enhanced weekly recap generation failed: {e}")
        weekly_md = ""

    if weekly_md:
        llm_html = _render_markdown_to_html(weekly_md)
        context["llm_weekly_recap_md"] = weekly_md
        context["llm_weekly_recap_html"] = llm_html

    # Subject
    dr = context.get("date_range", {})
    label = dr.get("label") or datetime.now(tz=NY).strftime("Week of %Y-%m-%d")
    subject = context.get("subject") or f"Options Plunge — Weekly Brief — {label}"

    # Render templates
    try:
        html, text = render_weekly_email(context)
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        sys.exit(1)

    # Test vs production
    if args.test_email:
        recipients = [args.test_email]
        logger.info(f"Sending weekly brief to test recipient: {args.test_email}")
    else:
        recipients = get_weekly_subscribers()
        if not recipients:
            logger.error("No recipients configured")
            sys.exit(1)
        confirm = os.getenv("CONFIRM_SEND")
        if confirm != "1":
            logger.error("Set CONFIRM_SEND=1 to confirm weekly send")
            sys.exit(1)

    # Dry run?
    if args.dry_run:
        outdir = Path("out/weekly") / datetime.now(tz=NY).strftime("%Y-%m-%d")
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "weekly.html").write_text(html, encoding="utf-8")
        (outdir / "weekly.txt").write_text(text, encoding="utf-8")
        logger.info(f"Dry-run files saved to {outdir}")
        save_preview(html, label="Weekly (dry-run)")
        return

    # Send
    try:
        success = send_weekly_brief(html, text, subject, recipients) or send_weekly_brief_direct(html, text, subject, recipients)
        if not success:
            logger.error("Weekly brief send failed")
            sys.exit(1)
        logger.info(f"Weekly brief sent to {len(recipients)} recipients")
        save_preview(html, label="Weekly")
    except Exception as e:
        logger.error(f"Error sending weekly brief: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()