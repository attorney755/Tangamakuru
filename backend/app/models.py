from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

from datetime import datetime, timezone

# Helper function for database default times
def utc_now():
    """Returns current UTC time - works with SQLAlchemy default"""
    return datetime.now(timezone.utc)

# /home/attorney/TANGAMAKURU/backend/app/models.py - Add to User class

class User(UserMixin, db.Model):
    """User model for all roles (Citizen, Officer, Admin)"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    phone = db.Column(db.String(20))
    
    # Role-based fields
    role = db.Column(db.String(20), nullable=False, default='citizen')  # 'citizen', 'officer', 'admin', 'super_admin', 'pending_officer'
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)  # For email verification
    is_approved = db.Column(db.Boolean, default=False)  # For officer approval
    approval_status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'denied'
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    denied_reason = db.Column(db.Text)
    
    # Location fields (for citizens and officers)
    province = db.Column(db.String(64))
    district = db.Column(db.String(64))
    sector = db.Column(db.String(64))
    cell = db.Column(db.String(64))
    village = db.Column(db.String(64))
    
    # Officer specific fields
    officer_id = db.Column(db.String(50), unique=True)
    department = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Notification preferences
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    
    # For super admin tracking
    deactivation_reason = db.Column(db.Text)
    deactivated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    deactivated_at = db.Column(db.DateTime)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relationships
    approved_by_user = db.relationship('User', foreign_keys=[approved_by], remote_side=[id])
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def __repr__(self):
        return f'<User {self.email} - {self.role}>'
    
    # Relationships (add these at the end of the class)
    submitted_reports = db.relationship('Report', 
                                       foreign_keys='Report.user_id',
                                       backref='reporter',
                                       lazy=True)
    
    assigned_reports = db.relationship('Report',
                                      foreign_keys='Report.assigned_officer_id',
                                      backref='assigned_officer',
                                      lazy=True)


class Media(db.Model):
    """Media model for storing evidence images"""
    __tablename__ = 'media'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # image/jpeg, image/png, etc.
    file_size = db.Column(db.Integer)  # in bytes
    
    # Relationships
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Media {self.filename}>'


class Report(db.Model):
    """Report model for crime/incident reports"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(20), unique=True, nullable=False)  # Format: REP-2024-001
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # theft, assault, corruption, etc.
    incident_date = db.Column(db.Date, nullable=False)
    report_type = db.Column(db.String(10), nullable=False, default='crime')  # 'crime' or 'claim'
    
    # Location details
    province = db.Column(db.String(64), nullable=False)
    district = db.Column(db.String(64), nullable=False)
    sector = db.Column(db.String(64), nullable=False)
    cell = db.Column(db.String(64), nullable=False)
    village = db.Column(db.String(64), nullable=False)
    specific_location = db.Column(db.String(200))  # e.g., "Near market"
    pending_officer_request = db.Column(db.Text)  # Store pending information request from officer to citizen
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, resolved, cancelled
    priority = db.Column(db.String(10), default='medium')  # low, medium, high, urgent
    
    # Media
    image_url = db.Column(db.String(500))  # Path to uploaded image
    video_url = db.Column(db.String(500))  # Path to uploaded video
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Officer assigned to case
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Additional fields
    is_anonymous = db.Column(db.Boolean, default=False)
    witness_info = db.Column(db.Text)
    evidence_details = db.Column(db.Text)

     # Add officer_notes here (for storing officer comments/updates)
    officer_notes = db.Column(db.Text)  # Store officer comments and status updates
    
    # Media relationship
    media_files = db.relationship('Media', backref='report', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Report {self.report_id}: {self.title}>'
    
    def generate_report_id(self):
        """Generate unique report ID: REP-YYYY-XXX"""
        year = datetime.now().year
        # Get the last report number for this year
        last_report = Report.query.filter(
            Report.report_id.like(f'REP-{year}-%')
        ).order_by(Report.id.desc()).first()
        
        if last_report:
            last_num = int(last_report.report_id.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'REP-{year}-{new_num:03d}'
    
class Notification(db.Model):
    """Notification model for system notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info')  # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(500))  # Optional link to related page
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title} for User {self.user_id}>'
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        db.session.commit()
    
    @classmethod
    def create_notification(cls, user_id, title, message, notification_type='info', link=None):
        """Create a new notification"""
        notification = cls(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @classmethod
    def get_unread_count(cls, user_id):
        """Get unread notifications count for a user"""
        return cls.query.filter_by(user_id=user_id, is_read=False).count()  

class Message(db.Model):
    """Messages between admin and officers about cases"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    report = db.relationship('Report', backref=db.backref('messages', lazy=True, cascade='all, delete-orphan'))
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    
    def __repr__(self):
        return f'<Message {self.id}: {self.message[:30]} for Report {self.report_id}>'
    
    def mark_as_read(self):
        """Mark message as read"""
        self.is_read = True
        db.session.commit()
    
    @classmethod
    def get_unread_count(cls, user_id):
        """Get unread messages count for a user"""
        return cls.query.filter_by(receiver_id=user_id, is_read=False).count()
    
    @classmethod
    def get_conversation(cls, report_id, user_id):
        """Get all messages for a specific report between admin and officer"""
        return cls.query.filter_by(report_id=report_id).order_by(cls.created_at.asc()).all()      

class Announcement(db.Model):
    """Announcements for officers from admin"""
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # normal, important, urgent
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For targeting specific sectors (null means all sectors)
    target_sector = db.Column(db.String(64), nullable=True)
    
    # NEW: Target audience - 'officers', 'citizens', or 'all'
    target_audience = db.Column(db.String(20), default='officers')
    
    # Relationship
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<Announcement {self.title}>'
    
    @classmethod
    def get_active_announcements(cls, user_role=None, sector=None):
        """Get active announcements based on user role and sector"""
        query = cls.query.order_by(cls.created_at.desc())
    
    # Filter by audience if role is provided
        if user_role == 'officer':
            query = query.filter(cls.target_audience.in_(['officers', 'all']))
        elif user_role == 'citizen':
            query = query.filter(cls.target_audience.in_(['citizens', 'all']))
    
    # Filter by sector if provided
        if sector:
            query = query.filter(
            (cls.target_sector.is_(None)) | (cls.target_sector == sector)
        )
    
        return query.all()

class UserAnnouncement(db.Model):
    """Announcement copies saved for each user"""
    __tablename__ = 'user_announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    announcement_id = db.Column(db.Integer)  # Remove ForeignKey, just store the ID
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    # Remove the announcement relationship since we're not using FK
    
    def __repr__(self):
        return f'<UserAnnouncement {self.id}: {self.title} for User {self.user_id}>'
    
    def mark_as_read(self):
        """Mark announcement as read"""
        self.is_read = True
        db.session.commit()
    
    @classmethod
    def get_unread_count(cls, user_id):
        """Get unread announcements count for a user"""
        return cls.query.filter_by(user_id=user_id, is_read=False).count()       
    
    @classmethod
    def get_unread_count(cls, user_id, sector=None):
        """Get count of unread announcements for a user"""
        from app.models import Notification
        # This is handled by notifications, so we'll return 0
        # The actual count is in notifications
        return 0
    
    @classmethod
    def get_unread_count_for_officer(cls, officer_id, sector=None):
        """Get count of unread announcements for an officer"""
        from app.models import Notification
        
        # Count notifications about announcements that are unread
        return Notification.query.filter_by(
            user_id=officer_id,
            is_read=False,
            title__like='📢%'  # Notifications about announcements start with 📢
        ).count()

@login_manager.user_loader
def load_user(user_id):
    """Callback for Flask-Login to reload user object"""
    return User.query.get(int(user_id))

# /home/attorney/TANGAMAKURU/backend/app/models.py - Add this new model

class PendingApproval(db.Model):
    """Track pending officer approvals"""
    __tablename__ = 'pending_approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email_type = db.Column(db.String(20), nullable=False)  # 'government' or 'personal'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'denied'
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    denial_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    officer = db.relationship('User', foreign_keys=[officer_id], backref='pending_approvals')
    admin = db.relationship('User', foreign_keys=[admin_id])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def __repr__(self):
        return f'<PendingApproval {self.id}: Officer {self.officer_id}>'

