from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash, make_response
from app import db
from app.models import User, Report
from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import User, Report, Media, Announcement
from app.models import Message
import pytz

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to check if user is admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('frontend.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard - shows ALL reports in admin's district (all sectors)"""
    user = session.get('user')
    
    # Get the admin's district only (ignore sector for reports)
    admin_district = user.get('district')
    
    # Base query for reports in admin's district (ALL sectors)
    reports_query = Report.query
    if admin_district:
        reports_query = reports_query.filter_by(district=admin_district)
    
    # Get statistics filtered by admin's district
    total_reports = reports_query.count()
    pending = reports_query.filter_by(status='pending').count()
    in_progress = reports_query.filter_by(status='in_progress').count()
    resolved = reports_query.filter_by(status='resolved').count()
    unassigned = reports_query.filter_by(assigned_officer_id=None).count()  # ADD THIS
    
    # User stats filtered by admin's district
    officers_query = User.query.filter_by(role='officer')
    if admin_district:
        officers_query = officers_query.filter_by(district=admin_district)
    
    total_officers = officers_query.count()
    active_officers = officers_query.filter_by(is_active=True).count()
    
    citizens_query = User.query.filter_by(role='citizen')
    if admin_district:
        citizens_query = citizens_query.filter_by(district=admin_district)
    
    total_citizens = citizens_query.count()
    new_users = citizens_query.filter(User.created_at >= datetime.now() - timedelta(days=30)).count()
    
    # New reports today in admin's district
    new_today = reports_query.filter(
        Report.created_at >= datetime.now().replace(hour=0, minute=0)
    ).count()
    
    # Recent reports in admin's district (ALL sectors)
    recent_reports = reports_query.order_by(Report.created_at.desc()).limit(10).all()
    reports_data = []
    for r in recent_reports:
        officer = User.query.get(r.assigned_officer_id) if r.assigned_officer_id else None
        reporter = User.query.get(r.user_id)
        reports_data.append({
            'id': r.id,
            'report_id': r.report_id,
            'title': r.title[:50] + '...' if len(r.title) > 50 else r.title,
            'category': r.category,
            'status': r.status,
            'priority': r.priority,
            'assigned_officer': f"{officer.first_name} {officer.last_name}" if officer else None,
            'reporter': f"{reporter.first_name} {reporter.last_name}" if reporter else "Anonymous",
            'created_at': r.created_at.strftime('%Y-%m-%d'),
            'sector': r.sector,
            'is_unassigned': r.assigned_officer_id is None  # Add this flag
        })
    
    # Officers list filtered by admin's district
    officers = officers_query.limit(10).all()
    officers_data = []
    for o in officers:
        assigned_count = Report.query.filter_by(assigned_officer_id=o.id).count()
        officers_data.append({
            'id': o.id,
            'first_name': o.first_name,
            'last_name': o.last_name,
            'email': o.email,
            'sector': o.sector or 'Not assigned',
            'assigned_count': assigned_count,
            'is_active': o.is_active
        })
    
    # Chart data (last 7 days)
    labels = []
    data = []
    for i in range(6, -1, -1):
        date = datetime.now() - timedelta(days=i)
        labels.append(date.strftime('%d %b'))
        count = reports_query.filter(
            func.date(Report.created_at) == date.date()
        ).count()
        data.append(count)
    
    # Category data
    category_query = db.session.query(
        Report.category, func.count(Report.id)
    )
    if admin_district:
        category_query = category_query.filter(Report.district == admin_district)
    
    category_results = category_query.group_by(Report.category).limit(6).all()
    
    if category_results:
        category_labels = [c[0] for c in category_results]
        category_data = [c[1] for c in category_results]
    else:
        category_labels = []
        category_data = []
    
    stats = {
        'total_reports': total_reports,
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved,
        'unassigned': unassigned,  # ADD THIS
        'total_officers': total_officers,
        'active_officers': active_officers,
        'total_citizens': total_citizens,
        'new_users': new_users,
        'new_today': new_today
    }
    
    return render_template('admin/dashboard.html',
                         user=user,
                         stats=stats,
                         recent_reports=reports_data,
                         officers=officers_data,
                         chart_labels=labels,
                         chart_data=data,
                         category_labels=category_labels,
                         category_data=category_data)

@admin_bp.route('/create-officer')
@admin_required
def create_officer_page():
    """Create officer page"""
    return render_template('admin/create_officer.html', user=session.get('user'))

@admin_bp.route('/api/create-officer', methods=['POST'])
@admin_required
def create_officer():
    """API endpoint to create officer"""
    try:
        data = request.get_json()
        
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
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        
        # Create officer
        officer = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone', ''),
            role='officer',
            province=data.get('province', 'Kigali City'),
            district=data.get('district', ''),
            sector=data['sector'],
            cell=data.get('cell', ''),
            village=data.get('village', ''),
            officer_id=data.get('officer_id', ''),
            department=data.get('department', ''),
            is_active=True,
            is_verified=True
        )
        
        officer.set_password(password)
        
        db.session.add(officer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Officer created successfully',
            'officer': {
                'id': officer.id,
                'email': officer.email,
                'name': f"{officer.first_name} {officer.last_name}",
                'password': password  # Only returned once
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/officers')
@admin_required
def officers_list():
    """List all officers in admin's district (all sectors)"""
    user = session.get('user')
    
    # Get admin's district only (ignore sector for officers list)
    admin_district = user.get('district')
    
    # Filter officers by admin's district only (all sectors)
    query = User.query.filter_by(role='officer')
    if admin_district:
        query = query.filter_by(district=admin_district)
    
    officers = query.all()
    officers_data = []
    for o in officers:
        assigned_count = Report.query.filter_by(assigned_officer_id=o.id).count()
        officers_data.append({
            'id': o.id,
            'first_name': o.first_name,
            'last_name': o.last_name,
            'name': f"{o.first_name} {o.last_name}",
            'email': o.email,
            'sector': o.sector or 'Not assigned',
            'assigned_count': assigned_count,
            'assigned': assigned_count,
            'is_active': o.is_active,
            'active': o.is_active
        })
    return render_template('admin/officers.html', 
                         user=session.get('user'), 
                         officers=officers_data)

@admin_bp.route('/profile')
@admin_required
def profile():
    """Admin profile page"""
    user = session.get('user')
    
    # Get full user data from database
    from app.models import User
    db_user = User.query.get(user['id'])
    
    return render_template('admin/profile.html', user=db_user)


@admin_bp.route('/reports')
@admin_required
def all_reports():
    """View all reports in admin's district with optional sector filter"""
    user = session.get('user')
    
    # Get filter parameters
    sector_filter = request.args.get('sector', 'all')
    status_filter = request.args.get('status', 'all')
    
    # Get admin's district
    admin_district = user.get('district')
    
    # Define all sectors for Kigali districts
    kigali_sectors = {
        'Gasabo': ['Bumbogo', 'Gatsata', 'Jabana', 'Kacyiru', 'Kimihurura', 'Kimironko', 'Remera', 'Rusororo', 'Nduba'],
        'Kicukiro': ['Gahanga', 'Gikondo', 'Kagarama', 'Kanombe', 'Kicukiro', 'Masaka', 'Niboye', 'Nyarugunga'],
        'Nyarugenge': ['Gitega', 'Kanyinya', 'Kigali', 'Kimisagara', 'Mageragere', 'Muhima', 'Nyakabanda', 'Nyamirambo']
    }
    
    # Get sectors for the admin's district, or empty list if district not found
    sectors = kigali_sectors.get(admin_district, [])
    
    # Base query for reports in admin's district
    query = Report.query
    if admin_district:
        query = query.filter_by(district=admin_district)
    
    # Get total count before filtering
    total_reports = query.count()
    
    # Apply sector filter if not 'all'
    if sector_filter and sector_filter != 'all':
        query = query.filter_by(sector=sector_filter)
    
    # Apply status filter if not 'all'
    if status_filter and status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Get filtered count
    filtered_count = query.count()
    
    reports = query.order_by(Report.created_at.desc()).all()
    reports_data = []
    for r in reports:
        reporter = User.query.get(r.user_id)
        officer = User.query.get(r.assigned_officer_id) if r.assigned_officer_id else None
        reports_data.append({
            'id': r.id,
            'report_id': r.report_id,
            'title': r.title,
            'category': r.category,
            'status': r.status,
            'priority': r.priority,
            'sector': r.sector,
            'reporter': f"{reporter.first_name} {reporter.last_name}" if reporter else "Anonymous",
            'assigned_to': f"{officer.first_name} {officer.last_name}" if officer else "Unassigned",
            'created_at': r.created_at.strftime('%Y-%m-%d')
        })
    
    return render_template('admin/reports.html', 
                         user=session.get('user'), 
                         reports=reports_data,
                         sectors=sectors,
                         current_sector=sector_filter,
                         current_status=status_filter,
                         total_reports=total_reports,
                         filtered_count=filtered_count,
                         admin_district=admin_district)


@admin_bp.route('/officers/<int:officer_id>')
@admin_required  # Make sure this decorator is present
def view_officer(officer_id):
    """View officer details"""
    officer = User.query.get_or_404(officer_id)
    if officer.role != 'officer':
        flash('User is not an officer', 'error')
        return redirect(url_for('admin.officers_list'))
    
    # Get reports assigned to this officer
    assigned_reports = Report.query.filter_by(assigned_officer_id=officer.id).count()
    resolved_reports = Report.query.filter_by(assigned_officer_id=officer.id, status='resolved').count()
    
    return render_template('admin/view_officer.html', 
                         user=session.get('user'),
                         officer=officer,
                         assigned_reports=assigned_reports,
                         resolved_reports=resolved_reports)

@admin_bp.route('/officers/<int:officer_id>/edit')
@admin_required
def edit_officer_page(officer_id):
    """Edit officer page"""
    officer = User.query.get_or_404(officer_id)
    if officer.role != 'officer':
        flash('User is not an officer', 'error')
        return redirect(url_for('admin.officers_list'))
    
    return render_template('admin/edit_officer.html', 
                         user=session.get('user'),
                         officer=officer)

@admin_bp.route('/api/officers/<int:officer_id>/update', methods=['POST'])
@admin_required
def update_officer(officer_id):
    """Update officer information"""
    try:
        officer = User.query.get_or_404(officer_id)
        data = request.get_json()
        
        # Update fields
        officer.first_name = data.get('first_name', officer.first_name)
        officer.last_name = data.get('last_name', officer.last_name)
        officer.email = data.get('email', officer.email)
        officer.phone = data.get('phone', officer.phone)
        officer.province = data.get('province', officer.province)
        officer.district = data.get('district', officer.district)
        officer.sector = data.get('sector', officer.sector)
        officer.cell = data.get('cell', officer.cell)
        officer.village = data.get('village', officer.village)
        officer.officer_id = data.get('officer_id', officer.officer_id)
        officer.department = data.get('department', officer.department)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Officer updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/officers/<int:officer_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_officer_status(officer_id):
    """Activate or deactivate officer"""
    try:
        officer = User.query.get_or_404(officer_id)
        officer.is_active = not officer.is_active
        db.session.commit()
        
        status = 'activated' if officer.is_active else 'deactivated'
        
        # Send notification to officer
        from app.utils.notifications import send_notification
        send_notification(
            user_id=officer.id,
            title='Account Status Updated',
            message=f'Your account has been {status} by an administrator.',
            notification_type='info' if officer.is_active else 'warning',
            link='/login'
        )
        
        return jsonify({
            'success': True,
            'is_active': officer.is_active,
            'message': f'Officer {status} successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/officers/<int:officer_id>/reset-password', methods=['POST'])
@admin_required
def reset_officer_password(officer_id):
    """Reset officer password"""
    try:
        officer = User.query.get_or_404(officer_id)
        
        # Generate random password
        import secrets
        import string
        new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        
        # Set new password
        officer.set_password(new_password)
        db.session.commit()
        
        # Send notification with new password
        from app.utils.notifications import send_notification
        send_notification(
            user_id=officer.id,
            title='Password Reset',
            message=f'Your password has been reset by an administrator. New password: {new_password}',
            notification_type='warning',
            link='/login'
        )
        
        return jsonify({
            'success': True,
            'new_password': new_password,
            'message': 'Password reset successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@admin_bp.route('/report/<int:report_id>')
@admin_required
def view_report(report_id):
    """View single report details"""
    report = Report.query.get_or_404(report_id)
    
    # Get reporter info
    reporter = User.query.get(report.user_id) if not report.is_anonymous else None
    
    # Get assigned officer
    assigned_officer = None
    if report.assigned_officer_id:
        assigned_officer = User.query.get(report.assigned_officer_id)
    
    # Get media files
    media_files = Media.query.filter_by(report_id=report.id).all()
    
    # Parse officer notes into comments (with safety check)
    comments = []
    if hasattr(report, 'officer_notes') and report.officer_notes:
        # Split by double newline to get individual comments
        raw_comments = report.officer_notes.split('\n\n')
        for raw in raw_comments:
            if raw.strip():

                # Check if it's a resolution report
                if 'RESOLUTION REPORT' in raw:
                    # Handle resolution report format
                    lines = raw.strip().split('\n')
                    if len(lines) >= 3:

                        # First line has timestamp and title
                        title_line = lines[0]
                        summary_line = lines[1] if len(lines) > 1 else ''
                        details = '\n'.join(lines[2:]) if len(lines) > 2 else ''

                        comments.append({
                            'type': 'resolution',
                            'title': title_line,
                            'summary': summary_line,
                            'details': details,
                            'officer': assigned_officer.get_full_name() if assigned_officer else 'Officer',
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
                        })

                else:
                    # Regular comment format: "timestamp - officer: comment"
                    parts = raw.strip().split(' - ', 1)
                    if len(parts) == 2:
                        timestamp_str, rest = parts
                        # Check if rest contains officer name
                        if ': ' in rest:
                            officer_part, comment = rest.split(': ', 1)
                        else:
                            officer_part = assigned_officer.get_full_name() if assigned_officer else 'Officer'
                            comment = rest

                        try:
                            # Parse timestamp
                            utc_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M')
                            local_tz = pytz.timezone('Africa/Kigali')
                            utc_time = pytz.utc.localize(utc_time)
                            local_time = utc_time.astimezone(local_tz)

                            # Format display time
                            now = datetime.now(local_tz)
                            today = now.date()
                            yesterday = today - timedelta(days=1)
                            comment_date = local_time.date()

                            if comment_date == today:
                                display_time = f"Today at {local_time.strftime('%H:%M')}"
                            elif comment_date == yesterday:
                                display_time = f"Yesterday at {local_time.strftime('%H:%M')}"
                            else:
                                display_time = local_time.strftime('%d %b %Y at %H:%M')

                        except:
                            display_time = timestamp_str
                    
                        comments.append({
                            'type': 'comment',
                            'officer': officer_part.strip(),
                            'comment': comment.strip(),
                            'timestamp': display_time,
                            'raw_timestamp': timestamp_str
                        })

                    else:
                        # If format is unexpected, treat as simple comment
                        comments.append({
                            'type': 'comment',
                            'officer': assigned_officer.get_full_name() if assigned_officer else 'Officer',
                            'comment': raw.strip(),
                            'timestamp': 'Unknown time',
                            'raw_timestamp': ''
                        })

                    print("="*50)
                    print("DEBUG COMMENTS:")
                    print(f"Total comments: {len(comments)}")
                    for i, comment in enumerate(comments):
                        print(f"\nComment {i}:")
                        for key, value in comment.items():
                            print(f"  {key}: {value}")
                    print("="*50)

    return render_template('admin/report_view.html',
                         user=session.get('user'),
                         report=report,
                         reporter=reporter,
                         assigned_officer=assigned_officer,
                         media_files=media_files,
                         comments=comments)

@admin_bp.route('/report/<int:report_id>/print')
@admin_required
def print_report(report_id):
    """Print single report"""
    from datetime import datetime
    from flask import make_response
    from weasyprint import HTML
    from app.models import Report, User, Media
    
    report = Report.query.get_or_404(report_id)
    
    # Get current user from session
    current_user_data = session.get('user')
    if not current_user_data:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Get related data
    reporter = User.query.get(report.user_id) if not report.is_anonymous else None
    assigned_officer = User.query.get(report.assigned_officer_id) if report.assigned_officer_id else None
    media_files = Media.query.filter_by(report_id=report.id).all()
    
    # Render print template with user info
    html = render_template('admin/print_report.html',
                         report=report,
                         reporter=reporter,
                         assigned_officer=assigned_officer,
                         media_files=media_files,
                         current_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
                         user=current_user_data)  # Pass the user data from session
    
    # Generate PDF
    pdf = HTML(string=html).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=report_{report.report_id}.pdf'
    
    return response

@admin_bp.route('/api/officers/list')
@admin_required
def list_officers():
    """API endpoint to list all officers"""
    officers = User.query.filter_by(role='officer', is_active=True).all()
    officers_data = [{
        'id': o.id,
        'name': o.get_full_name(),
        'sector': o.sector,
        'email': o.email
    } for o in officers]
    
    return jsonify({'officers': officers_data})

@admin_bp.route('/api/reports/<int:report_id>/assign', methods=['POST'])
@admin_required
def assign_report(report_id):
    """Assign report to officer"""
    try:
        data = request.get_json()
        officer_id = data.get('officer_id')
        
        report = Report.query.get_or_404(report_id)
        officer = User.query.get_or_404(officer_id)
        
        if officer.role != 'officer':
            return jsonify({'error': 'Selected user is not an officer'}), 400
        
        report.assigned_officer_id = officer_id
        report.status = 'in_progress'  # Auto-update status when assigned
        db.session.commit()
        
        # Send notification to officer
        from app.utils.notifications import send_notification
        send_notification(
            user_id=officer_id,
            title='New Report Assigned',
            message=f'Report {report.report_id} has been assigned to you.',
            notification_type='info',
            link=f'/officer/incident/{report.id}'
        )
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@admin_bp.route('/announcements')
@admin_required
def announcements():
    """Manage announcements"""
    from app.models import Announcement
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', 
                         user=session.get('user'),
                         announcements=announcements)

@admin_bp.route('/announcements/create', methods=['GET', 'POST'])
@admin_required
def create_announcement():
    """Create new announcement"""
    from app.models import Announcement, User, UserAnnouncement  # ADD UserAnnouncement here
    from app.utils.notifications import send_notification
    from datetime import datetime
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            title = data.get('title')
            content = data.get('content')
            priority = data.get('priority', 'normal')
            target_audience = data.get('target_audience', 'officers')
            target_sector = data.get('target_sector') or None

            print(f"=== DEBUG ===")
            print(f"Title: {title}")
            print(f"Target Audience from form: {target_audience}")
            print(f"Target Sector: {target_sector}")
            print(f"==============")
            
            announcement = Announcement(
                title=title,
                content=content,
                priority=priority,
                target_audience=target_audience,
                target_sector=target_sector,
                created_by=session['user']['id']
            )
            
            db.session.add(announcement)
            db.session.flush()  # Get the ID without committing yet
            
            # Send notifications based on target audience
            if target_audience in ['officers', 'all']:
                officers = User.query.filter_by(role='officer', is_active=True).all()
                for officer in officers:
                    if not target_sector or target_sector == officer.sector:
                        # Create user announcement copy
                        user_announcement = UserAnnouncement(   
                            user_id=officer.id,
                            announcement_id=announcement.id,
                            title=title,
                            content=content,
                            priority=priority,
                            is_read=False
                        )
                        db.session.add(user_announcement)
                        
                        # Send notification
                        send_notification(
                            user_id=officer.id,
                            title=f"📢 Official Announcement: {title}",
                            message=content[:100] + ('...' if len(content) > 100 else ''),
                            notification_type='info' if priority == 'normal' else 'warning' if priority == 'important' else 'danger',
                            link='/officer/announcements'
                        )
            
            if target_audience in ['citizens', 'all']:
                citizens = User.query.filter_by(role='citizen', is_active=True).all()
                for citizen in citizens:
                    send_notification(
                        user_id=citizen.id,
                        title=f"📢 Community Announcement: {title}",
                        message=content[:100] + ('...' if len(content) > 100 else ''),
                        notification_type='info',
                        link='/notifications'
                    )
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Announcement published successfully'}), 200
            else:
                flash('Announcement published successfully', 'success')
                return redirect(url_for('admin.announcements'))
                
        except Exception as e:
            db.session.rollback()
            print(f"Error creating announcement: {str(e)}")
            import traceback
            traceback.print_exc()
            if request.is_json:
                return jsonify({'error': str(e)}), 500
            else:
                flash(f'Error: {str(e)}', 'error')
                return render_template('admin/create_announcement.html', user=session.get('user'))
    
    return render_template('admin/create_announcement.html', user=session.get('user'))

@admin_bp.route('/api/announcements/<int:announcement_id>/delete', methods=['DELETE'])
@admin_required
def delete_announcement(announcement_id):
    """Delete an announcement (admin only - removes from admin panel only)"""
    from app.models import Announcement
    import traceback
    
    try:
        announcement = Announcement.query.get(announcement_id)
        
        if not announcement:
            return jsonify({'error': 'Announcement not found'}), 404
        
        # Just delete the announcement - user copies remain (no FK constraint)
        db.session.delete(announcement)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Announcement deleted from admin panel. User copies remain.'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR deleting announcement: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@admin_bp.route('/announcements/<int:announcement_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_announcement(announcement_id):
    """Edit an existing announcement"""
    from app.models import Announcement, User
    from app.utils.notifications import send_notification
    from datetime import datetime
    
    announcement = Announcement.query.get_or_404(announcement_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            # Store old values for notification
            old_title = announcement.title
            old_content = announcement.content
            
            # Update fields
            announcement.title = data.get('title', announcement.title)
            announcement.content = data.get('content', announcement.content)
            announcement.priority = data.get('priority', announcement.priority)
            announcement.target_audience = data.get('target_audience', announcement.target_audience)
            announcement.target_sector = data.get('target_sector') or announcement.target_sector
            
            db.session.commit()
            
            # Send notifications about the update to affected users
            if data.get('notify_users', True):
                # Get all users who received the original announcement
                if announcement.target_audience in ['officers', 'all']:
                    officers = User.query.filter_by(role='officer', is_active=True).all()
                    for officer in officers:
                        if not announcement.target_sector or announcement.target_sector == officer.sector:
                            send_notification(
                                user_id=officer.id,
                                title=f"📢 Announcement Updated: {announcement.title}",
                                message=f"The announcement '{old_title}' has been updated.\n\n{announcement.content[:100]}...",
                                notification_type='info',
                                link='/officer/announcements'
                            )
                
                if announcement.target_audience in ['citizens', 'all']:
                    citizens = User.query.filter_by(role='citizen', is_active=True).all()
                    for citizen in citizens:
                        send_notification(
                            user_id=citizen.id,
                            title=f"📢 Announcement Updated: {announcement.title}",
                            message=f"The announcement '{old_title}' has been updated.\n\n{announcement.content[:100]}...",
                            notification_type='info',
                            link='/notifications'
                        )
            
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'message': 'Announcement updated successfully'
                }), 200
            else:
                flash('Announcement updated successfully', 'success')
                return redirect(url_for('admin.announcements'))
                
        except Exception as e:
            db.session.rollback()
            print(f"Error updating announcement: {str(e)}")
            if request.is_json:
                return jsonify({'error': str(e)}), 500
            else:
                flash(f'Error: {str(e)}', 'error')
                return render_template('admin/edit_announcement.html', 
                                     user=session.get('user'),
                                     announcement=announcement)
    
    return render_template('admin/edit_announcement.html',
                         user=session.get('user'),
                         announcement=announcement)    


@admin_bp.context_processor
def utility_processor():
    from datetime import datetime
    return {'now': datetime.now}

@admin_bp.route('/api/announcements/<int:announcement_id>/expire', methods=['POST'])
@admin_required
def expire_announcement(announcement_id):
    """Expire an announcement immediately"""
    from app.models import Announcement
    try:
        announcement = Announcement.query.get_or_404(announcement_id)
        announcement.expires_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/messages/send', methods=['POST'])
@admin_required
def send_message():
    """Send a message to an officer about a report"""
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        receiver_id = data.get('receiver_id')
        message = data.get('message')
        
        if not all([report_id, receiver_id, message]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create message
        msg = Message(
            report_id=report_id,
            sender_id=session['user']['id'],
            receiver_id=receiver_id,
            message=message,
            is_read=False
        )
        
        db.session.add(msg)
        db.session.commit()
        
        # Send notification to officer
        from app.utils.notifications import send_notification
        report = Report.query.get(report_id)
        send_notification(
            user_id=receiver_id,
            title=f"💬 Question about Report {report.report_id}",
            message=message[:100] + ('...' if len(message) > 100 else ''),
            notification_type='info',
            link=f'/officer/incident/{report_id}?message=1'
        )
        
        return jsonify({'success': True, 'message': 'Message sent successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/messages/conversations', methods=['GET'])
@admin_required
def get_conversations():
    """Get all conversations for admin (grouped by report)"""
    try:
        from sqlalchemy import desc, func
        
        # Get all messages where admin is sender or receiver
        admin_id = session['user']['id']
        
        # Get distinct report IDs that have messages involving this admin
        report_ids = db.session.query(Message.report_id).filter(
            (Message.sender_id == admin_id) | (Message.receiver_id == admin_id)
        ).distinct().all()
        
        report_ids = [r[0] for r in report_ids]
        
        conversations = []
        for report_id in report_ids:
            report = Report.query.get(report_id)
            if not report:
                continue
            
            # Get the last message in this conversation
            last_message = Message.query.filter_by(report_id=report_id).order_by(desc(Message.created_at)).first()
            
            # Get the other participant (the officer)
            other_participant_id = last_message.sender_id if last_message.sender_id != admin_id else last_message.receiver_id
            officer = User.query.get(other_participant_id)
            
            # Count unread messages for admin in this conversation
            unread_count = Message.query.filter_by(
                report_id=report_id,
                receiver_id=admin_id,
                is_read=False
            ).count()
            
            conversations.append({
                'report_id': report_id,
                'officer_id': officer.id if officer else None,
                'report_title': report.title[:50] + '...' if len(report.title) > 50 else report.title,
                'report_number': report.report_id,
                'officer_id': officer.id if officer else None,
                'officer_name': officer.get_full_name() if officer else 'Unknown Officer',
                'officer_sector': officer.sector if officer else 'Unknown',
                'last_message': last_message.message[:50] + '...' if last_message and len(last_message.message) > 50 else (last_message.message if last_message else ''),
                'last_message_time': last_message.created_at.strftime('%Y-%m-%d %H:%M') if last_message else '',
                'unread_count': unread_count
            })
        
        # Sort by most recent message
        conversations.sort(key=lambda x: x['last_message_time'], reverse=True)
        
        return jsonify({'conversations': conversations}), 200
        
    except Exception as e:
        print(f"Error loading conversations: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/messages/<int:message_id>/read', methods=['POST'])
@admin_required
def mark_admin_message_read(message_id):
    """Mark a message as read for admin"""
    try:
        message = Message.query.get_or_404(message_id)
        if message.receiver_id == session['user']['id']:
            message.is_read = True
            db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/messages/<int:report_id>', methods=['GET'])
@admin_required
def get_messages(report_id):
    """Get all messages for a specific report"""
    try:
        messages = Message.get_conversation(report_id, session['user']['id'])
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'message': msg.message,
                'sender': msg.sender.get_full_name(),
                'sender_id': msg.sender_id,
                'is_read': msg.is_read,
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
                'is_me': msg.sender_id == session['user']['id']
            })
        
        return jsonify({'messages': messages_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/messages/unread-count')
@admin_required
def admin_unread_messages():
    """Get unread messages count for admin"""
    try:
        count = Message.get_unread_count(session['user']['id'])
        return jsonify({'count': count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/messages')
@admin_required
def messages_page():
    """Messages page for admin"""
    return render_template('admin/messages.html', 
                         user=session.get('user'),
                         current_user_id=session.get('user')['id'])  # Add this       


@admin_bp.route('/pending-officers')
@admin_required
def pending_officers():
    """View pending officer approvals - show pending, denied, and recently approved"""
    user = session.get('user')
    admin_district = user.get('district')
    
    # Get pending officers in admin's district (including denied and recently approved)
    from app.models import PendingApproval, User
    
    # Show pending, denied, and recently approved (last 24 hours)
    from datetime import datetime, timedelta
    last_24h = datetime.utcnow() - timedelta(hours=24)
    
    # Fixed query - proper SQLAlchemy syntax
    pending = db.session.query(PendingApproval, User).join(
        User, PendingApproval.officer_id == User.id
    ).filter(
        PendingApproval.admin_id == user['id'],
        User.district == admin_district
    ).filter(
        # Include pending, denied, and approved from last 24h
        (PendingApproval.status.in_(['pending', 'denied'])) |
        ((PendingApproval.status == 'approved') & (PendingApproval.reviewed_at >= last_24h))
    ).order_by(
        # Custom ordering
        PendingApproval.status != 'pending',  # This puts pending first (False comes before True)
        PendingApproval.status != 'approved',  # Then approved
        PendingApproval.reviewed_at.desc().nullslast()  # Then by review date
    ).all()
    
    pending_data = []
    for p, officer in pending:
        # Get reviewer name if exists
        reviewer_name = None
        if p.reviewer:
            reviewer_name = f"{p.reviewer.first_name} {p.reviewer.last_name}"
        
        pending_data.append({
            'officer': officer,
            'email_type': p.email_type,
            'created_at': p.created_at,
            'pending_id': p.id,
            'status': p.status,
            'denial_reason': p.denial_reason,
            'reviewed_at': p.reviewed_at,
            'reviewed_by_name': reviewer_name
        })
    
    return render_template('admin/pending_officers.html',
                         user=user,
                         pending_officers=pending_data)

@admin_bp.route('/api/pending-officers/count')
@admin_required
def pending_officers_count():
    """Get count of pending officers for this admin"""
    user = session.get('user')
    
    from app.models import PendingApproval
    
    count = PendingApproval.query.filter_by(
        admin_id=user['id'],
        status='pending'
    ).count()
    
    return jsonify({'count': count})

@admin_bp.route('/api/pending-officers/<int:officer_id>')
@admin_required
def get_pending_officer(officer_id):
    """Get pending officer details"""
    from app.models import User, PendingApproval
    
    officer = User.query.get_or_404(officer_id)
    pending = PendingApproval.query.filter_by(
        officer_id=officer_id,
        status='pending'
    ).first()
    
    if not pending:
        return jsonify({'error': 'No pending approval found'}), 404
    
    return jsonify({
        'success': True,
        'officer': {
            'id': officer.id,
            'first_name': officer.first_name,
            'last_name': officer.last_name,
            'email': officer.email,
            'phone': officer.phone,
            'province': officer.province,
            'district': officer.district,
            'sector': officer.sector,
            'cell': officer.cell,
            'village': officer.village,
            'officer_id': officer.officer_id,
            'department': officer.department
        },
        'email_type': pending.email_type,
        'created_at': pending.created_at.strftime('%d %b %Y, %H:%M')
    })

@admin_bp.route('/api/pending-officers/<int:officer_id>/approve', methods=['POST'])
@admin_required
def approve_officer(officer_id):
    """Approve a pending or previously denied officer"""
    try:
        from datetime import datetime
        user = session.get('user')
        from app.models import User, PendingApproval, Notification
        
        officer = User.query.get_or_404(officer_id)
        
        # Look for either pending or denied approval records
        pending = PendingApproval.query.filter_by(
            officer_id=officer_id
        ).filter(
            PendingApproval.status.in_(['pending', 'denied'])
        ).first()
        
        if not pending:
            return jsonify({'error': 'No pending or denied approval found'}), 404
        
        # Update officer status
        officer.is_active = True
        officer.is_verified = True
        officer.is_approved = True
        officer.approval_status = 'approved'
        officer.approved_by = user['id']
        officer.approved_at = datetime.utcnow()
        officer.denied_reason = None  # Clear any previous denial reason
        
        # Update pending record
        pending.status = 'approved'
        pending.reviewed_at = datetime.utcnow()
        pending.reviewed_by = user['id']
        pending.denial_reason = None  # Clear any previous denial reason
        
        # Create approval notification for officer
        notification = Notification(
            user_id=officer.id,
            title='Account Approved! ✅',
            message=f'Congratulations! Your officer account has been approved by the {officer.district} District Admin. You can now log in to access your dashboard.',
            notification_type='success',
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Officer approved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/pending-officers/<int:officer_id>/deny', methods=['POST'])
@admin_required
def deny_officer(officer_id):
    """Deny a pending officer registration"""
    try:
        from datetime import datetime 
        user = session.get('user')
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        from app.models import User, PendingApproval, Notification
        
        officer = User.query.get_or_404(officer_id)
        pending = PendingApproval.query.filter_by(
            officer_id=officer_id,
            status='pending'
        ).first()
        
        if not pending:
            return jsonify({'error': 'No pending approval found'}), 404
        
        # Update officer status
        officer.approval_status = 'denied'
        officer.denied_reason = reason
        
        # Update pending record
        pending.status = 'denied'
        pending.reviewed_at = datetime.utcnow()
        pending.reviewed_by = user['id']
        pending.denial_reason = reason
        
        # Create notification for officer
        notification = Notification(
            user_id=officer.id,
            title='Registration Not Approved',
            message=f'Your officer account registration has been denied. Reason: {reason}',
            notification_type='danger',
            is_read=False, 
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Officer registration denied'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/generate-monthly-report', methods=['POST'])
@admin_required
def generate_monthly_report():
    """Generate monthly report PDF for admin"""
    try:
        from app.utils.report_generator import generate_monthly_report as get_report_data, generate_pdf_report
        from datetime import datetime
        
        data = request.get_json()
        month = data.get('month')
        year = data.get('year')
        
        if month and year:
            month = int(month)
            year = int(year)
        
        # Get report data
        report_data = get_report_data(session['user'], month, year)
        
        if not report_data:
            return jsonify({'error': 'No data found for this period'}), 404
        
        # Generate PDF
        pdf = generate_pdf_report(report_data, session['user'])
        
        # Create response
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=monthly_report_{month}_{year}.pdf'
        
        return response
        
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/report-preview', methods=['POST'])
@admin_required
def report_preview():
    """Get report preview data"""
    try:
        from app.utils.report_generator import generate_monthly_report
        
        data = request.get_json()
        month = data.get('month')
        year = data.get('year')
        
        if month and year:
            month = int(month)
            year = int(year)
        
        report_data = generate_monthly_report(session['user'], month, year)
        
        if not report_data:
            return jsonify({'error': 'No data found for this period'}), 404
        
        # Format for JSON response
        preview = {
            'title': report_data['title'],
            'month': report_data['month'],
            'period': report_data['period'],
            'stats': report_data['stats'],
            'categories': report_data['categories'],
            'officer_count': len(report_data['officer_stats']),
            'report_count': len(report_data['reports'])
        }
        
        return jsonify({'success': True, 'data': preview})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@admin_bp.route('/monthly-report')
@admin_required
def monthly_report_page():
    """Monthly report page"""
    return render_template('admin/monthly_report.html', user=session.get('user'))    

@admin_bp.route('/api/generate-monthly-report', methods=['GET'])
@admin_required
def generate_monthly_report_get():
    """Generate monthly report PDF for admin - GET version"""
    try:
        month = request.args.get('month')
        year = request.args.get('year')
        
        if not month or not year:
            flash('Please select month and year', 'error')
            return redirect(url_for('admin.dashboard'))
        
        # Convert to integers
        month = int(month)
        year = int(year)
        
        from app.utils.report_generator import generate_monthly_report as get_report_data, generate_pdf_report
        from datetime import datetime
        
        user = session.get('user')
        
        # Get report data
        report_data = get_report_data(user, month, year)
        
        if not report_data:
            flash('No data found for the selected period', 'warning')
            return redirect(url_for('admin.dashboard'))
        
        # Generate PDF
        pdf = generate_pdf_report(report_data, user)
        
        # Create response
        from flask import make_response
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=monthly_report_{month}_{year}.pdf'
        
        return response
        
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        flash('Error generating report. Please try again.', 'error')
        return redirect(url_for('admin.dashboard'))    