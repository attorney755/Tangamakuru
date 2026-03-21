from app.models import Notification, User, Report
from app import db
from datetime import datetime

def send_notification(user_id, title, message, notification_type='info', link=None):
    """Send a notification to a user"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def notify_new_user(user):
    """Send welcome notification to new user only (not to admins)"""
    # Send welcome notification ONLY to the new user
    send_notification(
        user_id=user.id,
        title='Welcome to TANGAMAKURU! 🎉',
        message=f'Welcome {user.first_name}! Your account has been created successfully. You can now report incidents and track their progress.',
        notification_type='success',
        link='/dashboard'
    )

def notify_report_submitted(report):
    """Send notification when report is submitted"""
    # Get reporter info
    reporter = User.query.get(report.user_id)
    
    # Notify the user who submitted
    send_notification(
        user_id=report.user_id,
        title='Report Submitted Successfully ✅',
        message=f'Your report {report.report_id} has been submitted and is pending review by sector officers. An officer will be assigned within 24 hours.',
        notification_type='success',
        link=f'/view-report/{report.id}'
    )
    
    # Notify admins
    admins = User.query.filter_by(role='admin').all()
    for admin in admins:
        send_notification(
            user_id=admin.id,
            title='New Report Submitted',
            message=f'New report {report.report_id} submitted by {reporter.first_name} {reporter.last_name} in {report.sector} sector.',
            notification_type='info',
            link=f'/admin/reports/{report.id}'
        )
    
    # Notify officers in the same sector
    officers_in_sector = User.query.filter_by(
        role='officer', 
        sector=report.sector,
        is_active=True
    ).all()
    
    for officer in officers_in_sector:
        # Create notification for officer
        send_notification(
            user_id=officer.id,
            title=f'🚨 New Incident in {report.sector} Sector',
            message=f'A new incident ({report.report_id}) has been reported in your sector. Category: {report.category}. Priority: {report.priority}.',
            notification_type='warning' if report.priority in ['high', 'urgent'] else 'info',
            link=f'/officer/incident/{report.id}'
        )
        
        # Optional: Also send email notification if you have email system
        # send_email(officer.email, 'New Incident in Your Sector', f'A new incident has been reported...')

def notify_officer_created(officer, admin, password):
    """Send notification when officer is created"""
    # Notify the new officer
    send_notification(
        user_id=officer.id,
        title='Officer Account Created 👮',
        message=f'Your officer account has been created. Use email: {officer.email} and temporary password: {password}. Please change your password after first login.',
        notification_type='success',
        link='/login'
    )
    
    # Notify admin who created
    send_notification(
        user_id=admin.id,
        title='Officer Created Successfully',
        message=f'Officer {officer.first_name} {officer.last_name} has been created and assigned to {officer.sector} sector.',
        notification_type='success',
        link='/admin/officers'
    )

def notify_status_update(report, old_status, new_status, updated_by):
    """Send notification when report status is updated"""
    # Status emoji mapping
    status_emoji = {
        'pending': '⏳',
        'in_progress': '🔄',
        'resolved': '✅',
        'submitted': '📝'
    }
    emoji = status_emoji.get(new_status.lower(), '📋')
    
    # Notify the reporter
    send_notification(
        user_id=report.user_id,
        title=f'Report Status Updated {emoji}',
        message=f'Your report {report.report_id} status changed from {old_status} to {new_status}.',
        notification_type='info' if new_status != 'resolved' else 'success',
        link=f'/view-report/{report.id}'  # Keep this consistent
    )
    
    # Notify assigned officer if any
    if report.assigned_officer_id and report.assigned_officer_id != updated_by.id:
        send_notification(
            user_id=report.assigned_officer_id,
            title='Report Status Updated',
            message=f'Report {report.report_id} status changed to {new_status} by {updated_by.first_name} {updated_by.last_name}',
            notification_type='info',
            link=f'/officer/incident/{report.id}'  # Officer link
        )

def get_user_notifications(user_id, limit=50, unread_only=False):
    """Get notifications for a user"""
    query = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(is_read=False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()

def get_unread_count(user_id):
    """Get unread notifications count for a user"""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()

def mark_as_read(notification_id):
    """Mark a specific notification as read"""
    notification = Notification.query.get(notification_id)
    if notification:
        notification.is_read = True
        db.session.commit()
        return True
    return False

def mark_all_as_read(user_id):
    """Mark all notifications as read for a user"""
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return True

def delete_notification(notification_id, user_id):
    """Delete a notification (only if it belongs to the user)"""
    notification = Notification.query.filter_by(
        id=notification_id, 
        user_id=user_id
    ).first()
    
    if notification:
        db.session.delete(notification)
        db.session.commit()
        return True
    return False

def delete_all_read_notifications(user_id):
    """Delete all read notifications for a user"""
    Notification.query.filter_by(
        user_id=user_id, 
        is_read=True
    ).delete()
    db.session.commit()
    return True
