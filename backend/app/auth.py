from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timezone, timedelta
from app import db
from app.models import User
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    """Decorator to require JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            from app.models import User
            current_user = User.query.get(data['user_id'])
            
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# Helper function to generate JWT token
def generate_token(user_id, role):
    """Generate JWT token for authenticated users"""
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

# Registration endpoint

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user (citizen by default)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create new user
        user = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone', ''),
            role=data.get('role', 'citizen'),
            province=data.get('province', ''),
            district=data.get('district', ''),
            sector=data.get('sector', ''),
            cell=data.get('cell', ''),
            village=data.get('village', '')
        )
        
        # Set password
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Send welcome email
        from app.utils.email import send_welcome_email
        send_welcome_email(user)
        
        # Generate token
        token = generate_token(user.id, user.role)
        
        return jsonify({
            'message': 'Registration successful. Welcome email sent!',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role
            },
            'token': token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Get user profile with JWT token
@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    """Get user profile using JWT token"""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'role': current_user.role,
        'phone': current_user.phone,
        'province': current_user.province,
        'district': current_user.district,
        'sector': current_user.sector,
        'cell': current_user.cell,
        'village': current_user.village,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
        'is_active': current_user.is_active,
        'is_verified': current_user.is_verified
    }), 200    

# Login endpoint
@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user with email and password"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user
        user = User.query.filter_by(email=data['email']).first()
        
        # Check user exists and password is correct
        if not user or not check_password_hash(user.password_hash, data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check if user is active
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Login user (for Flask-Login session management)
        login_user(user, remember=data.get('remember', False))
        
        # Generate JWT token
        token = generate_token(user.id, user.role)
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'sector': user.sector if user.role == 'officer' else None
            },
            'token': token
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Logout endpoint
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout current user"""
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

# Get current user info
@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current authenticated user information"""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'role': current_user.role,
        'phone': current_user.phone,
        'province': current_user.province,
        'district': current_user.district,
        'sector': current_user.sector,
        'cell': current_user.cell,
        'village': current_user.village,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None
    }), 200

# Test endpoint
@auth_bp.route('/test')
def test():
    return jsonify({'message': 'Auth blueprint is working!'})


@auth_bp.route('/officer/register', methods=['POST'])
def officer_register():
    """Register a new officer (pending approval)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['email', 'first_name', 'last_name', 'phone', 'province', 
                   'district', 'sector', 'cell', 'village', 'officer_id', 
                   'department', 'password', 'email_type']
        
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if user exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Check if officer ID exists
        if User.query.filter_by(officer_id=data['officer_id']).first():
            return jsonify({'error': 'Officer ID already exists'}), 409
        
        # Create pending officer
        officer = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data['phone'],
            role='officer',
            province=data['province'],
            district=data['district'],
            sector=data['sector'],
            cell=data['cell'],
            village=data['village'],
            officer_id=data['officer_id'],
            department=data['department'],
            is_active=False,  # Not active until approved
            is_verified=False,  # Not verified until approved
            is_approved=False,
            approval_status='pending',
            created_at=datetime.now(timezone.utc)
        )
        
        # Set password
        officer.set_password(data['password'])
        
        db.session.add(officer)
        db.session.flush()  # Get the ID
        
        # Create notification for the officer
        from app.models import Notification
        officer_notification = Notification(
            user_id=officer.id,
            title='Registration Pending Approval',
            message=f'Your officer account registration has been submitted and is pending approval from the {officer.district} District Admin. You will receive a notification within 24 hours.',
            notification_type='info',
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(officer_notification)
        
        # Find the district admin to notify
        district_admin = User.query.filter_by(
            role='admin',
            district=officer.district,
            is_active=True
        ).first()
        
        if district_admin:
            # Create notification for admin
            admin_notification = Notification(
                user_id=district_admin.id,
                title='New Officer Registration Pending',
                message=f'New officer {officer.get_full_name()} from {officer.sector} sector has registered and is waiting for approval. Email type: {data["email_type"]}',
                notification_type='warning',
                is_read=False,
                created_at=datetime.now(timezone.utc),
                metadata={
                    'officer_id': officer.id,
                    'officer_email': officer.email,
                    'officer_name': officer.get_full_name(),
                    'sector': officer.sector,
                    'email_type': data['email_type']
                }
            )
            db.session.add(admin_notification)
            
            # Also create a pending approval record
            from app.models import PendingApproval
            pending = PendingApproval(
                officer_id=officer.id,
                admin_id=district_admin.id,
                email_type=data['email_type'],
                status='pending',
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(pending)
        
        db.session.commit()
        
        message = "Registration submitted successfully! "
        if data['email_type'] == 'personal':
            message += "Your account will be verified by the district admin within 24 hours. You will be notified once approved."
        else:
            message += "Your government email has been verified. Please wait for admin approval."
        
        return jsonify({
            'success': True,
            'message': message,
            'pending_id': officer.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in officer registration: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500