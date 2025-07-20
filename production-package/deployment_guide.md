# Flask App Deployment Guide for Hostinger VPS

This guide will walk you through deploying your AI Trading Analysis Flask app to a VPS on Hostinger.

## Prerequisites

1. **Hostinger VPS Access**: SSH access to your VPS
2. **Domain Name**: A domain pointing to your VPS (optional but recommended)
3. **API Keys**: Ensure you have your API keys ready:
   - OpenAI API Key
   - Tradier API Token
   - Email credentials (Gmail or other SMTP provider)

## Step 1: Prepare Your Local Project

### 1.1 Create a Production Configuration
Create a `.env.production` file with your production settings:

```bash
# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://username:password@localhost/trading_journal

# Security
SECRET_KEY=your-super-secret-production-key-here

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Tradier
TRADIER_API_TOKEN=your-tradier-token

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

### 1.2 Update Database Configuration
For production, you should use PostgreSQL instead of SQLite. Update your `config.py`:

```python
# In config.py, update the database URI
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///trading_journal.db'
```

## Step 2: Set Up Your VPS

### 2.1 Connect to Your VPS
```bash
ssh root@your-vps-ip
```

### 2.2 Update System
```bash
apt update && apt upgrade -y
```

### 2.3 Install Required Software
```bash
# Install Python and pip
apt install python3 python3-pip python3-venv -y

# Install PostgreSQL
apt install postgresql postgresql-contrib -y

# Install Nginx
apt install nginx -y

# Install Git
apt install git -y

# Install build dependencies
apt install build-essential python3-dev libpq-dev -y
```

### 2.4 Create a Non-Root User
```bash
# Create a new user
adduser tradingapp
usermod -aG sudo tradingapp

# Switch to the new user
su - tradingapp
```

## Step 3: Set Up PostgreSQL

### 3.1 Configure PostgreSQL
```bash
# Switch back to root
exit

# Access PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE trading_journal;
CREATE USER tradingapp WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE trading_journal TO tradingapp;
\q
```

### 3.2 Test Database Connection
```bash
# Switch to tradingapp user
su - tradingapp

# Test connection
psql -h localhost -U tradingapp -d trading_journal
```

## Step 4: Deploy Your Application

### 4.1 Clone Your Repository
```bash
# Create app directory
mkdir /home/tradingapp/trading-analysis
cd /home/tradingapp/trading-analysis

# Clone your repository (replace with your actual repo URL)
git clone https://github.com/yourusername/ai-trading-analysis-troubleshoot.git .

# Or upload files via SCP/SFTP if not using Git
```

### 4.2 Set Up Python Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4.3 Configure Environment Variables
```bash
# Create production environment file
cp .env.production .env

# Or create manually
nano .env
# Add your production environment variables here
```

### 4.4 Initialize Database
```bash
# Activate virtual environment
source venv/bin/activate

# Initialize database
python init_db.py

# Run migrations
flask db upgrade
```

## Step 5: Set Up Gunicorn

### 5.1 Create Systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/trading-analysis.service
```

Add the following content:
```ini
[Unit]
Description=Trading Analysis Flask App
After=network.target

[Service]
User=tradingapp
Group=tradingapp
WorkingDirectory=/home/tradingapp/trading-analysis
Environment="PATH=/home/tradingapp/trading-analysis/venv/bin"
ExecStart=/home/tradingapp/trading-analysis/venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5.2 Start the Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable trading-analysis
sudo systemctl start trading-analysis

# Check status
sudo systemctl status trading-analysis
```

## Step 6: Configure Nginx

### 6.1 Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/trading-analysis
```

Add the following configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/tradingapp/trading-analysis/static;
        expires 30d;
    }

    location /uploads {
        alias /home/tradingapp/trading-analysis/static/uploads;
        expires 30d;
    }
}
```

### 6.2 Enable the Site
```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/trading-analysis /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

## Step 7: Set Up SSL (Optional but Recommended)

### 7.1 Install Certbot
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## Step 8: Configure Firewall

### 8.1 Set Up UFW
```bash
# Install UFW
sudo apt install ufw -y

# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Enable firewall
sudo ufw enable
```

## Step 9: Testing and Monitoring

### 9.1 Test Your Application
```bash
# Check if the app is running
curl http://localhost:8000

# Check logs
sudo journalctl -u trading-analysis -f
```

### 9.2 Set Up Log Rotation
```bash
# Create log directory
sudo mkdir -p /var/log/trading-analysis

# Update systemd service to use log file
sudo nano /etc/systemd/system/trading-analysis.service
```

Add these lines to the service file:
```ini
StandardOutput=append:/var/log/trading-analysis/app.log
StandardError=append:/var/log/trading-analysis/error.log
```

## Step 10: Maintenance and Updates

### 10.1 Update Your Application
```bash
# Pull latest changes
cd /home/tradingapp/trading-analysis
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install new dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Restart the service
sudo systemctl restart trading-analysis
```

### 10.2 Backup Strategy
```bash
# Create backup script
nano /home/tradingapp/backup.sh
```

Add backup script content:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/tradingapp/backups"

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -h localhost -U tradingapp trading_journal > $BACKUP_DIR/db_backup_$DATE.sql

# Backup application files
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz /home/tradingapp/trading-analysis

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

Make it executable:
```bash
chmod +x /home/tradingapp/backup.sh
```

## Troubleshooting

### Common Issues:

1. **Permission Denied**: Make sure the `tradingapp` user owns the application directory
2. **Database Connection**: Verify PostgreSQL is running and credentials are correct
3. **Port Already in Use**: Check if port 8000 is available
4. **Static Files Not Loading**: Ensure Nginx has correct permissions for static directory

### Useful Commands:
```bash
# Check service status
sudo systemctl status trading-analysis

# View logs
sudo journalctl -u trading-analysis -f

# Check Nginx status
sudo systemctl status nginx

# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
psql -h localhost -U tradingapp -d trading_journal
```

## Security Considerations

1. **Change Default Passwords**: Update all default passwords
2. **Regular Updates**: Keep system and packages updated
3. **Firewall**: Only open necessary ports
4. **SSL**: Always use HTTPS in production
5. **Backups**: Regular automated backups
6. **Monitoring**: Set up monitoring for uptime and performance

Your Flask app should now be successfully deployed and accessible via your domain or VPS IP address! 