from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash
from app import db
from app.models import User, Announcement
from datetime import datetime, timedelta
from functools import wraps

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/super-admin')

def super_admin_required(f):
    """Decorator to check if user is super admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user:
            flash('Please login first', 'warning')
            return redirect(url_for('frontend.login'))
        
        if user.get('role') != 'super_admin':
            flash('Access denied. Super Admin privileges required.', 'error')
            return redirect(url_for('frontend.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@super_admin_bp.route('/dashboard')
@super_admin_required
def dashboard():
    """Super Admin dashboard - exclude soft-deleted admins"""
    user = session.get('user')
    
    # Get statistics - exclude soft-deleted admins
    total_admins = User.query.filter_by(role='admin').filter(
        (User.is_deleted == False) | (User.is_deleted.is_(None))
    ).count()
    
    total_officers = User.query.filter_by(role='officer').count()
    total_citizens = User.query.filter_by(role='citizen').count()
    
    # Recent admins created - exclude soft-deleted
    recent_admins = User.query.filter_by(role='admin').filter(
        (User.is_deleted == False) | (User.is_deleted.is_(None))
    ).order_by(User.created_at.desc()).limit(5).all()
    
    # Get announcements count
    from app.models import Announcement
    announcements_count = Announcement.query.count()
    
    stats = {
        'total_admins': total_admins,
        'total_officers': total_officers,
        'total_citizens': total_citizens
    }
    
    return render_template('super_admin/dashboard.html',
                         user=user,
                         stats=stats,
                         recent_admins=recent_admins,
                         announcements_count=announcements_count)

@super_admin_bp.route('/admins')
@super_admin_required
def list_admins():
    """List all admin accounts (excluding soft-deleted)"""
    admins = User.query.filter_by(role='admin').filter(
        (User.is_deleted == False) | (User.is_deleted.is_(None))
    ).all()
    return render_template('super_admin/admins.html', 
                         user=session.get('user'),
                         admins=admins)

@super_admin_bp.route('/admins/create', methods=['GET', 'POST'])
@super_admin_required
def create_admin():
    """Create a new admin account"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            # Validate required fields
            required = ['email', 'first_name', 'last_name', 'sector']
            for field in required:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            # Check if user exists
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already exists'}), 409
            
            # Generate random password
            import secrets
            import string
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            
            # Create admin
            admin = User(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data.get('phone', ''),
                role='admin',
                province=data.get('province', 'Kigali City'),
                district=data.get('district', ''),
                sector=data['sector'],
                cell=data.get('cell', ''),
                village=data.get('village', ''),
                is_active=True,
                is_verified=True
            )
            
            admin.set_password(password)
            
            db.session.add(admin)
            db.session.commit()
            
            # Send notification to new admin
            from app.utils.notifications import send_notification
            send_notification(
                user_id=admin.id,
                title='Admin Account Created',
                message=f'Your admin account has been created. Use email: {admin.email} and temporary password: {password}. Please change your password after first login.',
                notification_type='success',
                link='/login'
            )
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Admin created successfully',
                    'admin': {
                        'id': admin.id,
                        'email': admin.email,
                        'name': f"{admin.first_name} {admin.last_name}",
                        'password': password
                    }
                }), 201
            else:
                flash('Admin created successfully', 'success')
                return redirect(url_for('super_admin.list_admins'))
                
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    return render_template('super_admin/create_admin.html', user=session.get('user'))

@super_admin_bp.route('/admins/<int:admin_id>/deactivate', methods=['POST'])
@super_admin_required
def deactivate_admin(admin_id):
    """Deactivate an admin account"""
    try:
        admin = User.query.get_or_404(admin_id)
        if admin.role != 'admin':
            return jsonify({'error': 'User is not an admin'}), 400
        
        admin.is_active = False
        db.session.commit()
        
        # Notify the admin
        from app.utils.notifications import send_notification
        send_notification(
            user_id=admin.id,
            title='Account Deactivated',
            message='Your admin account has been deactivated by the super administrator.',
            notification_type='warning',
            link='/login'
        )
        
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/admins/<int:admin_id>/activate', methods=['POST'])
@super_admin_required
def activate_admin(admin_id):
    """Activate an admin account"""
    try:
        admin = User.query.get_or_404(admin_id)
        if admin.role != 'admin':
            return jsonify({'error': 'User is not an admin'}), 400
        
        admin.is_active = True
        db.session.commit()
        
        # Notify the admin
        from app.utils.notifications import send_notification
        send_notification(
            user_id=admin.id,
            title='Account Activated',
            message='Your admin account has been activated by the super administrator.',
            notification_type='success',
            link='/login'
        )
        
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/announcements')
@super_admin_required
def announcements():
    """System maintenance announcements"""
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('super_admin/announcements.html',
                         user=session.get('user'),
                         announcements=announcements)

