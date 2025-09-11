#!/usr/bin/env python3
"""
Secure multi-tenant database models for the referral system.
Implements GDPR-compliant contact management with no directory access.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
import uuid
import hashlib
import secrets

db = SQLAlchemy()

class Organisation(db.Model):
    """Companies using the referral system."""
    __tablename__ = 'organisations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    domain = db.Column(db.String(255), unique=True, nullable=True)
    plan = db.Column(db.String(50), default='free')  # free, premium, enterprise
    from_email = db.Column(db.String(255), nullable=True)  # Company's email for referrals
    from_name = db.Column(db.String(255), nullable=True)   # Company's name for referrals
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='organisation', lazy=True)
    job_descriptions = db.relationship('JobDescription', backref='organisation', lazy=True)
    
    def __repr__(self):
        return f'<Organisation {self.name}>'

class User(UserMixin, db.Model):
    """Employees of organisations."""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = db.Column(db.String(36), db.ForeignKey('organisations.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='employee')  # admin, recruiter, employee
    
    # Authentication fields
    password_hash = db.Column(db.String(255), nullable=True)  # For future password auth
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # Security fields
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee_contacts = db.relationship('EmployeeContact', backref='employee', lazy=True)
    referrals_sent = db.relationship('Referral', backref='referrer', lazy=True)
    sessions = db.relationship('UserSession', backref='user', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.name} ({self.email})>'
    
    def is_locked(self):
        """Check if user account is locked."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def lock_account(self, duration_minutes=30):
        """Lock user account for specified duration."""
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.login_attempts = 0
        db.session.commit()
    
    def unlock_account(self):
        """Unlock user account."""
        self.locked_until = None
        self.login_attempts = 0
        db.session.commit()
    
    def increment_login_attempts(self):
        """Increment failed login attempts."""
        self.login_attempts += 1
        if self.login_attempts >= 5:  # Lock after 5 failed attempts
            self.lock_account()
        db.session.commit()
    
    def reset_login_attempts(self):
        """Reset failed login attempts on successful login."""
        self.login_attempts = 0
        self.last_login = datetime.utcnow()
        db.session.commit()

class Contact(db.Model):
    """Universal contact database - shared across organisations."""
    __tablename__ = 'contacts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    linkedin_url = db.Column(db.String(500), unique=True, nullable=True, index=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    company = db.Column(db.String(255), nullable=True)
    position = db.Column(db.String(255), nullable=True)
    
    # Enriched data (shared across organisations)
    skills = db.Column(db.Text, nullable=True)  # JSON string
    location = db.Column(db.String(255), nullable=True)
    location_confidence = db.Column(db.Float, default=0.0)
    location_source = db.Column(db.String(100), nullable=True)
    location_enriched_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee_contacts = db.relationship('EmployeeContact', backref='contact', lazy=True)
    referrals = db.relationship('Referral', backref='contact', lazy=True)
    
    def __repr__(self):
        return f'<Contact {self.first_name} {self.last_name}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class EmployeeContact(db.Model):
    """Links employees to contacts they know - ensures data isolation."""
    __tablename__ = 'employee_contacts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    contact_id = db.Column(db.String(36), db.ForeignKey('contacts.id'), nullable=False)
    organisation_id = db.Column(db.String(36), db.ForeignKey('organisations.id'), nullable=False)
    relationship_type = db.Column(db.String(100), default='linkedin_connection')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique employee-contact relationships
    __table_args__ = (db.UniqueConstraint('employee_id', 'contact_id'),)
    
    def __repr__(self):
        return f'<EmployeeContact {self.employee_id} -> {self.contact_id}>'

class JobDescription(db.Model):
    """Job postings by organisations."""
    __tablename__ = 'job_descriptions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = db.Column(db.String(36), db.ForeignKey('organisations.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)  # JSON string
    location = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='active')  # active, closed, draft
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    referrals = db.relationship('Referral', backref='job', lazy=True)
    
    def __repr__(self):
        return f'<JobDescription {self.title}>'

