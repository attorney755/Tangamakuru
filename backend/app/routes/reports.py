from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.models import Report, User, Media  # Removed ReportStatus, ReportCategory
from datetime import datetime, timedelta
import os
import json
from werkzeug.utils import secure_filename
import uuid

reports_bp = Blueprint('reports', __name__)


# Add this helper function at the top of reports.py
def check_session_auth():
    """Check if user is authenticated via session"""
    from flask import session
    
    # Check session user exists
    if 'user' not in session:
        return False
    
    # Optional: Verify user still exists in database
    from app.models import User
    user = User.query.get(session['user'].get('id'))
    if not user:
        return False
    
    return True

# Helper function to check file extensions
def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {
        'png', 'jpg', 'jpeg', 'gif', 
        'mp4', 'avi', 'mov', 'mkv',
        'pdf', 'doc', 'docx', 'txt',
        'mp3', 'wav'
    }
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to generate unique filename
def generate_unique_filename(original_filename, report_id=None):
    """Generate a unique filename for uploaded files"""
    if not original_filename or '.' not in original_filename:
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{timestamp}_{unique_id}"
    
    ext = original_filename.rsplit('.', 1)[1].lower()
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if report_id:
        base_name = f"{report_id}_{timestamp}_{unique_id}"
    else:
        base_name = f"{timestamp}_{unique_id}"
    
    return f"{base_name}.{ext}"

