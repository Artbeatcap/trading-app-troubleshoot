#!/bin/bash
# Simple script to clean up VPS directory for fresh GitHub deployment

echo "Cleaning up VPS directory for fresh deployment..."

cd /home/tradingapp/trading-analysis

# Remove all files and directories (except the directory itself)
rm -rf *

echo "VPS directory cleaned. Ready for GitHub deployment."
echo "Current directory contents:"
ls -la 