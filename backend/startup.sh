#!/bin/bash

# Create necessary directories
mkdir -p /opt/render/project/src/uploads

echo "========================================"
echo "Creating database tables..."
echo "========================================"
python create_super_admin_force.py

echo ""
echo "========================================"
echo "Starting application..."
echo "========================================"
exec gunicorn wsgi:app