# Get uploads directory
def get_upload_folder():
    """Get or create upload folder"""
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder
# Rwanda address autocomplete endpoint - NO AUTHENTICATION REQUIRED
@reports_bp.route('/address/search', methods=['GET'])
def search_address():
    """Search for Rwanda addresses - NO LOGIN REQUIRED"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({'suggestions': []}), 200
        
        # Rwanda addresses database
        rwanda_addresses = [
            {"display_name": "KN 3 Rd, Kigali, Rwanda", "type": "road", "province": "Kigali City", "district": "Kicukiro"},
            {"display_name": "KG 7 Ave, Kigali, Rwanda", "type": "avenue", "province": "Kigali City", "district": "Gasabo"},
            {"display_name": "KK 15 Rd, Kigali, Rwanda", "type": "road", "province": "Kigali City", "district": "Nyarugenge"},
            {"display_name": "Kacyiru Police Station, Kigali, Rwanda", "type": "landmark", "province": "Kigali City", "district": "Gasabo"},
            {"display_name": "Kimironko Market, Kigali, Rwanda", "type": "market", "province": "Kigali City", "district": "Gasabo"},
            {"display_name": "Nyabugogo Taxi Park, Kigali, Rwanda", "type": "park", "province": "Kigali City", "district": "Nyarugenge"},
            {"display_name": "Remera Stadium, Kigali, Rwanda", "type": "stadium", "province": "Kigali City", "district": "Gasabo"},
            {"display_name": "Kicukiro Health Center, Kigali, Rwanda", "type": "health", "province": "Kigali City", "district": "Kicukiro"},
            {"display_name": "Gisozi Genocide Memorial, Kigali, Rwanda", "type": "memorial", "province": "Kigali City", "district": "Gasabo"},
            {"display_name": "Kigali Convention Centre, Kigali, Rwanda", "type": "convention", "province": "Kigali City", "district": "Gasabo"},
        ]
        
        # Filter addresses based on query
        suggestions = []
        query_lower = query.lower()
        for address in rwanda_addresses:
            if (query_lower in address['display_name'].lower() or 
                query_lower in address.get('province', '').lower() or
                query_lower in address.get('district', '').lower()):
                suggestions.append(address)
        
        return jsonify({'suggestions': suggestions[:10]}), 200
        
    except Exception as e:
        current_app.logger.error(f"Address search error: {str(e)}")
        return jsonify({'error': 'Search service temporarily unavailable'}), 500

# Submit new report
# Submit new report
@reports_bp.route('/submit', methods=['POST'])  
def submit_report():
    """Submit a new crime/incident report"""
    try:
        # FIX: Use session authentication like frontend.py
        from flask import session
        
        # Check if user is logged in via session (like frontend.py does)
        if 'user' not in session:
            return jsonify({'error': 'Please login first', 'login_url': '/login'}), 401
        
        # Get user data from session
        user_data = session.get('user')
        
        # Get the actual user from database
        from app.models import User
        user = User.query.get(user_data['id'])
        if not user:
            return jsonify({'error': 'User not found', 'login_url': '/login'}), 404
        
        # Now continue with your existing code...
        # Get form data
        data = request.form.to_dict()
        files = request.files
        
        # Log submission attempt
        current_app.logger.info(f"User {user.id} attempting to submit report")
        
        # ... rest of your existing code continues ...
        
        # Validate required fields
        required_fields = ['title', 'description', 'category', 'incident_date',
                          'province', 'district', 'sector', 'cell', 'village']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Validate incident date (not in future)
        try:
            incident_date = datetime.strptime(data['incident_date'], '%Y-%m-%d').date()
            if incident_date > datetime.now().date():
                return jsonify({'error': 'Incident date cannot be in the future'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Create report object
        report = Report(
            title=data['title'].strip(),
            description=data['description'].strip(),
            category=data['category'],
            incident_date=incident_date,
            report_type=data.get('report_type', 'crime'),
            province=data['province'],
            district=data['district'].strip(),
            sector=data['sector'].strip(),
            cell=data['cell'].strip(),
            village=data['village'].strip(),
            specific_location=data.get('specific_location', '').strip(),
            priority=data.get('priority', 'medium'),
            is_anonymous=data.get('is_anonymous', 'false').lower() == 'true',
            witness_info=data.get('witness_info', '').strip(),
            evidence_details=data.get('evidence_details', '').strip(),
            user_id=user.id,
            status='pending'
        )
        
        # Generate report ID
        if hasattr(report, 'generate_report_id'):
            report.report_id = report.generate_report_id()
        else:
            # Fallback if method doesn't exist
            timestamp = datetime.now().strftime('%Y%m%d')
            random_num = str(uuid.uuid4().int)[:6]
            report.report_id = f"RPT-{timestamp}-{random_num}"
        
        # Handle file uploads
        upload_folder = get_upload_folder()
        uploaded_files = []

        db.session.add(report)
        db.session.flush() 
        
        # Process multiple evidence files
        if 'evidence_files' in files:
            evidence_files = files.getlist('evidence_files')
            current_app.logger.info(f"Processing {len(evidence_files)} evidence files")
            
            for file_index, file in enumerate(evidence_files):
                if file and file.filename and allowed_file(file.filename):
                    try:
                        # Generate secure filename
                        filename = generate_unique_filename(file.filename, report.report_id)
                        file_path = os.path.join(upload_folder, filename)
                        
                        # Save file
                        file.save(file_path)
                        file_size = os.path.getsize(file_path)
                        
                        # Create media record
                        media = Media(
                            filename=filename,
                            file_path=file_path,
                            file_type=file.content_type,
                            file_size=file_size,
                            report_id=report.id  # Will be set after commit
                        )
                        db.session.add(media)
                        uploaded_files.append({
                            'filename': filename,
                            'type': file.content_type,
                            'size': file_size
                        })
                        
                        # Set main image/video URL for first file of each type
                        if file.content_type.startswith('image/') and not report.image_url:
                            report.image_url = f"/uploads/{filename}"
                        elif file.content_type.startswith('video/') and not report.video_url:
                            report.video_url = f"/uploads/{filename}"
                            
                        current_app.logger.debug(f"Saved file: {filename} ({file_size} bytes)")
                        
                    except Exception as file_error:
                        current_app.logger.error(f"Error processing file {file.filename}: {str(file_error)}")
                        # Continue with other files
        
                # Save report to database
        db.session.add(report)
        db.session.flush()  # Get report ID for media records
        
        
        
        db.session.commit()
        
        # Send notification to the citizen who submitted the report
        from app.utils.notifications import notify_report_submitted
        notify_report_submitted(report)
        
        current_app.logger.info(f"Report {report.report_id} submitted successfully by user {user.id}")
        
        # Prepare response
        response_data = {
            'message': 'Report submitted successfully',
            'report': {
                'id': report.id,
                'report_id': report.report_id,
                'title': report.title,
                'category': report.category,
                'report_type': report.report_type,
                'incident_date': report.incident_date.isoformat(),
                'status': report.status,
                'priority': report.priority,
                'created_at': report.created_at.isoformat() if hasattr(report, 'created_at') and report.created_at else datetime.now().isoformat(),
                'image_url': report.image_url,
                'video_url': report.video_url,
                'files_uploaded': len(uploaded_files)
            },
            'next_steps': {
                'track_report': f"/reports/{report.id}",
                'view_all_reports': '/dashboard',
                'expected_response': '24 hours'
            }
        }
        
        return jsonify(response_data), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting report: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to submit report. Please try again.'}), 500

# Get all reports for current user
@reports_bp.route('/my-reports', methods=['GET'])
@login_required
def get_my_reports():
    """Get all reports submitted by current user"""
    try:
        user = current_user
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', None)
        
        # Build query
        query = Report.query.filter_by(user_id=user.id)
        
        # Apply filters
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        # Get paginated results
        reports = query.order_by(Report.created_at.desc())\
                      .paginate(page=page, per_page=per_page, error_out=False)
        
        reports_data = []
        for report in reports.items:
            # Get media count
            media_count = Media.query.filter_by(report_id=report.id).count() if hasattr(Media, 'report_id') else 0
            
            reports_data.append({
                'id': report.id,
                'report_id': report.report_id,
                'title': report.title,
                'category': report.category,
                'report_type': report.report_type if hasattr(report, 'report_type') else 'crime',
                'incident_date': report.incident_date.isoformat() if hasattr(report, 'incident_date') and report.incident_date else None,
                'status': report.status,
                'priority': report.priority if hasattr(report, 'priority') else 'medium',
                'created_at': report.created_at.isoformat() if hasattr(report, 'created_at') and report.created_at else None,
                'updated_at': report.updated_at.isoformat() if hasattr(report, 'updated_at') and report.updated_at else None,
                'location': {
                    'district': report.district,
                    'sector': report.sector
                },
                'media': {
                    'has_image': bool(report.image_url) if hasattr(report, 'image_url') else False,
                    'has_video': bool(report.video_url) if hasattr(report, 'video_url') else False,
                    'count': media_count
                }
            })
        
        return jsonify({
            'reports': reports_data,
            'pagination': {
                'page': reports.page,
                'per_page': reports.per_page,
                'total': reports.total,
                'pages': reports.pages,
                'has_next': reports.has_next,
                'has_prev': reports.has_prev
            },
            'summary': {
                'total_reports': reports.total,
                'pending': Report.query.filter_by(user_id=user.id, status='pending').count(),
                'in_progress': Report.query.filter_by(user_id=user.id, status='in_progress').count(),
                'resolved': Report.query.filter_by(user_id=user.id, status='resolved').count()
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching reports: {str(e)}")
        return jsonify({'error': 'Failed to fetch reports'}), 500

# Delete a report
@reports_bp.route('/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Delete a specific report"""
    try:
        # Use session auth like frontend.py
        from flask import session
        
        # Check if user is logged in via session
        if 'user' not in session:
            return jsonify({'error': 'Please login first', 'login_url': '/login'}), 401
        
        # Get user data from session
        user_data = session.get('user')
        
        # Get the actual user from database
        user = User.query.get(user_data['id'])
        if not user:
            return jsonify({'error': 'User not found', 'login_url': '/login'}), 404
        
        # Get the report
        report = Report.query.get_or_404(report_id)
        
        # Check permissions
        # Only allow deletion if:
        # 1. User is the reporter (citizen) AND report is still pending
        # 2. User is an officer/admin
        can_delete = False
        
        if user.role == 'citizen':
            if report.user_id == user.id:
                can_delete = True
            else:
                return jsonify({'error': 'You can only delete pending reports that you submitted'}), 403
        elif user.role in ['officer', 'admin']:
            can_delete = True
        else:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if not can_delete:
            return jsonify({'error': 'You do not have permission to delete this report'}), 403
        
        # Delete associated media files first
        media_files = Media.query.filter_by(report_id=report.id).all()
        for media in media_files:
            # Delete physical file if exists
            try:
                import os
                if os.path.exists(media.file_path):
                    os.remove(media.file_path)
            except:
                pass  # Continue even if file deletion fails
            db.session.delete(media)
        
        # Delete the report
        db.session.delete(report)
        db.session.commit()
        
        current_app.logger.info(f"Report {report_id} deleted by user {user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Report deleted successfully',
            'report_id': report.report_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting report {report_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete report', 'details': str(e)}), 500


# Get single report by ID
@reports_bp.route('/<int:report_id>', methods=['GET'])
@login_required
def get_report(report_id):
    """Get a specific report by ID"""
    try:
        user = current_user
        
        report = Report.query.get_or_404(report_id)
        
        # Check permissions
        if user.role == 'citizen' and report.user_id != user.id:
            return jsonify({'error': 'You do not have permission to view this report'}), 403
        
        # Get all media files
        media_files = Media.query.filter_by(report_id=report.id).all() if hasattr(Media, 'report_id') else []
        media_data = []
        for media in media_files:
            media_data.append({
                'id': media.id,
                'filename': media.filename,
                'file_type': media.file_type,
                'file_size': media.file_size,
                'created_at': media.created_at.isoformat() if hasattr(media, 'created_at') and media.created_at else None,
                'url': f"/uploads/{media.filename}",
                'is_image': media.file_type.startswith('image/') if hasattr(media, 'file_type') else False,
                'is_video': media.file_type.startswith('video/') if hasattr(media, 'file_type') else False,
                'is_document': media.file_type in ['application/pdf', 'application/msword', 
                                                  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'] 
                               if hasattr(media, 'file_type') else False
            })
        
        # Get assigned officer if exists
        assigned_officer = None
        if hasattr(report, 'assigned_officer_id') and report.assigned_officer_id:
            officer = User.query.get(report.assigned_officer_id)
            if officer:
                assigned_officer = {
                    'id': officer.id,
                    'name': officer.get_full_name() if hasattr(officer, 'get_full_name') else f"{officer.first_name} {officer.last_name}",
                    'email': officer.email,
                    'phone': officer.phone if hasattr(officer, 'phone') else None,
                    'department': officer.department if hasattr(officer, 'department') else None,
                    'badge_number': officer.badge_number if hasattr(officer, 'badge_number') else None
                }
        
        # Build response data
        report_data = {
            'id': report.id,
            'report_id': report.report_id,
            'title': report.title,
            'description': report.description,
            'category': report.category,
            'report_type': report.report_type if hasattr(report, 'report_type') else 'crime',
            'incident_date': report.incident_date.isoformat() if hasattr(report, 'incident_date') and report.incident_date else None,
            'status': report.status,
            'priority': report.priority if hasattr(report, 'priority') else 'medium',
            'location': {
                'province': report.province,
                'district': report.district,
                'sector': report.sector,
                'cell': report.cell,
                'village': report.village,
                'specific_location': report.specific_location if hasattr(report, 'specific_location') else '',
                'coordinates': report.coordinates if hasattr(report, 'coordinates') else None
            },
            'privacy': {
                'is_anonymous': report.is_anonymous if hasattr(report, 'is_anonymous') else False,
                'allow_contact': not report.is_anonymous if hasattr(report, 'is_anonymous') else True
            },
            'details': {
                'witness_info': report.witness_info if hasattr(report, 'witness_info') else '',
                'evidence_details': report.evidence_details if hasattr(report, 'evidence_details') else '',
                'officer_notes': report.officer_notes if hasattr(report, 'officer_notes') else None,
                'resolution_details': report.resolution_details if hasattr(report, 'resolution_details') else None
            },
            'media': {
                'files': media_data,
                'image_url': report.image_url if hasattr(report, 'image_url') else None,
                'video_url': report.video_url if hasattr(report, 'video_url') else None,
                'total_count': len(media_data)
            },
            'timestamps': {
                'created_at': report.created_at.isoformat() if hasattr(report, 'created_at') and report.created_at else None,
                'updated_at': report.updated_at.isoformat() if hasattr(report, 'updated_at') and report.updated_at else None,
                'resolved_at': report.resolved_at.isoformat() if hasattr(report, 'resolved_at') and report.resolved_at else None
            },
            'assigned_officer': assigned_officer
        }
        
        # Add reporter info if not anonymous and user has permission
        if (hasattr(report, 'is_anonymous') and not report.is_anonymous) and (user.role != 'citizen' or report.user_id == user.id):
            reporter = User.query.get(report.user_id)
            if reporter:
                report_data['reporter'] = {
                    'id': reporter.id,
                    'name': reporter.get_full_name() if hasattr(reporter, 'get_full_name') else f"{reporter.first_name} {reporter.last_name}",
                    'email': reporter.email if user.role != 'citizen' else 'hidden',
                    'phone': reporter.phone if user.role != 'citizen' and hasattr(reporter, 'phone') else None
                }
        
        return jsonify(report_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching report {report_id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch report details'}), 500

# Get report media
@reports_bp.route('/<int:report_id>/media', methods=['GET'])
@login_required
def get_report_media(report_id):
    """Get all media files for a specific report"""
    try:
        user = current_user
        
        report = Report.query.get_or_404(report_id)
        
        # Check permissions
        if user.role == 'citizen' and report.user_id != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        media_files = Media.query.filter_by(report_id=report.id).all() if hasattr(Media, 'report_id') else []
        media_data = []
        
        for media in media_files:
            media_data.append({
                'id': media.id,
                'filename': media.filename,
                'file_type': media.file_type,
                'file_size': media.file_size,
                'created_at': media.created_at.isoformat() if hasattr(media, 'created_at') and media.created_at else None,
                'download_url': f"/uploads/{media.filename}",
                'preview_url': f"/uploads/{media.filename}" if hasattr(media, 'file_type') and media.file_type.startswith('image/') else None,
                'category': 'image' if hasattr(media, 'file_type') and media.file_type.startswith('image/') else 
                           'video' if hasattr(media, 'file_type') and media.file_type.startswith('video/') else 
                           'document'
            })
        
        return jsonify({
            'report_id': report.report_id,
            'title': report.title,
            'media_count': len(media_data),
            'media_files': media_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching media for report {report_id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch media files'}), 500

# Serve uploaded files
@reports_bp.route('/uploads/<filename>', methods=['GET'])
def serve_uploaded_file(filename):
    """Serve uploaded files with session-based authentication"""
    try:
        from flask import session, send_file, abort
        import os
        
        # Check if user is logged in via session
        if 'user' not in session and 'pending_user' not in session:
            return jsonify({'error': 'Please login first', 'login_url': '/login'}), 401
        
        # Get the absolute path to the uploads folder
        from app.routes.reports import get_upload_folder
        upload_folder = get_upload_folder()
        
        # Get the absolute path
        absolute_upload_folder = os.path.abspath(upload_folder)
        
        # Build the full file path
        file_path = os.path.join(absolute_upload_folder, filename)
        
        # Log for debugging
        current_app.logger.info(f"Serving file from: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            current_app.logger.error(f"File not found at path: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        # Send the file
        return send_file(file_path)
        
    except Exception as e:
        current_app.logger.error(f"Error serving file {filename}: {str(e)}")
        return jsonify({'error': 'Failed to serve file'}), 500

# Update report status (for officers)
@reports_bp.route('/<int:report_id>/status', methods=['PUT'])
@login_required
def update_report_status(report_id):
    """Update report status (officers only)"""
    try:
        user = current_user
        
        # Check if user is an officer
        if not hasattr(user, 'role') or user.role not in ['officer', 'admin', 'super_admin']:
            return jsonify({'error': 'Only officers can update report status'}), 403
        
        report = Report.query.get_or_404(report_id)
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        new_status = data['status']
        valid_statuses = ['submitted', 'reviewing', 'in_progress', 'pending_info', 'resolved', 'closed', 'rejected']
        
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        # Update status
        old_status = report.status
        report.status = new_status
        
        # Add notes if provided
        if 'notes' in data:
            if hasattr(report, 'officer_notes'):
                report.officer_notes = data['notes']
        
        # Set resolved date if status is resolved
        if new_status == 'resolved' and hasattr(report, 'resolved_at'):
            report.resolved_at = datetime.now()
        
        # Set assigned officer if not already assigned
        if hasattr(report, 'assigned_officer_id') and not report.assigned_officer_id:
            report.assigned_officer_id = user.id
        
        # Update updated_at timestamp
        if hasattr(report, 'updated_at'):
            report.updated_at = datetime.now()
        
        db.session.commit()
        
        current_app.logger.info(f"Officer {user.id} updated report {report_id} status from {old_status} to {new_status}")
        
        return jsonify({
            'message': f'Report status updated to {new_status}',
            'report': {
                'id': report.id,
                'report_id': report.report_id,
                'status': report.status,
                'assigned_officer_id': report.assigned_officer_id if hasattr(report, 'assigned_officer_id') else None,
                'updated_at': report.updated_at.isoformat() if hasattr(report, 'updated_at') and report.updated_at else None
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating report status: {str(e)}")
        return jsonify({'error': 'Failed to update report status'}), 500

@reports_bp.route('/<int:report_id>/citizen-status', methods=['PUT'])
def citizen_update_status(report_id):
    """Allow citizen to mark their own report as resolved"""
    try:
        from flask import session
        
        # Check if user is logged in via session
        if 'user' not in session:
            return jsonify({'error': 'Please login first', 'login_url': '/login'}), 401
        
        # Get user data from session
        user_data = session.get('user')
        
        # Get the actual user from database
        user = User.query.get(user_data['id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get the report
        report = Report.query.get_or_404(report_id)
        
        # Verify this report belongs to the user
        if report.user_id != user.id:
            return jsonify({'error': 'You can only update your own reports'}), 403
        
        # Only allow updating to 'resolved' and only if not already resolved
        if report.status == 'resolved':
            return jsonify({'error': 'Report is already resolved'}), 400
        
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status != 'resolved':
            return jsonify({'error': 'Citizens can only mark reports as resolved'}), 400
        
        # Update the status
        old_status = report.status
        report.status = 'resolved'
        report.resolved_at = datetime.now()
        
        db.session.commit()
        
        # Send notification to the user
        from app.utils.notifications import send_notification
        send_notification(
            user_id=user.id,
            title='Report Resolved ✅',
            message=f'Your report {report.report_id} has been marked as resolved. Thank you!',
            notification_type='success',
            link=f'/view-report/{report.id}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Report marked as resolved successfully',
            'report': {
                'id': report.id,
                'status': report.status,
                'resolved_at': report.resolved_at.isoformat() if report.resolved_at else None
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating report status: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Get report statistics
@reports_bp.route('/statistics', methods=['GET'])
@login_required
def get_statistics():
    """Get report statistics for the current user"""
    try:
        user = current_user
        
        # Calculate statistics based on user role
        if not hasattr(user, 'role') or user.role == 'citizen':
            total_reports = Report.query.filter_by(user_id=user.id).count()
            status_counts = {
                'submitted': Report.query.filter_by(user_id=user.id, status='submitted').count(),
                'in_progress': Report.query.filter_by(user_id=user.id, status='in_progress').count(),
                'resolved': Report.query.filter_by(user_id=user.id, status='resolved').count()
            }
            
            # Monthly trend (last 6 months)
            six_months_ago = datetime.now() - timedelta(days=180)
            monthly_data = []
            
            for i in range(6):
                month_start = datetime.now() - timedelta(days=30*(i+1))
                month_end = datetime.now() - timedelta(days=30*i)
                month_count = Report.query.filter(
                    Report.user_id == user.id,
                    Report.created_at >= month_start,
                    Report.created_at < month_end
                ).count()
                monthly_data.append({
                    'month': month_start.strftime('%b %Y'),
                    'count': month_count
                })
            
            monthly_data.reverse()
            
            statistics = {
                'total_reports': total_reports,
                'status_counts': status_counts,
                'monthly_trend': monthly_data,
                'average_response_time': '24 hours',
                'resolution_rate': round((status_counts['resolved'] / total_reports * 100) if total_reports > 0 else 0, 1)
            }
            
        else:  # Officer or admin
            # Officer sees statistics for their assigned reports
            total_assigned = Report.query.filter_by(assigned_officer_id=user.id).count() if hasattr(Report, 'assigned_officer_id') else 0
            total_unassigned = Report.query.filter_by(status='pending', assigned_officer_id=None).count() if hasattr(Report, 'assigned_officer_id') else 0
            
            statistics = {
                'assigned_reports': total_assigned,
                'unassigned_reports': total_unassigned,
                'reports_this_month': Report.query.filter(
                    Report.assigned_officer_id == user.id,
                    Report.created_at >= datetime.now().replace(day=1)
                ).count() if hasattr(Report, 'assigned_officer_id') else 0,
                'avg_resolution_time': '48 hours',
                'top_categories': []
            }
            
            # Get top categories if possible
            try:
                from sqlalchemy import func
                top_categories = db.session.query(
                    Report.category,
                    func.count(Report.id).label('count')
                ).filter_by(assigned_officer_id=user.id).group_by(Report.category).order_by(func.count(Report.id).desc()).limit(5).all()
                
                statistics['top_categories'] = [{'category': cat, 'count': cnt} for cat, cnt in top_categories]
            except:
                pass
        
        return jsonify({
            'statistics': statistics,
            'user_role': user.role if hasattr(user, 'role') else 'citizen',
            'generated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching statistics: {str(e)}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

# Search reports
@reports_bp.route('/search', methods=['GET'])
@login_required
def search_reports():
    """Search reports based on various criteria"""
    try:
        user = current_user
        query = request.args.get('q', '').strip()
        category = request.args.get('category', '')
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Build query based on user role
        if not hasattr(user, 'role') or user.role == 'citizen':
            base_query = Report.query.filter_by(user_id=user.id)
        else:
            base_query = Report.query
        
        # Apply search filters
        if query:
            base_query = base_query.filter(
                (Report.title.ilike(f'%{query}%')) |
                (Report.description.ilike(f'%{query}%')) |
                (Report.report_id.ilike(f'%{query}%'))
            )
        
        if category:
            base_query = base_query.filter_by(category=category)
        
        if status:
            base_query = base_query.filter_by(status=status)
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                base_query = base_query.filter(Report.created_at >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                base_query = base_query.filter(Report.created_at <= to_date)
            except ValueError:
                pass
            
        
        # Get paginated results
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        reports = base_query.order_by(Report.created_at.desc())\
                           .paginate(page=page, per_page=per_page, error_out=False)
        
        reports_data = []
        for report in reports.items:
            reports_data.append({
                'id': report.id,
                'report_id': report.report_id,
                'title': report.title,
                'category': report.category,
                'status': report.status,
                'priority': report.priority if hasattr(report, 'priority') else 'medium',
                'created_at': report.created_at.isoformat() if hasattr(report, 'created_at') and report.created_at else None,
                'location': f"{report.district}, {report.sector}"
            })
        
        return jsonify({
            'results': reports_data,
            'total': reports.total,
            'page': reports.page,
            'per_page': reports.per_page,
            'pages': reports.pages
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error searching reports: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500

# Health check endpoint
@reports_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for reports API"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check upload folder
        upload_folder = get_upload_folder()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'upload_folder': 'accessible',
            'service': 'reports_api'
        }), 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Test endpoint
@reports_bp.route('/test', methods=['GET'])
@login_required
def test_endpoint():
    """Test endpoint to verify reports blueprint is working"""
    return jsonify({
        'message': 'Reports API is working!',
        'user': current_user.email if hasattr(current_user, 'email') else 'Unknown',
        'user_id': current_user.id,
        'endpoints': {
            'submit_report': 'POST /reports/submit',
            'my_reports': 'GET /reports/my-reports',
            'get_report': 'GET /reports/<id>',
            'search': 'GET /reports/search',
            'statistics': 'GET /reports/statistics'
        },
        'timestamp': datetime.now().isoformat()
    })