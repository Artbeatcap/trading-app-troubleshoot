#!/bin/bash
# Deploy Options Calculator Fix to Live App
# This script updates the live trading analysis app with the latest changes

echo "🚀 Deploying Options Calculator Fix to Live App..."

# Configuration
SERVER_IP="167.88.43.61"
REMOTE_PATH="/home/tradingapp/trading-analysis"
LOCAL_PATH="."

# Step 1: Create a backup of the current live app
echo "📦 Creating backup of current live app..."
timestamp=$(date +"%Y%m%d_%H%M%S")
backup_name="trading-analysis-backup-$timestamp.tar.gz"

ssh root@$SERVER_IP "cd $REMOTE_PATH && tar -czf $backup_name --exclude='venv*' --exclude='__pycache__' --exclude='*.log' ."

# Step 2: Copy the updated .env file
echo "🔧 Updating environment configuration..."
scp .env root@${SERVER_IP}:${REMOTE_PATH}/.env

# Step 3: Copy the main application files
echo "📁 Copying updated application files..."

# Core application files
core_files=("app.py" "config.py" "models.py" "forms.py" "tasks.py" "wsgi.py" "requirements.txt")

for file in "${core_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  Copying $file..."
        scp "$file" root@${SERVER_IP}:${REMOTE_PATH}/
    fi
done

# Step 4: Copy templates
echo "🎨 Copying updated templates..."
if [ -d "templates" ]; then
    scp -r templates root@${SERVER_IP}:${REMOTE_PATH}/
fi

# Step 5: Copy static files
echo "📄 Copying static files..."
if [ -d "static" ]; then
    scp -r static root@${SERVER_IP}:${REMOTE_PATH}/
fi

# Step 6: Restart the application
echo "🔄 Restarting the application..."
ssh root@$SERVER_IP "systemctl restart trading-analysis"

# Step 7: Check application status
echo "✅ Checking application status..."
ssh root@$SERVER_IP "systemctl status trading-analysis --no-pager"

# Step 8: Test the options calculator
echo "🧪 Testing options calculator..."
ssh root@$SERVER_IP "cd $REMOTE_PATH && python3 -c 'import os; from dotenv import load_dotenv; load_dotenv(); token = os.getenv(\"TRADIER_API_TOKEN\"); print(\"TRADIER_API_TOKEN configured: \" + (\"Yes\" if token else \"No\")); print(\"Token preview: \" + token[:10] + \"...\" if token else \"No token\")'"

echo "🎉 Deployment completed!"
echo "📝 Next steps:"
echo "   1. Visit https://optionsplunge.com/tools/options-calculator"
echo "   2. Test with a stock symbol (e.g., AAPL)"
echo "   3. Verify the 500 error is resolved"



