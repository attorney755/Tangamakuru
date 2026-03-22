#!/usr/bin/env python3
"""
Create Super Admin account for TANGAMAKURU
Run this script after setting up the database
"""

import sys
import os
import getpass
import re
from datetime import datetime

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def validate_email(email):
    """Validate that email ends with @gov.rw"""
    if not email.endswith('@gov.rw'):
        print("❌ Error: Super Admin email must end with @gov.rw")
        print("   Example: admin@example.gov.rw")
        return False
    return True

def validate_password(password, confirm):
    """Validate password meets requirements"""
    if password != confirm:
        print("❌ Error: Passwords do not match")
        return False
    if len(password) < 8:
        print("❌ Error: Password must be at least 8 characters")
        return False
    return True

def create_super_admin():
    """Create the Super Admin account"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "=" * 50)
        print("  TANGAMAKURU - Super Admin Account Setup")
        print("=" * 50)
        print("\nThis account will have full system access.")
        print("It can create district administrators who will manage officers.\n")
        
        # Check if any Super Admin already exists
        existing_admins = User.query.filter_by(role='super_admin').all()
        
        if existing_admins:
            print("⚠️  Super Admin account(s) already exist:")
            for admin in existing_admins:
                print(f"   - {admin.email}")
            print("\nDo you want to create another Super Admin? (y/n)")
            choice = input().lower()
            if choice != 'y':
                print("Exiting...")
                return False
        
        # Get email
        print("Enter Super Admin email address:")
        print("(Note: Must end with @gov.rw, e.g., superadmin@gov.rw)")
        email = input("Email: ").strip().lower()
        
        while not validate_email(email):
            email = input("Email: ").strip().lower()
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"❌ Error: User with email {email} already exists!")
            return False
        
        # Get first name
        first_name = input("First Name: ").strip()
        while not first_name:
            first_name = input("First Name (required): ").strip()
        
        # Get last name
        last_name = input("Last Name: ").strip()
        while not last_name:
            last_name = input("Last Name (required): ").strip()
        
        # Get password
        print("\nCreate a strong password (minimum 8 characters):")
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm Password: ")
        
        while not validate_password(password, confirm):
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Confirm Password: ")
        
        # Create Super Admin
        super_admin = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='super_admin',
            is_active=True,
            is_verified=True,
            is_approved=True,
            district='System',
            created_at=datetime.utcnow()
        )
        
        # Set password
        super_admin.set_password(password)
        
        # Save to database
        db.session.add(super_admin)
        db.session.commit()
        
        print("\n" + "=" * 50)
        print("✅ SUPER ADMIN CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"📧 Email: {email}")
        print(f"👤 Name: {first_name} {last_name}")
        print("=" * 50)
        print("\n⚠️  IMPORTANT: Please keep your credentials safe!")
        print("\nNext steps:")
        print("1. Login to the system using your credentials")
        print("2. Create district admins from the Manage Admins page")
        print("3. District admins will then approve officer registrations")
        print("=" * 50)
        
        return True

if __name__ == '__main__':
    try:
        create_super_admin()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error creating Super Admin: {str(e)}")
        sys.exit(1)
