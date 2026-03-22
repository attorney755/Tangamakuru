#!/usr/bin/env python3
"""
Create Super Admin account for TANGAMAKURU
Run this script after setting up the database
"""

import sys
import os
from datetime import datetime

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def create_super_admin():
    """Create the Super Admin account"""
    app = create_app()
    
    with app.app_context():
        # Check if Super Admin already exists
        existing = User.query.filter_by(email='superadmin@gov.rw').first()
        
        if existing:
            print(f"⚠️  Super Admin already exists: {existing.email}")
            print(f"   Password: Vanessa@2025 (if you haven't changed it)")
            return False
        
        # Create Super Admin
        super_admin = User(
            email='superadmin@gov.rw',
            first_name='Super',
            last_name='Admin',
            role='super_admin',
            is_active=True,
            is_verified=True,
            is_approved=True,
            district='System',
            created_at=datetime.utcnow()
        )
        
        # Set password
        super_admin.set_password('Vanessa@2025')
        
        # Save to database
        db.session.add(super_admin)
        db.session.commit()
        
        print("=" * 50)
        print("✅ SUPER ADMIN CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"📧 Email: superadmin@gov.rw")
        print(f"🔑 Password: Vanessa@2025")
        print("=" * 50)
        print("\n⚠️  IMPORTANT: Change this password after first login!")
        print("\nNext steps:")
        print("1. Login to the system using these credentials")
        print("2. Create district admins from the Manage Admins page")
        print("3. District admins will then approve officer registrations")
        print("=" * 50)
        
        return True

if __name__ == '__main__':
    try:
        create_super_admin()
    except Exception as e:
        print(f"❌ Error creating Super Admin: {str(e)}")
        sys.exit(1)
