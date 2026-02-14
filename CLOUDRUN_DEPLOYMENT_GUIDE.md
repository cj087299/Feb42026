# Cloud Run Deployment Guide

## Quick Fix for QBO Credential Errors

If you're seeing these errors in Cloud Run:
```
ERROR:src.qbo_client:Cannot refresh access token: QBO credentials are not configured...
ERROR:src.invoice_manager:Failed to fetch invoices...
```

**This is normal for a freshly deployed application!** These errors appear when users try to access invoice or cashflow data before QuickBooks credentials have been configured.

## Solution: Configure QuickBooks Credentials

You have **three options** to configure credentials. Choose the one that works best for you:

### Option 1: Web UI (RECOMMENDED - Easiest)

This is the simplest method and works immediately after deployment:

1. **Deploy your application** to Cloud Run (if not already deployed)
2. **Access your application** at your Cloud Run URL (e.g., `https://feb42026-xxxxx-uc.a.run.app`)
3. **Log in as admin**:
   - Username: `admin@vzt.com` or `cjones@vztsolutions.com`
   - Password: `admin1234` (default - change after first login!)
4. **Navigate to** `/qbo-settings` or click "QBO Settings" in the navigation
5. **Click "Connect to QuickBooks"**
6. **Follow the OAuth flow** - log in to QuickBooks and authorize your app
7. **Done!** Credentials are automatically saved to the database

**Benefits:**
- ✅ No command-line work needed
- ✅ Works immediately after deployment
- ✅ Credentials stored securely in database
- ✅ Tokens refresh automatically
- ✅ No manual token management

### Option 2: Google Secret Manager

Use this if you want to share credentials across multiple services or prefer centralized secret management.

#### Step 1: Create Secrets

```bash
# Set your project
export PROJECT_ID="your-project-id"
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

#### Step 2: Set Environment Variables in Cloud Run

```bash
gcloud run services update feb42026 \
    --region=us-central1 \
    --update-env-vars="QBO_REFRESH_TOKEN=YOUR_REFRESH_TOKEN,QBO_REALM_ID=YOUR_REALM_ID"
```

Or use the Cloud Console:
1. Go to Cloud Run → feb42026 service
2. Click "Edit & Deploy New Revision"
3. Go to "Variables & Secrets" tab
4. Add environment variables:
   - `QBO_REFRESH_TOKEN`: Your refresh token
   - `QBO_REALM_ID`: Your QuickBooks Company ID
5. Optionally, mount secrets:
   - Mount `QBO_ID_2-3-26` as environment variable `QBO_CLIENT_ID`
   - Mount `QBO_Secret_2-3-26` as environment variable `QBO_CLIENT_SECRET`

### Option 3: Environment Variables Only

Set all credentials as environment variables in Cloud Run:

```bash
gcloud run services update feb42026 \
    --region=us-central1 \
    --update-env-vars="QBO_CLIENT_ID=YOUR_CLIENT_ID,QBO_CLIENT_SECRET=YOUR_CLIENT_SECRET,QBO_REFRESH_TOKEN=YOUR_REFRESH_TOKEN,QBO_REALM_ID=YOUR_REALM_ID"
```

⚠️ **Security Note**: This is less secure than using Secret Manager or the database method, but it works for testing.

## Understanding the Errors

The errors you're seeing are **informational errors** that occur when:

1. A user tries to access `/invoices` or `/cashflow` pages
2. The application tries to fetch data from QuickBooks
3. No valid credentials are configured yet

These errors are logged but don't crash the application. They simply return empty data until credentials are configured.

## Credential Priority

The application checks for credentials in this order:

1. **Database** (configured via `/qbo-settings`) - ⭐ HIGHEST PRIORITY
2. **Google Secret Manager** (`QBO_ID_2-3-26`, `QBO_Secret_2-3-26`)
3. **Environment Variables** (`QBO_CLIENT_ID`, `QBO_CLIENT_SECRET`, etc.)
4. **Dummy Values** - ❌ CAUSES THE ERRORS YOU'RE SEEING

Once you configure credentials using any method, the errors will stop.

## Deployment Process

Here's the complete deployment workflow:

### 1. Initial Deployment (Without Credentials)

```bash
# Deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Or deploy directly
gcloud run deploy feb42026 \
    --source . \
    --region=us-central1 \
    --platform=managed \
    --allow-unauthenticated
