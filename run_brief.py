#!/usr/bin/env python3
from app import app

with app.app_context():
    from market_brief_generator import send_market_brief_to_subscribers
    n = send_market_brief_to_subscribers()
    print("SENT", n)
