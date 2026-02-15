# QBO Environment Configuration

## Overview

The QuickBooks Online (QBO) integration now supports environment-based configuration through the `QBO_ENVIRONMENT` environment variable. This allows you to easily switch between QuickBooks Sandbox and Production environments.

## Environment Variable

### Variable Name
`QBO_ENVIRONMENT`

### Accepted Values
- `production` - Connects to QuickBooks Production environment (default)
- `sandbox` - Connects to QuickBooks Sandbox environment

### Default Behavior
If `QBO_ENVIRONMENT` is not set or contains an invalid value, the system will **default to the production environment**.

### Case Sensitivity
The environment variable is **case-insensitive**. Both `production`, `PRODUCTION`, and `Production` will work.

## Usage

### Setting the Environment Variable

**Linux/Mac:**
```bash
export QBO_ENVIRONMENT=production
```

**Windows:**
```cmd
set QBO_ENVIRONMENT=production
```

**Docker/Container:**
```bash
docker run -e QBO_ENVIRONMENT=production ...
```

**Cloud Run (gcloud):**
```bash
gcloud run services update YOUR_SERVICE_NAME \
  --set-env-vars QBO_ENVIRONMENT=production
```

**Cloud Run (YAML):**
```yaml
env:
  - name: QBO_ENVIRONMENT
    value: production
```

## Environments

### Production Environment (Default)
- **Base URL:** `https://quickbooks.api.intuit.com/v3/company`
- **Use for:** Live production data
- **When to use:** When you're ready to go live with real QuickBooks companies
- **Credentials:** Must use Production app credentials from developer.intuit.com

### Sandbox Environment
- **Base URL:** `https://sandbox-quickbooks.api.intuit.com/v3/company`
- **Use for:** Development, testing, and QA
- **When to use:** When you want to test the integration without affecting real data
- **Credentials:** Must use Sandbox app credentials from developer.intuit.com

## Important Notes

1. **Credential Matching**: Make sure your QuickBooks app credentials (Client ID and Client Secret) match the environment you're connecting to. Sandbox credentials won't work with production, and vice versa.

2. **Separate Apps**: You may need to create separate QuickBooks apps in the Intuit Developer Portal for sandbox and production environments.

3. **Testing Before Production**: Always test your integration thoroughly in the sandbox environment before switching to production.

4. **Verification**: Check the application logs when starting up. You should see a log message indicating which environment is being used:
   ```
   INFO:src.qbo_client:QBOClient initialized for PRODUCTION environment
   ```
   or
   ```
   INFO:src.qbo_client:QBOClient initialized for SANDBOX environment
   ```

5. **Diagnostic Endpoint**: Visit `/api/qbo/oauth/diagnostic` (requires admin access) to see the current environment configuration.

## Examples

### Development Setup (Sandbox)
```bash
# Need to explicitly set the variable to use sandbox
export QBO_ENVIRONMENT=sandbox
python3 main.py
```

### Production Setup
```bash
# No need to set the variable - defaults to production
python3 main.py
# Or explicitly set it
export QBO_ENVIRONMENT=production
python3 main.py
```

### Switching Between Environments
```bash
# Use sandbox
export QBO_ENVIRONMENT=sandbox
python3 main.py

# Use production
export QBO_ENVIRONMENT=production
python3 main.py
```

## Troubleshooting

### Error: "403 Forbidden" or "401 Unauthorized"
This usually means your credentials don't match the environment:
- If using `QBO_ENVIRONMENT=production`, ensure you have production app credentials
- If using sandbox (default), ensure you have sandbox app credentials

### How to Check Current Environment
1. Check the application logs for the initialization message
2. Visit the diagnostic endpoint at `/api/qbo/oauth/diagnostic` (admin access required)
3. The diagnostic page will show: "Using correct environment: PRODUCTION (from QBO_ENVIRONMENT variable)" or similar

## Migration Path

### From Sandbox to Production

1. **Test thoroughly in sandbox**
   ```bash
   export QBO_ENVIRONMENT=sandbox
   # Run all your tests
   ```

2. **Create production app** on developer.intuit.com

3. **Update credentials** to use production Client ID and Secret

4. **Switch environment**
   ```bash
   export QBO_ENVIRONMENT=production
   ```

5. **Reconnect to QuickBooks** via the OAuth flow to get new tokens for production

6. **Verify** the connection is working with production data

## Security Considerations

- Never commit credentials or environment variables to source control
- Use secret management systems (like Google Secret Manager) for production credentials
- Keep sandbox and production credentials separate
- Regularly rotate your credentials
- Monitor access logs for suspicious activity

## Support

If you encounter issues:
1. Check the application logs for environment initialization messages
2. Verify your credentials match the environment
3. Use the diagnostic endpoint to troubleshoot OAuth configuration
4. Ensure the `QBO_ENVIRONMENT` variable is set correctly in your deployment environment
