"""Email service for sending notifications and password resets."""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""
    
    def __init__(self):
        """Initialize email service with SMTP configuration."""
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_user = os.environ.get('SMTP_USER', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('FROM_EMAIL', self.smtp_user)
        self.from_name = os.environ.get('FROM_NAME', 'VZT Accounting')
        
        # For development/testing, we can disable actual email sending
        self.enabled = os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'
        
        if not self.enabled:
            logger.warning("Email service is disabled. Set EMAIL_ENABLED=true to enable.")
        elif not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Emails will not be sent.")
            self.enabled = False
    
    def send_email(self, to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content of the email
            text_body: Plain text content (optional, will use html_body if not provided)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, to_email):
            logger.error(f"Invalid email address format: {to_email}")
            return False
        
        if not self.enabled:
            logger.info(f"[EMAIL DISABLED] Would send email to {to_email}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Body: {text_body or html_body}")
            return True
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add plain text version
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                msg.attach(part1)
            
            # Add HTML version
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_password_reset_email(self, to_email: str, reset_token: str, base_url: str) -> bool:
        """Send password reset email with link and temporary password option.
        
        Args:
            to_email: User's email address
            reset_token: Password reset token
            base_url: Base URL of the application (e.g., https://example.com)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        reset_link = f"{base_url}/reset-password?token={reset_token}"
        
        subject = "Password Reset Request - VZT Accounting"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #4CAF50; 
                          color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; 
                           border-radius: 4px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔑 Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>We received a request to reset the password for your VZT Accounting account 
                       (<strong>{to_email}</strong>).</p>
                    
                    <p>To reset your password, click the button below:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </div>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background-color: #fff; padding: 10px; border: 1px solid #ddd;">
                        {reset_link}
                    </p>
                    
                    <div class="warning">
                        <strong>⚠️ Important:</strong>
                        <ul>
                            <li>This link will expire in <strong>1 hour</strong></li>
                            <li>If you didn't request this reset, please ignore this email</li>
                            <li>Your password will remain unchanged until you create a new one</li>
                        </ul>
                    </div>
                    
                    <p>For security reasons, we never send passwords via email. You must use the link 
                       above to create a new password.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from VZT Accounting.<br>
                    Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
Password Reset Request - VZT Accounting

Hello,

We received a request to reset the password for your VZT Accounting account ({to_email}).

To reset your password, visit this link:
{reset_link}

IMPORTANT:
- This link will expire in 1 hour
- If you didn't request this reset, please ignore this email
- Your password will remain unchanged until you create a new one

For security reasons, we never send passwords via email. You must use the link above to create a new password.

---
This is an automated message from VZT Accounting.
Please do not reply to this email.
        """
        
        return self.send_email(to_email, subject, html_body, text_body)
    
    def send_username_reminder_email(self, to_email: str) -> bool:
        """Send username reminder email.
        
        Args:
            to_email: User's email address (which is also their username)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        subject = "Username Reminder - VZT Accounting"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                .username-box {{ background-color: #e3f2fd; border: 2px solid #2196F3; padding: 20px; 
                                border-radius: 4px; text-align: center; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👤 Username Reminder</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>You requested a reminder of your username for VZT Accounting.</p>
                    
                    <div class="username-box">
                        <p style="margin: 0; font-size: 0.9em; color: #666;">Your username is:</p>
                        <h2 style="margin: 10px 0; color: #2196F3;">{to_email}</h2>
                    </div>
                    
                    <p>You can use this email address to log in to your account.</p>
                    
                    <p>If you've forgotten your password, you can reset it by visiting the 
                       "Forgot Password" link on the login page.</p>
                    
                    <p><strong>Note:</strong> If you didn't request this reminder, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from VZT Accounting.<br>
                    Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
Username Reminder - VZT Accounting

Hello,

You requested a reminder of your username for VZT Accounting.

Your username is: {to_email}

You can use this email address to log in to your account.

If you've forgotten your password, you can reset it by visiting the "Forgot Password" link on the login page.

Note: If you didn't request this reminder, please ignore this email.

---
This is an automated message from VZT Accounting.
Please do not reply to this email.
        """
        
        return self.send_email(to_email, subject, html_body, text_body)
