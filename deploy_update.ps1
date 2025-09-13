Write-Host "🚀 Deploying Updates to Live App..." -ForegroundColor Blue
Write-Host "====================================" -ForegroundColor Blue

$REMOTE_HOST = "167.88.43.61"
$REMOTE_USER = "root"
$REMOTE_APP_DIR = "/home/tradingapp/trading-analysis"

Write-Host "[INFO] Uploading base.html template..." -ForegroundColor Blue
scp templates/base.html ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/templates/

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Template uploaded" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Template upload failed" -ForegroundColor Red
}

Write-Host "[INFO] Uploading app.py..." -ForegroundColor Blue
scp app.py ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] app.py uploaded" -ForegroundColor Green
} else {
    Write-Host "[ERROR] app.py upload failed" -ForegroundColor Red
}

Write-Host "[INFO] Restarting application..." -ForegroundColor Blue
ssh ${REMOTE_USER}@${REMOTE_HOST} "systemctl restart trading-analysis"

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Application restarted" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Application restart failed" -ForegroundColor Red
}

Write-Host "[INFO] Checking status..." -ForegroundColor Blue
ssh ${REMOTE_USER}@${REMOTE_HOST} "systemctl is-active trading-analysis"

Write-Host "🎉 Deployment Complete!" -ForegroundColor Green



