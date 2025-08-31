# Options Plunge Morning Brief System

A comprehensive system for creating, previewing, and sending structured morning market briefs with support for email templates and social media content generation.

## Features

- **Structured Email Templates**: HTML and plain-text versions with consistent formatting
- **Data Validation**: Pydantic models ensure data integrity
- **Admin Interface**: Web-based form with live preview
- **Social Media Integration**: Automatic Twitter CSV generation
- **Flexible Sending**: Support for test emails and bulk distribution
- **CLI Tools**: Command-line interface for automation

## Quick Start

### 1. Install Dependencies

```bash
make install-deps
```

### 2. Test the System

```bash
make test
```

This will:
- Generate sample email files (dry run)
- Create Twitter CSV with 11 posts (5 one-offs + 6 thread posts)

### 3. Send a Test Email

```bash
python send_morning_brief.py daily_brief_sample.json --test-email your@email.com
```

### 4. Generate Social Media Content

```bash
make social-twitter
```

## File Structure

```
├── templates/email/
│   ├── morning_brief.html.jinja    # HTML email template
│   └── morning_brief.txt.jinja     # Plain-text email template
├── templates/admin/
│   └── morning_brief.html          # Admin interface
├── daily_brief_schema.py           # Pydantic data models
├── daily_brief_sample.json         # Sample data
├── emailer.py                      # Email rendering and sending
├── send_morning_brief.py           # CLI for sending emails
├── generate_twitter_csv.py         # CLI for social media
├── Makefile                        # Convenience commands
└── MORNING_BRIEF_README.md         # This file
```

## Data Schema

The morning brief uses a structured JSON format with the following fields:

### Required Fields
- `subject_theme`: Theme for the subject line
- `date`: Date in readable format (e.g., "August 20, 2025")
- `preheader`: Preheader text for email clients
- `market_overview`: Market overview section
- `macro_data`: Macro/Data section
- `spy_s1`, `spy_s2`, `spy_r1`, `spy_r2`, `spy_r3`: SPY levels
- `day_plan`: Array of day plan items
- `swing_plan`: Array of swing plan items
- `cta_url`: Call-to-action URL

### Optional Fields
- `logo_url`: URL to logo image
- `earnings`: Array of earnings items with `ticker` and `note`
- `sectors`: Sectors section
- `extra_levels`: Additional levels
- `on_deck`: On deck section

### Sample JSON

```json
{
  "subject_theme": "Range vibes, retail on deck",
  "date": "August 20, 2025",
  "preheader": "Indexes flat, housing starts beat, Home Depot miss w/ upbeat tone; SPY levels to watch inside.",
  "market_overview": "Indexes are flat after yesterday's tight range; with light news flow, expect range trading unless levels break.",
  "macro_data": "Housing Starts surprised to the upside (1.43M vs 1.29M expected). Rate-cut expectations make housing-sensitive names a focal point.",
  "earnings": [
    {
      "ticker": "HD",
      "note": "Small miss on rev/EPS ($45.3B vs $45.41B; $4.68 vs $4.72) but reiterated FY; momentum in smaller projects; retail sympathy with TGT tomorrow."
    }
  ],
  "spy_s1": "642.13",
  "spy_s2": "641.34/640",
  "spy_r1": "643.95",
  "spy_r2": "644.70",
  "spy_r3": "645.50+",
  "day_plan": [
    "Fade extremes of the range until it breaks; size down in chop.",
    "Track HD for retail read-through and position into TGT tomorrow."
  ],
  "swing_plan": [
    "Housing-linked names if data strength + rate-cut narrative persists; look for bases resolving higher."
  ],
  "on_deck": "Target (TGT) earnings tomorrow; monitor retail read-through.",
  "cta_url": "https://optionsplunge.com"
}
```

## Usage

### Make Commands

```bash
# Generate email files without sending (dry run)
make brief-dry

# Send to all subscribers (requires CONFIRM_SEND=1)
make brief-send

# Generate Twitter CSV
make social-twitter

# Run all tests
make test

# Clean output directories
make clean
```

### CLI Commands

