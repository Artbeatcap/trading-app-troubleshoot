# Domain Fix Guide - optionsplunge.com

## 🔍 **Issue Identified**

The live site is currently accessible via IP address `https://167.88.43.61/market_brief` but should be accessible via the domain `https://optionsplunge.com/market_brief`.

## ❌ **Current Problem**

The nginx configuration has conflicting redirect rules that are causing the domain to return 404 errors.

## ✅ **Solution**

Fix the nginx configuration to properly handle domain routing.

## 🚀 **Fix Steps**

### **Step 1: SSH to VPS**
```bash
ssh tradingapp@167.88.43.61
```

### **Step 2: Backup Current Config**
```bash
sudo cp /etc/nginx/sites-enabled/trading-analysis /etc/nginx/sites-enabled/trading-analysis.backup
```

### **Step 3: Apply Fixed Configuration**
```bash
sudo cp /home/tradingapp/trading-analysis/nginx_fixed.conf /etc/nginx/sites-enabled/trading-analysis
```

### **Step 4: Test Configuration**
```bash
sudo nginx -t
```

### **Step 5: Reload Nginx**
```bash
sudo systemctl reload nginx
```

### **Step 6: Test Domain Access**
```bash
curl -s -k -o /dev/null -w '%{http_code}' https://optionsplunge.com/market_brief
```

## 🧪 **Expected Results**

### **Before Fix**
- ❌ `https://optionsplunge.com/market_brief` → 404
- ✅ `https://167.88.43.61/market_brief` → 200

### **After Fix**
- ✅ `https://optionsplunge.com/market_brief` → 200
- ✅ `https://167.88.43.61/market_brief` → 200
- ✅ `http://optionsplunge.com/market_brief` → 301 redirect to HTTPS

## 🔧 **What Was Fixed**

### **Old Configuration Issues**
- Conflicting redirect rules in port 80 server block
- Redirects followed by 404 return statements
- Inconsistent handling of domain vs IP

### **New Configuration**
- Clean HTTP to HTTPS redirect
- Proper domain handling
- Consistent routing for both IP and domain

## 📋 **Configuration Changes**

### **Port 80 Server Block (Fixed)**
```nginx
server {
    listen 80;
    server_name 167.88.43.61 optionsplunge.com www.optionsplunge.com;
    
    # Redirect all HTTP traffic to HTTPS
    return 301 https://$server_name$request_uri;
}
```

### **Port 443 Server Block (Unchanged)**
- Handles all HTTPS traffic
- Proxies to Flask app on port 8000
- Serves static files and uploads

## 🎯 **Testing After Fix**

1. **Domain Access**: `https://optionsplunge.com/market_brief`
2. **IP Access**: `https://167.88.43.61/market_brief`
3. **HTTP Redirect**: `http://optionsplunge.com/market_brief`
4. **Market Brief Display**: Should show brief content first, then subscription form

## 🔍 **Monitoring**

### **Check Nginx Status**
```bash
sudo systemctl status nginx
```

### **Check Nginx Logs**
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### **Test Both URLs**
```bash
# Test domain
curl -s -k https://optionsplunge.com/market_brief | grep -i "latest morning market brief"

# Test IP
curl -s -k https://167.88.43.61/market_brief | grep -i "latest morning market brief"
```

## 🎉 **Expected Outcome**

After applying the fix:

- ✅ **Domain works**: `https://optionsplunge.com/market_brief`
- ✅ **IP still works**: `https://167.88.43.61/market_brief`
- ✅ **HTTP redirects**: `http://optionsplunge.com` → `https://optionsplunge.com`
- ✅ **Market brief displays**: Brief content shows before subscription form

**The domain will be fully functional after applying these nginx configuration changes!** 🚀
