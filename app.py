#!/usr/bin/env python3
"""
Flask web application for the referral matching system.
Uses Flask-Login and Flask-Session for robust authentication.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
# Removed Flask-Session import
from referral_api import ReferralAPI
from enhanced_contact_tagger import EnhancedContactTagger
from email_service import ReferralEmailService
from user_management import UserManager
from email_notifications import EmailNotifier
from database import init_database, get_organisation_contacts_for_job, get_employee_contacts_for_job, get_organisation_stats
from models import db, Organisation, User, Contact, EmployeeContact, JobDescription, Referral
from unified_matcher import UnifiedReferralMatcher
import pandas as pd
import os
import json
import time
import re
import secrets
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename
from functools import wraps
import uuid

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# SECRET_KEY is required
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    raise ValueError("SECRET_KEY environment variable must be set for security")

# Database configuration
database_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PUBLIC_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable must be set")
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Single session system configuration
app.config.update(
    SESSION_COOKIE_NAME="referral_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,  # HTTPS only in production
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    # Don't set SESSION_COOKIE_DOMAIN - let it default to host-only
)

# Simple session configuration - no Flask-Session
app.config['SESSION_COOKIE_NAME'] = 'referral_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Security configurations
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour

# Initialize extensions
db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

# No Flask-Session - using simple Flask sessions

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login."""
    return User.query.get(user_id)

# Demo mode flag
DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'

# Initialize services
try:
    print("🚀 Initializing Enhanced Contact Tagger...")
    tagger = EnhancedContactTagger()
    print("✅ Enhanced Contact Tagger initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Enhanced Contact Tagger: {e}")
    tagger = None

try:
    print("[INFO] UserManager initialized")
    user_manager = UserManager()
except Exception as e:
    print(f"❌ Failed to initialize UserManager: {e}")
    user_manager = None

try:
    print("[INFO] EmailNotifier initialized")
    email_notifier = EmailNotifier()
except Exception as e:
    print(f"❌ Failed to initialize EmailNotifier: {e}")
    email_notifier = None

try:
    print("[INFO] ReferralEmailService initialized")
    email_service = ReferralEmailService()
except Exception as e:
    print(f"❌ Failed to initialize ReferralEmailService: {e}")
    email_service = None

# Database initialization
try:
    with app.app_context():
        init_database(app)
        print("[INFO] Database initialized successfully")
        print("[INFO] ReferralAPI will be initialized per-request with database contacts")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")

# Security headers
@app.after_request
def security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "connect-src 'self';"
    )
    return response

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return render_template('error.html', 
                         error_code=400, 
                         error_message="Bad Request - Invalid data provided"), 400

@app.errorhandler(401)
def unauthorized(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('login'))

@app.errorhandler(403)
def forbidden(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Access forbidden'}), 403
    return render_template('error.html', 
                         error_code=403, 
                         error_message="Access Forbidden"), 403

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page Not Found"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal Server Error"), 500

