#!/bin/bash

# Deployment script for AI Trading Analysis Flask App
# Run this script on your VPS after initial setup

set -e  # Exit on any error

echo "🚀 Starting deployment of AI Trading Analysis App..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as tradingapp user."
   exit 1
fi

# Variables
APP_DIR="/home/tradingapp/trading-analysis"
VENV_DIR="$APP_DIR/venv"
BACKUP_DIR="/home/tradingapp/backups"

print_status "Setting up application directory..."

# Create backup directory
mkdir -p $BACKUP_DIR

# Create app directory if it doesn't exist
if [ ! -d "$APP_DIR" ]; then
    mkdir -p $APP_DIR
fi

cd $APP_DIR

# Backup existing installation if it exists
if [ -f "app.py" ]; then
    print_status "Backing up existing installation..."
    tar -czf $BACKUP_DIR/pre_update_backup_$(date +%Y%m%d_%H%M%S).tar.gz .
fi

print_status "Setting up Python virtual environment..."

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

print_status "Installing Python dependencies..."

# Upgrade pip
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    print_error "requirements.txt not found!"
    exit 1
fi

print_status "Setting up environment variables..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Please create it with your production settings."
    print_status "Creating example .env file..."
    cat > .env.example << EOF
# Database Configuration
DATABASE_URL=postgresql://tradingapp:your_password@localhost/trading_journal

# Security
SECRET_KEY=your-super-secret-production-key-here

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Tradier Configuration
TRADIER_API_TOKEN=your-tradier-token

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER_NAME=Options Plunge Support
MAIL_DEFAULT_SENDER_EMAIL=support@optionsplunge.com
EOF
    print_warning "Please copy .env.example to .env and update with your actual values"
    exit 1
fi

print_status "Initializing database..."

# Initialize database
if [ -f "init_db.py" ]; then
    python init_db.py
else
    print_warning "init_db.py not found. Database initialization skipped."
fi

# Run database migrations
if command -v flask &> /dev/null; then
    flask db upgrade
else
    print_warning "Flask CLI not found. Database migrations skipped."
fi

print_status "Setting up static directories..."

# Create static directories
mkdir -p static/uploads
mkdir -p static/css
mkdir -p static/js
mkdir -p static/images

# Set proper permissions
chmod 755 static/uploads

print_status "Testing application..."

# Test if the app can start
if python -c "from app import app; print('App import successful')" 2>/dev/null; then
    print_status "Application import test passed"
else
    print_error "Application import test failed"
    exit 1
fi

print_status "Setting up systemd service..."

# Create systemd service file
sudo tee /etc/systemd/system/trading-analysis.service > /dev/null << EOF
[Unit]
Description=Trading Analysis Flask App
After=network.target

[Service]
User=tradingapp
Group=tradingapp
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
StandardOutput=append:/var/log/trading-analysis/app.log
StandardError=append:/var/log/trading-analysis/error.log

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
sudo mkdir -p /var/log/trading-analysis
sudo chown tradingapp:tradingapp /var/log/trading-analysis

print_status "Starting services..."

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable trading-analysis
sudo systemctl restart trading-analysis

# Wait a moment for the service to start
sleep 3

# Check service status
if sudo systemctl is-active --quiet trading-analysis; then
    print_status "Trading Analysis service is running"
else
    print_error "Trading Analysis service failed to start"
    sudo systemctl status trading-analysis
    exit 1
fi

print_status "Setting up Nginx configuration..."

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/trading-analysis > /dev/null << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
    }

    location /uploads {
        alias $APP_DIR/static/uploads;
        expires 30d;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/trading-analysis /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
if sudo nginx -t; then
    sudo systemctl restart nginx
    print_status "Nginx configuration updated and restarted"
else
    print_error "Nginx configuration test failed"
    exit 1
fi

print_status "Setting up firewall..."

# Configure UFW if available
if command -v ufw &> /dev/null; then
    sudo ufw allow 80
    sudo ufw allow 443
    print_status "Firewall rules updated"
else
    print_warning "UFW not found. Please configure firewall manually."
fi

print_status "Creating backup script..."

# Create backup script
cat > /home/tradingapp/backup.sh << 'EOF'
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

echo "Backup completed: $DATE"
EOF

chmod +x /home/tradingapp/backup.sh

print_status "Deployment completed successfully! 🎉"

echo ""
echo "Next steps:"
echo "1. Update your .env file with production values"
echo "2. Configure your domain DNS to point to this server"
echo "3. Set up SSL certificate with: sudo certbot --nginx -d your-domain.com"
echo "4. Test your application at: http://$(curl -s ifconfig.me)"
echo ""
echo "Useful commands:"
echo "- Check service status: sudo systemctl status trading-analysis"
echo "- View logs: sudo journalctl -u trading-analysis -f"
echo "- Restart service: sudo systemctl restart trading-analysis"
echo "- Run backup: /home/tradingapp/backup.sh"
echo ""
echo "Your AI Trading Analysis app is now deployed and running!" 