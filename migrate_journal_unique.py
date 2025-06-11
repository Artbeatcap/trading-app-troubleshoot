#!/usr/bin/env python3
"""Database migration script to enforce unique journal dates per user."""

from app import app
from models import db


def migrate_database():
    """Add unique constraint on (user_id, journal_date) in trading_journal."""
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.execute(
                    db.text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uix_user_journal_date ON trading_journal (user_id, journal_date)"
                    )
                )
                conn.commit()
            print("✅ Added unique constraint on user_id and journal_date")
        except Exception as e:
            print(f"⚠️  Could not create constraint: {e}")

        print("\n🎉 Journal constraint migration completed!")


if __name__ == "__main__":
    print("🚀 Starting journal unique constraint migration...")
    migrate_database()
