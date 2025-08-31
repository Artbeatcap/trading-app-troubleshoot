# Google OAuth Setup Guide for Options Plunge

## 🔧 **Step-by-Step Setup**

### **1. Google Cloud Console Setup**

1. **Visit Google Cloud Console**: https://console.cloud.google.com/
2. **Create/Select Project**:
   - Create a new project or select existing one
   - Note your Project ID

3. **Enable APIs**:
   - Go to "APIs & Services" > "Library"
   - Search and enable these APIs:
     - Google+ API
     - Google Identity and Access Management (IAM) API

4. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Name: "Options Plunge OAuth"
   - Authorized JavaScript origins:
     ```
     http://localhost:5000
     https://yourdomain.com (for production)
     ```
   - Authorized redirect URIs:
     ```
     http://localhost:5000/login/google/authorized
     https://yourdomain.com/login/google/authorized (for production)
     ```

5. **Copy Credentials**:
   - After creation, you'll get:
     - **Client ID** (looks like: `123456789-abcdef.apps.googleusercontent.com`)
     - **Client Secret** (looks like: `GOCSPX-abcdefghijklmnop`)

### **2. Update Environment Variables**

Edit your `.env` file and replace the placeholder values:

```env
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=your-actual-client-id-here
GOOGLE_OAUTH_CLIENT_SECRET=your-actual-client-secret-here
```

### **3. Test the Setup**

1. **Restart your Flask app**:
   ```bash
   python app.py
   ```

2. **Test OAuth login**:
   - Visit: http://localhost:5000/login
   - Click "Sign in with Google"
   - Should redirect to Google and back successfully

### **4. Common Issues & Solutions**

#### **Error 401: invalid_client**
- **Cause**: Wrong client ID/secret or not configured properly
- **Solution**: Double-check your credentials in `.env` file

#### **Error: redirect_uri_mismatch**
- **Cause**: Redirect URI in Google Console doesn't match your app
- **Solution**: Add correct redirect URI to Google Console

#### **Error: OAuth 2 MUST utilize https**
- **Cause**: OAuth requires HTTPS in production
- **Solution**: Already fixed with `OAUTHLIB_INSECURE_TRANSPORT=1` for development

### **5. Production Setup**

For production, you'll need:

1. **HTTPS domain** (OAuth requires HTTPS)
2. **Update redirect URIs** in Google Console
3. **Remove** `OAUTHLIB_INSECURE_TRANSPORT=1` from production environment

### **6. Security Notes**

- **Never commit** your `.env` file to version control
- **Keep your client secret** secure
- **Use environment variables** in production
- **Regularly rotate** your OAuth credentials

## 🎯 **Quick Test**

After setup, test with:

```bash
python test_authenticated_checkout.py
```

This will verify OAuth is working correctly.

