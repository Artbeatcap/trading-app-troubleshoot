#!/usr/bin/env python3
"""
Backfill user newsletter subscriptions for existing users.

Rules:
- All users: ensure is_subscribed_weekly = True
- Pro (active or trialing): is_subscribed_daily = True
- Non‑Pro: is_subscribed_daily = False
- Ensure a confirmed, active MarketBriefSubscriber exists for each user
"""

from typing import Tuple
from datetime import datetime

from app import app
from models import db, User, MarketBriefSubscriber


def backfill() -> Tuple[int, int, int]:
    updated_users = 0
    created_subscribers = 0
    reactivated_subscribers = 0

    with app.app_context():
        users = User.query.all()
        for user in users:
            changed = False

            # Weekly on for everyone
            try:
                if getattr(user, 'is_subscribed_weekly', None) is not True:
                    user.is_subscribed_weekly = True
                    changed = True
            except Exception:
                pass

            # Daily based on Pro access
            try:
                want_daily = user.has_pro_access()
                if getattr(user, 'is_subscribed_daily', None) != want_daily:
                    user.is_subscribed_daily = want_daily
                    changed = True
            except Exception:
                pass

            if changed:
                updated_users += 1

            # Ensure MarketBriefSubscriber exists and is confirmed/active
            sub = MarketBriefSubscriber.query.filter_by(email=user.email).first()
            if not sub:
                sub = MarketBriefSubscriber(
                    email=user.email,
                    name=getattr(user, 'username', None) or getattr(user, 'display_name', None) or 'Trader',
                    confirmed=True,
                    is_active=True,
                    subscribed_at=datetime.utcnow(),
                )
                db.session.add(sub)
                created_subscribers += 1
            else:
                fixed = False
                if not sub.confirmed:
                    sub.confirmed = True
                    fixed = True
                if hasattr(sub, 'is_active') and not sub.is_active:
                    sub.is_active = True
                    fixed = True
                if fixed:
                    reactivated_subscribers += 1

        db.session.commit()

    return updated_users, created_subscribers, reactivated_subscribers


if __name__ == "__main__":
    u, c, r = backfill()
    print(f"Users updated: {u}, new subscribers: {c}, reactivated: {r}")


