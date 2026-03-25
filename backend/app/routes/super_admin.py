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
                is_verified=True,
                is_approved=True, 
                approval_status='approved'
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
            
            # Send welcome email to new admin
            try:
                from app.utils.email import send_admin_welcome_email
                send_admin_welcome_email(admin, password)
                print(f"Welcome email sent to {admin.email}")
            except Exception as email_error:
                print(f"Email sending failed: {email_error}")
                # Don't fail admin creation if email fails
            
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
        
        admin_name = admin.get_full_name()
        admin_email = admin.email
        
        admin.is_active = False
        db.session.commit()
        
        # Send notification to the admin
        from app.utils.notifications import send_notification
        send_notification(
            user_id=admin.id,
            title='Account Deactivated',
            message='Your admin account has been deactivated by the super administrator. Please contact your super admin for more information.',
            notification_type='warning',
            link='/login'
        )
        
        # Send email to the admin
        try:
            from app.utils.email import send_admin_deactivation_email
            send_admin_deactivation_email(admin)
            print(f"Deactivation email sent to {admin_email}")
        except Exception as email_error:
            print(f"Deactivation email failed: {email_error}")
        
        return jsonify({'success': True, 'message': f'Admin {admin_name} has been deactivated'}), 200
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
        
        admin_name = admin.get_full_name()
        admin_email = admin.email
        
        admin.is_active = True
        db.session.commit()
        
        # Send notification to the admin
        from app.utils.notifications import send_notification
        send_notification(
            user_id=admin.id,
            title='Account Activated',
            message='Your admin account has been activated by the super administrator. You can now log in.',
            notification_type='success',
            link='/login'
        )
        
        # Send email to the admin
        try:
            from app.utils.email import send_admin_activation_email
            send_admin_activation_email(admin)
            print(f"Activation email sent to {admin_email}")
        except Exception as email_error:
            print(f"Activation email failed: {email_error}")
        
        return jsonify({'success': True, 'message': f'Admin {admin_name} has been activated'}), 200
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

@super_admin_bp.route('/manage-users')
@super_admin_required
def manage_users():
    """User management page for super admin"""
    from app.models import User, Report
    
    users = User.query.all()
    users_data = []
    for user in users:
        report_count = Report.query.filter_by(user_id=user.id).count() if user.role == 'citizen' else 0
        if user.role == 'officer':
            report_count = Report.query.filter_by(assigned_officer_id=user.id).count()
        
        # Determine status
        if user.role == 'officer' and user.approval_status == 'pending':
            status = 'pending'
        elif user.role in ['admin', 'super_admin']:
            # Admins and super admins are always active if is_active is True
            status = 'active' if user.is_active else 'inactive'
        else:
            # Citizens and others
            status = 'active' if user.is_active else 'inactive'
        
        users_data.append({
            'id': user.id,
            'name': user.get_full_name(),
            'email': user.email,
            'role': user.role,
            'sector': user.sector,
            'district': user.district,
            'is_active': user.is_active,
            'approval_status': user.approval_status,
            'status': status,  # This is used in the table
            'created_at': user.created_at,
            'report_count': report_count
        })
    
    return render_template('super_admin/manage_users.html',
                         user=session.get('user'),
                         users=users_data)



@super_admin_bp.route('/api/user/<int:user_id>')
@super_admin_required
def get_user_details(user_id):
    """Get user details for modal"""
    from app.models import User, Report
    
    user = User.query.get_or_404(user_id)
    
    report_count = Report.query.filter_by(user_id=user.id).count() if user.role == 'citizen' else 0
    if user.role == 'officer':
        report_count = Report.query.filter_by(assigned_officer_id=user.id).count()
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'name': user.get_full_name(),
            'email': user.email,
            'phone': user.phone,
            'role': user.role,
            'province': user.province,
            'district': user.district,
            'sector': user.sector,
            'is_active': user.is_active,
            'approval_status': user.approval_status,
            'created_at': user.created_at.strftime('%d %b %Y, %H:%M'),
            'report_count': report_count
        }
    })

  
