# PowerShell script to set up SSH key on VPS
# This script will help you add your public key to the VPS

Write-Host "Setting up SSH key for VPS..." -ForegroundColor Green

# Your VPS details
$VPS_IP = "167.88.43.61"
$VPS_USER = "tradingapp"

# Your public key (copy from your local machine)
$PUBLIC_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDrD6Oe+dUmMxKdgtvy+deUc2n+vYVaSjgsBiNS5qkpYkddXxXvzmnl8/Yktw//FWHUcGF+RhAK7jBl6OwLpqF/plc1zxdshoA7+Irc9FIM5lwg53Xv2rgyEkhL8NQh8e4Uta/o5h06YO+QlUebBHOrOIBdupu1MzHQQNIXq3VPyEkvvC0fJ76kz6GqkqWRmuFFpBhpZ6kvByLys+r7x5YuEU+zSq1IZVSfA3NzS/yK2dWN1AO8mrlxD7sf0W6Clhtl6IXUoA32blbmYQBBthMf3CmuW1N22NLjgw8kr7qOIwzEInHh/Ylxq0H5L5aXnIX9+UaYHn/037eJAg+e9I9kCSybCztWkF9No1Ui8VE9dMbpuiAxkjpPapvwXZpjvUiKKWFobHIFJJKwEXRPpRnR+HY9x18wgvcfMH2epK6cwjvLzC58YTHDeS5mfqaAz9MRHNStL9P3DrnhuMQ/cTSMREt/hqwC+qiCfvN7RdW0l+pwifYQ6VXyZG0cQdpuDX7jqMu7pSHBFS2uPCNhz2g9UglpazvdXR9T/1SWDhM8v9r18iJtFmAXUSldrvw66QVeXlKZov7ddJjLGWpowXvmq9zSHAeBRx0lkB1FxSSfnSIhIURVlgXARNlp9X2E/PnsC+w7s50swPMe+Up0cotd+/r3VBiUSwpFCJByvRak8hNQ== art@DESKTOP-18S7V4L"

Write-Host "Step 1: SSH into your VPS and run these commands:" -ForegroundColor Yellow
Write-Host "ssh $VPS_USER@$VPS_IP" -ForegroundColor Cyan
Write-Host ""
Write-Host "Step 2: Once connected to VPS, run these commands:" -ForegroundColor Yellow
Write-Host "mkdir -p ~/.ssh" -ForegroundColor Cyan
Write-Host "echo `"$PUBLIC_KEY`" >> ~/.ssh/authorized_keys" -ForegroundColor Cyan
Write-Host "chmod 700 ~/.ssh" -ForegroundColor Cyan
Write-Host "chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Cyan
Write-Host "exit" -ForegroundColor Cyan
Write-Host ""
Write-Host "Step 3: Test the connection:" -ForegroundColor Yellow
Write-Host "ssh $VPS_USER@$VPS_IP" -ForegroundColor Cyan
Write-Host ""
Write-Host "If it works without asking for a password, your SSH key is set up correctly!" -ForegroundColor Green 