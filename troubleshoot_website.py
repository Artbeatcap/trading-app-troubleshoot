#!/usr/bin/env python3
"""
Website Troubleshooting Script
This script helps diagnose common issues with Flask app deployment
"""

import os
import sys
import subprocess
import requests
import socket
from pathlib import Path

def run_command(command, capture_output=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=capture_output, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def check_service_status():
    """Check if the Flask service is running"""
    print("🔍 Checking Flask service status...")
    code, stdout, stderr = run_command("sudo systemctl status trading-analysis")
    
    if code == 0:
        if "Active: active (running)" in stdout:
            print("✅ Flask service is running")
            return True
        else:
            print("❌ Flask service is not running properly")
            print(stdout)
            return False
    else:
        print("❌ Could not check service status")
        print(stderr)
        return False

def check_nginx_status():
    """Check if Nginx is running"""
    print("\n🔍 Checking Nginx status...")
    code, stdout, stderr = run_command("sudo systemctl status nginx")
    
    if code == 0:
        if "Active: active (running)" in stdout:
            print("✅ Nginx is running")
            return True
        else:
            print("❌ Nginx is not running properly")
            print(stdout)
            return False
    else:
        print("❌ Could not check Nginx status")
        print(stderr)
        return False

def check_port_listening():
    """Check if port 8000 is listening"""
    print("\n🔍 Checking if port 8000 is listening...")
    code, stdout, stderr = run_command("sudo netstat -tlnp | grep :8000")
    
    if code == 0 and stdout.strip():
        print("✅ Port 8000 is listening")
        print(f"   {stdout.strip()}")
        return True
    else:
        print("❌ Port 8000 is not listening")
        return False

def check_nginx_config():
    """Check Nginx configuration"""
    print("\n🔍 Checking Nginx configuration...")
    code, stdout, stderr = run_command("sudo nginx -t")
    
    if code == 0:
        print("✅ Nginx configuration is valid")
        return True
    else:
        print("❌ Nginx configuration has errors")
        print(stderr)
        return False

def check_app_logs():
    """Check application logs"""
    print("\n🔍 Checking application logs...")
    code, stdout, stderr = run_command("sudo journalctl -u trading-analysis --no-pager -n 20")
    
    if code == 0:
        print("📋 Recent application logs:")
        print(stdout)
    else:
        print("❌ Could not retrieve application logs")
        print(stderr)

def check_nginx_logs():
    """Check Nginx logs"""
    print("\n🔍 Checking Nginx error logs...")
    code, stdout, stderr = run_command("sudo tail -n 20 /var/log/nginx/error.log")
    
    if code == 0:
        print("📋 Recent Nginx error logs:")
        print(stdout)
    else:
        print("❌ Could not retrieve Nginx logs")
        print(stderr)

def check_local_connection():
    """Test local connection to the app"""
    print("\n🔍 Testing local connection to Flask app...")
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        print(f"✅ Local connection successful - Status: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask app on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing local connection: {e}")
        return False

def check_environment():
    """Check environment variables and configuration"""
    print("\n🔍 Checking environment configuration...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file exists")
        
        # Check for critical environment variables
        with open(env_file, 'r') as f:
            content = f.read()
            
        required_vars = ['SECRET_KEY', 'DATABASE_URL']
        for var in required_vars:
            if var in content:
                print(f"✅ {var} is configured")
            else:
                print(f"⚠️  {var} is missing")
    else:
        print("❌ .env file not found")
    
    # Check if virtual environment exists
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Virtual environment exists")
    else:
        print("❌ Virtual environment not found")

def check_database():
    """Check database connection"""
    print("\n🔍 Checking database connection...")
    
    # Try to import and test database connection
    try:
        from app import app, db
        with app.app_context():
            db.engine.execute("SELECT 1")
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_file_permissions():
    """Check file permissions"""
    print("\n🔍 Checking file permissions...")
    
    app_dir = Path(".")
    if app_dir.exists():
        stat = app_dir.stat()
        print(f"App directory permissions: {oct(stat.st_mode)[-3:]}")
    
    # Check if tradingapp user owns the directory
    code, stdout, stderr = run_command("ls -la .")
    if code == 0:
        print("📋 Directory contents and permissions:")
        print(stdout)

def main():
    """Main troubleshooting function"""
    print("🚀 Flask App Website Troubleshooting")
    print("=" * 50)
    
    # Check if running as root or with sudo
    if os.geteuid() != 0:
        print("⚠️  Some checks require sudo privileges")
        print("   Run with: sudo python3 troubleshoot_website.py")
    
    # Run all checks
    service_ok = check_service_status()
    nginx_ok = check_nginx_status()
    port_ok = check_port_listening()
    nginx_config_ok = check_nginx_config()
    local_ok = check_local_connection()
    env_ok = check_environment()
    db_ok = check_database()
    
    # Check logs
    check_app_logs()
    check_nginx_logs()
    check_file_permissions()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TROUBLESHOOTING SUMMARY")
    print("=" * 50)
    
    issues = []
    if not service_ok:
        issues.append("Flask service not running")
    if not nginx_ok:
        issues.append("Nginx not running")
    if not port_ok:
        issues.append("Port 8000 not listening")
    if not nginx_config_ok:
        issues.append("Nginx configuration errors")
    if not local_ok:
        issues.append("Cannot connect to Flask app locally")
    if not env_ok:
        issues.append("Environment configuration issues")
    if not db_ok:
        issues.append("Database connection issues")
    
    if not issues:
        print("✅ All basic checks passed!")
        print("\n💡 If website still not loading, check:")
        print("   - Domain DNS settings")
        print("   - Firewall rules")
        print("   - SSL certificate (if using HTTPS)")
    else:
        print("❌ Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        
        print("\n🔧 Recommended fixes:")
        if not service_ok:
            print("   - Start Flask service: sudo systemctl start trading-analysis")
        if not nginx_ok:
            print("   - Start Nginx: sudo systemctl start nginx")
        if not port_ok:
            print("   - Check if Flask app is binding to correct port")
        if not nginx_config_ok:
            print("   - Fix Nginx configuration and restart: sudo systemctl restart nginx")

if __name__ == "__main__":
    main() 