@super_admin_bp.route('/announcements/create', methods=['GET', 'POST'])
@super_admin_required
def create_announcement():
    """Create system maintenance announcement"""
    from app.models import Announcement, User, UserAnnouncement
    from app.utils.notifications import send_notification
    from datetime import datetime
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            title = data.get('title')
            content = data.get('content')
            priority = data.get('priority', 'normal')
            target_audience = data.get('target_audience', 'all')
            maintenance_start = data.get('maintenance_start')
            maintenance_end = data.get('maintenance_end')
            
            # Add maintenance info to content if provided
            if maintenance_start and maintenance_end:
                content = f"[SYSTEM MAINTENANCE]\nStart: {maintenance_start}\nEnd: {maintenance_end}\n\n{content}"
            
            announcement = Announcement(
                title=title,
                content=content,
                priority=priority,
                target_audience=target_audience,
                target_sector=None,  # Super admin announcements are system-wide
                created_by=session['user']['id']
            )
            
            db.session.add(announcement)
            db.session.flush()
            
            # Send to all users based on target audience
            if target_audience in ['admins', 'all']:
                admins = User.query.filter_by(role='admin', is_active=True).all()
                for admin in admins:
                    user_announcement = UserAnnouncement(
                        user_id=admin.id,
                        announcement_id=announcement.id,
                        title=title,
                        content=content,
                        priority=priority,
                        is_read=False
                    )
                    db.session.add(user_announcement)
                    
                    send_notification(
                        user_id=admin.id,
                        title=f"🔧 System Maintenance: {title}",
                        message=content[:100] + ('...' if len(content) > 100 else ''),
                        notification_type='warning',
                        link='/admin/announcements'
                    )
            
            if target_audience in ['officers', 'all']:
                officers = User.query.filter_by(role='officer', is_active=True).all()
                for officer in officers:
                    user_announcement = UserAnnouncement(
                        user_id=officer.id,
                        announcement_id=announcement.id,
                        title=title,
                        content=content,
                        priority=priority,
                        is_read=False
                    )
                    db.session.add(user_announcement)
                    
                    send_notification(
                        user_id=officer.id,
                        title=f"🔧 System Maintenance: {title}",
                        message=content[:100] + ('...' if len(content) > 100 else ''),
                        notification_type='warning',
                        link='/officer/announcements'
                    )
            
            if target_audience in ['citizens', 'all']:
                citizens = User.query.filter_by(role='citizen', is_active=True).all()
                for citizen in citizens:
                    send_notification(
                        user_id=citizen.id,
                        title=f"🔧 System Maintenance: {title}",
                        message=content[:100] + ('...' if len(content) > 100 else ''),
                        notification_type='warning',
                        link='/notifications'
                    )
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Announcement published successfully'}), 200
            else:
                flash('Announcement published successfully', 'success')
                return redirect(url_for('super_admin.announcements'))
                
        except Exception as e:
            db.session.rollback()
            print(f"Error creating announcement: {str(e)}")
            if request.is_json:
                return jsonify({'error': str(e)}), 500
            else:
                flash(f'Error: {str(e)}', 'error')
                return render_template('super_admin/create_announcement.html', user=session.get('user'))
    
    return render_template('super_admin/create_announcement.html', user=session.get('user'))

