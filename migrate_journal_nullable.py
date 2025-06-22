#!/usr/bin/env python3
"""Migration to allow NULL user_id in trading_journal."""
from app import app
from models import db


def migrate_database():
    """Alter trading_journal.user_id to be nullable."""
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text(
                    "ALTER TABLE trading_journal ALTER COLUMN user_id DROP NOT NULL"
                ))
                conn.commit()
            print("✅ user_id column set to nullable in trading_journal")
        except Exception as e:
            print(f"⚠️  Could not alter user_id column: {e}")


if __name__ == "__main__":
    print("🚀 Starting trading journal nullable migration...")
    migrate_database()
