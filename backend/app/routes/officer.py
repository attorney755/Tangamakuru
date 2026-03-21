from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash, make_response
from app import db
from app.models import User, Report, Notification, Media
from datetime import datetime, timedelta
from sqlalchemy import func
from functools import wraps
from weasyprint import HTML
import io
from app.models import Message
from datetime import datetime

officer_bp = Blueprint('officer', __name__, url_prefix='/officer')

@officer_bp.context_processor
def utility_processor():
    return {'now': datetime.now}

def officer_required(f):
    """Decorator to check if user is an officer"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user:
            flash('Please login first', 'warning')
            return redirect(url_for('frontend.login'))
        
        if user.get('role') != 'officer':
            flash('Access denied. Officer privileges required.', 'error')
            return redirect(url_for('frontend.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@officer_bp.route('/dashboard')
@officer_required
def dashboard():
    """Officer dashboard - shows incidents in their sector"""
    user = session.get('user')
    
    # Get the actual officer from database
    officer = User.query.get(user['id'])
    
    # Get reports in officer's sector that are either unassigned OR assigned to this officer
    reports_query = Report.query.filter(
        Report.sector == officer.sector,
        (Report.assigned_officer_id.is_(None)) | (Report.assigned_officer_id == officer.id)
    )
    
    # Statistics
    total_reports = reports_query.count()
    pending = reports_query.filter_by(status='pending').count()
    in_progress = reports_query.filter_by(status='in_progress').count()
    resolved = reports_query.filter_by(status='resolved').count()
    
    # Recent reports
    recent_reports = reports_query.order_by(Report.created_at.desc()).limit(10).all()
    reports_data = []
    for r in recent_reports:
        reporter = User.query.get(r.user_id)
        reports_data.append({
            'id': r.id,
            'report_id': r.report_id,
            'title': r.title[:50] + '...' if len(r.title) > 50 else r.title,
            'category': r.category,
            'status': r.status,
            'priority': r.priority,
            'reporter': f"{reporter.first_name} {reporter.last_name}" if reporter and not r.is_anonymous else "Anonymous",
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'assigned_to_me': r.assigned_officer_id == officer.id,
            'is_unassigned': r.assigned_officer_id is None
        })
    
    # Reports by category
    categories = db.session.query(
        Report.category, func.count(Report.id)
    ).filter(Report.sector == officer.sector).group_by(Report.category).all()
    
    category_labels = [c[0] for c in categories]
    category_data = [c[1] for c in categories]
    
    # Unassigned reports count (only unassigned in officer's sector)
    unassigned = Report.query.filter_by(
        sector=officer.sector,
        assigned_officer_id=None
    ).count()
    
    # My assigned reports
    my_assigned = Report.query.filter_by(
        sector=officer.sector,
        assigned_officer_id=officer.id
    ).count()
    
    stats = {
        'total': total_reports,
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved,
        'unassigned': unassigned,
        'my_assigned': my_assigned
    }
    
    return render_template('officer/dashboard.html',
                         user=user,
                         officer=officer,
                         stats=stats,
                         recent_reports=reports_data,
                         category_labels=category_labels,
                         category_data=category_data)

@officer_bp.route('/incidents')
@officer_required
def incidents():
    """List incidents - only unassigned and assigned to current officer"""
    user = session.get('user')
    officer = User.query.get(user['id'])
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    
    # Base query: incidents in officer's sector that are either:
    # 1. Unassigned, OR
    # 2. Assigned to this officer
    query = Report.query.filter(
        Report.sector == officer.sector,
        (Report.assigned_officer_id.is_(None)) | (Report.assigned_officer_id == officer.id)
    )
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    
    reports = query.order_by(Report.created_at.desc()).all()
    
    reports_data = []
    for r in reports:
        reporter = User.query.get(r.user_id)
        reports_data.append({
            'id': r.id,
            'report_id': r.report_id,
            'title': r.title,
            'category': r.category,
            'status': r.status,
            'priority': r.priority,
            'reporter': f"{reporter.first_name} {reporter.last_name}" if reporter and not r.is_anonymous else "Anonymous",
            'location': f"{r.village}, {r.cell}",
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'assigned_to_me': r.assigned_officer_id == officer.id,
            'is_unassigned': r.assigned_officer_id is None
        })
    
    # Statistics - now only counting what officers can see
    all_query = Report.query.filter(
        Report.sector == officer.sector,
        (Report.assigned_officer_id.is_(None)) | (Report.assigned_officer_id == officer.id)
    )
    
    stats = {
        'all': all_query.count(),
        'pending': all_query.filter_by(status='pending').count(),
        'in_progress': all_query.filter_by(status='in_progress').count(),
        'resolved': all_query.filter_by(status='resolved').count()
    }
    
    return render_template('officer/incidents.html',
                         user=user,
                         officer=officer,
                         reports=reports_data,
                         stats=stats,
                         current_status=status_filter,
                         current_priority=priority_filter)

@officer_bp.route('/incident/<int:report_id>')
@officer_required
def view_incident(report_id):
    """View single incident details"""
    user = session.get('user')
    officer = User.query.get(user['id'])
    
    report = Report.query.get_or_404(report_id)
    
    # Verify officer has access to this sector
    if report.sector != officer.sector:
        flash('You do not have permission to view this incident', 'error')
        return redirect(url_for('officer.incidents'))
    
    # Get reporter info
    reporter = User.query.get(report.user_id) if not report.is_anonymous else None
    
    # Get assigned officer info
    assigned_officer = None
    if report.assigned_officer_id:
        assigned_officer = User.query.get(report.assigned_officer_id)
    
    # Get media files
    media_files = Media.query.filter_by(report_id=report.id).all()
    
    # Get status history (you might want to create a StatusHistory model for this)
    # For now, we'll just show current status
    
    return render_template('officer/incident_view.html',
                         user=user,
                         officer=officer,
                         report=report,
                         reporter=reporter,
                         assigned_officer=assigned_officer,
                         media_files=media_files)

@officer_bp.route('/incident/<int:report_id>/update-status', methods=['POST'])
@officer_required
def update_incident_status(report_id):
    """Update incident status with comment"""
    try:
        user = session.get('user')
        officer = User.query.get(user['id'])
        
        report = Report.query.get_or_404(report_id)
        
        # Verify officer has access to this sector
        if report.sector != officer.sector:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        new_status = data.get('status')
        comment = data.get('comment', '')
        
        if new_status not in ['pending', 'in_progress', 'resolved', 'cancelled']:
            return jsonify({'error': 'Invalid status'}), 400
        
        old_status = report.status
        report.status = new_status
        
        # Add comment to officer_notes or create a new field
        if comment:
            officer_name = f"{officer.first_name} {officer.last_name}"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

            # Format: "2024-03-11 14:30 - John Doe: Comment here"
            formatted_comment = f"{timestamp} - {officer_name}: {comment}"

            if hasattr(report, 'officer_notes'):
              # Prepend new comment to show most recent first
                if report.officer_notes:
              # Use DOUBLE newline to separate comments properly
                    report.officer_notes = formatted_comment + "\n\n" + report.officer_notes
            else:
                    report.officer_notes = formatted_comment
            
        # Assign officer if not assigned
        if not report.assigned_officer_id:
            report.assigned_officer_id = officer.id
        
        # Set resolved_at if status is resolved
        if new_status == 'resolved':
            report.resolved_at = datetime.now()
        
        db.session.commit()
        
        # Create notification for the citizen
        if not report.is_anonymous:
            status_messages = {
                'pending': 'Your report has been received and is pending review.',
                'in_progress': 'Your report is now being processed by an officer.',
                'resolved': 'Your report has been resolved. Thank you for your patience.',
                'cancelled': 'Your report has been marked as cancelled.'
            }
            
            message = status_messages.get(new_status, f'Your report status has been updated to {new_status}.')
            if comment:
                message += f" Officer comment: {comment}"
            
            Notification.create_notification(
              user_id=report.user_id,
              title=f'Report Status Update - {report.report_id}',
              message=message,
              notification_type='success' if new_status == 'resolved' else 'info',
              link=f'/view-report/{report.id}'  # Change from '/reports/{report.id}' to '/view-report/{report.id}'
)
        
        return jsonify({
            'success': True,
            'message': f'Status updated to {new_status}',
            'new_status': new_status
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/incident/<int:report_id>/print')
@officer_required
def print_report(report_id):
    """Generate printable report for an incident"""
    user = session.get('user')
    officer = User.query.get(user['id'])
    
    report = Report.query.get_or_404(report_id)
    
    # Verify officer has access to this sector
    if report.sector != officer.sector:
        flash('You do not have permission to view this incident', 'error')
        return redirect(url_for('officer.incidents'))
    
    # Get reporter info
    reporter = User.query.get(report.user_id) if not report.is_anonymous else None
    
    # Get assigned officer info
    assigned_officer = None
    if report.assigned_officer_id:
        assigned_officer = User.query.get(report.assigned_officer_id)
    
    # Get media files
    media_files = Media.query.filter_by(report_id=report.id).all()
    
    # Render HTML template for print
    html = render_template('officer/print_report.html',
                         report=report,
                         reporter=reporter,
                         assigned_officer=assigned_officer or officer,
                         media_files=media_files,
                         current_date=datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    # Generate PDF
    pdf = HTML(string=html).write_pdf()
    
    # Create response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=incident_{report.report_id}.pdf'
    
    return response

@officer_bp.route('/stats')
@officer_required
def statistics():
    """Detailed statistics for officer"""
    user = session.get('user')
    officer = User.query.get(user['id'])
    
    # Reports by month (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        count = Report.query.filter(
            Report.sector == officer.sector,
            Report.created_at >= month_start,
            Report.created_at <= month_end
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })
    
    # Reports by category
    categories = db.session.query(
        Report.category, func.count(Report.id)
    ).filter(Report.sector == officer.sector).group_by(Report.category).all()
    
    # Reports by status
    status_counts = {
        'pending': Report.query.filter_by(sector=officer.sector, status='pending').count(),
        'in_progress': Report.query.filter_by(sector=officer.sector, status='in_progress').count(),
        'resolved': Report.query.filter_by(sector=officer.sector, status='resolved').count(),
        'cancelled': Report.query.filter_by(sector=officer.sector, status='cancelled').count()
    }
    
    # Average resolution time
    resolved_reports = Report.query.filter(
        Report.sector == officer.sector,
        Report.status == 'resolved',
        Report.resolved_at.isnot(None)
    ).all()
    
    avg_resolution = None
    if resolved_reports:
        total_days = sum((r.resolved_at - r.created_at).days for r in resolved_reports if r.resolved_at)
        avg_resolution = round(total_days / len(resolved_reports), 1)
    
    return render_template('officer/statistics.html',
                         user=user,
                         officer=officer,
                         monthly_data=monthly_data,
                         categories=categories,
                         status_counts=status_counts,
                         avg_resolution=avg_resolution,
                         total_reports=sum(status_counts.values()))

@officer_bp.route('/announcements')
@officer_required
def announcements():
    """View announcements (from user copies)"""
    user = session.get('user')
    officer = User.query.get(user['id'])
    
    from app.models import UserAnnouncement
    
    # Get user's announcement copies
    announcements = UserAnnouncement.query.filter_by(
        user_id=officer.id
    ).order_by(UserAnnouncement.created_at.desc()).all()
    
    return render_template('officer/announcements.html',
                         user=user,
                         officer=officer,
                         announcements=announcements)

@officer_bp.route('/api/announcements/unread-count')
@officer_required
def api_announcement_unread_count():
    """Get unread announcements count for officer"""
    user = session.get('user')
    from app.models import UserAnnouncement
    
    count = UserAnnouncement.get_unread_count(user['id'])
    
    return jsonify({'count': count})

@officer_bp.route('/api/announcements/<int:announcement_id>/read', methods=['POST'])
@officer_required
def mark_announcement_read(announcement_id):
    """Mark an announcement as read"""
    user = session.get('user')
    from app.models import UserAnnouncement
    
    announcement = UserAnnouncement.query.filter_by(
        id=announcement_id,
        user_id=user['id']
    ).first_or_404()
    
    announcement.mark_as_read()
    
    return jsonify({'success': True})

@officer_bp.route('/api/announcements/<int:announcement_id>/delete', methods=['DELETE'])
@officer_required
def delete_user_announcement(announcement_id):
    """Delete a user's copy of an announcement"""
    user = session.get('user')
    from app.models import UserAnnouncement
    
    try:
        announcement = UserAnnouncement.query.filter_by(
            id=announcement_id,
            user_id=user['id']
        ).first_or_404()
        
        db.session.delete(announcement)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/api/announcements/read-all', methods=['POST'])
