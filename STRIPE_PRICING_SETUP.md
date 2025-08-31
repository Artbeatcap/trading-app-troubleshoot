# Stripe Pricing Setup Guide

This guide will help you set up the new pricing system with Stripe integration for Options Plunge.

## 🚀 Quick Start

1. **Install Stripe**: `pip install stripe==7.11.0`
2. **Run Migration**: `python migrate_subscription_fields.py`
3. **Configure Stripe**: Set up your Stripe account and get API keys
4. **Update Environment**: Add Stripe variables to your `.env` file
5. **Test**: Visit `/pricing` to test the checkout flow

## 📋 Prerequisites

- Stripe account (free to set up)
- Python 3.7+
- Flask application running

## 🔧 Step-by-Step Setup

### 1. Install Dependencies

The Stripe library has been added to `requirements.txt`. Install it:

```bash
pip install stripe==7.11.0
```

### 2. Database Migration

Run the migration script to add subscription fields to your User model:

```bash
python migrate_subscription_fields.py
```

This will add the following columns to your `user` table:
- `subscription_status` (free, trialing, active, canceled)
- `plan_type` (none, monthly, annual)
- `stripe_customer_id` (unique)
- `stripe_subscription_id` (unique)

### 3. Stripe Account Setup

#### Create Stripe Account
1. Go to [stripe.com](https://stripe.com) and create an account
2. Complete the account verification process
3. Switch to test mode for development

#### Get API Keys
1. Go to [Stripe Dashboard > API Keys](https://dashboard.stripe.com/apikeys)
2. Copy your **Publishable Key** and **Secret Key**
3. Keep these secure - never commit them to version control

#### Create Products and Prices
1. Go to [Stripe Dashboard > Products](https://dashboard.stripe.com/products)
2. Create a new product called "Options Plunge Pro"
3. Add two prices:
   - **Monthly**: $29/month
   - **Annual**: $228/year ($19/month billed annually)
4. Copy the Price IDs (they start with `price_`)

#### Set Up Webhooks
1. Go to [Stripe Dashboard > Webhooks](https://dashboard.stripe.com/webhooks)
2. Click "Add endpoint"
3. Set the endpoint URL to: `https://yourdomain.com/api/billing/webhook`
4. Select these events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
5. Copy the webhook signing secret

### 4. Environment Configuration

Add these variables to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your-secret-key-here
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret-here

# Stripe Price IDs
STRIPE_PRICE_MONTHLY=price_your-monthly-price-id
STRIPE_PRICE_ANNUAL=price_your-annual-price-id
```

### 5. Test the Setup

1. Start your Flask application
2. Visit `/pricing` to see the pricing page
3. Test the checkout flow with Stripe test cards:
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`

## 🎯 Features Implemented

### Frontend
- ✅ Modern pricing page with Bootstrap styling
- ✅ Monthly/Annual billing toggle
- ✅ Feature comparison grid
- ✅ Secure checkout integration
- ✅ Loading states and error handling
- ✅ Mobile-responsive design

### Backend
- ✅ Stripe Checkout Session creation
- ✅ Webhook handling for subscription events
- ✅ User subscription status tracking
- ✅ Pro feature protection with `@requires_pro` decorator
- ✅ Database migration for subscription fields

### Pricing Structure
- **Free Plan**: Basic features, no cost
- **Pro Plan**: 
  - Monthly: $29/month
  - Annual: $19/month billed annually ($228/year) - **34% savings**

## 🔒 Pro Features Protection

The following features are now protected with the `@requires_pro` decorator:

- **Bulk Analysis** (`/bulk_analysis`)
- **AI Trading Tool** (already protected)
- **Options Calculator** (already protected)
- **Daily Market Brief** (already protected)

To protect additional routes, add the decorator:

```python
from billing import requires_pro

@app.route("/your-pro-route")
@requires_pro
def your_pro_route():
    # Only accessible to Pro users
    pass
```

## 🧪 Testing

### Test Cards
Use these Stripe test cards for testing:

| Card Number | Description |
|-------------|-------------|
| `4242 4242 4242 4242` | Successful payment |
| `4000 0000 0000 0002` | Declined payment |
| `4000 0025 0000 3155` | Requires authentication |

### Test Scenarios
1. **Free User**: Should be redirected to pricing when accessing Pro features
2. **Pro User**: Should have full access to all features
3. **Checkout Flow**: Should redirect to Stripe and back to success page
4. **Webhook Events**: Should update user subscription status

## 🚨 Production Checklist

Before going live:

- [ ] Switch Stripe to live mode
- [ ] Update environment variables with live keys
- [ ] Set up production webhook endpoint
- [ ] Test with real payment methods
- [ ] Configure proper error handling
- [ ] Set up monitoring for webhook failures
- [ ] Review security settings

## 🔧 Troubleshooting

### Common Issues

**"Stripe price ID not configured"**
- Check that `STRIPE_PRICE_MONTHLY` and `STRIPE_PRICE_ANNUAL` are set
- Verify the price IDs exist in your Stripe dashboard

**"Webhook signature verification failed"**
- Ensure `STRIPE_WEBHOOK_SECRET` is correct
- Check that webhook endpoint URL is accessible

**"User not found for checkout"**
- Verify user authentication is working
- Check that user exists in database

**Migration errors**
- Ensure database connection is working
- Check that you have write permissions to the database

### Debug Mode

Enable debug logging by adding to your `.env`:

```bash
FLASK_ENV=development
FLASK_DEBUG=1
```

## 📞 Support

If you encounter issues:

1. Check the Flask application logs
2. Verify Stripe dashboard for webhook events
3. Test with Stripe's webhook testing tool
4. Review the billing.py module for error handling

## 🎉 Success!

Once everything is working:

1. Users can visit `/pricing` to see plans
2. Pro users get access to premium features
3. Subscription management is handled automatically
4. Revenue tracking is available in Stripe dashboard

The pricing system is now fully integrated and ready for production use!

