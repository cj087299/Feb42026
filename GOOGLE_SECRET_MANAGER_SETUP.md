# Google Secret Manager Setup for QuickBooks OAuth

## Overview

This guide explains how to properly configure QuickBooks OAuth credentials in Google Secret Manager for your Cloud Run application.

## Current Status Based on Error

The 401 Unauthorized error you're seeing indicates one of these issues:

1. **Secrets don't exist** in Google Secret Manager (most likely)
2. **Secrets exist but contain invalid/expired values**
3. **No credentials in database** (checking /qbo-settings)

## Solution: Configure Credentials

You have **three options** to configure credentials. Choose the one that works best for you:

### Option 1: Use the Web UI (RECOMMENDED)

This is the easiest and most secure method:

1. **Access your Cloud Run application** at its URL
2. **Log in as admin** (admin@vzt.com / admin1234 or cjones@vztsolutions.com / admin1234)
3. **Navigate to** `/qbo-settings`
4. **Click "Connect to QuickBooks"**
5. **Follow the OAuth flow** - log in to QuickBooks and authorize
6. **Done!** Credentials are automatically saved to the database

This method:
- ✅ Stores credentials in the database (highest priority)
- ✅ Automatically handles token exchange
- ✅ No need to manually configure Secret Manager
- ✅ Works immediately

### Option 2: Set Up Google Secret Manager

If you prefer to use Google Secret Manager (for shared credentials across multiple services):

#### Step 1: Get Your QuickBooks Credentials

You need four pieces of information:
- **Client ID**: From your QuickBooks app
- **Client Secret**: From your QuickBooks app  
- **Refresh Token**: From completing the OAuth flow
- **Realm ID**: Your QuickBooks Company ID

To get these, you can use the [QuickBooks OAuth 2.0 Playground](https://developer.intuit.com/app/developer/playground).

#### Step 2: Create Secrets in Google Secret Manager

```bash
# Set your project
export PROJECT_ID="project-df2be397-d2f7-4b71-944"
gcloud config set project $PROJECT_ID

# Create the Client ID secret
echo -n "YOUR_CLIENT_ID" | gcloud secrets create QBO_ID_2-3-26 \
    --data-file=- \
    --replication-policy="automatic"

# Create the Client Secret secret
echo -n "YOUR_CLIENT_SECRET" | gcloud secrets create QBO_Secret_2-3-26 \
    --data-file=- \
    --replication-policy="automatic"

# Grant access to Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding QBO_ID_2-3-26 \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding QBO_Secret_2-3-26 \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

#### Step 3: Set Environment Variables in Cloud Run

Set the refresh token and realm ID as environment variables:

```bash
gcloud run services update feb42026 \
    --region=us-central1 \
    --set-env-vars="QBO_REFRESH_TOKEN=YOUR_REFRESH_TOKEN,QBO_REALM_ID=YOUR_REALM_ID"
```

Or set them in the Cloud Run console:
1. Go to Cloud Run → feb42026 service
2. Click "Edit & Deploy New Revision"
3. Go to "Variables & Secrets" tab
4. Add environment variables:
   - `QBO_REFRESH_TOKEN`: Your refresh token
   - `QBO_REALM_ID`: Your QuickBooks Company ID

### Option 3: Use Only Environment Variables

If you don't want to use Secret Manager at all:

```bash
gcloud run services update feb42026 \
    --region=us-central1 \
    --set-env-vars="QBO_CLIENT_ID=YOUR_CLIENT_ID,QBO_CLIENT_SECRET=YOUR_CLIENT_SECRET,QBO_REFRESH_TOKEN=YOUR_REFRESH_TOKEN,QBO_REALM_ID=YOUR_REALM_ID"
```

⚠️ **Security Note**: Using environment variables directly is less secure than Secret Manager or the database method.

## Verifying Your Setup

### In Cloud Run

1. Check the logs after deployment:
   ```bash
   gcloud run services logs read feb42026 --region=us-central1 --limit=50
   ```

2. Look for these log messages:
   - ✅ `Retrieved QBO credentials from database`
   - ✅ `Retrieved secret 'QBO_ID_2-3-26' from Google Secret Manager`
   - ❌ `QBO credentials are not configured` (means using dummy values)

### Using the Diagnostic Script

Run this in your Cloud Run container:

```bash
python3 diagnose_credentials_cloudrun.py
```

This will show exactly where credentials are coming from.

### Via the API

Call the credential status endpoint:

```bash
curl -X GET https://your-app-url.com/api/qbo/credentials \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

## Understanding Credential Priority

The application checks for credentials in this order:

1. **Database** (configured via `/qbo-settings`) - ⭐ HIGHEST PRIORITY
2. **Google Secret Manager** (`QBO_ID_2-3-26`, `QBO_Secret_2-3-26`)
3. **Environment Variables** (`QBO_CLIENT_ID`, `QBO_CLIENT_SECRET`, etc.)
4. **Dummy Values** - ❌ CAUSES 401 ERRORS

## Common Issues and Solutions

### Issue: Still Getting 401 After Configuration

**Cause**: Refresh token expired (after 101 days) or is invalid

**Solution**:
1. Go to `/qbo-settings`
2. Click "Connect to QuickBooks" to get a fresh refresh token
3. The old token will be replaced automatically

### Issue: Secrets Created but Still Using Dummy Values

**Cause**: Cloud Run service account doesn't have permission to access secrets

**Solution**: Grant permissions as shown in Step 2 above

### Issue: "google-cloud-secret-manager not installed"

**Cause**: Missing dependency (shouldn't happen in Cloud Run)

**Solution**: Run `pip install google-cloud-secret-manager` and redeploy

## Checking Current Secret Values

To see what's currently in your secrets (without revealing the actual value):

```bash
# Check if secrets exist
gcloud secrets list --filter="name:QBO"

# Check secret metadata
gcloud secrets describe QBO_ID_2-3-26
gcloud secrets describe QBO_Secret_2-3-26

# View secret (BE CAREFUL - this shows the actual value)
gcloud secrets versions access latest --secret="QBO_ID_2-3-26"
```

## Updating Secrets

If you need to update a secret with a new value:

```bash
# Add a new version of the secret
echo -n "NEW_CLIENT_ID" | gcloud secrets versions add QBO_ID_2-3-26 --data-file=-

# The application will use the latest version automatically
```

## Recommended Approach

For your situation, I recommend **Option 1 (Web UI)**:

1. It's the simplest - just click "Connect to QuickBooks"
2. It's the most secure - credentials stay in your database
3. It handles token refresh automatically
4. No need to manually manage Secret Manager

Then, if needed, you can migrate to Secret Manager later for multi-service sharing.

## Need Help?

If you're still having issues:

1. Run `python3 diagnose_credentials_cloudrun.py` in Cloud Run
2. Check the application logs for detailed error messages
3. Verify your QuickBooks app is active in the Intuit Developer Portal
4. Make sure your redirect URIs are configured correctly

See also:
- `OAUTH_CREDENTIAL_SETUP_GUIDE.md` - General OAuth troubleshooting
- `QBO_OAUTH_FLOW.md` - OAuth flow documentation
- `QBO_TOKEN_MANAGEMENT.md` - Token management details
