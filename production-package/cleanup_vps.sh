#!/bin/bash
# Cleanup script to remove test files and keep only production files

echo "Cleaning up VPS directory..."

cd /home/tradingapp/trading-analysis

# Remove test files and directories
rm -rf tests/
rm -f test_*.py
rm -f *_test.py
rm -f test-*.py

# Remove development files
rm -rf venv/
rm -rf __pycache__/
rm -rf .git/
rm -rf .github/
rm -f .gitignore

# Remove migration scripts (keep migrations folder)
rm -f migrate_*.py
rm -f fix_*.py

# Remove instance folder (contains local database)
rm -rf instance/

# Remove backup and temporary files
rm -f *.log
rm -f *.tmp
rm -f *.bak

# Keep only essential production files
echo "Keeping essential files:"
echo "- app.py"
echo "- config.py"
echo "- models.py"
echo "- forms.py"
echo "- ai_analysis.py"
echo "- requirements.txt"
echo "- wsgi.py"
echo "- gunicorn.conf.py"
echo "- deploy.sh"
echo "- templates/"
echo "- static/"
echo "- migrations/"

echo "Cleanup completed!" 