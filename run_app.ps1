# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1

# Path to venv's python
$venvPython = ".\venv\Scripts\python.exe"

# Check if activation was successful
if ($env:VIRTUAL_ENV) {
    Write-Host "Virtual environment activated successfully!" -ForegroundColor Green
    
    # Install required packages using venv's python
    Write-Host "Installing required packages..." -ForegroundColor Green
    & $venvPython -m pip install -r requirements.txt
    & $venvPython -m pip install scipy
    
    # Run the Flask application using venv's python
    Write-Host "Starting Flask application..." -ForegroundColor Green
    & $venvPython app.py
} else {
    Write-Host "Failed to activate virtual environment!" -ForegroundColor Red
    exit 1
} 