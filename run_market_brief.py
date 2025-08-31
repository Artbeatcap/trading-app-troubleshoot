#!/usr/bin/env python3

import os
import sys
import subprocess
import time

def run_market_brief():
    """Run market brief generation and deploy to server"""
    
    print("🚀 Running Market Brief Generation...")
    print("=" * 50)
    
    # 1. Run market brief generation locally
    print("\n1. Generating market brief...")
    try:
        result = subprocess.run([
            sys.executable, "market_brief_generator.py"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ Market brief generated successfully!")
            print("Output:", result.stdout[-500:] if result.stdout else "No output")
        else:
            print("❌ Market brief generation failed!")
            print("Error:", result.stderr[-500:] if result.stderr else "No error output")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Market brief generation timed out")
        return False
    except Exception as e:
        print(f"❌ Error running market brief: {e}")
        return False
    
    # 2. Deploy the generated brief to server
    print("\n2. Deploying to server...")
    try:
        # Copy the generated brief file
        result = subprocess.run([
            "scp", "static/uploads/brief_latest.html", 
            "root@167.88.43.61:/home/tradingapp/trading-analysis/static/uploads/"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Brief file deployed successfully!")
        else:
            print("❌ Failed to deploy brief file!")
            print("Error:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Deployment timed out")
        return False
    except Exception as e:
        print(f"❌ Error deploying: {e}")
        return False
    
    # 3. Restart the service
    print("\n3. Restarting service...")
    try:
        result = subprocess.run([
            "ssh", "root@167.88.43.61", "systemctl restart trading-analysis"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Service restarted successfully!")
        else:
            print("❌ Failed to restart service!")
            print("Error:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Service restart timed out")
        return False
    except Exception as e:
        print(f"❌ Error restarting service: {e}")
        return False
    
    # 4. Test the live page
    print("\n4. Testing live page...")
    time.sleep(5)  # Wait for service to start
    
    try:
        result = subprocess.run([
            "curl", "-I", "https://optionsplunge.com/market_brief", "-k"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and "200 OK" in result.stdout:
            print("✅ Live page is accessible!")
            print("Response:", result.stdout.split('\n')[0])
        else:
            print("❌ Live page test failed!")
            print("Response:", result.stdout)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Live page test timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing live page: {e}")
        return False
    
    print("\n🎉 Market Brief Update Complete!")
    print("📊 Check: https://optionsplunge.com/market_brief")
    return True

if __name__ == "__main__":
    run_market_brief()
