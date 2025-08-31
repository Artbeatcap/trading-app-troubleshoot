# Weekly Market Brief System

A complete Weekly Market Brief system that sends emails every Sunday at 12:00 PM ET to all users subscribed to weekly emails. Uses the same visual layout as the Daily Brief but with Weekly-specific content sections.

## Features

- **Same Layout as Daily Brief**: Reuses all CSS classes and styling from the Daily Brief
- **Weekly Content Sections**: Last Week in 60s, Sector Rotations, Top Movers, Options Sentiment, Levels to Watch, Week Ahead, Swing Playbook
- **Scheduled Delivery**: Automatically sends every Sunday at 12:00 PM ET
- **Free for All Users**: Weekly Brief is available to Free + Pro users (Daily remains Pro-only)
- **Database Integration**: Tracks subscriptions and delivery logs
- **Validation**: Pydantic schema validation for all content

## File Structure

```
├── templates/email/
│   ├── weekly_brief.html.jinja    # HTML email template
│   └── weekly_brief.txt.jinja     # Text email template
├── weekly_brief_schema.py         # Pydantic schema for validation
├── weekly_brief_sample.json       # Sample content data
├── send_weekly_brief.py           # Main sender script
├── weekly_brief_scheduler.py      # APScheduler implementation
├── migrate_weekly_subscription.py # Database migration
├── weekly-brief-scheduler.service # Systemd service file
├── weekly_brief_cron.sh          # Cron job script
└── WEEKLY_BRIEF_README.md        # This file
```

## Quick Start

### 1. Install Dependencies

```bash
make install-deps
```

### 2. Run Database Migration

```bash
make migrate-db
```

### 3. Test the System

```bash
# Test dry run (generates emails without sending)
make weekly-dry

# Validate JSON schema
make validate-weekly-json

# Run all tests
make test
```

### 4. Send Weekly Brief

```bash
# Send to all weekly subscribers
CONFIRM_SEND=1 make weekly-send
```

## Content Structure

The Weekly Brief uses this JSON structure:

```json
{
  "subject_theme": "Recap & Week Ahead",
  "date_human": "Aug 24, 2025",
  "preheader": "Your weekly market recap and what's ahead",
  "recap": {
    "index_blurb": "SPY gained 2.3% last week...",
    "sector_blurb": "Technology and communication services led gains...",
    "movers_bullets": ["NVDA +8.2% - AI chip demand surge", ...],
    "flow_blurb": "Put/call ratio dropped to 0.65..."
  },
  "levels": {
    "spy": {"s1": "445.50", "s2": "442.20", "r1": "451.80", "r2": "455.10", "r3": "458.40"},
    "qqq": {"s1": "375.20", "s2": "371.50", "r1": "382.10", "r2": "385.80", "r3": "389.20"}
  },
  "week_ahead": {
    "macro_bullets": ["Tue 2:00 PM ET - Fed Chair Powell speech...", ...],
    "earnings_bullets": ["Mon 4:05 PM ET - NVDA earnings", ...]
  },
  "swing_playbook_bullets": ["Long NVDA calls ahead of earnings...", ...],
  "cta_url": "https://optionsplunge.com/market-brief"
}
```

## Scheduling Options

### Option A: System Cron (Recommended)

Add to `/etc/crontab`:

```bash
CRON_TZ=America/New_York
0 12 * * SUN /srv/optionsplunge/weekly_brief_cron.sh >> /var/log/optionsplunge/weekly_brief.log 2>&1
```

### Option B: Systemd Service

```bash
# Copy service file
sudo cp weekly-brief-scheduler.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable weekly-brief-scheduler
sudo systemctl start weekly-brief-scheduler

# Check status
sudo systemctl status weekly-brief-scheduler
```

### Option C: APScheduler (In-App)

Add to your Flask app:

```python
from weekly_brief_scheduler import start_weekly_brief_scheduler

if os.getenv("ENABLE_SCHEDULER") == "1":
    start_weekly_brief_scheduler()
```

## Database Schema

The system adds these fields to the `users` table:

```sql
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS is_subscribed_weekly BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS is_subscribed_daily  BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS email_deliveries (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  kind VARCHAR(16) NOT NULL,    -- 'weekly' | 'daily'
  subject TEXT NOT NULL,
  sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
  provider_id TEXT
);
```

## Email Templates

### HTML Template (`weekly_brief.html.jinja`)
- Uses identical CSS classes as Daily Brief
- Responsive design with mobile optimization
- Sections: Header, Last Week in 60s, Sector Rotations, Top Movers, Options Sentiment, Levels to Watch, Week Ahead, Swing Playbook, Footer

### Text Template (`weekly_brief.txt.jinja`)
- Plain text fallback
- Clean formatting with section dividers
- All content preserved in text format

## Make Targets

```bash
make weekly-dry          # Generate emails without sending
make weekly-send         # Send to all weekly subscribers
make validate-weekly-json # Validate JSON schema
make migrate-db          # Run database migration
make test                # Run all tests
```

## Environment Variables

Required environment variables:

```bash
DATABASE_URL=postgresql://user:pass@localhost/dbname
SENDGRID_API_KEY=your_sendgrid_key
EMAIL_FROM_NAME=Options Plunge
EMAIL_FROM=support@optionsplunge.com
WEEKLY_BRIEF_SOURCE=weekly_brief_sample.json
CONFIRM_SEND=1  # Only for actual sending
```

## Logging

The system logs to:
- Console output with timestamps
- `/var/log/optionsplunge/weekly_brief.log` (if using cron)
- Database `email_deliveries` table

## Troubleshooting

### Common Issues

1. **Template rendering fails**: Check that all required fields are present in JSON
2. **Database connection fails**: Verify `DATABASE_URL` environment variable
3. **SendGrid errors**: Check `SENDGRID_API_KEY` and email configuration
4. **No subscribers found**: Verify `is_subscribed_weekly = TRUE` in database

### Debug Commands

```bash
# Test template rendering
python -c "from emailer import render_weekly_brief; import json; data=json.load(open('weekly_brief_sample.json')); html,text=render_weekly_brief(data); print('Templates rendered successfully')"

# Check database subscribers
python -c "from send_weekly_brief import get_weekly_subscribers; print(get_weekly_subscribers())"

# Validate JSON manually
python -c "from weekly_brief_schema import WeeklyBrief; import json; WeeklyBrief(**json.load(open('weekly_brief_sample.json')))"
```

## Integration with Daily Brief

- **Daily Brief**: Pro-only, sent weekdays at 8:00 AM ET
- **Weekly Brief**: Free + Pro, sent Sundays at 12:00 PM ET
- **Same Visual Design**: Both use identical CSS classes and layout
- **Separate Subscriptions**: Users can subscribe to daily, weekly, or both

## Future Enhancements

- [ ] A/B testing for subject lines
- [ ] Analytics tracking for open rates
- [ ] Dynamic content based on market conditions
- [ ] User preference management in web UI
- [ ] Archive of past weekly briefs