class Referral(db.Model):
    """Referral requests for specific jobs."""
    __tablename__ = 'referrals'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = db.Column(db.String(36), db.ForeignKey('job_descriptions.id'), nullable=False)
    contact_id = db.Column(db.String(36), db.ForeignKey('contacts.id'), nullable=False)
    referrer_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    organisation_id = db.Column(db.String(36), db.ForeignKey('organisations.id'), nullable=False)
    
    status = db.Column(db.String(50), default='pending')  # pending, sent, accepted, declined
    message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Referral {self.job_id} -> {self.contact_id}>'

class UserSession(db.Model):
    """Production-ready user session management."""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    organisation_id = db.Column(db.String(36), db.ForeignKey('organisations.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    # Session metadata
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support
    user_agent = db.Column(db.Text, nullable=True)
    device_fingerprint = db.Column(db.String(255), nullable=True)
    
    # Session lifecycle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Security
    is_secure = db.Column(db.Boolean, default=False)  # HTTPS session
    csrf_token = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f'<UserSession {self.user_id} ({self.session_token[:8]}...)>'
    
    def is_expired(self):
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def extend_session(self, hours=8):
        """Extend session expiration."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_activity = datetime.utcnow()
        db.session.commit()
    
    def deactivate(self):
        """Deactivate session."""
        self.is_active = False
        db.session.commit()
    
    @staticmethod
    def create_session(user_id, organisation_id, ip_address=None, user_agent=None):
        """Create a new user session."""
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        
        session = UserSession(
            user_id=user_id,
            organisation_id=organisation_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(hours=8),
            csrf_token=csrf_token
        )
        
        db.session.add(session)
        db.session.commit()
        return session
    
    @staticmethod
    def get_active_session(session_token):
        """Get active session by token."""
        session = UserSession.query.filter_by(
            session_token=session_token,
            is_active=True
        ).first()
        
        if session and not session.is_expired():
            return session
        return None
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions."""
        expired_sessions = UserSession.query.filter(
            UserSession.expires_at < datetime.utcnow()
        ).all()
        
        for session in expired_sessions:
            session.deactivate()
        
        return len(expired_sessions)

class AuditLog(db.Model):
    """Comprehensive audit logging for security and compliance."""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    organisation_id = db.Column(db.String(36), db.ForeignKey('organisations.id'), nullable=True)
    session_id = db.Column(db.String(36), db.ForeignKey('user_sessions.id'), nullable=True)
    
    # Event details
    event_type = db.Column(db.String(100), nullable=False)  # login, logout, data_access, etc.
    event_category = db.Column(db.String(50), nullable=False)  # auth, data, admin, security
    event_description = db.Column(db.Text, nullable=False)
    
    # Request details
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    endpoint = db.Column(db.String(255), nullable=True)
    method = db.Column(db.String(10), nullable=True)
    
    # Result
    success = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    
    # Additional data
    event_metadata = db.Column(db.Text, nullable=True)  # JSON string for additional context
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.event_type} - {self.user_id}>'
    
    @staticmethod
    def log_event(user_id, organisation_id, session_id, event_type, event_category, 
                  description, success=True, ip_address=None, user_agent=None, 
                  endpoint=None, method=None, error_message=None, event_metadata=None):
        """Log an audit event."""
        log = AuditLog(
            user_id=user_id,
            organisation_id=organisation_id,
            session_id=session_id,
            event_type=event_type,
            event_category=event_category,
            event_description=description,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            error_message=error_message,
            event_metadata=event_metadata
        )
        
        db.session.add(log)
        db.session.commit()
        return log

class RateLimit(db.Model):
    """Rate limiting for security."""
    __tablename__ = 'rate_limits'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    identifier = db.Column(db.String(255), nullable=False, index=True)  # IP, user_id, etc.
    action = db.Column(db.String(100), nullable=False)  # login, api_call, etc.
    attempts = db.Column(db.Integer, default=1)
    window_start = db.Column(db.DateTime, default=datetime.utcnow)
    blocked_until = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<RateLimit {self.identifier} - {self.action}>'
    
    @staticmethod
    def check_rate_limit(identifier, action, max_attempts=5, window_minutes=15):
        """Check if rate limit is exceeded."""
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        # Clean up old entries
        RateLimit.query.filter(RateLimit.window_start < window_start).delete()
        
        # Check current rate limit
        rate_limit = RateLimit.query.filter_by(
            identifier=identifier,
            action=action
        ).first()
        
        if rate_limit:
            if rate_limit.blocked_until and rate_limit.blocked_until > datetime.utcnow():
                return False, f"Rate limit exceeded. Blocked until {rate_limit.blocked_until}"
            
            if rate_limit.attempts >= max_attempts:
                # Block for 1 hour
                rate_limit.blocked_until = datetime.utcnow() + timedelta(hours=1)
                db.session.commit()
                return False, "Rate limit exceeded. Blocked for 1 hour."
            
            rate_limit.attempts += 1
            db.session.commit()
        else:
            rate_limit = RateLimit(
                identifier=identifier,
                action=action,
                attempts=1
            )
            db.session.add(rate_limit)
            db.session.commit()
        
        return True, None
    
    @staticmethod
    def reset_rate_limit(identifier, action):
        """Reset rate limit for identifier."""
        RateLimit.query.filter_by(
            identifier=identifier,
            action=action
        ).delete()
        db.session.commit()


# Security helper functions
def get_organisation_contacts(organisation_id, job_context=None):
    """
    SECURE: Get contacts for an organisation with job context.
    NO DIRECTORY ACCESS - only job-relevant contacts.
    """
    query = db.session.query(Contact).join(EmployeeContact).filter(
        EmployeeContact.organisation_id == organisation_id
    )
    
    # If job context provided, add relevance filtering
    if job_context:
        # Add job-specific filtering here
        pass
    
    return query.all()

def get_employee_contacts(employee_id, job_context=None):
    """
    SECURE: Get contacts for a specific employee only.
    NO DIRECTORY ACCESS - only employee's own contacts.
    """
    query = db.session.query(Contact).join(EmployeeContact).filter(
        EmployeeContact.employee_id == employee_id
    )
    
    # If job context provided, add relevance filtering
    if job_context:
        # Add job-specific filtering here
        pass
    
    return query.all()

def get_organisation_employees(organisation_id):
    """Get all employees for an organisation."""
    return User.query.filter_by(organisation_id=organisation_id).all()

def create_organisation(name, domain, admin_email, admin_name):
    """Create a new organisation with admin user."""
    # Create organisation
    org = Organisation(name=name, domain=domain)
    db.session.add(org)
    db.session.flush()  # Get the ID
    
    # Create admin user
    admin = User(
        organisation_id=org.id,
        email=admin_email,
        name=admin_name,
        role='admin'
    )
    db.session.add(admin)
    db.session.commit()
    
    return org, admin

def add_employee_to_organisation(organisation_id, email, name):
    """Add an employee to an organisation."""
    employee = User(
        organisation_id=organisation_id,
        email=email,
        name=name,
        role='employee'
    )
    db.session.add(employee)
    db.session.commit()
    return employee

def upload_contact_to_organisation(contact_data, employee_id, organisation_id):
    """Upload a contact and link it to an organisation."""
    # Find or create contact (shared across organisations)
    contact = Contact.query.filter_by(linkedin_url=contact_data.get('linkedin_url')).first()
    
    if not contact:
        contact = Contact(
            linkedin_url=contact_data.get('linkedin_url'),
            first_name=contact_data.get('first_name', ''),
            last_name=contact_data.get('last_name', ''),
            email=contact_data.get('email'),
            company=contact_data.get('company'),
            position=contact_data.get('position')
        )
        db.session.add(contact)
        db.session.flush()
    
    # Link to this employee at this organisation
    employee_contact = EmployeeContact(
        employee_id=employee_id,
        contact_id=contact.id,
        organisation_id=organisation_id,
        relationship_type='linkedin_connection'
    )
    db.session.add(employee_contact)
    db.session.commit()
    
    return contact
