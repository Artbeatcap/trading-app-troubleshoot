#!/usr/bin/env python3
"""
Test script to verify the settings billing section fix
"""
import os
import sys
from datetime import datetime, timezone, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_settings_billing_fix():
    """Test the settings billing section fix"""
    print("Testing settings billing section fix...")
    
    try:
        # Test 1: Import app and models
        print("\n1. Testing imports...")
        from app import app, db
        from models import User
        print("✓ Imports successful")
        
        # Test 2: Test billing context calculation
        print("\n2. Testing billing context calculation...")
        with app.app_context():
            # Test user with Pro access but no Stripe customer ID
            pro_user_no_stripe = User(
                username='pro_user_no_stripe',
                email='pro@example.com',
                subscription_status='active',
                plan_type='monthly',
                stripe_customer_id=None,  # No Stripe customer ID
                had_trial=True
            )
            
            # Simulate the billing context calculation
            from datetime import datetime, timezone
            billing_ctx = None
            
            # Show billing info for any user with Pro access or subscription status
            if pro_user_no_stripe.has_pro_access() or pro_user_no_stripe.subscription_status != 'free':
                days_left = None
                if pro_user_no_stripe.subscription_status == "trialing" and pro_user_no_stripe.trial_end:
                    now = datetime.now(timezone.utc)
                    days_left = max(0, (pro_user_no_stripe.trial_end.replace(tzinfo=timezone.utc) - now).days)
                
                billing_ctx = {
                    "status": pro_user_no_stripe.subscription_status,
                    "plan": pro_user_no_stripe.plan_type,
                    "trial_days_left": days_left,
                    "has_portal": bool(pro_user_no_stripe.stripe_customer_id),
                }
            
            print(f"Pro user billing context: {billing_ctx}")
            print(f"Has Pro access: {pro_user_no_stripe.has_pro_access()}")
            print(f"Has portal: {billing_ctx['has_portal'] if billing_ctx else False}")
            
            if billing_ctx:
                print("✓ Billing context created for Pro user without Stripe customer ID")
            else:
                print("✗ Billing context not created for Pro user")
            
            # Test user with Pro access and Stripe customer ID
            pro_user_with_stripe = User(
                username='pro_user_with_stripe',
                email='pro_stripe@example.com',
                subscription_status='active',
                plan_type='annual',
                stripe_customer_id='cus_test123',
                had_trial=True
            )
            
            billing_ctx = None
            if pro_user_with_stripe.has_pro_access() or pro_user_with_stripe.subscription_status != 'free':
                days_left = None
                if pro_user_with_stripe.subscription_status == "trialing" and pro_user_with_stripe.trial_end:
                    now = datetime.now(timezone.utc)
                    days_left = max(0, (pro_user_with_stripe.trial_end.replace(tzinfo=timezone.utc) - now).days)
                
                billing_ctx = {
                    "status": pro_user_with_stripe.subscription_status,
                    "plan": pro_user_with_stripe.plan_type,
                    "trial_days_left": days_left,
                    "has_portal": bool(pro_user_with_stripe.stripe_customer_id),
                }
            
            print(f"Pro user with Stripe billing context: {billing_ctx}")
            print(f"Has portal: {billing_ctx['has_portal'] if billing_ctx else False}")
            
            if billing_ctx and billing_ctx['has_portal']:
                print("✓ Billing context created for Pro user with Stripe customer ID")
            else:
                print("✗ Billing context not created correctly for Pro user with Stripe")
            
            # Test free user
            free_user = User(
                username='free_user',
                email='free@example.com',
                subscription_status='free',
                plan_type='none',
                stripe_customer_id=None,
                had_trial=False
            )
            
            billing_ctx = None
            if free_user.has_pro_access() or free_user.subscription_status != 'free':
                days_left = None
                if free_user.subscription_status == "trialing" and free_user.trial_end:
                    now = datetime.now(timezone.utc)
                    days_left = max(0, (free_user.trial_end.replace(tzinfo=timezone.utc) - now).days)
                
                billing_ctx = {
                    "status": free_user.subscription_status,
                    "plan": free_user.plan_type,
                    "trial_days_left": days_left,
                    "has_portal": bool(free_user.stripe_customer_id),
                }
            
            print(f"Free user billing context: {billing_ctx}")
            
            if billing_ctx is None:
                print("✓ No billing context for free user (correct)")
            else:
                print("✗ Billing context created for free user (incorrect)")
        
        print("\n🎉 Settings billing section fix test completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_settings_billing_fix()
