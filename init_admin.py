"""
Script to initialize the VZT Accounting database with a default master admin user.
Run this once to set up the first user for the system.
"""

import sys
import os

# Add the parent directory to the path so we can import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.auth import hash_password

def init_admin_user():
    """Create a default master admin user."""
    database = Database()
    
    # Default credentials
    email = "admin@vzt.com"
    password = "admin123"  # This should be changed after first login
    full_name = "System Administrator"
    role = "master_admin"
    
    # Check if user already exists
    existing_user = database.get_user_by_email(email)
    if existing_user:
        print(f"User {email} already exists. Skipping creation.")
        return
    
    # Hash password
    password_hash = hash_password(password)
    
    # Create user
    user_id = database.create_user(email, password_hash, full_name, role)
    
    if user_id:
        print(f"\n✓ Master admin user created successfully!")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"  \n⚠️  IMPORTANT: Please change the password after first login!\n")
    else:
        print(f"\n✗ Failed to create master admin user")

if __name__ == "__main__":
    print("Initializing VZT Accounting database...\n")
    init_admin_user()
