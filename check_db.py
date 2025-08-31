#!/usr/bin/env python3
from app import app, db
from sqlalchemy import text

def check_db():
    with app.app_context():
        try:
            # Check user table columns
            result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'user'"))
            columns = [row[0] for row in result]
            print("User table columns:", columns)
            
            # Check for our new columns
            if 'trial_end' in columns:
                print("✓ trial_end column exists")
            else:
                print("✗ trial_end column missing")
                
            if 'had_trial' in columns:
                print("✓ had_trial column exists")
            else:
                print("✗ had_trial column missing")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