@officer_required
def mark_all_announcements_read():
    """Mark all announcements as read"""
    user = session.get('user')
    from app.models import UserAnnouncement
    
    UserAnnouncement.query.filter_by(
        user_id=user['id'],
        is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    
    return jsonify({'success': True})

@officer_bp.route('/api/messages/send', methods=['POST'])
@officer_required
def officer_send_message():
    """Send a message to admin about a report"""
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        receiver_id = data.get('receiver_id')  # Usually admin ID
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
        
        # Send notification to admin
        from app.utils.notifications import send_notification
        report = Report.query.get(report_id)
        send_notification(
            user_id=receiver_id,
            title=f"💬 Officer Response - Report {report.report_id}",
            message=message[:100] + ('...' if len(message) > 100 else ''),
            notification_type='info',
            link=f'/admin/report/{report_id}?message=1'
        )
        
        return jsonify({'success': True, 'message': 'Message sent successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/api/messages/<int:report_id>', methods=['GET'])
@officer_required
def get_officer_messages(report_id):
    """Get all messages for a specific report (officer view)"""
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


@officer_bp.route('/api/messages/conversations', methods=['GET'])
@officer_required
def get_officer_conversations():
    """Get all conversations for officer"""
    try:
        from sqlalchemy import desc, func
        from app.models import Message, Report, User
        
        officer_id = session['user']['id']
        
        # Get all messages where officer is sender or receiver
        messages = Message.query.filter(
            (Message.sender_id == officer_id) | (Message.receiver_id == officer_id)
        ).order_by(desc(Message.created_at)).all()
        
        # Group by report
        conversations = {}
        for msg in messages:
            if msg.report_id not in conversations:
                report = Report.query.get(msg.report_id)
                
                # Get the other participant
                other_id = msg.sender_id if msg.sender_id != officer_id else msg.receiver_id
                other_user = User.query.get(other_id)
                
                # Get the last message in this conversation
                last_msg = Message.query.filter_by(report_id=msg.report_id).order_by(desc(Message.created_at)).first()
                
                # Check if officer has already provided a resolution report
                has_report = False
                if report and report.officer_notes and 'RESOLUTION REPORT' in report.officer_notes:
                    has_report = True
                
                # Get the initial question (first message from admin)
                initial_question = Message.query.filter_by(
                    report_id=msg.report_id,
                    sender_id=other_id
                ).order_by(Message.created_at.asc()).first()
                
                conversations[msg.report_id] = {
                    'report_id': msg.report_id,
                    'report_number': report.report_id if report else 'Unknown',
                    'report_title': report.title[:50] + '...' if report and len(report.title) > 50 else (report.title if report else 'Unknown'),
                    'admin_id': other_id if other_user.role == 'admin' else None,
                    'admin_name': other_user.get_full_name() if other_user else 'Unknown',
                    'question': initial_question.message if initial_question else 'No question',
                    'question_time': initial_question.created_at.strftime('%Y-%m-%d %H:%M') if initial_question else '',
                    'last_message': last_msg.message[:50] + '...' if last_msg and len(last_msg.message) > 50 else (last_msg.message if last_msg else ''),
                    'last_message_time': last_msg.created_at.strftime('%Y-%m-%d %H:%M') if last_msg else '',
                    'has_report': has_report,
                    'unread_count': Message.query.filter_by(
                        report_id=msg.report_id,
                        receiver_id=officer_id,
                        is_read=False
                    ).count()
                }
        
        # Sort by last message time
        sorted_conversations = sorted(
            conversations.values(), 
            key=lambda x: x['last_message_time'], 
            reverse=True
        )
        
        return jsonify({'conversations': sorted_conversations}), 200
        
    except Exception as e:
        print(f"Error loading conversations: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@officer_bp.route('/api/messages/provide-report', methods=['POST'])
@officer_required
def provide_resolution_report():
    """Officer provides a full resolution report"""
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        admin_id = data.get('admin_id')
        resolution = data.get('resolution')
        
        if not all([report_id, admin_id, resolution]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get the report
        report = Report.query.get_or_404(report_id)
        officer = User.query.get(session['user']['id'])
        
        # Format the resolution report
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        officer_name = f"{officer.first_name} {officer.last_name}"
        formatted_report = f"\n\n RESOLUTION REPORT\n{timestamp} - {officer_name}:\n{resolution}\n\n"
        
        # Add to officer_notes
        if report.officer_notes:
            report.officer_notes = report.officer_notes + formatted_report
        else:
            report.officer_notes = formatted_report
        
        # Mark all messages in this conversation as read
        Message.query.filter_by(
            report_id=report_id,
            receiver_id=session['user']['id']
        ).update({'is_read': True})
        
        db.session.commit()
        
        # Send notification to admin
        from app.utils.notifications import send_notification
        send_notification(
            user_id=admin_id,
            title=f"📋 Resolution Report - {report.report_id}",
            message=f"Officer {officer_name} has provided a resolution report for case {report.report_id}.",
            notification_type='success',
            link=f'/admin/report/{report_id}'
        )
        
        return jsonify({'success': True, 'message': 'Resolution report submitted'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting report: {str(e)}")
        return jsonify({'error': str(e)}), 500


@officer_bp.route('/api/messages/unread-count')
@officer_required
def officer_unread_messages():
    """Get unread messages count for officer"""
    try:
        count = Message.get_unread_count(session['user']['id'])
        return jsonify({'count': count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/messages')
@officer_required
def messages_page():
    """Messages page for officer"""
    return render_template('officer/messages.html', user=session.get('user'))

@officer_bp.route('/api/messages/<int:message_id>/read', methods=['POST'])
@officer_required
def mark_message_read(message_id):
    """Mark a message as read"""
    try:
        message = Message.query.get_or_404(message_id)
        if message.receiver_id == session['user']['id']:
            message.is_read = True
            db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/api/messages/mark-all-read/<int:report_id>', methods=['POST'])
@officer_required
def mark_all_messages_read(report_id):
    """Mark all messages in a conversation as read"""
    try:
        Message.query.filter_by(
            report_id=report_id,
            receiver_id=session['user']['id'],
            is_read=False
        ).update({'is_read': True})
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/api/ask-for-info', methods=['POST'])
@officer_required
def ask_for_info():
    """Officer requests more information from citizen"""
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        citizen_id = data.get('citizen_id')
        request_text = data.get('request')
        request_type = data.get('request_type', 'text')
        
        if not all([report_id, citizen_id, request_text]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        report = Report.query.get_or_404(report_id)
        officer = User.query.get(session['user']['id'])
        
        # Store the pending request
        report.pending_officer_request = request_text
        
        # Create a notification for the citizen with the actual question
        from app.utils.notifications import send_notification
        
        type_text = {
            'text': 'more text information',
            'evidence': 'photos or video evidence',
            'both': 'more text information and evidence'
        }.get(request_type, 'more information')
        
        send_notification(
            user_id=citizen_id,
            title=f"🔍 Officer Requests More Information - Report {report.report_id}",
            message=f"Officer {officer.first_name} {officer.last_name} is requesting {type_text}:\n\n\"{request_text}\"\n\nPlease check your report to provide additional details.",
            notification_type='info',
            link=f'/view-report/{report_id}?request=1'
        )
        
        # Also add a note to officer_notes about the request
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        officer_name = f"{officer.first_name} {officer.last_name}"
        request_note = f"{timestamp} - {officer_name}: Requested more information: {request_text} (Type: {request_type})"
        
        if report.officer_notes:
            report.officer_notes = request_note + "\n\n" + report.officer_notes
        else:
            report.officer_notes = request_note
        
        db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error asking for info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/api/generate-monthly-report', methods=['POST'])
@officer_required
def generate_monthly_report():
    """Generate monthly report PDF for officer"""
    try:
        from app.utils.report_generator import generate_monthly_report as get_report_data, generate_pdf_report
        
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


@officer_bp.route('/api/report-preview', methods=['POST'])
@officer_required
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
            'report_count': len(report_data['reports'])
        }
        
        return jsonify({'success': True, 'data': preview})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@officer_bp.route('/monthly-report')
@officer_required
def monthly_report_page():
    """Monthly report page"""
    return render_template('officer/monthly_report.html', user=session.get('user'))
