from flask import render_template, current_app
from flask_mail import Message
import os

def send_email(to, subject, template, **kwargs):
    """Send an email using Flask-Mail"""
    try:
        # Get the mail instance from the app
        mail = current_app.mail
        
        # Create message
        msg = Message(
            subject=subject,
            recipients=[to],
            html=render_template(template, **kwargs),
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Send email
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Email sending failed: {str(e)}")
        return False

def send_welcome_email(user):
    """Send welcome email to a new citizen"""
    try:
        return send_email(
            to=user.email,
            subject="Welcome to TANGAMAKURU! 🛡️",
            template="emails/welcome.html",
            user=user
        )
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        return False