@super_admin_bp.route('/api/user/<int:user_id>/delete', methods=['DELETE'])
@super_admin_required
def delete_user(user_id):
    """Delete a user and all their associated data"""
    from app.models import User, Report, Media, Message, Notification, PendingApproval
    
    try:
        user = User.query.get_or_404(user_id)
        
        # Don't allow deleting super admin
        if user.role == 'super_admin':
            return jsonify({'error': 'Cannot delete super admin account'}), 400
        
        user_name = user.get_full_name()
        
        print(f"=== DELETING USER: {user_name} (ID: {user_id}) ===")
        
        # Delete in correct order due to foreign keys
        
        # 1. Delete notifications
        Notification.query.filter_by(user_id=user.id).delete()
        
        # 2. Delete messages and media related to reports
        if user.role == 'citizen':
            reports = Report.query.filter_by(user_id=user.id).all()
        elif user.role == 'officer':
            reports = Report.query.filter_by(assigned_officer_id=user.id).all()
        else:
            reports = []
        
        for report in reports:
            Message.query.filter_by(report_id=report.id).delete()
            Media.query.filter_by(report_id=report.id).delete()
            db.session.delete(report)
        
        # 3. Delete pending approvals for officers
        if user.role == 'officer':
            PendingApproval.query.filter_by(officer_id=user.id).delete()
        
        # 4. Finally delete the user
        db.session.delete(user)
        db.session.commit()
        
        response_data = {
            'success': True,
            'message': f'User {user_name} has been deleted successfully'
        }
        print(f"=== RETURNING: {response_data} ===")
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"=== ERROR DELETING USER: {str(e)} ===")
        return jsonify({'error': str(e)}), 500
    
@super_admin_bp.route('/api/user/<int:user_id>/officers-count')
@super_admin_required
def get_admin_officers_count(user_id):
    """Get count of officers under an admin"""
    from app.models import User
    
    user = User.query.get_or_404(user_id)
    if user.role != 'admin':
        return jsonify({'officers_count': 0})
    
    # Count officers in the same district as the admin
    officers = User.query.filter_by(role='officer', district=user.district).count()
    return jsonify({'officers_count': officers})


@super_admin_bp.route('/api/user/<int:user_id>/delete-with-officers', methods=['DELETE'])
@super_admin_required
def delete_user_with_officers(user_id):
    """Delete an admin and all their officers"""
    from app.models import User, Report, Media, Message, Notification, PendingApproval
    
    try:
        user = User.query.get_or_404(user_id)
        
        # Don't allow deleting super admin
        if user.role == 'super_admin':
            return jsonify({'error': 'Cannot delete super admin account'}), 400
        
        # Only admins can have officers
        if user.role != 'admin':
            return jsonify({'error': 'User is not an admin'}), 400
        
        # Don't allow deleting yourself
        if user.id == session['user']['id']:
            return jsonify({'error': 'You cannot delete your own account'}), 400
        
        user_name = user.get_full_name()
        
        # Get all officers under this admin (based on district)
        officers = User.query.filter_by(role='officer', district=user.district).all()
        officer_ids = [o.id for o in officers]
        officer_count = len(officers)
        
        # Delete in correct order for foreign key constraints
        
        # 1. Delete notifications for all officers and admin
        if officer_ids:
            Notification.query.filter(Notification.user_id.in_(officer_ids)).delete(synchronize_session=False)
        Notification.query.filter_by(user_id=user.id).delete()
        
        # 2. Delete reports, messages, media for officers
        for officer in officers:
            reports = Report.query.filter_by(assigned_officer_id=officer.id).all()
            for report in reports:
                # Delete messages for this report
                Message.query.filter_by(report_id=report.id).delete()
                # Delete media for this report
                Media.query.filter_by(report_id=report.id).delete()
                # Delete the report
                db.session.delete(report)
            
            # Delete pending approvals for officer
            PendingApproval.query.filter_by(officer_id=officer.id).delete()
        
        # 3. Delete officers
        if officer_ids:
            User.query.filter(User.id.in_(officer_ids)).delete(synchronize_session=False)
        
        # 4. Delete the admin
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'✅ Admin {user_name} and {officer_count} officer(s) deleted successfully!'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting admin with officers: {str(e)}")
        return jsonify({'error': str(e)}), 500






