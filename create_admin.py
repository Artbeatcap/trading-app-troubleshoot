#!/usr/bin/env python3
"""
Script to create admin user for the trading app
"""

import os
import sys
from app import app, db
from models import User

def create_admin_user():
    """Create admin user"""
    with app.app_context():
        # Check if admin already exists
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin = User(
            username='admin',
            email='clarencebellwork@gmail.com',
            email_verified=True
        )
        admin.set_password('admin123')
        
        # Add to database
        db.session.add(admin)
        db.session.commit()
        
        print("✅ Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("Email: clarencebellwork@gmail.com")

if __name__ == "__main__":
    create_admin_user() 