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
    """Create default master admin users.
    
    SECURITY NOTE: The credentials here are default values for initial setup.
    In a production environment, consider using environment variables or
    a secure configuration system. Always change the default password
    immediately after first login.
    """
    database = Database()
    
    # Default credentials for multiple admin users
    admin_users = [
        {
            "email": "cjones@vztsolutions.com",
            "password": "admin1234",
            "full_name": "CJones",
            "role": "master_admin"
        },
        {
            "email": "admin@vzt.com",
            "password": "admin1234",
            "full_name": "Admin",
            "role": "master_admin"
        }
    ]
    
    created_users = []
    
    for user_data in admin_users:
        email = user_data["email"]
        password = user_data["password"]
        full_name = user_data["full_name"]
        role = user_data["role"]
        
        # Check if user already exists
        existing_user = database.get_user_by_email(email)
        if existing_user:
            print(f"User {email} already exists. Skipping creation.")
            continue
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user
        user_id = database.create_user(email, password_hash, full_name, role)
        
        if user_id:
            created_users.append({
                "email": email,
                "password": password
            })
            print(f"✓ User created: {email}")
        else:
            print(f"✗ Failed to create user: {email}")
    
    if created_users:
        print(f"\n{'='*60}")
        print(f"Master admin user(s) created successfully!")
        print(f"{'='*60}")
        for user in created_users:
            print(f"  Email: {user['email']}")
            print(f"  Password: {user['password']}")
            print()
        print(f"⚠️  IMPORTANT: Please change the passwords after first login!\n")
    else:
        print(f"\n✗ Failed to create any master admin users")

if __name__ == "__main__":
    print("Initializing VZT Accounting database...\n")
    init_admin_user()
