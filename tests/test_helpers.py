"""Test helpers for authentication and test setup."""

import unittest
from src.auth import hash_password


class AuthenticatedTestCase(unittest.TestCase):
    """Base test case with authentication helper methods."""
    
    def create_test_user(self, email='test@example.com', password='testpass123', 
                        role='admin', full_name='Test User'):
        """Create a test user in the database."""
        from main import database
        
        password_hash = hash_password(password)
        user_id = database.create_user(
            email=email,
            password_hash=password_hash,
            role=role,
            full_name=full_name
        )
        return user_id
    
    def login_test_user(self, client, email='test@example.com', password='testpass123'):
        """Login a test user and return the session."""
        # Login via the API
        response = client.post('/api/login', json={
            'email': email,
            'password': password
        })
        return response
    
    def create_and_login_user(self, client, email='test@example.com', 
                              password='testpass123', role='admin', 
                              full_name='Test User'):
        """Helper to create and login a test user in one call."""
        self.create_test_user(email=email, password=password, role=role, 
                             full_name=full_name)
        return self.login_test_user(client, email=email, password=password)
    
    def cleanup_test_user(self, email='test@example.com'):
        """Remove a test user from the database."""
        from main import database
        user = database.get_user_by_email(email)
        if user:
            database.delete_user(user['id'])
