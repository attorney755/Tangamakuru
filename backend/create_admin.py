#!/usr/bin/env python3
"""
Create admin user for TANGAMAKURU
Run this script to create the initial admin account
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app, db
from backend.app.models import User
from werkzeug.security import generate_password_hash

def create_admin():
    """Create admin user if it doesn't exist"""
    app = create_app()
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email='adminattorney@gov.rw').first()
        
        if admin:
            print("✅ Admin user already exists!")
            print(f"Email: {admin.email}")
            print(f"Role: {admin.role}")
            print(f"Name: {admin.first_name} {admin.last_name}")
            return
        
        # Create new admin
        admin = User(
            email='adminattorney@gov.rw',
            first_name='System',
            last_name='Administrator',
            phone='+250788888888',
            role='admin',
            province='Kigali City',
            district='Gasabo',
            sector='Remera',
            cell='Gishushu',
            village='Amahoro',
            is_active=True,
            is_verified=True
        )
        
        # Set password using the model method
        admin.set_password('Attorney@2025')
        
        try:
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created successfully!")
            print(f"Email: adminattorney@gov.rw")
            print(f"Password: Attorney@2025")
            print(f"Role: admin")
            print(f"Name: System Administrator")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating admin: {str(e)}")
            
            # Try with direct SQL as fallback
            try:
                from sqlalchemy import text
                # Check if user exists
                result = db.session.execute(
                    text("SELECT * FROM users WHERE email = 'adminattorney@gov.rw'")
                ).fetchone()
                
                if result:
                    print("✅ Admin already exists in database (found via raw SQL)")
                else:
                    # Insert using raw SQL
                    import hashlib
                    password_hash = generate_password_hash('Attorney@2025')
                    
                    db.session.execute(
                        text("""
                            INSERT INTO users (
                                email, password_hash, first_name, last_name, phone, role,
                                province, district, sector, cell, village,
                                is_active, is_verified, created_at, updated_at
                            ) VALUES (
                                :email, :password_hash, :first_name, :last_name, :phone, :role,
                                :province, :district, :sector, :cell, :village,
                                :is_active, :is_verified, NOW(), NOW()
                            )
                        """),
                        {
                            'email': 'adminattorney@gov.rw',
                            'password_hash': password_hash,
                            'first_name': 'System',
                            'last_name': 'Administrator',
                            'phone': '+250788888888',
                            'role': 'admin',
                            'province': 'Kigali City',
                            'district': 'Gasabo',
                            'sector': 'Remera',
                            'cell': 'Gishushu',
                            'village': 'Amahoro',
                            'is_active': True,
                            'is_verified': True
                        }
                    )
                    db.session.commit()
                    print("✅ Admin user created successfully using raw SQL!")
                    print(f"Email: adminattorney@gov.rw")
                    print(f"Password: Attorney@2025")
            except Exception as e2:
                print(f"❌ Raw SQL also failed: {str(e2)}")

if __name__ == '__main__':
    create_admin()