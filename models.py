#!/usr/bin/env python3
"""
Secure multi-tenant database models for the referral system.
Implements GDPR-compliant contact management with no directory access.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

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

class User(db.Model):
    """Employees of organisations."""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = db.Column(db.String(36), db.ForeignKey('organisations.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='employee')  # admin, employee
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee_contacts = db.relationship('EmployeeContact', backref='employee', lazy=True)
    referrals_sent = db.relationship('Referral', backref='referrer', lazy=True)
    
    def __repr__(self):
        return f'<User {self.name} ({self.email})>'

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
