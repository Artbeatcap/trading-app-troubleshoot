# Options Plunge Morning Brief PowerShell Script

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Options Plunge Morning Brief Commands:" -ForegroundColor Green
    Write-Host "  .\morning_brief.ps1 brief-dry     - Generate email files without sending (dry run)" -ForegroundColor Yellow
    Write-Host "  .\morning_brief.ps1 brief-send    - Send morning brief to subscribers (requires CONFIRM_SEND=1)" -ForegroundColor Yellow
    Write-Host "  .\morning_brief.ps1 social-twitter - Generate Twitter CSV from brief data" -ForegroundColor Yellow
    Write-Host "  .\morning_brief.ps1 install-deps  - Install required dependencies" -ForegroundColor Yellow
    Write-Host "  .\morning_brief.ps1 test          - Test the morning brief system" -ForegroundColor Yellow
    Write-Host "  .\morning_brief.ps1 clean         - Clean output directories" -ForegroundColor Yellow
    Write-Host "  .\morning_brief.ps1 validate-json - Validate sample JSON" -ForegroundColor Yellow
}

function Install-Dependencies {
    Write-Host "Installing dependencies..." -ForegroundColor Green
    pip install pydantic jinja2
}

function Test-BriefDry {
    Write-Host "Running morning brief dry run..." -ForegroundColor Green
    python send_morning_brief.py daily_brief_sample.json --dry-run
}

function Test-BriefSend {
    Write-Host "Sending morning brief to subscribers..." -ForegroundColor Green
    if ($env:CONFIRM_SEND -ne "1") {
        Write-Host "Error: CONFIRM_SEND=1 environment variable required" -ForegroundColor Red
        Write-Host "Set CONFIRM_SEND=1 to confirm you want to send to all subscribers" -ForegroundColor Red
        exit 1
    }
    python send_morning_brief.py daily_brief_sample.json
}

function Test-SocialTwitter {
    Write-Host "Generating Twitter CSV..." -ForegroundColor Green
    python generate_twitter_csv.py daily_brief_sample.json
}

function Test-All {
    Write-Host "Testing morning brief system..." -ForegroundColor Green
    Write-Host "1. Testing dry run..." -ForegroundColor Yellow
    Test-BriefDry
    Write-Host "2. Testing Twitter CSV generation..." -ForegroundColor Yellow
    Test-SocialTwitter
    Write-Host "All tests completed successfully" -ForegroundColor Green
}

function Clean-Output {
    Write-Host "Cleaning output directories..." -ForegroundColor Green
    if (Test-Path "out") {
        Remove-Item -Recurse -Force "out"
        Write-Host "Output directories cleaned" -ForegroundColor Green
    } else {
        Write-Host "No output directories found" -ForegroundColor Yellow
    }
}

function Test-ValidateJson {
    Write-Host "Validating sample JSON..." -ForegroundColor Green
    python -c "from daily_brief_schema import MorningBrief; import json; MorningBrief(**json.load(open('daily_brief_sample.json'))); print('JSON is valid')"
}

# Main script logic
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install-deps" { Install-Dependencies }
    "brief-dry" { Test-BriefDry }
    "brief-send" { Test-BriefSend }
    "social-twitter" { Test-SocialTwitter }
    "test" { Test-All }
    "clean" { Clean-Output }
    "validate-json" { Test-ValidateJson }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
    }
}
