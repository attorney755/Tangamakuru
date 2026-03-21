from flask import session, request, redirect, url_for, flash
from datetime import datetime

def init_session_timeout(app):
    """Initialize session timeout checking for all requests"""
    
    @app.before_request
    def check_session_timeout():
        # Skip timeout check for static files and login/register pages
        if request.endpoint in ['static', 'frontend.login', 'frontend.register', 'auth.login', 'auth.register', 'frontend.officer_register_page']:
            return
        
        # Skip check for the session check API endpoint
        if request.endpoint == 'frontend.check_session':
            return
        
        # Skip check for the home page (index)
        if request.endpoint == 'frontend.index':
            return
        
        # If there's no user in session but there was a cookie, redirect to login
        if not session.get('user') and not session.get('pending_user'):
            # Don't flash message here, we'll do it on login page
            return redirect(url_for('frontend.login', timeout=1))
    
    @app.after_request
    def add_no_cache_headers(response):
        """Add headers to prevent page from being restored from cache"""
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response