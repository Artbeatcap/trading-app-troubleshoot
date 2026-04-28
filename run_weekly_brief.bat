@echo off
REM Weekly Market Brief Scheduler
REM Run this script via Windows Task Scheduler on Sundays

cd /d "C:\Users\Art\VScode\ai-trading-analysis-troubleshoot"

REM Set environment variables
set CONFIRM_SEND=1
set FLASK_ENV=production

REM Run the weekly brief (update path to your weekly brief JSON file)
python send_weekly_brief.py --source weekly_brief_sample.json

REM Log the result
echo Weekly brief completed at %date% %time% >> weekly_brief.log