# Utility functions
def require_admin(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Admin access required'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def get_demo_contacts():
    """Get demo contacts for unauthenticated users."""
    if not DEMO_MODE:
        return []
    
    try:
        # Load demo contacts from CSV
        demo_file = 'enhanced_tagged_contacts.csv'
        if os.path.exists(demo_file):
            df = pd.read_csv(demo_file)
            return df.to_dict('records')
    except Exception as e:
        print(f"❌ Failed to load demo contacts: {e}")
    
    return []

# Routes
@app.route('/')
@login_required
def index():
    """Main job search page."""
    user_role = current_user.role
    csrf_token = generate_csrf()
    return render_template('index.html', user_role=user_role, csrf_token=csrf_token)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        # CSRF validation is automatic with Flask-WTF
        email = request.form.get('email', '').strip()
        name = request.form.get('name', '').strip()
        
        if not email or not name:
            csrf_token = generate_csrf()
            return render_template('login.html', 
                                 error='Please provide both name and email.', 
                                 csrf_token=csrf_token)
        
        # Find user
        user = User.query.filter_by(email=email).first()
        if user:
            # Login user
            login_user(user, remember=False)
            return redirect(url_for('dashboard'))
        else:
            csrf_token = generate_csrf()
            return render_template('login.html', 
                                 error='User not found. Please register your company first.', 
                                 csrf_token=csrf_token)
    
    csrf_token = generate_csrf()
    return render_template('login.html', csrf_token=csrf_token)

@app.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    user = current_user
    organisation = user.organisation
    
    # Get team members
    team_members = User.query.filter_by(organisation_id=user.organisation_id).all()
    
    # Get stats
    contact_count = get_organisation_stats(user.organisation_id)['total_contacts']
    job_count = JobDescription.query.filter_by(organisation_id=user.organisation_id).count()
    
    csrf_token = generate_csrf()
    return render_template('dashboard.html', 
                         user=user, 
                         organisation=organisation, 
                         team_members=team_members, 
                         contact_count=contact_count, 
                         job_count=job_count, 
                         user_role=user.role,
                         csrf_token=csrf_token)

@app.route('/api/match', methods=['POST'])
@login_required
def match_job():
    """Match job description to contacts."""
    try:
        data = request.get_json()
        job_description = data.get('job_description', '').strip()
        
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400
        
        # Get contacts based on user role
        if current_user.role in ['admin', 'recruiter']:
            # Admins and recruiters see all org contacts
            contacts = get_organisation_contacts_for_job(current_user.organisation_id, job_description)
            print(f"🔍 ORG MODE: Found {len(contacts)} contacts for org {current_user.organisation_id}")
        else:
            # Employees see only their own contacts
            contacts = get_employee_contacts_for_job(current_user.id, job_description)
            print(f"🔍 EMPLOYEE MODE: Found {len(contacts)} contacts for user {current_user.id}")
        
        if not contacts:
            return jsonify({
                'matches': [],
                'message': 'No contacts found. Upload some contacts first!',
                'total_contacts': 0
            })
        
        # Create matcher with database contacts
        matcher = UnifiedReferralMatcher(contacts)
        matches = matcher.find_matches(job_description, top_n=10)
        
        return jsonify({
            'matches': matches,
            'total_contacts': len(contacts),
            'message': f'Found {len(matches)} potential matches from {len(contacts)} contacts'
        })
        
    except Exception as e:
        print(f"❌ Error in match_job: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/fetch-job', methods=['POST'])
@login_required
def fetch_job_description():
    """Fetch job description from URL."""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Fetch job description
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find job description
        job_description = ""
        
        # Common selectors for job descriptions
        selectors = [
            '.job-description',
            '.job-details',
            '.description',
            '[data-testid="job-description"]',
            '.jobsearch-jobDescriptionText',
            '.jobs-description-content__text'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                job_description = element.get_text(strip=True)
                break
        
        if not job_description:
            # Fallback: get all text content
            job_description = soup.get_text(strip=True)
            # Limit length
            if len(job_description) > 5000:
                job_description = job_description[:5000] + "..."
        
        return jsonify({
            'job_description': job_description,
            'url': url
        })
        
    except Exception as e:
        print(f"❌ Error fetching job description: {e}")
        return jsonify({'error': 'Failed to fetch job description'}), 500

@app.route('/api/import-contacts', methods=['POST'])
@login_required
def import_contacts():
    """Import contacts from CSV."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400
        
        # Read CSV
        df = pd.read_csv(file)
        
        # Required columns
        required_columns = ['name', 'email']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': f'CSV must contain columns: {", ".join(required_columns)}'}), 400
        
        # Process contacts
        imported_count = 0
        for _, row in df.iterrows():
            name = str(row.get('name', '')).strip()
            email = str(row.get('email', '')).strip()
            
            if not name or not email:
                continue
            
            # Check if contact exists
            contact = Contact.query.filter_by(email=email).first()
            if not contact:
                contact = Contact(
                    name=name,
                    email=email,
                    linkedin_url=row.get('linkedin_url', ''),
                    location=row.get('location', ''),
                    skills=row.get('skills', ''),
                    company=row.get('company', ''),
                    title=row.get('title', '')
                )
                db.session.add(contact)
                db.session.flush()  # Get the ID
            
            # Check if employee-contact relationship exists
            existing_relationship = EmployeeContact.query.filter_by(
                employee_id=current_user.id,
                contact_id=contact.id
            ).first()
            
            if not existing_relationship:
                employee_contact = EmployeeContact(
                    employee_id=current_user.id,
                    contact_id=contact.id,
                    source='csv_upload'
                )
                db.session.add(employee_contact)
                imported_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully imported {imported_count} contacts',
            'imported_count': imported_count
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error importing contacts: {e}")
        return jsonify({'error': 'Failed to import contacts'}), 500

@app.route('/api/contacts-info')
@login_required
def contacts_info():
    """Get contact statistics."""
    try:
        if current_user.role in ['admin', 'recruiter']:
            # Org-wide stats
            stats = get_organisation_stats(current_user.organisation_id)
        else:
            # Employee's own contacts
            contact_count = EmployeeContact.query.filter_by(employee_id=current_user.id).count()
            stats = {'total_contacts': contact_count}
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"❌ Error getting contacts info: {e}")
        return jsonify({'error': 'Failed to get contacts info'}), 500

@app.route('/api/invite-employee', methods=['POST'])
@require_admin
def invite_employee():
    """Invite a new team member."""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()
        role = data.get('role', 'employee').strip()
        
        if not email or not name:
            return jsonify({'error': 'Email and name are required'}), 400
        
        if role not in ['admin', 'recruiter', 'employee']:
            return jsonify({'error': 'Invalid role'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 400
        
        # Create new user
        new_user = User(
            organisation_id=current_user.organisation_id,
            email=email,
            name=name,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Send invitation email
        try:
            email_service.send_team_invitation_email(
                to_email=email,
                to_name=name,
                company_name=current_user.organisation.name,
                inviter_name=current_user.name,
                role=role
            )
        except Exception as e:
            print(f"⚠️ Failed to send invitation email: {e}")
        
        return jsonify({
            'message': f'Successfully invited {name} as {role}',
            'user_id': new_user.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error inviting employee: {e}")
        return jsonify({'error': 'Failed to invite employee'}), 500

@app.route('/api/init-database', methods=['GET', 'POST'])
def init_database_endpoint():
    """Initialize database with demo data."""
    try:
        with app.app_context():
            init_database(app)
            print("✅ Database initialization completed successfully")
            return jsonify({'message': 'Database initialized successfully'})
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return jsonify({'error': 'Database initialization failed'}), 500

@app.route('/api/create-demo-users', methods=['GET', 'POST'])
def create_demo_users():
    """Create demo users for testing."""
    try:
        # Find the organisation with the most contacts
        org_with_most_contacts = db.session.query(Organisation).join(User).join(EmployeeContact).group_by(Organisation.id).order_by(db.func.count(EmployeeContact.id).desc()).first()
        
        if not org_with_most_contacts:
            return jsonify({'error': 'No organisation found'}), 400
        
        # Create demo users
        demo_users = [
            {'name': 'Admin User', 'email': 'admin@demo.com', 'role': 'admin'},
            {'name': 'Recruiter User', 'email': 'recruiter@demo.com', 'role': 'recruiter'},
            {'name': 'Employee User', 'email': 'employee@demo.com', 'role': 'employee'}
        ]
        
        created_users = []
        for user_data in demo_users:
            # Check if user already exists
            existing_user = User.query.filter_by(email=user_data['email']).first()
            if not existing_user:
                user = User(
                    organisation_id=org_with_most_contacts.id,
                    email=user_data['email'],
                    name=user_data['name'],
                    role=user_data['role']
                )
                db.session.add(user)
                created_users.append(user_data)
        
        db.session.commit()
        
        return jsonify({
            'message': f'Created {len(created_users)} demo users',
            'users': created_users,
            'organisation': org_with_most_contacts.name
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating demo users: {e}")
        return jsonify({'error': 'Failed to create demo users'}), 500

# Additional routes for other pages
@app.route('/gamification')
@login_required
def gamification():
    csrf_token = generate_csrf()
    return render_template('gamification.html', csrf_token=csrf_token)

@app.route('/upload')
@login_required
def upload():
    csrf_token = generate_csrf()
    return render_template('upload.html', csrf_token=csrf_token)

@app.route('/import')
@login_required
def import_page():
    csrf_token = generate_csrf()
    return render_template('import.html', csrf_token=csrf_token)

@app.route('/enrichment')
@login_required
def enrichment():
    csrf_token = generate_csrf()
    return render_template('enrichment.html', csrf_token=csrf_token)

@app.route('/job-descriptions')
@login_required
def job_descriptions():
    csrf_token = generate_csrf()
    return render_template('job_descriptions.html', csrf_token=csrf_token)

@app.route('/referrals')
@login_required
def referrals():
    csrf_token = generate_csrf()
    return render_template('referrals.html', csrf_token=csrf_token)

@app.route('/register-company')
def register_company():
    csrf_token = generate_csrf()
    return render_template('register_company.html', csrf_token=csrf_token)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
