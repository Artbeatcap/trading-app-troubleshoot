#!/usr/bin/env python3
"""
Send welcome confirmation emails to subscribers created by the backfill.

Criteria:
- MarketBriefSubscriber.confirmed = True and is_active = True
- subscribed_at within the last N hours (default 24)
Logs an EmailDelivery record with kind = 'welcome_on_register'.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from app import app
from models import db, User, MarketBriefSubscriber, EmailDelivery


def send_to_recent(recent_hours: int = 24) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=recent_hours)
    sent = 0

    with app.app_context():
        # Ensure cutoff is naive if DB stores naive UTC
        naive_cutoff = cutoff.replace(tzinfo=None)

        recent_subs = (
            MarketBriefSubscriber.query
            .filter(MarketBriefSubscriber.confirmed == True)
            .filter(MarketBriefSubscriber.is_active == True)
            .filter(MarketBriefSubscriber.subscribed_at >= naive_cutoff)
            .all()
        )

        from emails import send_welcome_on_register

        for sub in recent_subs:
            user: Optional[User] = User.query.filter_by(email=sub.email).first()
            if not user:
                continue

            # avoid duplicate by checking EmailDelivery
            existing = (
                EmailDelivery.query
                .filter_by(user_id=user.id, kind='welcome_on_register')
                .first()
            )
            if existing:
                continue

            ok = False
            try:
                ok = send_welcome_on_register(user)
            except Exception:
                ok = False

            if ok:
                try:
                    ed = EmailDelivery(
                        user_id=user.id,
                        kind='welcome_on_register',
                        subject='Welcome to Options Plunge — Market Brief Preferences',
                        sent_at=datetime.utcnow(),
                        provider_id=None,
                    )
                    db.session.add(ed)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                sent += 1

    return sent


if __name__ == '__main__':
    hours = int(os.getenv('WELCOME_BACKFILL_HOURS', '24'))
    n = send_to_recent(hours)
    print(f"Welcome emails sent: {n}")


