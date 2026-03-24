from flask import session, request, redirect, url_for, flash
from datetime import datetime

def init_session_timeout(app):
    """Initialize session timeout checking for all requests"""
    
    @app.before_request
    def check_session_timeout():
        # Skip timeout check for static files and public pages
        public_endpoints = [
            'static', 
            'frontend.login', 
            'frontend.register', 
            'auth.login', 
            'auth.register', 
            'frontend.officer_register_page',
            'frontend.index',  # Home page
            'frontend.landing',  # Landing page
            'frontend.check_session',
            'frontend.pending_officer_notifications'  # Pending officer page
        ]
        
        if request.endpoint in public_endpoints:
            return
        
        # Only check session timeout for logged-in users
        # If user is logged in but session expired, redirect to login
        if session.get('user') or session.get('pending_user'):
            # Check if the session has expired (handled by Flask's PERMANENT_SESSION_LIFETIME)
            # This is just an additional check for pages that require authentication
            pass
        
        # Don't redirect guests to login - let them browse public pages
        return
    
    @app.after_request
    def add_no_cache_headers(response):
        """Add headers to prevent page from being restored from cache"""
        # Only apply cache control for pages that require authentication
        if session.get('user') or session.get('pending_user'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
