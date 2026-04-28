#!/bin/bash
# Edit .env file on server
# Usage: ./edit_server_env.sh [upload]

REMOTE_HOST="167.88.43.61"
REMOTE_USER="root"
REMOTE_ENV="/home/tradingapp/trading-analysis/.env"
LOCAL_ENV=".env.server"

echo "📝 Editing .env file on server"
echo "==============================="
echo ""

# Step 1: Download .env file
echo "[INFO] Downloading .env file from server..."
scp "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_ENV}" "$LOCAL_ENV"

if [ -f "$LOCAL_ENV" ]; then
    echo "[SUCCESS] .env file downloaded to $LOCAL_ENV"
    echo ""
    echo "File location: $(pwd)/$LOCAL_ENV"
    echo ""
    echo "You can now edit the file with your favorite editor:"
    echo "  nano $LOCAL_ENV"
    echo "  vim $LOCAL_ENV"
    echo "  code $LOCAL_ENV  # VS Code"
    echo ""
    
    # Open in default editor if not uploading
    if [ "$1" != "upload" ]; then
        read -p "Open in editor now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} "$LOCAL_ENV"
        fi
    fi
else
    echo "[ERROR] Failed to download .env file"
    exit 1
fi

# Step 2: Upload if "upload" argument provided
if [ "$1" = "upload" ]; then
    echo ""
    echo "[INFO] Uploading edited .env file back to server..."
    
    # Create backup on server first
    timestamp=$(date +%Y%m%d_%H%M%S)
    ssh "${REMOTE_USER}@${REMOTE_HOST}" "cp ${REMOTE_ENV} ${REMOTE_ENV}.backup.${timestamp}"
    
    # Upload the file
    scp "$LOCAL_ENV" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_ENV}"
    
    if [ $? -eq 0 ]; then
        echo "[SUCCESS] .env file uploaded successfully"
        echo "[INFO] Setting correct permissions..."
        ssh "${REMOTE_USER}@${REMOTE_HOST}" "chown tradingapp:tradingapp ${REMOTE_ENV} && chmod 600 ${REMOTE_ENV}"
        echo "[SUCCESS] Permissions set correctly"
        echo ""
        echo "⚠️  IMPORTANT: Restart the application for changes to take effect:"
        echo "   ssh ${REMOTE_USER}@${REMOTE_HOST} \"systemctl restart trading-analysis\""
    else
        echo "[ERROR] Failed to upload .env file"
        exit 1
    fi
fi




