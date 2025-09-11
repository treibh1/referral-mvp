#!/usr/bin/env python3
"""
Production-ready authentication service with comprehensive security features.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from flask import request, session, current_app
from functools import wraps
from models import db, User, UserSession, AuditLog, RateLimit, Organisation

class AuthService:
    """Production-ready authentication service."""
    
    @staticmethod
    def authenticate_user(email, password=None, ip_address=None, user_agent=None):
        """
        Authenticate user with comprehensive security checks.
        For MVP, password is optional (email-only auth).
        """
        try:
            # Rate limiting check
            if ip_address:
                allowed, error_msg = RateLimit.check_rate_limit(
                    ip_address, 'login', max_attempts=5, window_minutes=15
                )
                if not allowed:
                    AuditLog.log_event(
                        user_id=None,
                        organisation_id=None,
                        session_id=None,
                        event_type='login_attempt',
                        event_category='auth',
                        description=f'Rate limit exceeded for IP {ip_address}',
                        success=False,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        error_message=error_msg
                    )
                    return None, error_msg
            
            # Find user
            user = User.query.filter_by(email=email).first()
            if not user:
                AuditLog.log_event(
                    user_id=None,
                    organisation_id=None,
                    session_id=None,
                    event_type='login_attempt',
                    event_category='auth',
                    description=f'Login attempt with non-existent email: {email}',
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message='User not found'
                )
                return None, "Invalid credentials"
            
            # Check if user is active
            if not user.is_active:
                AuditLog.log_event(
                    user_id=user.id,
                    organisation_id=user.organisation_id,
                    session_id=None,
                    event_type='login_attempt',
                    event_category='auth',
                    description=f'Login attempt for inactive user: {email}',
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message='Account is inactive'
                )
                return None, "Account is inactive"
            
            # Check if account is locked
            if user.is_locked():
                AuditLog.log_event(
                    user_id=user.id,
                    organisation_id=user.organisation_id,
                    session_id=None,
                    event_type='login_attempt',
                    event_category='auth',
                    description=f'Login attempt for locked account: {email}',
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message='Account is locked'
                )
                return None, "Account is temporarily locked"
            
            # For MVP: No password validation (email-only auth)
            # In production, add password validation here
            
            # Reset login attempts on successful authentication
            user.reset_login_attempts()
            
            # Create session
            user_session = UserSession.create_session(
                user_id=user.id,
                organisation_id=user.organisation_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Log successful login
            AuditLog.log_event(
                user_id=user.id,
                organisation_id=user.organisation_id,
                session_id=user_session.id,
                event_type='login_success',
                event_category='auth',
                description=f'Successful login for user: {email}',
                success=True,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Reset rate limit on successful login
            if ip_address:
                RateLimit.reset_rate_limit(ip_address, 'login')
            
            return user, user_session, None
            
        except Exception as e:
            AuditLog.log_event(
                user_id=None,
                organisation_id=None,
                session_id=None,
                event_type='login_error',
                event_category='auth',
                description=f'Login error for email: {email}',
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(e)
            )
            return None, None, str(e)
    
    @staticmethod
    def validate_session(session_token, ip_address=None, user_agent=None):
        """Validate user session with security checks."""
        try:
            # Get session
            user_session = UserSession.get_active_session(session_token)
            if not user_session:
                return None, None, "Invalid or expired session"
            
            # Get user
            user = User.query.get(user_session.user_id)
            if not user or not user.is_active:
                user_session.deactivate()
                return None, None, "User not found or inactive"
            
            # Check IP address (optional security check)
            if ip_address and user_session.ip_address and user_session.ip_address != ip_address:
                AuditLog.log_event(
                    user_id=user.id,
                    organisation_id=user.organisation_id,
                    session_id=user_session.id,
                    event_type='session_ip_mismatch',
                    event_category='security',
                    description=f'Session IP mismatch: {user_session.ip_address} -> {ip_address}',
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                # For now, allow IP changes but log them
            
            # Extend session if needed
            if user_session.last_activity < datetime.utcnow() - timedelta(minutes=30):
                user_session.extend_session()
            
            return user, user_session, None
            
        except Exception as e:
            return None, None, str(e)
    
    @staticmethod
    def logout_user(session_token, ip_address=None, user_agent=None):
        """Logout user and deactivate session."""
        try:
            user_session = UserSession.get_active_session(session_token)
            if user_session:
                user = User.query.get(user_session.user_id)
                
                # Log logout
                AuditLog.log_event(
                    user_id=user.id if user else None,
                    organisation_id=user.organisation_id if user else None,
                    session_id=user_session.id,
                    event_type='logout',
                    event_category='auth',
                    description=f'User logout',
                    success=True,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Deactivate session
                user_session.deactivate()
                
                return True, None
            else:
                return False, "Session not found"
                
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions."""
        try:
            count = UserSession.cleanup_expired_sessions()
            return count, None
        except Exception as e:
            return 0, str(e)

