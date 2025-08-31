#!/bin/bash
# Weekly Market Brief Cron Job
# Runs every Sunday at 12:00 PM ET

# Set environment variables
export DATABASE_URL="postgresql://optionsplunge:password@localhost/optionsplunge"
export SENDGRID_API_KEY="your_sendgrid_key_here"
export EMAIL_FROM_NAME="Options Plunge"
export EMAIL_FROM="support@optionsplunge.com"
export CONFIRM_SEND="1"

# Set working directory
cd /srv/optionsplunge

# Activate virtual environment
source venv/bin/activate

# Run weekly brief sender
python send_weekly_brief.py --source weekly_brief_sample.json

# Log completion
echo "$(date): Weekly brief cron job completed" >> /var/log/optionsplunge/weekly_brief.log
