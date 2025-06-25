# Quick Deployment Steps for VPS Update

## Immediate Next Steps

### 1. Set Up GitHub Secrets (Required for Automated Deployment)

1. Go to your GitHub repository: `https://github.com/Artbeatcap/trading-app-troubleshoot`
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `VPS_HOST` | Your VPS IP address |
| `VPS_USERNAME` | `tradingapp` (or your VPS username) |
| `VPS_SSH_KEY` | Your private SSH key content |
| `VPS_PORT` | `22` |

### 2. Get Your SSH Key (if needed)

```bash
# On your local machine
cat ~/.ssh/id_rsa
```

Copy the entire output (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`)

### 3. Test SSH Connection to VPS

```bash
# Test connection
ssh tradingapp@YOUR_VPS_IP
```

### 4. Prepare Your VPS

SSH into your VPS and run:

```bash
# Navigate to app directory
cd /home/tradingapp/trading-analysis

# Make sure Git is configured
git config --global user.name "VPS Deploy"
git config --global user.email "deploy@yourdomain.com"

# Set up sudo access for service restart
sudo visudo
# Add this line:
# tradingapp ALL=(ALL) NOPASSWD: /bin/systemctl restart trading-analysis, /bin/systemctl status trading-analysis, /bin/systemctl is-active trading-analysis
```

### 5. Merge to Main Branch

```bash
# On your local machine
git checkout main
git merge codex/improve-visuals-for-unauthenticated-users
git push origin main
```

### 6. Test Automated Deployment

1. Make a small change to your code
2. Commit and push to main branch
3. Go to **Actions** tab in GitHub
4. Watch the deployment workflow run

## Manual Update (Alternative)

If you prefer manual updates, SSH into your VPS and run:

```bash
cd /home/trading-analysis
chmod +x update_vps.sh
./update_vps.sh
```

## Troubleshooting

### If deployment fails:

1. **Check GitHub Actions logs** in the Actions tab
2. **Check VPS logs**: `sudo journalctl -u trading-analysis -f`
3. **Verify SSH connection**: Test manually first
4. **Check service status**: `sudo systemctl status trading-analysis`

### Common Issues:

- **SSH key not working**: Make sure the public key is in `~/.ssh/authorized_keys` on VPS
- **Permission denied**: Check sudo configuration
- **Service not starting**: Check application logs and environment variables

## Quick Commands Reference

```bash
# Check service status
sudo systemctl status trading-analysis

# View logs
sudo journalctl -u trading-analysis -f

# Restart service manually
sudo systemctl restart trading-analysis

# Check if port is in use
sudo netstat -tlnp | grep :8000
```

## Success Indicators

✅ **Deployment successful when:**
- GitHub Actions workflow completes without errors
- Service status shows "active (running)"
- Application is accessible via your domain/IP
- No error messages in logs

Your app will now automatically update every time you push to the main branch! 🚀 