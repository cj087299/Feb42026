# Email Configuration Guide

This document explains how to configure email functionality for password reset and username reminder features in VZT Accounting.

## Overview

The VZT Accounting system **requires** email functionality for:
- **Password Reset**: Sends a secure reset link to users who forgot their password
- **Username Reminder**: Sends the username (email) to users who forgot their login credentials

⚠️ **IMPORTANT**: Email configuration is mandatory. The application will not start without proper SMTP configuration.

## Configuration

Email functionality is controlled through environment variables. The system uses SMTP to send emails.

### Required Environment Variables

```bash
# Base URL for password reset links (prevents Host header injection)
BASE_URL=https://your-domain.com  # Your application's base URL

# SMTP Server Configuration (REQUIRED)
SMTP_HOST=smtp.gmail.com           # Your SMTP server hostname
SMTP_PORT=587                       # SMTP port (587 for TLS, 465 for SSL)
SMTP_USER=your-email@gmail.com     # SMTP username (usually your email) - REQUIRED
SMTP_PASSWORD=your-app-password    # SMTP password or app-specific password - REQUIRED

# Email Sender Information
FROM_EMAIL=your-email@gmail.com    # Email address that appears in "From" field
FROM_NAME=VZT Accounting           # Name that appears in "From" field
```

### Optional: Disable Email (Not Recommended)

If you need to disable email functionality temporarily (e.g., for testing), you can set:

```bash
EMAIL_ENABLED=false
```

⚠️ **WARNING**: Disabling email will prevent users from resetting passwords. This is not recommended for production environments.

### Example: Gmail Configuration

For Gmail, you'll need to use an App Password (not your regular Gmail password):

1. Enable 2-Factor Authentication in your Google Account
2. Go to Google Account > Security > 2-Step Verification > App passwords
3. Generate a new app password for "Mail"
4. Use this app password in the `SMTP_PASSWORD` variable

```bash
BASE_URL=https://your-domain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=VZT Accounting
```

### Example: Other SMTP Providers

#### SendGrid
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

#### Mailgun
```bash
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@your-domain.mailgun.org
SMTP_PASSWORD=your-mailgun-password
```

#### Amazon SES
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
```

## Testing Email Configuration

The email service is enabled by default and **requires** valid SMTP credentials to start the application.

To test your email configuration:

1. Set the required environment variables as shown above
2. Run the application
3. The application will fail to start if SMTP credentials are missing
4. If credentials are valid, try the "Forgot Password" feature on the login page
5. Check your email inbox for the password reset link

### Development/Testing Mode

If you need to test the application without sending actual emails:

1. Set `EMAIL_ENABLED=false` in your environment
2. The application will log email content to the console instead
3. This mode is useful for development but **not recommended for production**

## Security Considerations

1. **Never commit email credentials** to your repository
2. Use environment variables or a secure secret manager
3. Use app-specific passwords rather than your main account password
4. Consider using a dedicated email account for the application
5. Enable DKIM, SPF, and DMARC records for production email sending
6. Regularly rotate email credentials

## Troubleshooting

### Emails Not Being Sent

1. Check that `EMAIL_ENABLED=true`
2. Verify SMTP credentials are correct
3. Check application logs for error messages
4. Ensure your email provider allows SMTP connections
5. Check if your email provider requires app-specific passwords
6. Verify firewall rules allow outbound connections on the SMTP port

### Email Goes to Spam

1. Configure SPF records for your domain
2. Set up DKIM signing
3. Configure DMARC policy
4. Use a reputable email service provider
5. Avoid spam trigger words in email content

### Rate Limiting

Most email providers have rate limits:
- Gmail: 500 emails/day (free), 2000/day (Google Workspace)
- SendGrid: Varies by plan
- Amazon SES: Starts at 200/day

Monitor your usage and upgrade as needed.

## Production Recommendations

For production deployments:

1. Use a professional email service (SendGrid, Mailgun, Amazon SES)
2. Set up a custom domain with proper DNS records
3. Use Google Cloud Secret Manager or similar for credentials
4. Monitor email delivery rates and bounce rates
5. Implement email queue for reliability
6. Add email templates for branding consistency
7. Include unsubscribe links where applicable

## Default Users

The system creates two default admin users:

- **Email**: `admin@vzt.com`
  - **Password**: `admin1234`
  - **Role**: Master Admin

- **Email**: `cjones@vztsolutions.com`
  - **Password**: `admin1234`
  - **Role**: Master Admin

⚠️ **IMPORTANT**: Change these default passwords immediately after first login!

## Support

For issues with email configuration:
1. Check the application logs
2. Verify environment variables are set correctly
3. Test SMTP connectivity with telnet or similar tools
4. Consult your email provider's documentation
