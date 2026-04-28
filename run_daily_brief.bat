@echo off
REM Daily Market Brief Scheduler
REM Run this script via Windows Task Scheduler or cron equivalent

cd /d "C:\Users\Art\VScode\ai-trading-analysis-troubleshoot"

REM Set environment variables
set CONFIRM_SEND=1
set FLASK_ENV=production

REM Run the daily brief
python send_daily_brief.py

REM Log the result
echo Daily brief completed at %date% %time% >> daily_brief.log
