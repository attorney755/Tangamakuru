from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # Create tables if they don't exist
    db.create_all()
    
    # Check if super admin exists
    existing = User.query.filter_by(email='superadmin@gov.rw').first()
    if not existing:
        super_admin = User(
            email='superadmin@gov.rw',
            first_name='Super',
            last_name='Admin',
            role='super_admin',
            is_active=True,
            is_verified=True,
            is_approved=True,
            district='Kigali City'
        )
        super_admin.set_password('Vanessa@2025')
        db.session.add(super_admin)
        db.session.commit()
        print("✅ Super Admin created successfully!")
    else:
        print("✅ Super Admin already exists")
