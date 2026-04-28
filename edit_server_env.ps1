# Edit .env file on server
# This script will download, allow you to edit, and upload back

$REMOTE_HOST = "167.88.43.61"
$REMOTE_USER = "root"
$REMOTE_ENV = "/home/tradingapp/trading-analysis/.env"
$LOCAL_ENV = ".env.server"

Write-Host "📝 Editing .env file on server" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Download .env file
Write-Host "[INFO] Downloading .env file from server..." -ForegroundColor Blue
scp "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_ENV}" $LOCAL_ENV

if (Test-Path $LOCAL_ENV) {
    Write-Host "[SUCCESS] .env file downloaded to $LOCAL_ENV" -ForegroundColor Green
    Write-Host ""
    Write-Host "File location: $PWD\$LOCAL_ENV" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "You can now:" -ForegroundColor Cyan
    Write-Host "1. Edit the file: notepad $LOCAL_ENV" -ForegroundColor White
    Write-Host "2. Or open in VS Code: code $LOCAL_ENV" -ForegroundColor White
    Write-Host ""
    Write-Host "After editing, run this script again with -upload flag:" -ForegroundColor Yellow
    Write-Host "  .\edit_server_env.ps1 -upload" -ForegroundColor White
    Write-Host ""
    
    # Open in default editor
    $openEditor = Read-Host "Open in editor now? (y/n)"
    if ($openEditor -eq "y" -or $openEditor -eq "Y") {
        notepad $LOCAL_ENV
    }
} else {
    Write-Host "[ERROR] Failed to download .env file" -ForegroundColor Red
    exit 1
}

# Step 2: Upload if -upload flag is provided
if ($args -contains "-upload") {
    Write-Host ""
    Write-Host "[INFO] Uploading edited .env file back to server..." -ForegroundColor Blue
    
    # Create backup on server first
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupCmd = "cp $REMOTE_ENV ${REMOTE_ENV}.backup.${timestamp}"
    ssh "${REMOTE_USER}@${REMOTE_HOST}" $backupCmd
    
    # Upload the file
    scp $LOCAL_ENV "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_ENV}"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] .env file uploaded successfully" -ForegroundColor Green
        Write-Host "[INFO] Setting correct permissions..." -ForegroundColor Blue
        $permCmd = "chown tradingapp:tradingapp $REMOTE_ENV; chmod 600 $REMOTE_ENV"
        ssh "${REMOTE_USER}@${REMOTE_HOST}" $permCmd
        Write-Host "[SUCCESS] Permissions set correctly" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  IMPORTANT: Restart the application for changes to take effect:" -ForegroundColor Yellow
        Write-Host "   ssh ${REMOTE_USER}@${REMOTE_HOST} `"systemctl restart trading-analysis`"" -ForegroundColor White
    } else {
        Write-Host "[ERROR] Failed to upload .env file" -ForegroundColor Red
        exit 1
    }
}

