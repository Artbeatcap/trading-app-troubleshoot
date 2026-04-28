#!/usr/bin/env python3
"""
Manual helper to send the latest market brief email to a single address.
"""

import os
from datetime import datetime

from app import app
from market_brief_generator import send_market_brief_to_subscribers


def _send_to_single(brief_html: str, date_str: str | None = None) -> int:
    """
    Replacement for emails.send_daily_brief_direct that emails a single address.
    """
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail as SGMail, Email as SGEmail, To as SGTo, Content as SGContent
    from flask_mail import Message
    from app import mail

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    subject = f"Morning Market Brief - {date_str} (manual send)"
    recipient = os.getenv("MANUAL_BRIEF_EMAIL", "clarencebell@gmail.com")

    sendgrid_key = os.getenv("SENDGRID_KEY")
    if sendgrid_key:
        sg = SendGridAPIClient(api_key=sendgrid_key)
        from_email = SGEmail("support@optionsplunge.com", "Options Plunge")
        to_email = SGTo(recipient)
        content = SGContent("text/html", brief_html)
        sg_mail = SGMail(from_email, to_email, subject, content)
        response = sg.send(sg_mail)
        if response.status_code not in (200, 202):
            raise RuntimeError(f"SendGrid returned {response.status_code}: {response.body}")
        return 1

    msg = Message(
        subject=subject,
        recipients=[recipient],
        html=brief_html,
        sender=app.config.get("MAIL_DEFAULT_SENDER"),
    )
    mail.send(msg)
    return 1


def main() -> None:
    import emails

    target = os.getenv("MANUAL_BRIEF_EMAIL", "clarencebell@gmail.com")
    print(f"Sending manual brief to {target}")
    emails.send_daily_brief_direct = _send_to_single

    with app.app_context():
        result = send_market_brief_to_subscribers()
        print(f"Manual brief send result: {result}")


if __name__ == "__main__":
    main()






