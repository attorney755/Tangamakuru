from flask import Blueprint, render_template, jsonify, redirect, url_for, flash, request, session, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length
import json
from app.utils.notifications import get_unread_count
from app import db
from app.models import Report, Media, User
from sqlalchemy import func

frontend_bp = Blueprint('frontend', __name__)

# Simple Login Form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

@frontend_bp.route('/api/stats')
def get_stats():
    """Get real statistics for landing page"""
    try:
        # Count total reports
        total_reports = Report.query.count()
        
        # Count resolved reports (case insensitive)
        resolved_count = Report.query.filter(
            func.lower(Report.status) == 'resolved'
        ).count()
        
        # Count active users (citizens only, active accounts)
        active_users = User.query.filter_by(
            role='citizen',
            is_active=True
        ).count()
        
        # Calculate average response time (you might need to adjust this based on your data)
        # For now, we'll calculate based on resolved reports
        from datetime import timedelta
        resolved_reports = Report.query.filter(
            func.lower(Report.status) == 'resolved'
        ).all()
        
        total_response_time = 0
        response_count = 0
        
        for report in resolved_reports:
            if report.created_at and report.resolved_at:
                # Calculate hours between created and resolved
                delta = report.resolved_at - report.created_at
                hours = delta.total_seconds() / 3600
                total_response_time += hours
                response_count += 1
        
        avg_response_time = round(total_response_time / response_count, 1) if response_count > 0 else 24.0
        
        return jsonify({
            'success': True,
            'stats': {
                'reports': total_reports,
                'resolved': resolved_count,
                'users': active_users,
                'response_time': avg_response_time
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching stats: {str(e)}")
        return jsonify({
            'success': False,
            'stats': {
                'reports': 0,
                'resolved': 0,
                'users': 0,
                'response_time': 0
            }
        }), 500    

@frontend_bp.route('/')
def index():
    """Landing page - main website"""
    return render_template('landing.html')

@frontend_bp.route('/officer/register')
def officer_register_page():
    """Officer registration page"""
    # Check if user is already logged in
    if session.get('user'):
        flash('You are already logged in', 'info')
        return redirect(url_for('frontend.dashboard'))
    
    return render_template('officer_register.html')

@frontend_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    form = LoginForm()
    
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        try:
            from app.models import User
            
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                # Check if user is soft deleted
                if hasattr(user, 'is_deleted') and user.is_deleted:
                    reason = user.deactivation_reason or 'No specific reason provided'
                    return render_template('login.html', 
                                         form=form,
                                         deactivated=True,
                                         deactivation_reason=reason,
                                         deactivation_type='deleted')
                
                # Check if user is deactivated (but not deleted)
                if not user.is_active:
                    if user.role == 'officer' and user.approval_status == 'pending':
                        flash('Your account is pending approval. Please check your notifications for updates.', 'info')
                        session.permanent = True  # Set session as permanent
                        session['pending_user'] = {
                            'id': user.id,
                            'email': user.email,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'role': 'pending_officer'
                        }
                        return redirect(url_for('frontend.pending_officer_notifications'))
                    else:
                        reason = getattr(user, 'deactivation_reason', 'No specific reason provided')
                        return render_template('login.html',
                                             form=form,
                                             deactivated=True,
                                             deactivation_reason=reason,
                                             deactivation_type='deactivated')
                
                # Store user data in session with permanent flag
                user_data = {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'role': user.role,
                    'phone': user.phone,
                    'province': user.province,
                    'district': user.district,
                    'sector': user.sector
                }
                
                session.permanent = True  # This enables the timeout
                session['user'] = user_data
                
                # Check if this is a timeout redirect (coming from session expiry)
                timeout = request.args.get('timeout', '0')
                if timeout == '1':
                    flash('You have been logged out due to inactivity.', 'info')
                
                flash('Login successful!', 'success')
                
                # Role-based redirect
                if user.role == 'super_admin':
                    return redirect(url_for('super_admin.dashboard'))
                elif user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user.role == 'officer':
                    return redirect(url_for('officer.dashboard'))
                else:
                    return redirect(url_for('frontend.dashboard'))
                
            else:
                flash('Invalid email or password', 'error')
                form.email.errors = []
                form.password.errors = []
                
        except Exception as e:
            flash('Login error: Please try again.', 'error')
            form.email.errors = []
            form.password.errors = []
    
    return render_template('login.html', form=form)

@frontend_bp.route('/register')
def register():
    """Registration page"""
    return render_template('register.html')


@frontend_bp.route('/dashboard')
def dashboard():
    """User dashboard"""
    # Check if user is logged in
    user = session.get('user')
    if not user:
        flash('Please login first', 'warning')
        return redirect(url_for('frontend.login'))
    
    # Import models
    from app.models import Report, User
    
    # Get the actual user from database
    db_user = User.query.get(user['id'])
    if not db_user:
        flash('User not found', 'error')
        return redirect(url_for('frontend.logout'))
    
    # Fetch actual reports from database for this user
    user_reports = []
    if user['role'] == 'citizen':
        user_reports = Report.query.filter_by(user_id=user['id']).order_by(Report.created_at.desc()).all()
    elif user['role'] == 'officer':
        user_reports = Report.query.filter_by(assigned_officer_id=user['id']).order_by(Report.created_at.desc()).all()
    elif user['role'] == 'admin':
        user_reports = Report.query.order_by(Report.created_at.desc()).all()
    
    # Calculate real stats from database
    if user_reports:
        total_reports = len(user_reports)
        pending = len([r for r in user_reports if r.status.lower() == 'pending'])
        in_progress = len([r for r in user_reports if r.status.lower() in ['in_progress', 'in progress']])
        resolved = len([r for r in user_reports if r.status.lower() == 'resolved'])
    else:
        total_reports = pending = in_progress = resolved = 0
    
    stats = {
        'total_reports': total_reports,
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved
    }
    
    # Format reports for template (show only 5 most recent)
    reports = []
    for report in user_reports[:5]:
        reports.append({
            'id': report.id,  # Use report.id for the URL, not report.report_id
            'report_id': report.report_id,  # Display ID like REP-2026-001
            'title': report.title,
            'category': report.category,
            'status': report.status.upper(),
            'priority': report.priority.upper(),
            'date': report.created_at.strftime('%d %b %Y') if report.created_at else 'N/A'
        })
    
    # Update user data in session with real data from database
    session['user'] = {
        'id': db_user.id,
        'first_name': db_user.first_name,
        'last_name': db_user.last_name,
        'email': db_user.email,
        'role': db_user.role,
        'phone': db_user.phone,
        'province': db_user.province,
        'district': db_user.district,
        'sector': db_user.sector
    }
    
    return render_template('dashboard.html', 
                          user=session['user'], 
                          stats=stats, 
                          reports=reports)

@frontend_bp.route('/reports')
def reports():
    """User's reports page - Show ALL reports"""
    user = session.get('user')
    if not user:
        flash('Please login first', 'warning')
        return redirect(url_for('frontend.login'))
    
    # Import models
    from app.models import Report, User
    
    # Get the actual user from database
    db_user = User.query.get(user['id'])
    
    # Fetch ALL reports from database for this user
    user_reports = []
    if user['role'] == 'citizen':
        user_reports = Report.query.filter_by(user_id=user['id']).order_by(Report.created_at.desc()).all()
    elif user['role'] == 'officer':
        user_reports = Report.query.filter_by(assigned_officer_id=user['id']).order_by(Report.created_at.desc()).all()
    elif user['role'] == 'admin':
        user_reports = Report.query.order_by(Report.created_at.desc()).all()
    
    # Format reports for template
    all_reports = []
    for report in user_reports:
        all_reports.append({
            'id': report.id,  # Use report.id for the URL
            'report_id': report.report_id,  # Display ID like REP-2026-001
            'title': report.title,
            'category': report.category,
            'status': report.status.upper(),
            'priority': report.priority.upper(),
            'date': report.created_at.strftime('%d %b %Y') if report.created_at else 'N/A',
            'description': report.description[:100] + '...' if report.description and len(report.description) > 100 else (report.description or 'No description')
        })
    
    return render_template('reports.html', 
                          user=session['user'], 
                          reports=all_reports,
                          total_reports=len(all_reports))


@frontend_bp.route('/submit-report')
def submit_report_page():
    """Submit report page"""
    user = session.get('user')
    if not user:
        flash('Please login first', 'warning')
        return redirect(url_for('frontend.login'))
    
    return render_template('submit_report_real.html', user=user)


# Update the view_report route in frontend.py:
@frontend_bp.route('/reports/<int:report_id>')
def view_report(report_id):
    """View single report page"""
    user = session.get('user')
    if not user:
        flash('Please login first', 'warning')
        return redirect(url_for('frontend.login'))
    
    # Import models
    from app.models import Report
    
    # Fetch the report
    report = Report.query.get(report_id)
    
    if not report:
        flash('Report not found', 'error')
        return redirect(url_for('frontend.reports'))
    
    # Check if user has permission to view this report
    if user['role'] == 'citizen' and report.user_id != user['id']:
        flash('You are not authorized to view this report', 'error')
        return redirect(url_for('frontend.reports'))
    
    # Format report data
    report_data = {
        'id': report.id,
        'report_id': report.report_id,
        'title': report.title,
        'description': report.description,
        'category': report.category,
        'status': report.status.upper(),
        'priority': report.priority.upper(),
        'incident_date': report.incident_date.strftime('%d %b %Y') if report.incident_date else 'N/A',
        'created_at': report.created_at.strftime('%d %b %Y %H:%M') if report.created_at else 'N/A',
        'province': report.province,
        'district': report.district,
        'sector': report.sector,
        'cell': report.cell,
        'village': report.village,
        'specific_location': report.specific_location,
        'is_anonymous': report.is_anonymous,
        'image_url': report.image_url,
        'pending_officer_request': report.pending_officer_request if hasattr(report, 'pending_officer_request') else None
    }
    
    return render_template('view_report.html', user=user, report=report_data)

@frontend_bp.route('/view-report/<int:report_id>')
def view_report_page(report_id):
    """View single report page - alternative route to avoid API conflict"""
    print(f"DEBUG: view_report_page called with report_id={report_id}")  # Add this
    user = session.get('user')
    print(f"DEBUG: user from session: {user}")  # Add this
    if not user:
        flash('Please login first', 'warning')
        return redirect(url_for('frontend.login'))
    
    # Import models
    from app.models import Report, Media, User
    import re
    
    # Fetch the report
    report = Report.query.get(report_id)
    print(f"DEBUG: report found: {report is not None}")  # Add this
    
    if not report:
        flash('Report not found', 'error')
        return redirect(url_for('frontend.reports'))
    
    # Check if user has permission to view this report
    if user['role'] == 'citizen' and report.user_id != user['id']:
        flash('You are not authorized to view this report', 'error')
        return redirect(url_for('frontend.reports'))
    
    # Check if there's a pending officer request
    officer_request = report.pending_officer_request if hasattr(report, 'pending_officer_request') else None
    
    # Get media files for this report
    media_files = Media.query.filter_by(report_id=report.id).all()
    print(f"DEBUG: Found {len(media_files)} media files for report {report.id}")  # Add this
    
    # Parse officer notes into comments for citizens
    officer_comments = []
    if report.officer_notes:
        # Split by double newline
        raw_comments = report.officer_notes.split('\n\n')
        for raw in raw_comments:
            if raw.strip() and 'RESOLUTION REPORT' not in raw:
                # Try to parse timestamp and comment
                parts = raw.strip().split(' - ', 1)
                if len(parts) == 2:
                    timestamp, content = parts
                    # Try to extract officer name and comment
                    if ': ' in content:
                        officer_name, comment = content.split(': ', 1)
                    else:
                        officer_name = 'Officer'
                        comment = content
                    
                    officer_comments.append({
                        'officer': officer_name,
                        'comment': comment,
                        'timestamp': timestamp
                    })
    
    # Format report data for template
    report_data = {
        'id': report.id,
        'report_id': report.report_id,
        'title': report.title,
        'description': report.description,
        'category': report.category,
        'status': report.status.upper(),
        'priority': report.priority.upper(),
        'incident_date': report.incident_date.strftime('%d %b %Y') if report.incident_date else 'N/A',
        'created_at': report.created_at.strftime('%d %b %Y %H:%M') if report.created_at else 'N/A',
        'province': report.province,
        'district': report.district,
        'sector': report.sector,
        'cell': report.cell,
        'village': report.village,
        'specific_location': report.specific_location,
        'is_anonymous': report.is_anonymous,
        'image_url': report.image_url,
        'pending_officer_request': report.pending_officer_request  # ADD THIS LINE
    }
    
    # DEBUG: Print what's in report_data
    print(f"DEBUG: pending_officer_request in report_data: {report_data.get('pending_officer_request')}")
    
    return render_template('view_report.html', 
                         user=user, 
                         report=report_data,
                         officer_request=officer_request,
                         media_files=media_files,
                         officer_comments=officer_comments)


@frontend_bp.route('/api/profile/update', methods=['POST'])
def update_profile():
    """Update user profile"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    
    try:
        from app.models import User
        db_user = User.query.get(user['id'])
        
        # Update fields
        db_user.first_name = data.get('first_name', db_user.first_name)
        db_user.last_name = data.get('last_name', db_user.last_name)
        db_user.phone = data.get('phone', db_user.phone)
        db_user.province = data.get('province', db_user.province)
        db_user.district = data.get('district', db_user.district)
        db_user.sector = data.get('sector', db_user.sector)
        db_user.cell = data.get('cell', db_user.cell)
        db_user.village = data.get('village', db_user.village)
        
        db.session.commit()
        
        # Update session
        session['user'] = {
            'id': db_user.id,
            'first_name': db_user.first_name,
            'last_name': db_user.last_name,
            'email': db_user.email,
            'role': db_user.role,
            'phone': db_user.phone,
            'province': db_user.province,
            'district': db_user.district,
            'sector': db_user.sector
        }
        
        return jsonify({'success': True, 'user': session['user']}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@frontend_bp.route('/api/profile/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    
    try:
        from app.models import User
        from werkzeug.security import check_password_hash
        
        db_user = User.query.get(user['id'])
        
        # Verify current password
        if not check_password_hash(db_user.password_hash, data.get('current_password', '')):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Set new password
        db_user.set_password(data.get('new_password'))
        db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@frontend_bp.route('/profile')
def profile():
    """User profile page"""
    user = session.get('user')
    if not user:
        flash('Please login first', 'warning')
        return redirect(url_for('frontend.login'))
    
    return render_template('profile.html', user=user)

@frontend_bp.route('/logout')
def logout():
    """Logout page"""
    # Clear all session data
    session.clear()
    
    # Check if this was a timeout logout
    timeout = request.args.get('timeout', '0')
    if timeout == '1':
        flash('You have been logged out due to inactivity.', 'info')
    else:
        flash('You have been logged out. Please login again.', 'info')
    
    # Redirect to login page instead of home
    return redirect(url_for('frontend.login'))

@frontend_bp.route('/test')
def test():
    """Test endpoint"""
    return jsonify({'message': 'Frontend is working'})

@frontend_bp.route('/notifications')
def notifications():
    """User notifications page - accessible to pending officers too"""
    # Check for both regular users and pending users
    user = session.get('user')
    pending_user = session.get('pending_user')
    
    if not user and not pending_user:
        flash('Please login first', 'warning')
        return redirect(url_for('frontend.login'))
    
    # Get the user ID from either session
    user_id = None
    user_role = 'guest'
    user_name = ''
    
    if user:
        user_id = user['id']
        user_role = user['role']
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    elif pending_user:
        user_id = pending_user['id']
        user_role = 'pending_officer'
        user_name = f"{pending_user.get('first_name', '')} {pending_user.get('last_name', '')}".strip()
    
    # Get real notifications from database
    from app.models import Notification
    from app.utils.notifications import get_user_notifications
    
    notifications_list = get_user_notifications(user_id, limit=50)
    
    # Format for template
    formatted_notifications = []
    pending_approval = False
    
    for n in notifications_list:
        formatted_notifications.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'date': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'read': n.is_read,
            'type': n.notification_type,
            'link': n.link
        })
        
        # Check if there's a pending approval notification
        if 'pending approval' in n.title.lower() or 'pending approval' in n.message.lower():
            pending_approval = True
    
    # Also check the user's own status for pending approval
    if user_role == 'pending_officer':
        pending_approval = True
    
    # Get unread count for the template
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    
    # Count approval notifications
    approval_count = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.title.like('%Pending%') | Notification.title.like('%Approved%') | Notification.title.like('%Denied%')
    ).count()
    
    return render_template('notifications.html', 
                         user=user or pending_user,
                         notifications=formatted_notifications,
                         unread_count=unread_count,
                         approval_count=approval_count,
                         pending_approval=pending_approval,
                         user_role=user_role)

@frontend_bp.route('/pending-logout')
def pending_logout():
    """Logout for pending users"""
    session.pop('pending_user', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('frontend.login'))                         

@frontend_bp.route('/api/notifications/unread-count')
def api_unread_count():
    """API endpoint for unread notifications count"""
    user = session.get('user')
    if not user:
        return jsonify({'count': 0}), 200
    
    from app.utils.notifications import get_unread_count
    count = get_unread_count(user['id'])
    return jsonify({'count': count}), 200

@frontend_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def api_mark_read(notification_id):
    """Mark a notification as read"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    from app.utils.notifications import mark_as_read
    success = mark_as_read(notification_id)
    
    if success:
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Notification not found'}), 404

@frontend_bp.route('/api/notifications/<int:notification_id>/delete', methods=['DELETE'])
def api_delete_notification(notification_id):
    """Delete a notification"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    from app.utils.notifications import delete_notification
    success = delete_notification(notification_id, user['id'])
    
    if success:
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Notification not found'}), 404

@frontend_bp.route('/api/notifications/<int:notification_id>/delete', methods=['DELETE'])
def delete_notification(notification_id):
    """Delete a specific notification"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    from app.utils.notifications import delete_notification
    success = delete_notification(notification_id, user['id'])
    
    if success:
        return jsonify({'success': True, 'message': 'Notification deleted successfully'}), 200
    return jsonify({'error': 'Notification not found'}), 404

@frontend_bp.route('/api/notifications/delete-read-all', methods=['DELETE'])
def api_delete_all_read():
    """Delete all read notifications"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    from app.utils.notifications import delete_all_read_notifications
    delete_all_read_notifications(user['id'])
    
    return jsonify({'success': True}), 200

@frontend_bp.route('/api/notifications/delete-all', methods=['DELETE'])
def delete_all_notifications():
    """Delete all notifications for current user (regardless of read status)"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    from app.models import Notification
    
    try:
        # Delete ALL notifications for this user
        Notification.query.filter_by(user_id=user['id']).delete()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'All notifications deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500    

@frontend_bp.route('/api/notifications/read-all', methods=['POST'])
def api_mark_all_read():
    """Mark all notifications as read"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    from app.utils.notifications import mark_all_as_read
    mark_all_as_read(user['id'])
    
    return jsonify({'success': True}), 200

@frontend_bp.route('/announcements')
def citizen_announcements():
    """View announcements for citizens"""
    user = session.get('user')
    if not user:
        flash('Please login first', 'warning')
        return redirect(url_for('frontend.login'))
    
    from app.models import Announcement
    announcements = Announcement.get_active_announcements(user_role='citizen')
    
    return render_template('citizen/announcements.html',
                         user=user,
                         announcements=announcements)

from datetime import datetime

@frontend_bp.context_processor
def utility_processor():
    return {'now': datetime.now}

@frontend_bp.route('/citizen/api/add-info', methods=['POST'])
def add_additional_info():
    """Citizen adds additional information to a report"""
    try:
        from app.models import Report, Media, User
        from datetime import datetime
        import os
        
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Not logged in'}), 401
        
        report_id = request.form.get('report_id')
        additional_text = request.form.get('additional_text', '')
        files = request.files.getlist('additional_evidence')
        
        report = Report.query.get_or_404(report_id)
        
        # Verify this report belongs to the user
        if report.user_id != user['id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check if report is resolved
        if report.status == 'resolved':
            return jsonify({'error': 'Cannot add information to a resolved report'}), 400
        
        # Update description with additional info
        if additional_text:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            additional_note = f"\n\n[Additional Information - {timestamp}]\n{additional_text}"
            report.description += additional_note
        
        # Handle file uploads
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        for file in files:
            if file and file.filename:
                from app.routes.reports import allowed_file, generate_unique_filename
                
                if allowed_file(file.filename):
                    filename = generate_unique_filename(file.filename, report.report_id)
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    
                    media = Media(
                        filename=filename,
                        file_path=file_path,
                        file_type=file.content_type,
                        file_size=os.path.getsize(file_path),
                        report_id=report.id
                    )
                    db.session.add(media)
        
        # Clear the pending officer request
        if hasattr(report, 'pending_officer_request'):
            report.pending_officer_request = None
            # After clearing the request
            print(f"Cleared pending request for report {report.id}")
        
        # Notify the assigned officer if any
        if report.assigned_officer_id:
            from app.utils.notifications import send_notification
            citizen = User.query.get(user['id'])
            send_notification(
                user_id=report.assigned_officer_id,
                title=f"📝 Additional Information Received - {report.report_id}",
                message=f"Citizen {citizen.first_name} {citizen.last_name} has provided additional information for this case.",
                notification_type='info',
                link=f'/officer/incident/{report.id}'
            )
        
        db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding additional info: {str(e)}")
        return jsonify({'error': str(e)}), 500


@frontend_bp.route('/pending-officer/notifications')
def pending_officer_notifications():
    """Special notifications page for pending officers"""
    pending_user = session.get('pending_user')
    
    if not pending_user:
        flash('Please login first', 'warning')
        return redirect(url_for('frontend.login'))
    
    # Get the actual officer from database
    from app.models import User, Notification
    
    officer = User.query.get(pending_user['id'])
    if not officer:
        session.pop('pending_user', None)
        flash('User not found', 'error')
        return redirect(url_for('frontend.login'))
    
    # Get notifications for this officer
    notifications_list = Notification.query.filter_by(
        user_id=officer.id
    ).order_by(Notification.created_at.desc()).all()
    
    # Format notifications
    formatted_notifications = []
    for n in notifications_list:
        formatted_notifications.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'date': n.created_at.strftime('%d %b %Y, %H:%M'),
            'read': n.is_read,
            'type': n.notification_type
        })
    
    return render_template('pending_officer_notifications.html',
                         officer=officer,
                         notifications=formatted_notifications)


# API endpoints for pending officer notifications
@frontend_bp.route('/api/pending-officer/notifications/<int:notification_id>/read', methods=['POST'])
def pending_officer_mark_read(notification_id):
    """Mark a pending officer notification as read"""
    pending_user = session.get('pending_user')
    
    if not pending_user:
        return jsonify({'error': 'Not authorized'}), 401
    
    from app.utils.notifications import mark_as_read
    success = mark_as_read(notification_id)
    
    if success:
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Notification not found'}), 404


@frontend_bp.route('/api/pending-officer/notifications/read-all', methods=['POST'])
def pending_officer_mark_all_read():
    """Mark all pending officer notifications as read"""
    pending_user = session.get('pending_user')
    
    if not pending_user:
        return jsonify({'error': 'Not authorized'}), 401
    
    from app.utils.notifications import mark_all_as_read
    mark_all_as_read(pending_user['id'])
    
    return jsonify({'success': True}), 200


@frontend_bp.route('/api/pending-officer/notifications/<int:notification_id>/delete', methods=['DELETE'])
def pending_officer_delete_notification(notification_id):
    """Delete a pending officer notification"""
    pending_user = session.get('pending_user')
    
    if not pending_user:
        return jsonify({'error': 'Not authorized'}), 401
    
    from app.utils.notifications import delete_notification
    success = delete_notification(notification_id, pending_user['id'])
    
    if success:
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Notification not found'}), 404


@frontend_bp.route('/api/pending-officer/notifications/delete-all', methods=['DELETE'])
def pending_officer_delete_all():
    """Delete all pending officer notifications"""
    pending_user = session.get('pending_user')
    
    if not pending_user:
        return jsonify({'error': 'Not authorized'}), 401
    
    from app.models import Notification
    
    try:
        Notification.query.filter_by(user_id=pending_user['id']).delete()
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@frontend_bp.route('/api/check-session')
def check_session():
    """Check if user session is still valid"""
    if session.get('user') or session.get('pending_user'):
        return jsonify({'authenticated': True})
    # Return 200 OK with authenticated: false instead of 401
    return jsonify({'authenticated': False})

@frontend_bp.route('/admin/clear-all-test-data')
def clear_all_test_data():
    """Temporary route to delete all test data (citizens and their reports)"""
    from app.models import User, Report, Media, Message
    
    # Check if user is logged in as super admin
    user = session.get('user')
    if not user or user.get('role') != 'super_admin':
        return "Access denied. Super admin only.", 403
    
    # Get all citizen accounts
    citizens = User.query.filter_by(role='citizen').all()
    citizen_ids = [c.id for c in citizens]
    citizen_count = len(citizens)
    
    # Delete in correct order (due to foreign keys)
    # 1. Delete messages related to citizen reports
    for report in Report.query.filter(Report.user_id.in_(citizen_ids)).all():
        Message.query.filter_by(report_id=report.id).delete()
    
    # 2. Delete media related to citizen reports
    for report in Report.query.filter(Report.user_id.in_(citizen_ids)).all():
        Media.query.filter_by(report_id=report.id).delete()
    
    # 3. Delete reports from citizens
    deleted_reports = Report.query.filter(Report.user_id.in_(citizen_ids)).delete()
    
    # 4. Delete citizen accounts
    deleted_citizens = User.query.filter_by(role='citizen').delete()
    
    db.session.commit()
    
    return f"""
    <h2>✅ Cleanup Complete</h2>
    <p>Deleted {deleted_citizens} citizen accounts.</p>
    <p>Deleted {deleted_reports} reports.</p>
    <p>Super admin account preserved: superadmin@gov.rw</p>
    <a href="/">Go to Home</a>
    """