```bash
# Send morning brief
python send_morning_brief.py daily_brief_sample.json

# Dry run (generate files only)
python send_morning_brief.py daily_brief_sample.json --dry-run

# Send test email
python send_morning_brief.py daily_brief_sample.json --test-email your@email.com

# Generate Twitter CSV
python generate_twitter_csv.py daily_brief_sample.json
```

### Admin Interface

Access the admin interface at `/admin/morning-brief` (admin access required).

Features:
- **Live Preview**: See email rendering in real-time
- **Form Validation**: Client-side and server-side validation
- **Test Sending**: Send test emails to verify delivery
- **Bulk Publishing**: Send to all confirmed subscribers

## Environment Variables

### Required
- `SENDGRID_API_KEY`: SendGrid API key for email delivery
- `EMAIL_FROM_NAME`: From name (default: "Options Plunge")
- `EMAIL_FROM`: From email (default: "support@optionsplunge.com")

### Optional
- `NEWSLETTER_TO`: Comma-separated list of recipients for CLI sends
- `TEST_EMAIL`: Email address for test sends
- `CONFIRM_SEND`: Set to "1" to enable production sends
- `MAIL_PROVIDER`: Email provider ("sendgrid" or "smtp")

## Email Templates

### HTML Template Features
- Responsive design for mobile and desktop
- Clean, professional styling
- Support for light/dark mode
- Optimized for Gmail and Outlook

### Plain-Text Template Features
- Structured formatting with clear sections
- Compatible with all email clients
- Fallback for HTML-disabled clients

## Social Media Integration

### Twitter CSV Format
The system generates a CSV with columns:
- `post_text`: The tweet content
- `type`: "one-off" or "thread"
- `order`: Post order for sequencing

### Content Structure
- **5 One-off Posts**: Key highlights, levels, earnings, plans
- **6 Thread Posts**: Comprehensive morning brief thread
- **Automatic Formatting**: Emojis, hashtags, and proper line breaks

## Integration with Existing System

The morning brief system integrates with the existing Options Plunge application:

### Database Integration
- Uses existing `MarketBriefSubscriber` model
- Leverages current email infrastructure
- Maintains user authentication and permissions

### Admin Access
- Restricted to `support@optionsplunge.com`
- Integrated with existing admin tools
- Consistent UI/UX with main application

### Email Infrastructure
- Uses existing SendGrid configuration
- Falls back to Flask-Mail SMTP
- Maintains email templates and styling

## Development

### Adding New Fields

1. Update `daily_brief_schema.py` with new Pydantic fields
2. Modify email templates to include new sections
3. Update admin form in `templates/admin/morning_brief.html`
4. Test with sample data

### Customizing Templates

Templates use Jinja2 syntax and support:
- Conditional sections (`{% if %}`)
- Loops (`{% for %}`)
- Variable interpolation (`{{ }}`)
- Template inheritance

### Testing

```bash
# Validate JSON schema
make validate-json

# Test email rendering
make brief-dry

# Test social media generation
make social-twitter

# Full system test
make test
```

## Troubleshooting

### Common Issues

1. **Template Rendering Errors**
   - Check Jinja2 syntax in templates
   - Verify all required fields are provided
   - Check for missing template files

2. **Email Sending Failures**
   - Verify SendGrid API key
   - Check email configuration
   - Review recipient list format

3. **Admin Access Issues**
   - Ensure user email matches `support@optionsplunge.com`
   - Check login status
   - Verify route permissions

### Debug Mode

Enable debug logging by setting environment variables:
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
```

## Production Deployment

### Environment Setup
1. Set all required environment variables
2. Configure SendGrid API key
3. Set up proper email domains
4. Test with small recipient list

### Monitoring
- Monitor email delivery rates
- Track template rendering performance
- Log admin actions for audit trail
- Monitor subscriber engagement

### Backup and Recovery
- Backup email templates
- Store sample data for recovery
- Document custom configurations
- Maintain deployment scripts

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review environment configuration
3. Test with sample data
4. Check application logs
5. Contact development team

---

**Last Updated**: January 2025
**Version**: 1.0.0



