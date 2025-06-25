# GitHub Actions Deployment Setup Guide

This guide will help you set up automated deployment from GitHub to your Hostinger VPS.

## Prerequisites

1. **GitHub Repository**: Your code must be in a GitHub repository
2. **VPS Access**: SSH access to your Hostinger VPS
3. **SSH Key**: SSH key pair for secure authentication

## Step 1: Generate SSH Key Pair (if not already done)

### On your local machine:
```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"

# Copy the public key
cat ~/.ssh/id_rsa.pub
```

### On your VPS:
```bash
# Add the public key to authorized_keys
mkdir -p ~/.ssh
echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

## Step 2: Configure GitHub Secrets

1. Go to your GitHub repository
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

### Required Secrets:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `VPS_HOST` | Your VPS IP address or domain | `123.456.789.012` |
| `VPS_USERNAME` | SSH username (usually `tradingapp`) | `tradingapp` |
| `VPS_SSH_KEY` | Your private SSH key content | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `VPS_PORT` | SSH port (usually 22) | `22` |

### How to get your private SSH key:
```bash
# On your local machine
cat ~/.ssh/id_rsa
```

**Copy the entire content including the BEGIN and END lines.**

## Step 3: Test SSH Connection

Before setting up GitHub Actions, test your SSH connection:

```bash
# Test connection from your local machine
ssh tradingapp@YOUR_VPS_IP
```

## Step 4: Prepare Your VPS

Make sure your VPS is ready for automated deployments:

### 1. Ensure Git is installed:
```bash
sudo apt update
sudo apt install git -y
```

### 2. Configure Git on VPS:
```bash
git config --global user.name "VPS Deploy"
git config --global user.email "deploy@yourdomain.com"
```

### 3. Make sure the app directory exists:
```bash
mkdir -p /home/tradingapp/trading-analysis
cd /home/tradingapp/trading-analysis

# If this is a fresh setup, clone your repository
git clone https://github.com/yourusername/ai-trading-analysis-troubleshoot.git .
```

### 4. Set up Python environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 5: Configure Sudo Access

The deployment script needs sudo access to restart services. Configure sudo for the tradingapp user:

```bash
# Edit sudoers file
sudo visudo

# Add this line (replace 'tradingapp' with your actual username):
tradingapp ALL=(ALL) NOPASSWD: /bin/systemctl restart trading-analysis, /bin/systemctl status trading-analysis, /bin/systemctl is-active trading-analysis
```

## Step 6: Test the Deployment

### Option 1: Manual Test
1. Push a small change to your main branch
2. Go to **Actions** tab in GitHub
3. Watch the deployment workflow run

### Option 2: Manual Trigger
1. Go to **Actions** tab in GitHub
2. Click on **Deploy to VPS** workflow
3. Click **Run workflow**
4. Select your branch and click **Run workflow**

## Step 7: Monitor Deployment

### Check deployment status:
```bash
# On your VPS
sudo systemctl status trading-analysis
sudo journalctl -u trading-analysis -f
```

### Check GitHub Actions:
- Go to **Actions** tab in your GitHub repository
- Click on the latest workflow run
- Check the logs for any errors

## Troubleshooting

### Common Issues:

1. **SSH Connection Failed**
   - Verify VPS_HOST and VPS_PORT are correct
   - Check if SSH key is properly added to authorized_keys
   - Test SSH connection manually

2. **Permission Denied**
   - Ensure the user has proper permissions
   - Check sudo configuration
   - Verify file ownership

3. **Service Not Starting**
   - Check application logs: `sudo journalctl -u trading-analysis -f`
   - Verify environment variables are set correctly
   - Check if all dependencies are installed

4. **Database Migration Errors**
   - Ensure database is accessible
   - Check database credentials in .env file
   - Verify PostgreSQL is running

### Useful Commands:

```bash
# Check service status
sudo systemctl status trading-analysis

# View application logs
sudo journalctl -u trading-analysis -f

# Check if port is in use
sudo netstat -tlnp | grep :8000

# Test database connection
psql -h localhost -U tradingapp -d trading_journal

# Check Nginx status
sudo systemctl status nginx
```

## Security Best Practices

1. **Use SSH Keys**: Never use password authentication
2. **Restrict Sudo Access**: Only allow necessary commands
3. **Regular Updates**: Keep your VPS updated
4. **Monitor Logs**: Regularly check application and system logs
5. **Backup Strategy**: Ensure regular backups are working

## Manual Update (Alternative)

If you prefer manual updates, you can use the `update_vps.sh` script:

```bash
# On your VPS
cd /home/tradingapp/trading-analysis
chmod +x update_vps.sh
./update_vps.sh
```

## Next Steps

1. **Set up monitoring**: Consider setting up monitoring for your application
2. **SSL Certificate**: Set up Let's Encrypt for HTTPS
3. **Backup Automation**: Set up automated database backups
4. **Performance Optimization**: Monitor and optimize application performance

Your automated deployment is now ready! Every time you push to the main branch, your VPS will automatically update with the latest changes. 