@super_admin_bp.route('/api/announcements/<int:announcement_id>/delete', methods=['DELETE'])
@super_admin_required
def delete_announcement(announcement_id):
    """Delete an announcement"""
    from app.models import Announcement
    
    try:
        announcement = Announcement.query.get(announcement_id)
        
        if not announcement:
            return jsonify({'error': 'Announcement not found'}), 404
        
        db.session.delete(announcement)
        db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/admins/<int:admin_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_admin(admin_id):
    """Edit admin details or reset password"""
    admin = User.query.get_or_404(admin_id)
    
    if admin.role != 'admin':
        flash('User is not an admin', 'error')
        return redirect(url_for('super_admin.list_admins'))
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            # Update basic info
            admin.first_name = data.get('first_name', admin.first_name)
            admin.last_name = data.get('last_name', admin.last_name)
            admin.email = data.get('email', admin.email)
            admin.phone = data.get('phone', admin.phone)
            admin.province = data.get('province', admin.province)
            admin.district = data.get('district', admin.district)
            admin.sector = data.get('sector', admin.sector)
            admin.cell = data.get('cell', admin.cell)
            admin.village = data.get('village', admin.village)
            
            # Reset password if requested
            new_password = None
            if data.get('reset_password'):
                import secrets
                import string
                new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
                admin.set_password(new_password)
            
            db.session.commit()
            
            response_data = {'success': True, 'message': 'Admin updated successfully'}
            if new_password:
                response_data['new_password'] = new_password
                # Send notification to admin
                from app.utils.notifications import send_notification
                send_notification(
                    user_id=admin.id,
                    title='Password Reset',
                    message=f'Your password has been reset by super admin. New password: {new_password}',
                    notification_type='warning',
                    link='/login'
                )
            
            if request.is_json:
                return jsonify(response_data), 200
            else:
                flash('Admin updated successfully', 'success')
                return redirect(url_for('super_admin.list_admins'))
                
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': str(e)}), 500
            else:
                flash(f'Error: {str(e)}', 'error')
                return render_template('super_admin/edit_admin.html', user=session.get('user'), admin=admin)
    
    return render_template('super_admin/edit_admin.html', user=session.get('user'), admin=admin)        


@super_admin_bp.route('/profile')
@super_admin_required
def profile():
    """Super admin profile page"""
    user = session.get('user')
    
    # Get full user data from database
    from app.models import User
    db_user = User.query.get(user['id'])
    
    return render_template('super_admin/profile.html', user=db_user) 

@super_admin_bp.route('/admins/<int:admin_id>/delete', methods=['DELETE'])
@super_admin_required
def delete_admin(admin_id):
    """Soft delete an admin account (deactivate with reason)"""
    try:
        admin = User.query.get_or_404(admin_id)
        if admin.role != 'admin':
            return jsonify({'error': 'User is not an admin'}), 400
        
        # Don't allow deleting yourself
        if admin.id == session['user']['id']:
            return jsonify({'error': 'You cannot delete your own account'}), 400
        
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        deleted_by = data.get('deleted_by', 'Unknown')
        
        # Soft delete - mark as inactive and store deletion info
        admin.is_active = False
        admin.is_deleted = True
        admin.deactivation_reason = reason
        admin.deactivated_by = session['user']['id']
        admin.deactivated_at = datetime.utcnow()
        
        # Also update email to prevent reuse (optional but recommended)
        # admin.email = f"deleted_{admin.id}_{admin.email}"
        
        db.session.commit()
        
        # Send notification to the deleted admin
        from app.utils.notifications import send_notification
        send_notification(
            user_id=admin.id,
            title='Account Deleted',
            message=f'Your admin account has been deleted. Reason: {reason}. For more information, contact your super administrator.',
            notification_type='danger',
            link='/login'
        )
        
        return jsonify({
            'success': True, 
            'message': 'Admin account deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/fix-citizen-status')
@super_admin_required
def fix_citizen_status():
    """Temporary route to fix citizen approval status"""
    from app.models import User
    
    citizens = User.query.filter_by(role='citizen').all()
    count = 0
    for c in citizens:
        if c.approval_status != 'approved' or not c.is_approved:
            c.approval_status = 'approved'
            c.is_approved = True
            count += 1
    
    db.session.commit()
    return f"✅ Fixed {count} citizen accounts. <a href='/super-admin/manage-users'>Go to User Management</a>"


