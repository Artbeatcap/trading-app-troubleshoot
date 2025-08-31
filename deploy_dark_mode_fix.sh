#!/bin/bash
# Deploy dark mode fix and recent changes to live app

echo "🚀 Deploying dark mode fix and recent changes to live app..."
echo "=========================================================="

# Set variables
REMOTE_HOST="root@167.88.43.61"
REMOTE_DIR="/home/tradingapp/trading-analysis"
LOCAL_DIR="."

# Create timestamp for backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="trading-analysis-backup-${TIMESTAMP}.tar.gz"

echo "📦 Creating backup of current live app..."
ssh $REMOTE_HOST "cd $REMOTE_DIR && tar -czf $BACKUP_NAME --exclude='*.tar.gz' --exclude='venv*' --exclude='__pycache__' --exclude='.git' ."

echo "✅ Backup created: $BACKUP_NAME"

# Files to update (focusing on dark mode and recent changes)
FILES_TO_UPDATE=(
    "app.py"
    "forms.py"
    "models.py"
    "templates/base.html"
    "templates/settings.html"
    "migrate_user_settings.py"
    "requirements.txt"
)

echo "📤 Uploading updated files..."

for file in "${FILES_TO_UPDATE[@]}"; do
    if [ -f "$file" ]; then
        echo "  📄 Uploading $file..."
        scp "$file" "$REMOTE_HOST:$REMOTE_DIR/$file"
    else
        echo "  ⚠️  Warning: $file not found locally"
    fi
done

echo "🔧 Running database migrations..."
ssh $REMOTE_HOST "cd $REMOTE_DIR && source venv/bin/activate && python migrate_user_settings.py"

echo "🔄 Restarting the application..."
ssh $REMOTE_HOST "systemctl restart trading-analysis"

echo "⏳ Waiting for app to start..."
sleep 5

echo "🔍 Checking application status..."
ssh $REMOTE_HOST "systemctl status trading-analysis --no-pager"

echo "✅ Deployment completed!"
echo ""
echo "🌐 Live app should now have dark mode functionality working correctly."
echo "📝 To test:"
echo "   1. Visit your live app"
echo "   2. Log in to your account"
echo "   3. Go to Settings page"
echo "   4. Toggle the 'Enable dark mode' checkbox"
echo "   5. Save changes and refresh to see dark mode applied"
echo ""
echo "📦 Backup saved as: $BACKUP_NAME"
