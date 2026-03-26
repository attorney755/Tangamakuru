from flask import render_template, current_app
from flask_mail import Message
import os
import traceback

def send_email(to, subject, template, **kwargs):
    """Send an email using Flask-Mail"""
    try:
        # Get the mail instance from the app
        mail = current_app.mail
        
        # Get sender with fallback
        sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
        
        if not sender:
            print("ERROR: No sender email configured")
            return False
        
        print(f"Sending email to: {to}")
        
        # Create message
        msg = Message(
            subject=subject,
            recipients=[to],
            html=render_template(template, **kwargs),
            sender=sender
        )
        
        # Send email
        mail.send(msg)
        print(f"Email sent successfully to {to}")
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        print(traceback.format_exc())
        current_app.logger.error(f"Email sending failed: {str(e)}")
        return False

def send_welcome_email(user):
    """Send welcome email to a new citizen"""
    try:
        print(f"Attempting to send welcome email to {user.email}")
        return send_email(
            to=user.email,
            subject="Welcome to TANGAMAKURU!",
            template="emails/welcome.html",
            user=user
        )
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        print(traceback.format_exc())
        return False


def send_admin_welcome_email(admin, password):
    """Send welcome email to a new admin with their login credentials"""
    try:
        return send_email(
            to=admin.email,
            subject="Welcome to TANGAMAKURU - Your Admin Account",
            template="emails/admin_welcome.html",
            admin=admin,
            password=password
        )
    except Exception as e:
        print(f"Error sending admin welcome email: {e}")
        return False


def send_admin_deactivation_email(admin, reason):
    """Send deactivation email to an admin with reason"""
    try:
        return send_email(
            to=admin.email,
            subject="TANGAMAKURU - Your Admin Account Has Been Deactivated",
            template="emails/admin_deactivation.html",
            admin=admin,
            reason=reason
        )
    except Exception as e:
        print(f"Error sending admin deactivation email: {e}")
        return False


def send_admin_activation_email(admin):
    """Send activation email to an admin"""
    try:
        return send_email(
            to=admin.email,
            subject="TANGAMAKURU - Your Admin Account Has Been Activated",
            template="emails/admin_activation.html",
            admin=admin
        )
    except Exception as e:
        print(f"Error sending admin activation email: {e}")
        return False