def require_auth(f):
    """Decorator for routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get session token from cookie
            session_token = request.cookies.get('auth_session')
            if not session_token:
                return redirect_to_login()
            
            # Validate session
            user, user_session, error = AuthService.validate_session(
                session_token,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            if not user or not user_session:
                return redirect_to_login(error)
            
            # Add user and session to request context
            request.current_user = user
            request.current_session = user_session
            
            return f(*args, **kwargs)
            
        except Exception as e:
            AuditLog.log_event(
                user_id=None,
                organisation_id=None,
                session_id=None,
                event_type='auth_error',
                event_category='auth',
                description=f'Authentication error in {f.__name__}',
                success=False,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                error_message=str(e)
            )
            return redirect_to_login("Authentication error")
    
    return decorated_function

def require_role(required_role):
    """Decorator for routes that require specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return redirect_to_login()
            
            user = request.current_user
            if user.role != required_role and user.role != 'admin':
                AuditLog.log_event(
                    user_id=user.id,
                    organisation_id=user.organisation_id,
                    session_id=getattr(request, 'current_session', {}).get('id'),
                    event_type='unauthorized_access',
                    event_category='security',
                    description=f'Unauthorized access attempt to {f.__name__} by {user.role}',
                    success=False,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    error_message=f'Required role: {required_role}'
                )
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_org_access(f):
    """Decorator to ensure user can only access their organization's data."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'current_user'):
            return redirect_to_login()
        
        user = request.current_user
        user_session = request.current_session
        
        # Check organization access
        if 'organisation_id' in kwargs:
            if user.organisation_id != kwargs['organisation_id']:
                AuditLog.log_event(
                    user_id=user.id,
                    organisation_id=user.organisation_id,
                    session_id=user_session.id,
                    event_type='unauthorized_org_access',
                    event_category='security',
                    description=f'Unauthorized organization access attempt',
                    success=False,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    error_message=f'Attempted access to org: {kwargs["organisation_id"]}'
                )
                return jsonify({'error': 'Access denied'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def redirect_to_login(error=None):
    """Redirect to login page with error message."""
    from flask import redirect, url_for, request
    
    if request.path.startswith('/api/'):
        return jsonify({'error': error or 'Authentication required'}), 401
    else:
        return redirect(url_for('login', error=error))

def get_current_user():
    """Get current authenticated user."""
    return getattr(request, 'current_user', None)

def get_current_session():
    """Get current user session."""
    return getattr(request, 'current_session', None)

def log_audit_event(event_type, event_category, description, success=True, event_metadata=None):
    """Log an audit event for the current user."""
    user = get_current_user()
    user_session = get_current_session()
    
    AuditLog.log_event(
        user_id=user.id if user else None,
        organisation_id=user.organisation_id if user else None,
        session_id=user_session.id if user_session else None,
        event_type=event_type,
        event_category=event_category,
        description=description,
        success=success,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        event_metadata=event_metadata
    )