```

At this point, the app is running but will show credential errors when users try to access QBO features.

### 2. Configure Credentials

Choose one of the three options above to configure credentials.

### 3. Verify

Access your application and try to view invoices. If credentials are valid, you should see data from QuickBooks.

## Automated Deployment with Credentials

If you want to include credential configuration in your CI/CD pipeline:

### Using Cloud Build Substitutions

You can pass environment variables during deployment:

```yaml
# In cloudbuild.yaml, modify the deploy step:
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'feb42026'
      - '--image=gcr.io/$PROJECT_ID/feb42026'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID'
      # Optional: Reference secrets stored in Secret Manager
      - '--update-secrets=QBO_CLIENT_ID=QBO_ID_2-3-26:latest,QBO_CLIENT_SECRET=QBO_Secret_2-3-26:latest,QBO_REFRESH_TOKEN=QBO_REFRESH_TOKEN:latest,QBO_REALM_ID=QBO_REALM_ID:latest'
```

**Note**: Only add the `--update-secrets` line if you've created the corresponding secrets in Secret Manager. Otherwise, deployment will fail.

### Using Build-Time Secrets

If you store secrets in Google Cloud Secret Manager and want to use them during build:

```yaml
# At the top of cloudbuild.yaml, add:
availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/QBO_ID_2-3-26/versions/latest
      env: 'QBO_CLIENT_ID'
    - versionName: projects/$PROJECT_ID/secrets/QBO_Secret_2-3-26/versions/latest
      env: 'QBO_CLIENT_SECRET'

# Then in the deploy step:
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'feb42026'
      - '--image=gcr.io/$PROJECT_ID/feb42026'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--update-env-vars=QBO_CLIENT_ID=$$QBO_CLIENT_ID,QBO_CLIENT_SECRET=$$QBO_CLIENT_SECRET'
    secretEnv: ['QBO_CLIENT_ID', 'QBO_CLIENT_SECRET']
```

## Troubleshooting

### Issue: Still seeing errors after configuring credentials

**Solution**: Check the credential priority:
1. If you configured via `/qbo-settings`, make sure the database is persistent (not in-memory)
2. If using Secret Manager, verify the service account has `secretmanager.secretAccessor` role
3. If using environment variables, verify they're set correctly: `gcloud run services describe feb42026 --region=us-central1`

### Issue: 401 Unauthorized errors

**Cause**: Refresh token expired (after 101 days) or invalid credentials

**Solution**:
1. Go to `/qbo-settings`
2. Click "Connect to QuickBooks" to get a fresh token
3. Or update your credentials using one of the methods above

### Issue: Deployment fails with "secret not found"

**Cause**: You added `--update-secrets` but the secrets don't exist in Secret Manager

**Solution**: Either:
1. Create the secrets first (see Option 2 above)
2. Remove the `--update-secrets` flag from cloudbuild.yaml
3. Use Option 1 (Web UI) instead

## Recommended Approach

For most users, we recommend:

1. **Deploy without credentials** using the basic cloudbuild.yaml
2. **Access the deployed application** at your Cloud Run URL
3. **Configure via Web UI** at `/qbo-settings`
4. **Done!**

This approach:
- ✅ Is the simplest and fastest
- ✅ Doesn't require command-line work
- ✅ Handles token refresh automatically
- ✅ Works immediately

## Database Persistence

Important: For Cloud Run deployments, make sure you're using a persistent database:

- **Cloud SQL**: Set `USE_CLOUD_SQL=true` and configure Cloud SQL connection
- **External Database**: Mount a persistent volume or use a managed database
- **SQLite** (default): Only for development - data is lost on container restart!

For production, use Cloud SQL:

```bash
gcloud run services update feb42026 \
    --region=us-central1 \
    --update-env-vars="USE_CLOUD_SQL=true,CLOUD_SQL_CONNECTION_NAME=your-project:region:instance,CLOUD_SQL_DATABASE_NAME=accounting_app,CLOUD_SQL_USER=root" \
    --update-secrets="CLOUD_SQL_PASSWORD=db-password:latest"
```

## Getting QuickBooks Credentials

To get your QuickBooks OAuth credentials:

1. Go to [Intuit Developer Portal](https://developer.intuit.com/)
2. Create an app or use existing app
3. Get your Client ID and Client Secret
4. Use the [OAuth 2.0 Playground](https://developer.intuit.com/app/developer/playground) to get access and refresh tokens
5. Note your Realm ID (Company ID) - shown after authorization

## Additional Resources

- `GOOGLE_SECRET_MANAGER_SETUP.md` - Detailed Secret Manager setup
- `QBO_OAUTH_FLOW.md` - OAuth flow documentation
- `QBO_TOKEN_MANAGEMENT.md` - Token management details
- `OAUTH_CREDENTIAL_SETUP_GUIDE.md` - General OAuth troubleshooting

## Need Help?

If you're still experiencing issues:

1. Check Cloud Run logs: `gcloud run services logs read feb42026 --region=us-central1 --limit=100`
2. Verify credentials are configured: Access `/api/qbo/credentials` (requires login)
3. Run diagnostic script (if you have SSH access to container): `python3 diagnose_credentials_cloudrun.py`
