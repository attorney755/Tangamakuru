from flask import Flask, jsonify, render_template
from dotenv import load_dotenv
import os
from datetime import timedelta
from flask_mail import Mail

# Import extensions from extensions.py
from .extensions import db, login_manager, migrate


def create_app():
    """Application factory function"""
    # Get absolute paths - Go up TWO levels from app/__init__.py
    # __file__ = /home/attorney/TANGAMAKURU/backend/app/__init__.py
    # We want: /home/attorney/TANGAMAKURU
    current_file_dir = os.path.dirname(os.path.abspath(__file__))  # /home/attorney/TANGAMAKURU/backend/app
    backend_dir = os.path.dirname(current_file_dir)  # /home/attorney/TANGAMAKURU/backend
    base_dir = os.path.dirname(backend_dir)  # /home/attorney/TANGAMAKURU
    
    # Define template and static directories FIRST
    template_dir = os.path.join(base_dir, 'frontend', 'templates')
    static_dir = os.path.join(base_dir, 'frontend', 'static')
    
    print(f"DEBUG: Current file: {__file__}")
    print(f"DEBUG: Base dir: {base_dir}")
    print(f"DEBUG: Template dir: {template_dir}")
    print(f"DEBUG: Template exists: {os.path.exists(template_dir)}")
    
    if not os.path.exists(template_dir):
        print(f"ERROR: Template directory not found: {template_dir}")
        print(f"Looking for: login.html at {os.path.join(template_dir, 'login.html')}")
    
    # Create app with the directories
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)

    # Load environment variables
    load_dotenv()

    # Configuration
    app.config['SECRET_KEY'] = os.getenv(
        'SECRET_KEY', 'dev-secret-key-change-in-production'
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'postgresql://tangamakuru_user:secure_password_123@localhost/tangamakuru_db',
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Session timeout configuration
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
    app.config['SESSION_REFRESH_EACH_REQUEST'] = False
    app.config['SESSION_COOKIE_NAME'] = 'tangamakuru_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Email configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    # Initialize mail
    mail = Mail(app)

    # Make mail available to the app
    app.mail = mail

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Configure login manager
    login_manager.login_view = 'frontend.login'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Register officer blueprint
    from .routes.officer import officer_bp
    app.register_blueprint(officer_bp)

    # Import models so Flask-Migrate can detect them
    from . import models  # noqa: F401

    # Register reports blueprint
    from .routes.reports import reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    # Register frontend blueprint
    from .routes.frontend import frontend_bp
    app.register_blueprint(frontend_bp)

    # Register admin blueprint
    from .routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    # Register super admin blueprint
    from .routes.super_admin import super_admin_bp
    app.register_blueprint(super_admin_bp)

    # Initialize session timeout middleware
    from .middleware import init_session_timeout
    init_session_timeout(app)
    
    # Register custom template filters
    try:
        from .template_filters import timeago_filter
        app.jinja_env.filters['timeago'] = timeago_filter
        print("✓ Registered timeago filter")
    except ImportError:
        print("⚠️ timeago filter not found - install if needed")
    except Exception as e:
        print(f"⚠️ Could not register timeago filter: {e}")

    # Health check route
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy', 'service': 'TANGAMAKURU API'})

    # Context processor MUST come BEFORE return app
    @app.context_processor
    def inject_notification_counts():
        """Inject notification counts into all templates"""
        from flask import has_request_context, session
        
        # Only run if we're in an active request context
        if not has_request_context():
            return {'notification_count': 0, 'announcement_count': 0}
        
        from app.models import Notification
        
        counts = {
            'notification_count': 0,
            'announcement_count': 0
        }
        
        if 'user' in session:
            user_id = session['user']['id']
            user_role = session['user']['role']
            
            # Regular notifications count
            counts['notification_count'] = Notification.query.filter_by(
                user_id=user_id, 
                is_read=False
            ).count()
            
            # For officers, also get announcement notifications count
            if user_role == 'officer':
                counts['announcement_count'] = Notification.query.filter(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.title.like('📢%')
                ).count()
        
        return counts

    return app
