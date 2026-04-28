#!/usr/bin/env python3
"""Debug register route context"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from flask import render_template

with app.app_context():
    with app.test_request_context('/register'):
        # Get the context
        from app import inject_config
        ctx = inject_config()
        
        print("=" * 50)
        print("Register Route Context Debug")
        print("=" * 50)
        print(f"google_oauth_enabled: {ctx.get('google_oauth_enabled')}")
        print(f"Type: {type(ctx.get('google_oauth_enabled'))}")
        print(f"Bool value: {bool(ctx.get('google_oauth_enabled'))}")
        
        # Check config
        print(f"\nApp config GOOGLE_OAUTH_CLIENT_ID: {app.config.get('GOOGLE_OAUTH_CLIENT_ID')[:20] if app.config.get('GOOGLE_OAUTH_CLIENT_ID') else 'None'}...")
        print(f"Blueprints: {list(app.blueprints.keys())}")
        print(f"'google' in blueprints: {'google' in app.blueprints}")
        
        # Try rendering the template
        print("\n" + "=" * 50)
        print("Template Rendering Test")
        print("=" * 50)
        from forms import RegistrationForm
        form = RegistrationForm()
        html = render_template("register.html", form=form, hide_sidebar=True)
        
        has_button = 'Sign up with Google' in html
        print(f"Button in rendered HTML: {has_button}")
        
        if has_button:
            idx = html.find('Sign up with Google')
            print(f"Found at index: {idx}")
            print(f"Context: {html[max(0, idx-100):idx+100]}")
        else:
            # Check what's after the submit button
            submit_idx = html.find('btn-success')
            if submit_idx > 0:
                print(f"\nAfter submit button:")
                print(html[submit_idx:submit_idx+500])


