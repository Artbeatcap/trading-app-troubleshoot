# Google OAuth Setup Guide

This guide will walk you through setting up Google OAuth for your Options Plunge trading app.

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API (if not already enabled)

## Step 2: Configure OAuth Consent Screen

1. In Google Cloud Console, go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** user type (unless you have Google Workspace)
3. Fill in the required information:
   - **App name**: Options Plunge
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `https://www.googleapis.com/auth/userinfo.email`
5. Add test users (your email) if in testing mode

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Set the following:
   - **Name**: Options Plunge Web Client
   - **Authorized JavaScript origins**:
     - `http://127.0.0.1:5000` (for local development)
     - `http://localhost:5000` (for local development)
     - `https://yourdomain.com` (for production)
   - **Authorized redirect URIs**:
     - `http://127.0.0.1:5000/login/google/authorized` (for local development)
     - `http://localhost:5000/login/google/authorized` (for local development)
     - `https://yourdomain.com/login/google/authorized` (for production)

## Step 4: Get Your Credentials

After creating the OAuth client, you'll get:
- **Client ID**: A long string ending with `.apps.googleusercontent.com`
- **Client Secret**: A shorter string

## Step 5: Update Environment Variables

1. Copy your `.env` file (if it doesn't exist, create one)
2. Add these lines:
   ```
   GOOGLE_OAUTH_CLIENT_ID=your-client-id-here
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
   ```

## Step 6: Test the Setup

1. Restart your Flask app
2. Go to the login page
3. You should see a "Sign in with Google" button
4. Click it and test the OAuth flow

## Troubleshooting

### Common Issues:

1. **"Invalid redirect URI" error**:
   - Make sure the redirect URI in Google Console matches exactly
   - Check for trailing slashes or protocol mismatches

2. **"OAuth consent screen not configured"**:
   - Complete the OAuth consent screen setup
   - Add your email as a test user

3. **"Client ID not found"**:
   - Double-check your Client ID and Secret
   - Make sure they're in your `.env` file

### For Production:

1. Update the OAuth consent screen to **Production**
2. Add your production domain to authorized origins
3. Update redirect URIs for your production domain
4. Consider using environment-specific credentials

## Security Notes

- Never commit your `.env` file to version control
- Keep your Client Secret secure
- Use HTTPS in production
- Regularly rotate your credentials

## Next Steps

Once OAuth is working:
1. Test the complete login flow
2. Verify user data is being stored correctly
3. Test the logout functionality
4. Consider adding additional OAuth providers if needed 