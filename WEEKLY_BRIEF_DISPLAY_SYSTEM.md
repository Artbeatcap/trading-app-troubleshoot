# Weekly Brief Display System

## Overview

The Weekly Market Brief system now includes a comprehensive display interface that shows both Daily and Weekly briefs with historical access up to 14 days back.

## Features

### 🎯 **Dual Brief Display**
- **Daily Brief Tab**: Pro-only access with "Pro" badge
- **Weekly Brief Tab**: Free for all users with "Free" badge
- **Tabbed Interface**: Clean separation between brief types

### 📚 **Historical Brief Access**
- **14-Day History**: Users can view briefs from the last 14 days
- **Daily Briefs**: Pro users see up to 10 recent daily briefs
- **Weekly Briefs**: All users see up to 5 recent weekly briefs
- **Individual Brief Pages**: Click any brief to view full content

### 🔐 **Access Control**
- **Daily Briefs**: Pro users only (`subscription_status == 'active'`)
- **Weekly Briefs**: Free for all users
- **Pro Upsell**: Free users see upgrade prompt on Daily tab

## Database Schema

### MarketBrief Model
```python
class MarketBrief(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brief_type = db.Column(db.String(16), nullable=False)  # 'daily' or 'weekly'
    date = db.Column(db.Date, nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    html_content = db.Column(db.Text, nullable=False)
    text_content = db.Column(db.Text, nullable=False)
    json_data = db.Column(db.Text)  # Store original JSON data
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
```

### EmailDelivery Model
```python
class EmailDelivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kind = db.Column(db.String(16), nullable=False)  # 'daily' or 'weekly'
    subject = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    provider_id = db.Column(db.String(100))
```

## File Structure

```
templates/
├── market_brief.html          # Main brief display page with tabs
└── view_brief.html           # Individual brief viewing page

scripts/
├── send_weekly_brief.py      # Weekly brief sender (stores in DB)
├── populate_sample_briefs.py # Sample data generator
└── migrate_market_briefs_table.py # Database migration

models.py                     # Updated with MarketBrief and EmailDelivery models
app.py                       # Updated routes for brief display
```

## Routes

### `/market_brief`
- **GET**: Display main brief page with tabs
- **POST**: Handle email subscriptions
- **Features**: 
  - Loads latest daily/weekly briefs
  - Shows historical briefs (14 days)
  - Pro access control for daily briefs

### `/brief/<brief_id>`
- **GET**: View individual brief
- **Features**:
  - Full brief content display
  - Access control (daily = Pro only)
  - Share functionality
  - Navigation between briefs

## User Experience

### Pro Users
1. **Daily Tab**: See latest daily brief + historical access
2. **Weekly Tab**: See latest weekly brief + historical access
3. **Full Access**: All features and historical briefs

### Free Users
1. **Daily Tab**: Pro upsell with lock icon
2. **Weekly Tab**: Full access to weekly briefs
3. **Limited Access**: Weekly briefs only

## Admin Testing

### Quick Commands
```bash
# Check admin status
python upgrade_admin_to_pro.py status

# Switch between Pro and Free
python upgrade_admin_to_pro.py upgrade   # Pro
python upgrade_admin_to_pro.py downgrade # Free

# Create sample briefs
python populate_sample_briefs.py

# Test weekly brief system
python send_weekly_brief.py --source weekly_brief_sample.json --dry-run
```

### Makefile Targets
```bash
make admin-pro          # Upgrade admin to Pro
make admin-free         # Downgrade admin to Free
make admin-status       # Show admin status
make migrate-briefs     # Create database table
make populate-samples   # Create sample briefs
make test-briefs        # Test complete system
```

## Implementation Details

### Brief Storage
- **Automatic Storage**: Briefs stored in database when sent
- **JSON Backup**: Original data preserved for regeneration
- **Deduplication**: Prevents duplicate briefs for same date

### Historical Access
- **14-Day Limit**: Configurable cutoff for performance
- **Pagination**: Limits number of briefs shown (10 daily, 5 weekly)
- **Date Filtering**: Efficient queries with database indexes

### Access Control
- **User Authentication**: Check login status
- **Subscription Status**: Verify Pro access for daily briefs
- **Graceful Degradation**: Show upsell for restricted content

## Future Enhancements

### Potential Features
- **Search Functionality**: Search briefs by content/date
- **Export Options**: PDF/email export of briefs
- **Bookmarking**: Save favorite briefs
- **Analytics**: Track brief views and engagement
- **Mobile Optimization**: Responsive design improvements

### Technical Improvements
- **Caching**: Redis cache for frequently accessed briefs
- **CDN**: Static content delivery for better performance
- **API Endpoints**: REST API for brief access
- **Webhooks**: Real-time brief notifications

## Testing Checklist

- [x] Database migration creates tables correctly
- [x] Weekly brief sender stores in database
- [x] Sample briefs populate successfully
- [x] Pro users can access daily briefs
- [x] Free users see weekly briefs only
- [x] Historical briefs display correctly
- [x] Individual brief pages work
- [x] Access control functions properly
- [x] Admin tools work for testing

## Deployment Notes

1. **Run Migration**: `python migrate_market_briefs_table.py`
2. **Update Models**: Ensure `models.py` includes new models
3. **Test Brief Storage**: Verify briefs save to database
4. **Check Access Control**: Test Pro vs Free user experience
5. **Monitor Performance**: Watch database query performance

## Support

For issues or questions about the Weekly Brief Display System:
- Check database connectivity
- Verify user subscription status
- Test with sample data first
- Review access control logic
