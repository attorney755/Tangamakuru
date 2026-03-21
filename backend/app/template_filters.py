from datetime import datetime, timedelta

def timeago_filter(dt):
    """Convert datetime to human readable 'time ago' format"""
    if not dt:
        return "Unknown"
    
    now = datetime.utcnow()
    diff = now - dt
    
    if diff < timedelta(seconds=60):
        return "just now"
    elif diff < timedelta(minutes=60):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < timedelta(hours=24):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif diff < timedelta(days=365):
        months = int(diff.days / 30)
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = int(diff.days / 365)
        return f"{years} year{'s' if years > 1 else ''} ago"