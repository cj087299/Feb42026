"""Tests for email service with various credential scenarios."""

import unittest
import os
from unittest.mock import patch
from src.email_service import EmailService


class TestEmailServiceCredentials(unittest.TestCase):
    """Test email service behavior with different credential configurations."""
    
    def setUp(self):
        """Save original environment variables."""
        self.original_env = {}
        for key in ['SMTP_USER', 'SMTP_PASSWORD', 'EMAIL_ENABLED', 'SMTP_HOST', 'SMTP_PORT']:
            self.original_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
    
    def tearDown(self):
        """Restore original environment variables."""
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
    
    def test_service_initializes_without_credentials(self):
        """Test that email service can initialize without SMTP credentials."""
        # This should not raise an exception
        email_service = EmailService()
        self.assertIsNotNone(email_service)
        self.assertTrue(email_service.enabled)
        self.assertFalse(email_service.credentials_configured)
    
    def test_service_initializes_with_email_disabled(self):
        """Test that email service can initialize with EMAIL_ENABLED=false."""
        os.environ['EMAIL_ENABLED'] = 'false'
        email_service = EmailService()
        self.assertIsNotNone(email_service)
        self.assertFalse(email_service.enabled)
        self.assertFalse(email_service.credentials_configured)
    
    def test_service_initializes_with_credentials(self):
        """Test that email service initializes properly with credentials."""
        os.environ['SMTP_USER'] = 'test@example.com'
        os.environ['SMTP_PASSWORD'] = 'testpassword'
        
        email_service = EmailService()
        self.assertIsNotNone(email_service)
        self.assertTrue(email_service.enabled)
        self.assertTrue(email_service.credentials_configured)
    
    def test_send_email_fails_without_credentials(self):
        """Test that sending email fails gracefully without credentials."""
        email_service = EmailService()
        
        # Should return False, not raise an exception
        result = email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            '<p>Test body</p>',
            'Test body'
        )
        
        self.assertFalse(result)
    
    def test_send_email_logs_when_disabled(self):
        """Test that sending email logs content when disabled."""
        os.environ['EMAIL_ENABLED'] = 'false'
        email_service = EmailService()
        
        # Should return True (logged) even without credentials
        result = email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            '<p>Test body</p>',
            'Test body'
        )
        
        self.assertTrue(result)
    
    def test_send_email_with_invalid_email_format(self):
        """Test that invalid email format is rejected."""
        os.environ['SMTP_USER'] = 'test@example.com'
        os.environ['SMTP_PASSWORD'] = 'testpassword'
        email_service = EmailService()
        
        # Invalid email formats should return False
        self.assertFalse(email_service.send_email('not-an-email', 'Subject', 'Body'))
        self.assertFalse(email_service.send_email('missing@domain', 'Subject', 'Body'))
        self.assertFalse(email_service.send_email('@example.com', 'Subject', 'Body'))
    
    def test_credentials_configured_property(self):
        """Test the credentials_configured property."""
        # Without credentials
        email_service = EmailService()
        self.assertFalse(email_service.credentials_configured)
    
    def test_credentials_configured_with_only_username(self):
        """Test credentials_configured with only username set."""
        os.environ['SMTP_USER'] = 'test@example.com'
        email_service = EmailService()
        self.assertFalse(email_service.credentials_configured)
    
    def test_credentials_configured_with_both(self):
        """Test credentials_configured with both username and password."""
        os.environ['SMTP_USER'] = 'test@example.com'
        os.environ['SMTP_PASSWORD'] = 'testpassword'
        email_service = EmailService()
        self.assertTrue(email_service.credentials_configured)


class TestEmailServiceDefaultConfiguration(unittest.TestCase):
    """Test email service default configuration values."""
    
    def setUp(self):
        """Save and clear environment variables."""
        self.original_env = {}
        for key in ['SMTP_USER', 'SMTP_PASSWORD', 'EMAIL_ENABLED', 'SMTP_HOST', 
                    'SMTP_PORT', 'FROM_EMAIL', 'FROM_NAME']:
            self.original_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
    
    def tearDown(self):
        """Restore original environment variables."""
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
    
    def test_default_smtp_host(self):
        """Test default SMTP host is Gmail."""
        email_service = EmailService()
        self.assertEqual(email_service.smtp_host, 'smtp.gmail.com')
    
    def test_default_smtp_port(self):
        """Test default SMTP port is 587."""
        email_service = EmailService()
        self.assertEqual(email_service.smtp_port, 587)
    
    def test_default_email_enabled(self):
        """Test default EMAIL_ENABLED is true."""
        email_service = EmailService()
        self.assertTrue(email_service.enabled)
    
    def test_custom_smtp_settings(self):
        """Test custom SMTP settings are respected."""
        os.environ['SMTP_HOST'] = 'smtp.sendgrid.net'
        os.environ['SMTP_PORT'] = '465'
        os.environ['SMTP_USER'] = 'apikey'
        os.environ['SMTP_PASSWORD'] = 'secret'
        
        email_service = EmailService()
        self.assertEqual(email_service.smtp_host, 'smtp.sendgrid.net')
        self.assertEqual(email_service.smtp_port, 465)
        self.assertEqual(email_service.smtp_user, 'apikey')


if __name__ == '__main__':
    unittest.main()
