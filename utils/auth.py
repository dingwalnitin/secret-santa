# utils/auth.py
from functools import wraps
from flask import session, abort
from datetime import datetime, timedelta
from models import LoginAttempt

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            # show 404 for unauthorised access
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # show 404 for unauthorised access
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

def check_rate_limit(ip_address, max_attempts=5, window_minutes=15):
    """Check if IP has exceeded login attempts"""
    cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)

    recent_attempts = LoginAttempt.query.filter(
        LoginAttempt.ip_address == ip_address,
        LoginAttempt.timestamp > cutoff_time,
        LoginAttempt.success == False
    ).count()

    return recent_attempts < max_attempts

def log_login_attempt(ip_address, email, success):
    """Log a login attempt"""
    attempt = LoginAttempt(
        ip_address=ip_address,
        email=email,
        success=success
    )
    from models import db
    db.session.add(attempt)
    db.session.commit()
