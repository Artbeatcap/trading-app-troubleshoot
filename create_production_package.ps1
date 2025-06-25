# PowerShell script to create a clean production package
# Run this on your local machine before uploading to VPS

Write-Host "Creating production package..." -ForegroundColor Green

# Create production directory
$prodDir = "production-package"
if (Test-Path $prodDir) {
    Remove-Item $prodDir -Recurse -Force
}
New-Item -ItemType Directory -Path $prodDir

# Essential files to copy
$essentialFiles = @(
    "app.py",
    "config.py", 
    "models.py",
    "forms.py",
    "ai_analysis.py",
    "requirements.txt",
    "wsgi.py",
    "gunicorn.conf.py",
    "deploy.sh",
    "init_db.py",
    "env_production_template.txt",
    "vps_setup_commands.txt",
    "deployment_commands.txt",
    "cleanup_vps.sh",
    "deployment_guide.md"
)

# Copy essential files
foreach ($file in $essentialFiles) {
    if (Test-Path $file) {
        Copy-Item $file $prodDir
        Write-Host "Copied: $file" -ForegroundColor Yellow
    } else {
        Write-Host "Warning: $file not found" -ForegroundColor Red
    }
}

# Copy essential directories
$essentialDirs = @("templates", "static", "migrations")

foreach ($dir in $essentialDirs) {
    if (Test-Path $dir) {
        Copy-Item $dir $prodDir -Recurse
        Write-Host "Copied directory: $dir" -ForegroundColor Yellow
    } else {
        Write-Host "Warning: $dir directory not found" -ForegroundColor Red
    }
}

Write-Host "Production package created in: $prodDir" -ForegroundColor Green
Write-Host "You can now upload this directory to your VPS" -ForegroundColor Cyan 