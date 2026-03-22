#!/bin/bash

# Create necessary directories
mkdir -p /opt/render/project/src/uploads
mkdir -p /opt/render/project/src/frontend/static

# Run database migrations
echo "========================================"
echo "Running database migrations..."
echo "========================================"
flask db upgrade

# Check if migrations were successful
if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully!"
else
    echo "❌ Database migrations failed!"
    exit 1
fi

# Create super admin if not exists
echo ""
echo "========================================"
echo "Creating super admin account..."
echo "========================================"
python -c "
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
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
        print('✅ Super Admin created successfully!')
        print('   Email: superadmin@gov.rw')
        print('   Password: Vanessa@2025')
    else:
        print('✅ Super Admin already exists')
"

# Start the application
echo ""
echo "========================================"
echo "Starting application..."
echo "========================================"
exec gunicorn wsgi:app
