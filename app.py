#!/usr/bin/env python3
"""
Simple Flask web application for the referral matching system.
Demonstrates how to integrate the unified matcher into a web interface.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from referral_api import ReferralAPI
from enhanced_contact_tagger import EnhancedContactTagger
from email_service import ReferralEmailService
from user_management import UserManager
from email_notifications import EmailNotifier
from database import init_database, get_organisation_contacts_for_job, get_employee_contacts_for_job, get_organisation_stats
from models import db, Organisation, User, Contact, EmployeeContact, JobDescription, Referral, UserSession
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

# Location enrichment temporarily disabled
# from smart_geo_enricher import SmartGeoEnricher

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    raise ValueError("SECRET_KEY environment variable must be set for security")

# Security configurations
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session timeout

# CRITICAL: Session isolation for multi-tenant security
app.config['SESSION_COOKIE_NAME'] = 'referral_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['SESSION_COOKIE_DOMAIN'] = None  # Don't share across subdomains

# Initialize CSRF protection
csrf = CSRFProtect(app)

def load_contacts_from_csv_demo():
    """Load demo contacts from CSV for demo mode."""
    try:
        import pandas as pd
        csv_file = 'enhanced_tagged_contacts.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            # Convert to Contact objects for compatibility
            contacts = []
            for _, row in df.iterrows():
                contact = Contact(
                    first_name=row.get('First Name', ''),
                    last_name=row.get('Last Name', ''),
                    position=row.get('Position', ''),
                    company=row.get('Company', ''),
                    location=row.get('Location', ''),
                    linkedin_url=row.get('LinkedIn URL', '')
                )
                contacts.append(contact)
            return contacts
        else:
            return []
    except Exception as e:
        print(f"Error loading demo contacts: {e}")
        return []

# Security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data: https:;"
    return response

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Security utility functions
def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_input(text, max_length=1000, allowed_chars=None):
    """Validate and sanitize user input."""
    if not text or not isinstance(text, str):
        return ""
    
    # Remove potentially dangerous characters
    if allowed_chars:
        text = ''.join(c for c in text if c in allowed_chars)
    else:
        # Remove script tags and other potentially dangerous content
        text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    
    # Limit length
    return text[:max_length].strip()

def secure_log(message, level="INFO"):
    """Secure logging that doesn't expose sensitive information."""
    # Remove sensitive patterns from logs
    sensitive_patterns = [
        r'password["\']?\s*[:=]\s*["\']?[^"\']+["\']?',
        r'api_key["\']?\s*[:=]\s*["\']?[^"\']+["\']?',
        r'token["\']?\s*[:=]\s*["\']?[^"\']+["\']?',
        r'secret["\']?\s*[:=]\s*["\']?[^"\']+["\']?'
    ]
    
    for pattern in sensitive_patterns:
        message = re.sub(pattern, '[REDACTED]', message, flags=re.IGNORECASE)
    
    print(f"[{level}] {message}")

def create_database_session(user_id, session_data=None):
    """Create a new database-backed session."""
    session_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=8)  # 8 hours expiry
    
    print(f"🔍 DEBUG: Creating database session - session_id: {session_id}, user_id: {user_id}")
    
    try:
        db_session = UserSession(
            session_id=session_id,
            user_id=user_id,
            session_data=json.dumps(session_data) if session_data else None,
            expires_at=expires_at
        )
        
        db.session.add(db_session)
        db.session.commit()
        
        print(f"✅ DEBUG: Database session created successfully")
        return session_id
    except Exception as e:
        print(f"❌ DEBUG: Failed to create database session: {str(e)}")
        db.session.rollback()
        raise

def get_database_session(session_id):
    """Get session data from database."""
    print(f"🔍 DEBUG: get_database_session called with session_id: {session_id}")
    
    if not session_id:
        print(f"❌ DEBUG: No session_id provided")
        return None, None
    
    try:
        print(f"🔍 DEBUG: Querying UserSession table for session_id: {session_id}")
        db_session = UserSession.query.filter_by(session_id=session_id).first()
        print(f"🔍 DEBUG: Database query result: {db_session}")
        
        if not db_session:
            print(f"❌ DEBUG: No database session found for session_id: {session_id}")
            # Let's check what sessions exist in the database
            all_sessions = UserSession.query.all()
            print(f"🔍 DEBUG: All sessions in database: {len(all_sessions)}")
            for sess in all_sessions:
                print(f"  - Session ID: {sess.session_id}, User ID: {sess.user_id}, Expires: {sess.expires_at}")
            return None, None
        
        print(f"🔍 DEBUG: Found database session - User ID: {db_session.user_id}, Expires: {db_session.expires_at}")
        
        # Check if expired
        current_time = datetime.now(timezone.utc)
        print(f"🔍 DEBUG: Current time: {current_time}, Session expires: {db_session.expires_at}")
        
        if current_time > db_session.expires_at:
            print(f"❌ DEBUG: Session expired, deleting")
            db.session.delete(db_session)
            db.session.commit()
            return None, None
        
        print(f"✅ DEBUG: Session is valid, updating last_accessed and extending expiry")
        
        # Update last accessed and extend expiry time
        db_session.last_accessed = current_time
        db_session.expires_at = current_time + timedelta(hours=8)  # Extend by 8 hours from now
        db.session.commit()
        
        # Parse session data
        session_data = json.loads(db_session.session_data) if db_session.session_data else {}
        print(f"✅ DEBUG: Parsed session data: {session_data}")
        return db_session.user_id, session_data
    except Exception as e:
        print(f"❌ DEBUG: Error getting database session: {str(e)}")
        import traceback
        print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
        return None, None

def validate_session_isolation():
    """Validate that session is properly isolated using database sessions."""
    # Get session ID from cookie
    session_id = request.cookies.get('referral_session')
    print(f"🔍 DEBUG: Cookie session_id = {session_id}")
    
    if not session_id:
        print("❌ DEBUG: No session cookie found - using Flask default session")
        # Fallback to Flask session for debugging
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                return True, f"Flask session fallback for {user.name} ({user.email})"
        return False, "No session cookie found"
    
    # Get session from database
    user_id, session_data = get_database_session(session_id)
    print(f"🔍 DEBUG: Database session lookup - user_id: {user_id}, data: {session_data}")
    
    if not user_id:
        print("❌ DEBUG: Invalid or expired database session")
        return False, "Invalid or expired session"
    
    # Verify user still exists
    user = User.query.get(user_id)
    if not user:
        print("❌ DEBUG: User not found in database")
        return False, "User not found in database"
    
    # Update Flask session with database data
    session.update(session_data)
    print(f"✅ DEBUG: Updated Flask session with database data")
    
    return True, f"Valid database session for {user.name} ({user.email})"

def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"🔍 DEBUG: require_auth decorator called for {f.__name__}")
        print(f"🔍 DEBUG: Current session: {dict(session)}")
        
        # Validate session isolation
        is_valid, message = validate_session_isolation()
        
        if not is_valid:
            print(f"❌ DEBUG: Auth failed - {message}")
            # For API endpoints, return JSON error instead of redirect
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required', 'message': message}), 401
            return redirect(url_for('login'))
        
        print(f"✅ DEBUG: Auth successful - {message}")
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Initialize database
try:
    init_database(app)
    secure_log("Database initialized successfully")
except Exception as e:
    secure_log(f"Database initialization failed: {str(e)}", "ERROR")
    import traceback
    secure_log(f"Database init traceback: {traceback.format_exc()}", "ERROR")
    # Don't crash the app, just log the error
    pass

# Initialize services with error handling
# NOTE: ReferralAPI will be initialized per-request with database contacts
# instead of loading CSV contacts during startup
api = None
secure_log("ReferralAPI will be initialized per-request with database contacts")

try:
    tagger = EnhancedContactTagger()
    secure_log("EnhancedContactTagger initialized")
except Exception as e:
    secure_log(f"EnhancedContactTagger initialization failed: {str(e)}", "WARNING")
    tagger = None

try:
    user_manager = UserManager()
    secure_log("UserManager initialized")
except Exception as e:
    secure_log(f"UserManager initialization failed: {str(e)}", "WARNING")
    user_manager = None

try:
    email_notifier = EmailNotifier()
    secure_log("EmailNotifier initialized")
except Exception as e:
    secure_log(f"EmailNotifier initialization failed: {str(e)}", "WARNING")
    email_notifier = None

try:
    email_service = ReferralEmailService()
    secure_log("ReferralEmailService initialized")
except Exception as e:
    secure_log(f"ReferralEmailService initialization failed: {str(e)}", "WARNING")
    email_service = None

@app.route('/')
def index():
    # Get user role for role-based UI
    user_role = session.get('user_role', 'employee')
    return render_template('index.html', user_role=user_role)

@app.route('/gamification')
def gamification():
    return render_template('gamification.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if request.method == 'POST':
        print(f"🔍 DEBUG: Login POST request received")
        print(f"🔍 DEBUG: CSRF token in form: {request.form.get('csrf_token')}")
        print(f"🔍 DEBUG: CSRF token in headers: {request.headers.get('X-CSRFToken')}")
        print(f"🔍 DEBUG: Request form data: {dict(request.form)}")
        print(f"🔍 DEBUG: CSRF validation error: {request.form.get('csrf_token') is None}")
        email = request.form.get('email', '').strip()
        name = request.form.get('name', '').strip()
        
        # Validate input
        if not email:
            return render_template('login.html', error='Email is required')
        
        if not validate_email(email):
            return render_template('login.html', error='Invalid email format')
        
        # Sanitize inputs
        email = validate_input(email, max_length=255)
        name = validate_input(name, max_length=100)
        
        # Find user in database
        user = User.query.filter_by(email=email).first()
        print(f"🔍 DEBUG: Looking for user with email: {email}")
        print(f"🔍 DEBUG: User found: {user}")
        
        if user:
            print(f"✅ DEBUG: User found - ID: {user.id}, Name: {user.name}, Email: {user.email}, Role: {user.role}")
            print(f"✅ DEBUG: User organisation: {user.organisation.name if user.organisation else 'None'}")
            
            # Create database-backed session
            session_data = {
                'user_id': str(user.id),
                'user_email': user.email,
                'user_name': user.name,
                'organisation_id': str(user.organisation_id),
                'user_role': user.role
            }
            
            try:
                session_id = create_database_session(user.id, session_data)
                
                print(f"✅ DEBUG: Database session created - session_id: {session_id}, user_id: {user.id}")
                print(f"✅ DEBUG: Session data: {session_data}")
                secure_log(f"User logged in: {user.name} from {user.organisation.name}")
                
                # Create response with session cookie
                response = redirect(url_for('dashboard'))
                response.set_cookie('referral_session', session_id, max_age=3600, httponly=True, secure=True, samesite='Lax')
                print(f"✅ DEBUG: Cookie set - referral_session: {session_id}")
                return response
            except Exception as e:
                print(f"❌ DEBUG: Failed to create database session: {str(e)}")
                return render_template('login.html', error=f'Login failed: {str(e)}')
        else:
            # User doesn't exist, show error
            print(f"❌ DEBUG: No user found with email: {email}")
            print(f"❌ DEBUG: Available users in database:")
            all_users = User.query.all()
            for u in all_users:
                print(f"  - {u.email} ({u.name}) - Role: {u.role}")
            secure_log(f"Login attempt with unknown email: {email}", "WARNING")
            return render_template('login.html', error='User not found. Please register your company first.')
    
    print(f"🔍 DEBUG: Rendering login template")
    return render_template('login.html')

@app.route('/old-dashboard')
def old_dashboard():
    """Legacy user dashboard - redirect to new dashboard."""
    return redirect(url_for('dashboard'))

@app.route('/upload')
@require_auth
def upload_page():
    """Contact upload page."""
    return render_template('upload.html')

@app.route('/import')
@require_auth
def import_page():
    """Contact import page."""
    return render_template('import.html')

@app.route('/enrichment')
@require_auth
def enrichment_page():
    """Contact enrichment page."""
    return render_template('contact_enrichment.html')

@app.route('/job-descriptions')
@require_auth
def job_descriptions_page():
    """Job descriptions management page."""
    return render_template('job_descriptions.html')


@app.route('/api/match', methods=['POST'])
@require_auth
def match_job():
    """Match job description to contacts with full feature set."""
    try:
        data = request.get_json()
        job_description = data.get('jobDescription', '')
        job_location = data.get('jobLocation', '')
        preferred_companies = data.get('preferredCompanies', [])
        preferred_industries = data.get('preferredIndustries', [])
        top_n = data.get('topN', 10)
        desired_location = data.get('desiredLocation', '')
        acceptable_locations = data.get('acceptableLocations', [])
        enable_location_enrichment = data.get('enableLocationEnrichment', True)  # Enable by default
        brave_api_key = data.get('braveApiKey', '')
        serpapi_key = data.get('serpapiKey', '')  # Not needed for Bright Data
        
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400
        
        # CRITICAL: Validate session isolation first
        session_valid, session_msg = validate_session_isolation()
        print(f"🔍 DEBUG: Session validation: {session_msg}")
        print(f"🔍 DEBUG: Current Flask session: {dict(session)}")
        
        if not session_valid:
            print("⚠️ DEBUG: Invalid session - using DEMO MODE")
            print(f"⚠️ DEBUG: Session validation failed: {session_msg}")
            current_user = None
            demo_mode = True
        else:
            # Session is valid, get user
            user_id = session.get('user_id')
            current_user = User.query.get(user_id)
            demo_mode = False
            print(f"✅ DEBUG: Valid session for {current_user.name} ({current_user.email}) from {current_user.organisation.name}")
            print(f"✅ DEBUG: User role: {current_user.role}")
        
        # SECURE: Get contacts based on user role
        try:
            if demo_mode:
                # Demo mode - use demo organization
                demo_org = Organisation.query.filter_by(name='Demo Company').first()
                if demo_org:
                    contacts = get_organisation_contacts_for_job(demo_org.id, job_description)
                else:
                    # Fallback to CSV if no demo org
                    contacts = load_contacts_from_csv_demo()
            else:
                # Role-based contact access
                if current_user.role == 'employee':
                    # Employees can only see their own contacts
                    contacts = get_employee_contacts_for_job(current_user.id, job_description)
                    print(f"👤 EMPLOYEE MODE: {current_user.name} sees only their own {len(contacts)} contacts")
                elif current_user.role in ['recruiter', 'admin']:
                    # Recruiters and admins can see ALL contacts uploaded by ANYONE in the organization
                    contacts = get_organisation_contacts_for_job(current_user.organisation_id, job_description)
                    print(f"🏢 ORG MODE: {current_user.name} ({current_user.role}) sees ALL {len(contacts)} contacts in organization")
                else:
                    return jsonify({'error': 'Invalid user role'}), 403
            if demo_mode:
                print(f"📊 Using {len(contacts)} contacts in demo mode")
            else:
                print(f"📊 Using {len(contacts)} contacts from database for organisation: {current_user.organisation.name}")
            
            # Convert to DataFrame for compatibility with existing matching logic
            contacts_data = []
            for contact in contacts:
                contacts_data.append({
                    'First Name': contact.first_name,
                    'Last Name': contact.last_name,
                    'Email': contact.email or '',
                    'Company': contact.company or '',
                    'Position': contact.position or '',
                    'LinkedIn': contact.linkedin_url or '',
                    'location_raw': contact.location or '',
                    'skills_tag': contact.skills or '[]',
                    'employee_connection': 'Demo Employee'  # For MVP
                })
            
            contacts_df = pd.DataFrame(contacts_data)
                
        except Exception as e:
            print(f"❌ Error loading contacts from database: {e}")
            return jsonify({'error': 'Could not load contacts'}), 500
        
        if len(contacts_df) == 0:
            return jsonify({'error': 'No contacts found'}), 404
        
        # Use full-featured job matching
        print(f"🔍 Using full-featured job matching")
        print(f"   Preferred Companies: {preferred_companies}")
        print(f"   Preferred Industries: {preferred_industries}")
        print(f"   Top N: {top_n}")
        print(f"   Location Enrichment: {enable_location_enrichment}")
        
        # Extract job title and alternative titles from request
        job_title = data.get('jobTitle', '').strip()
        alternative_titles = data.get('alternativeTitles', [])
        
        # DATABASE-DRIVEN: Use database contacts instead of CSV
        # Get contacts from database based on user role
        if demo_mode:
            print("⚠️ DEBUG: Using demo mode - no database contacts available")
            results = {
                'matches': [],
                'job_analysis': {
                    'role_detected': 'Unknown',
                    'role_confidence': 0.0,
                    'company_detected': 'Unknown',
                    'seniority_detected': 'Unknown',
                    'skills_found': [],
                    'platforms_found': []
                },
                'processing_time': 0.0
            }
        else:
            print(f"✅ DEBUG: Using database contacts for user {current_user.name}")
            
            # Get contacts from database based on user role
            if current_user.role == 'employee':
                contacts = get_employee_contacts_for_job(current_user.id, job_description)
                print(f"👤 EMPLOYEE MODE: Found {len(contacts)} contacts for employee {current_user.name}")
            else:  # admin or recruiter
                contacts = get_organisation_contacts_for_job(current_user.organisation_id, job_description)
                print(f"🏢 ORG MODE: Found {len(contacts)} contacts for organization {current_user.organisation.name}")
            
            if not contacts:
                print("⚠️ DEBUG: No contacts found in database")
                results = {
                    'matches': [],
                    'job_analysis': {
                        'role_detected': 'Unknown',
                        'role_confidence': 0.0,
                        'company_detected': 'Unknown',
                        'seniority_detected': 'Unknown',
                        'skills_found': [],
                        'platforms_found': []
                    },
                    'processing_time': 0.0
                }
            else:
                # Convert database contacts to the format expected by the matcher
                contacts_data = []
                for contact in contacts:
                    contact_dict = {
                        'name': contact.name,
                        'company': contact.company,
                        'position': contact.position,
                        'location': contact.location,
                        'linkedin_url': contact.linkedin_url,
                        'skills': contact.skills.split(',') if contact.skills else [],
                        'tags': contact.tags.split(',') if contact.tags else []
                    }
                    contacts_data.append(contact_dict)
                
                print(f"✅ DEBUG: Converted {len(contacts_data)} database contacts for matching")
                
                # Create a temporary matcher with database contacts
                
                # Convert contacts to DataFrame format
                contacts_df = pd.DataFrame(contacts_data)
                
                # Create matcher with database contacts
                db_matcher = UnifiedReferralMatcher()
                db_matcher.df = contacts_df  # Use database contacts instead of CSV
                
                # Perform matching
                results = db_matcher.match_job(
                    job_description=job_description,
                    job_title=job_title,
                    alternative_titles=alternative_titles,
                    top_n=top_n,
                    preferred_companies=preferred_companies,
                    preferred_industries=preferred_industries,
                    job_location=job_location,
                    enable_location_enrichment=enable_location_enrichment,
                    serpapi_key=serpapi_key
                )
        
        # Add contact IDs to the results for referral functionality
        if results.get('success') and 'candidates' in results:
            # Create a mapping from contact details to contact IDs
            contact_id_map = {}
            for contact in contacts:
                key = f"{contact.first_name}_{contact.last_name}_{contact.company}"
                contact_id_map[key] = contact.id
            
            # Add contact IDs to candidates
            for candidate in results['candidates']:
                candidate_key = f"{candidate.get('First Name', '')}_{candidate.get('Last Name', '')}_{candidate.get('Company', '')}"
                candidate['contact_id'] = contact_id_map.get(candidate_key, None)
        
        return jsonify(results)
            
    except Exception as e:
        print(f"Error in job matching: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/import-contacts', methods=['POST'])
@require_auth
def import_contacts():
    """API endpoint for importing and tagging LinkedIn contacts."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({
                'success': False,
                'error': 'Please upload a CSV file'
            }), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Load and process contacts
        print(f"📄 Processing uploaded file: {filename}")
        
        # Smart CSV parsing to handle LinkedIn export format
        def smart_read_csv(filepath):
            """Intelligently read CSV file, detecting header row and skipping intro text."""
            try:
                # First, read the first few lines to understand the structure
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]  # Read first 10 lines
                
                # Look for the header row by checking for common LinkedIn column names
                linkedin_columns = [
                    'first name', 'last name', 'full name', 'email', 'company', 
                    'position', 'title', 'current company', 'current position',
                    'firstname', 'lastname', 'fullname', 'emailaddress', 'companyname',
                    'jobtitle', 'currentcompany', 'currentposition'
                ]
                
                header_row = 0
                for i, line in enumerate(lines):
                    # Convert to lowercase and split by comma
                    columns = [col.strip().lower().replace('"', '') for col in line.split(',')]
                    
                    # Check if this line contains LinkedIn-like column headers
                    if any(col in linkedin_columns for col in columns):
                        header_row = i
                        print(f"🔍 Detected header row at line {i + 1}: {columns[:5]}...")
                        break
                
                # If no clear header found, try to detect by looking for data patterns
                if header_row == 0:
                    for i, line in enumerate(lines):
                        # Skip empty lines or lines that are clearly not data
                        if not line.strip() or len(line.split(',')) < 3:
                            continue
                        
                        # Check if this looks like a data row (has reasonable content)
                        columns = line.split(',')
                        if len(columns) >= 3 and any(len(col.strip()) > 2 for col in columns[:3]):
                            # This might be the header row
                            header_row = i
                            print(f"🔍 Inferred header row at line {i + 1}")
                            break
                
                # Read the CSV with the detected header row
                if header_row > 0:
                    print(f"📊 Reading CSV with header at row {header_row + 1}")
                    # Skip rows before the header, then read with header=0
                    df = pd.read_csv(filepath, header=0, skiprows=header_row)
                else:
                    print("📊 Reading CSV with default header (row 1)")
                    df = pd.read_csv(filepath)
                
                # Clean up column names (strip whitespace but preserve case)
                df.columns = df.columns.str.strip()
                
                # Handle common LinkedIn column name variations
                column_mapping = {
                    'first name': 'First Name',
                    'last name': 'Last Name', 
                    'full name': 'Full Name',
                    'email address': 'Email Address',
                    'emailaddress': 'Email Address',
                    'company name': 'Company',
                    'companyname': 'Company',
                    'job title': 'Position',
                    'jobtitle': 'Position',
                    'current company': 'Company',
                    'currentcompany': 'Company',
                    'current position': 'Position',
                    'currentposition': 'Position',
                    'connected on': 'Connected On'
                }
                
                df = df.rename(columns=column_mapping)
                
                print(f"✅ Successfully loaded {len(df)} contacts with columns: {list(df.columns)}")
                return df
                
            except Exception as e:
                print(f"❌ Error in smart CSV parsing: {str(e)}")
                # Fallback to standard pandas reading
                print("🔄 Falling back to standard CSV reading...")
                return pd.read_csv(filepath)
        
        contacts_df = smart_read_csv(filepath)
        
        # Tag contacts
        tagged_df = tagger.tag_contacts(contacts_df)
        
        # Get current user's organization
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Use current user's organization
        user_org = current_user.organisation
        if not user_org:
            return jsonify({'error': 'No organisation found'}), 500
        
        # Store contacts in database
        stored_count = 0
        for _, row in tagged_df.iterrows():
            try:
                contact_data = {
                    'linkedin_url': row.get('LinkedIn', ''),
                    'first_name': row.get('First Name', ''),
                    'last_name': row.get('Last Name', ''),
                    'email': row.get('Email', ''),
                    'company': row.get('Company', ''),
                    'position': row.get('Position', '')
                }
                
                # Skip if no LinkedIn URL
                if not contact_data['linkedin_url']:
                    continue
                
                # Find or create contact
                contact = Contact.query.filter_by(linkedin_url=contact_data['linkedin_url']).first()
                
                if not contact:
                    contact = Contact(
                        linkedin_url=contact_data['linkedin_url'],
                        first_name=contact_data['first_name'],
                        last_name=contact_data['last_name'],
                        email=contact_data['email'],
                        company=contact_data['company'],
                        position=contact_data['position']
                    )
                    db.session.add(contact)
                    db.session.flush()
                
                # Check if this employee-contact relationship already exists
                existing_relationship = EmployeeContact.query.filter_by(
                    employee_id=current_user.id,
                    contact_id=contact.id
                ).first()
                
                if not existing_relationship:
                    # Link to this employee at this organisation
                    employee_contact = EmployeeContact(
                        employee_id=current_user.id,
                        contact_id=contact.id,
                        organisation_id=user_org.id,
                        relationship_type='linkedin_connection'
                    )
                    db.session.add(employee_contact)
                    stored_count += 1
                else:
                    print(f"Contact {contact.first_name} {contact.last_name} already linked to employee")
                
            except Exception as e:
                print(f"Error storing contact {row.get('First Name', 'Unknown')}: {e}")
                continue
        
        db.session.commit()
        
        # Get summary statistics
        summary = tagger._print_tagging_summary(tagged_df)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': f'Successfully stored {stored_count} contacts in database',
            'contacts_processed': stored_count,
            'organisation': user_org.name,
            'summary': {
                'roles': tagged_df['role_tag'].value_counts().to_dict(),
                'functions': tagged_df['function_tag'].value_counts().to_dict(),
                'seniority': tagged_df['seniority_tag'].value_counts().to_dict()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get-contacts-for-enrichment')
def get_contacts_for_enrichment():
    """Get contacts for enrichment interface."""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        user_id = session['user_id']
        
        # Load the user's contacts from the most recent import
        contacts = user_manager.get_user_contacts_for_enrichment(user_id)
        
        return jsonify({
            'success': True,
            'contacts': contacts
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/save-enrichment', methods=['POST'])
def save_enrichment():
    """Save enrichment data for a contact."""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        data = request.get_json()
        user_id = session['user_id']
        
        # Save enrichment data
        success = user_manager.save_contact_enrichment(
            user_id=user_id,
            contact_id=data['contact_id'],
            location=data['location'],
            seniority=data['seniority'],
            skills=data['skills'],
            platforms=data['platforms'],
            is_superstar=data['is_superstar'],
            notes=data['notes']
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Enrichment data saved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save enrichment data'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/send-referral-emails', methods=['POST'])
def send_referral_emails():
    """Send bulk referral emails to employees."""
    try:
        data = request.get_json()
        contacts = data.get('contacts', [])
        job_title = data.get('jobTitle', 'this role')
        job_location = data.get('jobLocation', 'this location')
        
        if not contacts:
            return jsonify({'error': 'No contacts provided'}), 400
        
        # Group contacts by employee
        contacts_by_employee = {}
        for contact in contacts:
            employee = contact.get('employee_connection')
            if employee:
                if employee not in contacts_by_employee:
                    contacts_by_employee[employee] = []
                contacts_by_employee[employee].append(contact)
        
        if not contacts_by_employee:
            return jsonify({'error': 'No contacts with employee connections found'}), 400
        
        # Send bulk emails
        result = email_service.send_bulk_referral_emails(
            contacts_by_employee, job_title, job_location
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error sending referral emails: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify(api.test_connection())

@app.route('/api/db-status')
def db_status():
    """Check database status."""
    try:
        # Test database connection
        org_count = Organisation.query.count()
        user_count = User.query.count()
        
        return jsonify({
            'success': True,
            'database_connected': True,
            'organisations_count': org_count,
            'users_count': user_count,
            'tables_exist': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'database_connected': False,
            'error': str(e),
            'tables_exist': False
        }), 500

@app.route('/api/migrate-database', methods=['GET', 'POST'])
def migrate_database():
    """Run database migration to add missing columns."""
    try:
        from sqlalchemy import text
        
        print("🔧 Starting database migration...")
        
        # Check if from_email column exists and add it if missing
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'organisations' 
            AND column_name = 'from_email'
        """))
        
        if not result.fetchone():
            print("➕ Adding from_email column to organisations table...")
            db.session.execute(text("ALTER TABLE organisations ADD COLUMN from_email VARCHAR(255)"))
            db.session.commit()
            print("✅ Added from_email column")
        else:
            print("✅ from_email column already exists")
        
        # Check if from_name column exists and add it if missing
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'organisations' 
            AND column_name = 'from_name'
        """))
        
        if not result.fetchone():
            print("➕ Adding from_name column to organisations table...")
            db.session.execute(text("ALTER TABLE organisations ADD COLUMN from_name VARCHAR(255)"))
            db.session.commit()
            print("✅ Added from_name column")
        else:
            print("✅ from_name column already exists")
        
        # Test the migration
        print("🧪 Testing migration...")
        org_count = Organisation.query.count()
        print(f"✅ Migration successful! Found {org_count} organisations")
        
        return jsonify({
            'success': True,
            'message': 'Database migration completed successfully',
            'organisations_count': org_count
        })
        
    except Exception as e:
        db.session.rollback()
        secure_log(f"Database migration failed: {str(e)}", "ERROR")
        return jsonify({
            'success': False,
            'error': f'Migration failed: {str(e)}'
        }), 500

@app.route('/api/stats')
def get_stats():
    """Get system statistics."""
    return jsonify(api.get_system_stats())

# REMOVED: Duplicate /api/request-referral route - using the database-integrated version below

@app.route('/referrals/<referral_id>')
@require_auth
def view_referral(referral_id):
    """View specific referral request."""
    
    # This would load the referral details
    # For now, return a placeholder page
    return render_template('referral_detail.html', referral_id=referral_id)

@app.route('/api/fetch-job', methods=['POST'])
@require_auth
def fetch_job_description():
    """Fetch job description from a URL."""
    try:
        # Ensure we return JSON even on errors
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data'
                }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'JSON parsing error: {str(e)}'
            }), 400
            
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        # Import requests here to avoid issues if not installed
        try:
            import requests
            from bs4 import BeautifulSoup
            import re
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Web scraping dependencies not installed. Please install: pip install requests beautifulsoup4'
            }), 500
        
        # Set up headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Fetch the page
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up the text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Extract job-specific content based on URL type
        job_description = ""
        job_title = ""
        company = ""
        
        # LinkedIn job pages
        if 'linkedin.com/jobs' in url:
            # Look for job title
            title_selectors = [
                'h1[class*="job-title"]',
                'h1[class*="title"]',
                '.job-title',
                '.title',
                'h1'
            ]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    job_title = title_elem.get_text().strip()
                    break
            
            # Look for company name
            company_selectors = [
                '[class*="company"]',
                '[class*="employer"]',
                '.company-name',
                '.employer-name'
            ]
            for selector in company_selectors:
                company_elem = soup.select_one(selector)
                if company_elem:
                    company = company_elem.get_text().strip()
                    break
            
            # Extract job description (look for common patterns)
            desc_selectors = [
                '[class*="description"]',
                '[class*="details"]',
                '.job-description',
                '.description',
                '.details'
            ]
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    job_description = desc_elem.get_text().strip()
                    break
        
        # Generic company career pages
        else:
            # Qualtrics-specific scraping
            if 'qualtrics.com' in url:
                # Look for Qualtrics-specific content structure
                job_content = []
                
                # Look for job description in common Qualtrics patterns
                desc_selectors = [
                    '[class*="description"]',
                    '[class*="details"]',
                    '[class*="content"]',
                    '[class*="job"]',
                    '.job-description',
                    '.description',
                    '.details',
                    'main',
                    'article',
                    'section',
                    'div[class*="body"]',
                    'div[class*="text"]'
                ]
                
                for selector in desc_selectors:
                    elements = soup.select(selector)
                    for elem in elements:
                        text = elem.get_text().strip()
                        if len(text) > 100:  # Only consider substantial content
                            job_content.append(text)
                
                if job_content:
                    # Take the longest content block as the job description
                    job_description = max(job_content, key=len)
                else:
                    # Fallback: try to extract from the entire page content
                    # Remove navigation, headers, footers
                    for elem in soup(['nav', 'header', 'footer', 'script', 'style']):
                        elem.decompose()
                    
                    # Get remaining text
                    remaining_text = soup.get_text()
                    if len(remaining_text) > 200:
                        job_description = remaining_text[:3000]  # Take first 3000 chars
                
                # Extract job title from Qualtrics page
                title_selectors = [
                    'h1',
                    '[class*="title"]',
                    '[class*="job-title"]',
                    '.job-title',
                    '.title',
                    '[class*="position"]',
                    '[class*="role"]',
                    'h2',
                    'h3'
                ]
                
                for selector in title_selectors:
                    title_elem = soup.select_one(selector)
                    if title_elem:
                        potential_title = title_elem.get_text().strip()
                        print(f"🔍 Debug - Found title with selector '{selector}': {potential_title}")
                        
                        # Skip if this looks like an error message
                        if any(phrase in potential_title.lower() for phrase in [
                            'we\'re sorry', 'job has been filled', 'position has been filled',
                            'no longer accepting', 'position closed'
                        ]):
                            print(f"🔍 Debug - Skipping error message title: {potential_title}")
                            continue
                        
                        job_title = potential_title
                        break
                
                # If no title found, try to extract from URL
                if not job_title and 'qualtrics.com' in url:
                    # Extract from URL path
                    url_parts = url.split('/')
                    for part in url_parts:
                        if part and '-' in part:
                            # Convert URL slug to title
                            potential_title = part.replace('-', ' ').title()
                            if 'sales' in potential_title.lower() or 'development' in potential_title.lower():
                                job_title = potential_title
                                print(f"🔍 Debug - Extracted title from URL: {job_title}")
                                break
                
                # Extract company name
                company = 'qualtrics'
            
            # Generic scraping for other companies
            else:
                # Look for common job description patterns
                job_keywords = ['job description', 'role description', 'position description', 
                              'responsibilities', 'requirements', 'qualifications', 'about this role']
                
                # Find paragraphs containing job-related content
                paragraphs = soup.find_all(['p', 'div', 'section'])
                job_content = []
                
                for p in paragraphs:
                    p_text = p.get_text().strip()
                    if any(keyword in p_text.lower() for keyword in job_keywords):
                        job_content.append(p_text)
                
                if job_content:
                    job_description = '\n\n'.join(job_content)
                
                # Try to extract job title from page title or headings
                page_title = soup.find('title')
                if page_title:
                    title_text = page_title.get_text()
                    # Look for patterns like "Job Title - Company" or "Job Title at Company"
                    title_match = re.search(r'([^-|]+?)(?:\s*[-|]\s*|\s+at\s+)([^-|]+)', title_text)
                    if title_match:
                        job_title = title_match.group(1).strip()
                        company = title_match.group(2).strip()
        
        # Debug: Print what we found
        print(f"🔍 Debug - URL: {url}")
        print(f"🔍 Debug - Page title: {soup.find('title').get_text() if soup.find('title') else 'No title found'}")
        print(f"🔍 Debug - Text length: {len(text)}")
        print(f"🔍 Debug - First 200 chars: {text[:200]}")
        
        # Check for common scraping issues
        if len(text) < 100:
            if 'workday' in url.lower() or 'myworkdayjobs' in url.lower():
                return jsonify({
                    'success': False,
                    'error': 'This job posting uses Workday (requires JavaScript). Please copy the job description manually or try the LinkedIn version of this posting.',
                    'job_description': '',
                    'job_title': '',
                    'company': '',
                    'url': url
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': 'Unable to extract job content from this URL. This could be due to:\n• The job posting requiring JavaScript\n• The job being no longer active\n• Website blocking automated access\n\nPlease copy and paste the full job description manually into the "Job Description" field below.',
                    'job_description': '',
                    'job_title': '',
                    'company': '',
                    'url': url
                }), 400
        
        # Check if the job posting is no longer active (do this early)
        if any(phrase in text.lower() for phrase in ['job has been filled', 'position has been filled', 'no longer accepting applications', 'position closed', 'we\'re sorry']):
            return jsonify({
                'success': False,
                'error': 'This job posting is no longer active or has been filled. Please try a different job posting or paste the job description manually.',
                'job_description': '',
                'job_title': '',
                'company': '',
                'url': url
            }), 400
        
        # If we couldn't extract specific content, use the cleaned page text
        if not job_description:
            # Take the first 2000 characters as a fallback
            job_description = text[:2000]
        
        # Clean up the job description
        if job_description:
            # Remove excessive whitespace
            job_description = re.sub(r'\s+', ' ', job_description)
            # Remove common web artifacts
            job_description = re.sub(r'(cookie|privacy|terms|conditions|apply|application)', '', job_description, flags=re.IGNORECASE)
            job_description = job_description.strip()
        
        # Clean up job title - remove common prefixes
        if job_title:
            # Remove common prefixes
            job_title = re.sub(r'^(job application for|application for|apply for)\s*', '', job_title, flags=re.IGNORECASE)
            job_title = job_title.strip()
            
            # Try to match to known roles for better consistency
            job_title = match_to_known_role(job_title)
        
        return jsonify({
            'success': True,
            'job_description': job_description,
            'job_title': job_title,
            'company': company,  # Don't auto-populate preferred companies
            'url': url
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch URL: {str(e)}'
        }), 400
    except Exception as e:
        print(f"Error fetching job description: {e}")
        return jsonify({
            'success': False,
            'error': f'Error processing URL: {str(e)}'
        }), 500

def match_to_known_role(job_title):
    """Match job title to known role names for consistency."""
    if not job_title:
        return job_title
    
    # Known role mappings (canonical names)
    known_roles = {
        'customer success manager': 'Customer Success Manager',
        'csm': 'Customer Success Manager',
        'account executive': 'Account Executive',
        'ae': 'Account Executive',
        'sales development representative': 'Sales Development Representative',
        'sdr': 'Sales Development Representative',
        'business development representative': 'Business Development Representative',
        'bdr': 'Business Development Representative',
        'sales representative': 'Sales Representative',
        'sales rep': 'Sales Representative',
        'software engineer': 'Software Engineer',
        'developer': 'Software Engineer',
        'product manager': 'Product Manager',
        'pm': 'Product Manager',
        'data scientist': 'Data Scientist',
        'ml engineer': 'Data Scientist',
        'machine learning engineer': 'Data Scientist',
        'marketing manager': 'Marketing Manager',
        'financial planning & analysis manager': 'Financial Planning & Analysis Manager',
        'fp&a manager': 'Financial Planning & Analysis Manager',
        'revenue operations manager': 'Revenue Operations Manager',
        'revops manager': 'Revenue Operations Manager',
        'gtm finance manager': 'GTM Finance Manager',
        'go-to-market finance manager': 'GTM Finance Manager',
        'strategic finance manager': 'Strategic Finance Manager',
        'business finance manager': 'Business Finance Manager',
        'financial operations manager': 'Financial Operations Manager',
        'revenue strategy manager': 'Revenue Strategy Manager',
        'business intelligence manager': 'Business Intelligence Manager',
        'bi manager': 'Business Intelligence Manager',
        'data analytics manager': 'Data Analytics Manager',
        'analytics manager': 'Data Analytics Manager',
        'corporate finance manager': 'Corporate Finance Manager',
        'strategy manager': 'Strategy Manager',
        'business strategy manager': 'Business Strategy Manager',
        'strategic planning manager': 'Strategic Planning Manager',
        'corporate strategy manager': 'Corporate Strategy Manager',
        'business development manager': 'Business Development Manager',
        'strategic initiatives manager': 'Strategic Initiatives Manager',
        'business operations manager': 'Business Operations Manager',
        'strategic partnerships manager': 'Strategic Partnerships Manager',
        'operations manager': 'Operations Manager',
        'process improvement manager': 'Process Improvement Manager',
        'operational excellence manager': 'Operational Excellence Manager',
        'business process manager': 'Business Process Manager',
        'operations strategy manager': 'Operations Strategy Manager',
        'operational analytics manager': 'Operational Analytics Manager',
        'solution architect': 'Solution Architect',
        'solutions architect': 'Solution Architect',
        'solution consultant': 'Solution Consultant',
        'solutions consultant': 'Solution Consultant',
        'data engineer': 'Data Engineer',
        'devops engineer': 'DevOps Engineer',
        'engineering manager': 'Engineering Manager',
        'business analyst': 'Business Analyst',
        'data analyst': 'Data Analyst',
        'quality assurance': 'Quality Assurance Engineer',
        'qa engineer': 'Quality Assurance Engineer',
        'research scientist': 'Research Scientist'
    }
    
    # Try exact match first
    title_lower = job_title.lower().strip()
    if title_lower in known_roles:
        return known_roles[title_lower]
    
    # Try partial matches
    for key, value in known_roles.items():
        if key in title_lower or title_lower in key:
            return value
    
    # If no match found, return the cleaned title as-is
    return job_title

@app.route('/health')
def simple_health():
    """Simple health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'message': 'Referral system is running'
    })

@app.route('/api/contacts-info')
def contacts_info():
    """Get information about currently loaded contacts - SECURE VERSION."""
    try:
        # Get current user's organization
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get organisation stats
        stats = get_organisation_stats(current_user.organisation_id)
        
        # Get sample contacts (limited to 5 for security)
        contacts = get_organisation_contacts_for_job(current_user.organisation_id)
        sample_contacts = []
        
        for contact in contacts[:5]:  # Limit to 5 for security
            sample_contacts.append({
                'First Name': contact.first_name,
                'Last Name': contact.last_name,
                'Company': contact.company or '',
                'Position': contact.position or ''
            })
        
        return jsonify({
            'total_contacts': stats['total_contacts'],
            'source': f"Database: {current_user.organisation.name}",
            'sample_contacts': sample_contacts,
            'organisation_stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# SECURITY: Removed /api/contacts endpoint to prevent directory access
# Users can only access contacts through job-specific matching

# Job Descriptions API endpoints
@app.route('/api/job-descriptions', methods=['GET'])
def get_job_descriptions():
    """Get all job descriptions."""
    try:
        # For now, return empty list - you'll need to implement a database
        # This is a placeholder for the job descriptions storage
        job_descriptions = []
        
        return jsonify({
            'success': True,
            'job_descriptions': job_descriptions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/job-descriptions', methods=['POST'])
def create_job_description():
    """Create a new job description."""
    try:
        data = request.get_json()
        
        # For now, just return success - you'll need to implement database storage
        # This is a placeholder for the job description creation
        
        return jsonify({
            'success': True,
            'message': 'Job description created successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/job-descriptions/<int:job_id>', methods=['GET'])
def get_job_description(job_id):
    """Get a specific job description."""
    try:
        # For now, return a placeholder - you'll need to implement database lookup
        # This is a placeholder for the job description retrieval
        
        return jsonify({
            'success': False,
            'error': 'Job description not found'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/job-descriptions/<int:job_id>', methods=['DELETE'])
def delete_job_description(job_id):
    """Delete a job description."""
    try:
        # For now, just return success - you'll need to implement database deletion
        # This is a placeholder for the job description deletion
        
        return jsonify({
            'success': True,
            'message': 'Job description deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/job-descriptions/stats', methods=['GET'])
def get_job_descriptions_stats():
    """Get statistics for job descriptions."""
    try:
        # For now, return placeholder stats - you'll need to implement database queries
        stats = {
            'total_jobs': 0,
            'active_jobs': 0,
            'total_referrals': 0,
            'avg_candidates': 0
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Referrals API endpoints
@app.route('/api/referrals', methods=['GET'])
def get_referrals():
    """Get all referrals for the current user."""
    try:
        # For now, return empty list - you'll need to implement database queries
        # This is a placeholder for the referrals retrieval
        
        referrals = []
        stats = {
            'total_jobs': 0,
            'total_candidates': 0,
            'exact_matches': 0,
            'other_matches': 0
        }
        
        return jsonify({
            'success': True,
            'referrals': referrals,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== MULTI-TENANT SYSTEM ROUTES =====

@app.route('/register-company')
def register_company_page():
    """Company registration page."""
    return render_template('register_company.html')

@app.route('/api/register-company', methods=['POST'])
def register_company():
    """Register a new company."""
    try:
        data = request.get_json()
        company_name = data.get('companyName', '').strip()
        admin_email = data.get('adminEmail', '').strip()
        admin_name = data.get('adminName', '').strip()
        company_domain = data.get('companyDomain', '').strip()
        from_email = data.get('fromEmail', '').strip()
        from_name = data.get('fromName', '').strip()
        
        # Validate required fields
        if not all([company_name, admin_email, admin_name, from_email, from_name]):
            return jsonify({
                'success': False,
                'error': 'Company name, admin email, admin name, referral email, and referral name are required'
            }), 400
        
        # Validate email format
        if not validate_email(admin_email):
            return jsonify({
                'success': False,
                'error': 'Invalid admin email format'
            }), 400
            
        if not validate_email(from_email):
            return jsonify({
                'success': False,
                'error': 'Invalid referral email format'
            }), 400
        
        # Sanitize inputs
        company_name = validate_input(company_name, max_length=100)
        admin_email = validate_input(admin_email, max_length=255)
        admin_name = validate_input(admin_name, max_length=100)
        company_domain = validate_input(company_domain, max_length=100)
        from_email = validate_input(from_email, max_length=255)
        from_name = validate_input(from_name, max_length=100)
        
        # Validate input lengths
        if len(company_name) < 2:
            return jsonify({
                'success': False,
                'error': 'Company name must be at least 2 characters'
            }), 400
        
        if len(admin_name) < 2:
            return jsonify({
                'success': False,
                'error': 'Admin name must be at least 2 characters'
            }), 400
        
        # Check if company already exists
        existing_org = Organisation.query.filter_by(name=company_name).first()
        if existing_org:
            return jsonify({
                'success': False,
                'error': 'Company already exists'
            }), 400
        
        # Check if admin email already exists
        existing_admin = User.query.filter_by(email=admin_email).first()
        if existing_admin:
            return jsonify({
                'success': False,
                'error': 'Admin email already registered'
            }), 400
        
        # Create new organisation
        new_org = Organisation(
            name=company_name,
            domain=company_domain,
            plan='free',  # Start with free plan
            from_email=from_email,
            from_name=from_name
        )
        db.session.add(new_org)
        db.session.flush()
        
        # Create admin user
        admin_user = User(
            organisation_id=new_org.id,
            email=admin_email,
            name=admin_name,
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()
        
        secure_log(f"New company registered: {company_name} with admin {admin_name}")
        
        return jsonify({
            'success': True,
            'message': 'Company registered successfully',
            'organisation_id': new_org.id,
            'admin_id': admin_user.id
        })
        
    except Exception as e:
        db.session.rollback()
        secure_log(f"Company registration failed: {str(e)}", "ERROR")
        return jsonify({
            'success': False,
            'error': 'Registration failed. Please try again.'
        }), 500

@app.route('/api/invite-employee', methods=['POST'])
@require_auth
def invite_employee():
    """Invite a new employee or admin to the company."""
    try:
        data = request.get_json()
        employee_email = data.get('employeeEmail', '').strip()
        employee_name = data.get('employeeName', '').strip()
        employee_role = data.get('employeeRole', 'employee').strip()  # New field
        
        if not all([employee_email, employee_name]):
            return jsonify({
                'success': False,
                'error': 'Employee email and name are required'
            }), 400
        
        # Validate role
        if employee_role not in ['employee', 'recruiter', 'admin']:
            return jsonify({
                'success': False,
                'error': 'Role must be "employee", "recruiter", or "admin"'
            }), 400
        
        # Get current user's organisation
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Not authenticated'
            }), 401
        
        current_user = User.query.get(user_id)
        if not current_user or current_user.role != 'admin':
            return jsonify({
                'success': False,
                'error': 'Only admins can invite users'
            }), 403
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=employee_email).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': 'User email already registered'
            }), 400
        
        # Create new user
        new_user = User(
            organisation_id=current_user.organisation_id,
            email=employee_email,
            name=employee_name,
            role=employee_role
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Send invitation email
        email_result = None
        if email_service:
            try:
                # Use organization-specific email settings if available
                if current_user.organisation.from_email:
                    email_service.from_email = current_user.organisation.from_email
                if current_user.organisation.from_name:
                    email_service.from_name = current_user.organisation.from_name
                
                email_result = email_service.send_team_invitation_email(
                    employee_name=employee_name,
                    employee_email=employee_email,
                    role=employee_role,
                    company_name=current_user.organisation.name,
                    inviter_name=current_user.name
                )
                
                if email_result['success']:
                    secure_log(f"📧 Invitation email sent to {employee_name} ({employee_email})")
                else:
                    secure_log(f"⚠️ Failed to send invitation email to {employee_name}: {email_result.get('error', 'Unknown error')}")
            except Exception as email_error:
                secure_log(f"⚠️ Error sending invitation email: {str(email_error)}")
        
        role_text = "admin" if employee_role == 'admin' else "employee"
        message = f'{role_text.title()} invited successfully'
        
        # Add email status to message
        if email_result and email_result['success']:
            message += ' and invitation email sent'
        elif email_result and not email_result['success']:
            message += ' (email invitation failed)'
        else:
            message += ' (email service unavailable)'
        
        return jsonify({
            'success': True,
            'message': message,
            'user_id': new_user.id,
            'role': employee_role,
            'email_sent': email_result['success'] if email_result else False
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/company-dashboard', methods=['GET'])
def get_company_dashboard():
    """Get company dashboard data."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Not authenticated'
            }), 401
        
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        organisation = Organisation.query.get(current_user.organisation_id)
        if not organisation:
            return jsonify({
                'success': False,
                'error': 'Organisation not found'
            }), 404
        
        # Get company stats
        stats = get_organisation_stats(current_user.organisation_id)
        
        # Get all employees in the company
        employees = User.query.filter_by(organisation_id=current_user.organisation_id).all()
        employee_data = []
        for emp in employees:
            employee_data.append({
                'id': emp.id,
                'name': emp.name,
                'email': emp.email,
                'role': emp.role,
                'created_at': emp.created_at.isoformat() if emp.created_at else None
            })
        
        return jsonify({
            'success': True,
            'organisation': {
                'id': organisation.id,
                'name': organisation.name,
                'domain': organisation.domain,
                'plan': organisation.plan
            },
            'stats': stats,
            'employees': employee_data,
            'current_user': {
                'id': current_user.id,
                'name': current_user.name,
                'email': current_user.email,
                'role': current_user.role
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/dashboard')
@require_auth
def dashboard():
    """Company dashboard page."""
    print(f"🔍 DEBUG: Dashboard accessed - session: {dict(session)}")
    
    user_id = session.get('user_id')
    print(f"🔍 DEBUG: Dashboard user_id from session: {user_id}")
    
    user = User.query.get(user_id)
    print(f"🔍 DEBUG: Dashboard user lookup result: {user}")
    
    if not user:
        print(f"❌ DEBUG: Dashboard - No user found, redirecting to login")
        return redirect(url_for('login'))
    
    print(f"✅ DEBUG: Dashboard - User found: {user.name} ({user.email})")
    
    # Get organisation data
    organisation = user.organisation
    print(f"✅ DEBUG: Dashboard - Organisation: {organisation.name if organisation else 'None'}")
    
    # Get team members
    team_members = User.query.filter_by(organisation_id=user.organisation_id).all()
    print(f"✅ DEBUG: Dashboard - Team members count: {len(team_members)}")
    
    # Get contact count
    contact_count = db.session.query(Contact).join(EmployeeContact).filter(
        EmployeeContact.organisation_id == user.organisation_id
    ).count()
    print(f"✅ DEBUG: Dashboard - Contact count: {contact_count}")
    
    # Get job descriptions count
    job_count = JobDescription.query.filter_by(organisation_id=user.organisation_id).count()
    print(f"✅ DEBUG: Dashboard - Job count: {job_count}")
    
    print(f"✅ DEBUG: Dashboard - Rendering template")
    return render_template('dashboard.html', 
                         user=user, 
                         organisation=organisation,
                         team_members=team_members,
                         contact_count=contact_count,
                         job_count=job_count)

@app.route('/referrals')
@require_auth
def referrals_page():
    """Referrals management page."""
    return render_template('referrals.html')

@app.route('/api/init-database', methods=['POST', 'GET'])
@csrf.exempt
def init_database_endpoint():
    """Manually initialize database with demo organization and run migrations."""
    try:
        # First, run database migration to add missing columns
        from sqlalchemy import text
        
        print("🔧 Running database migration...")
        
        # Check if from_email column exists and add it if missing
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'organisations' 
            AND column_name = 'from_email'
        """))
        
        if not result.fetchone():
            print("➕ Adding from_email column to organisations table...")
            db.session.execute(text("ALTER TABLE organisations ADD COLUMN from_email VARCHAR(255)"))
            db.session.commit()
            print("✅ Added from_email column")
        else:
            print("✅ from_email column already exists")
        
        # Check if from_name column exists and add it if missing
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'organisations' 
            AND column_name = 'from_name'
        """))
        
        if not result.fetchone():
            print("➕ Adding from_name column to organisations table...")
            db.session.execute(text("ALTER TABLE organisations ADD COLUMN from_name VARCHAR(255)"))
            db.session.commit()
            print("✅ Added from_name column")
        else:
            print("✅ from_name column already exists")
        
        # Check if user_sessions table exists and create it if missing
        result = db.session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'user_sessions'
        """))
        
        if not result.fetchone():
            print("➕ Creating user_sessions table...")
            db.session.execute(text("""
                CREATE TABLE user_sessions (
                    id VARCHAR(36) PRIMARY KEY,
                    session_id VARCHAR(36) UNIQUE NOT NULL,
                    user_id VARCHAR(36) REFERENCES users(id),
                    session_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.execute(text("CREATE INDEX idx_user_sessions_session_id ON user_sessions(session_id)"))
            db.session.commit()
            print("✅ Created user_sessions table")
        else:
            print("✅ user_sessions table already exists")
        
        print("✅ Database migration completed successfully")
        
        # Now check if demo organization already exists (after migration)
        demo_org = Organisation.query.filter_by(name="Demo Company").first()
        
        if demo_org:
            return jsonify({
                'success': True,
                'message': 'Demo organization already exists. Database migration completed.',
                'organisation_id': str(demo_org.id)
            })
        
        # Create demo organization
        from database import create_demo_organisation
        create_demo_organisation()
        
        # Get the created organization
        demo_org = Organisation.query.filter_by(name="Demo Company").first()
        
        return jsonify({
            'success': True,
            'message': 'Database initialized successfully',
            'organisation_id': str(demo_org.id)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/create-demo-users', methods=['POST', 'GET'])
@csrf.exempt
def create_demo_users_endpoint():
    """Create demo users for the organization with the most contacts."""
    try:
        from models import EmployeeContact
        
        # Find the organization with the most contacts
        org_contact_counts = db.session.query(
            EmployeeContact.organisation_id,
            db.func.count(EmployeeContact.id).label('contact_count')
        ).group_by(EmployeeContact.organisation_id).all()
        
        if not org_contact_counts:
            return jsonify({
                'success': False,
                'error': 'No organizations with contacts found'
            }), 404
        
        # Find organization with most contacts
        max_contacts = max(org_contact_counts, key=lambda x: x.contact_count)
        target_org_id = max_contacts.organisation_id
        contact_count = max_contacts.contact_count
        
        # Get the organization
        target_org = Organisation.query.get(target_org_id)
        if not target_org:
            return jsonify({
                'success': False,
                'error': 'Target organization not found'
            }), 404
        
        # Check if demo users already exist
        existing_admin = User.query.filter_by(
            organisation_id=target_org_id,
            email="admin@demo.com"
        ).first()
        
        existing_employee = User.query.filter_by(
            organisation_id=target_org_id,
            email="employee@demo.com"
        ).first()
        
        created_users = []
        
        # Create demo admin user
        if not existing_admin:
            demo_admin = User(
                organisation_id=target_org_id,
                email="admin@demo.com",
                name="Demo Admin",
                role="admin"
            )
            db.session.add(demo_admin)
            created_users.append("admin@demo.com")
        
        # Create demo employee user
        if not existing_employee:
            demo_employee = User(
                organisation_id=target_org_id,
                email="employee@demo.com",
                name="Demo Employee",
                role="employee"
            )
            db.session.add(demo_employee)
            created_users.append("employee@demo.com")
        
        # Commit changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Demo users created for {target_org.name}',
            'organisation_name': target_org.name,
            'contact_count': contact_count,
            'created_users': created_users,
            'existing_users': {
                'admin': existing_admin.email if existing_admin else None,
                'employee': existing_employee.email if existing_employee else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== REFERRAL WORKFLOW ROUTES =====

@app.route('/api/request-referral', methods=['POST'])
def request_referral():
    """Request a referral from an employee for a specific contact."""
    try:
        data = request.get_json()
        contact_id = data.get('contactId')
        job_description = data.get('jobDescription', '')
        job_title = data.get('jobTitle', '')
        requester_message = data.get('requesterMessage', '')
        
        if not contact_id:
            return jsonify({
                'success': False,
                'error': 'Contact ID is required'
            }), 400
        
        # Get current user
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Not authenticated'
            }), 401
        
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Get the contact
        contact = Contact.query.get(contact_id)
        if not contact:
            return jsonify({
                'success': False,
                'error': 'Contact not found'
            }), 404
        
        # Find which employee in the organization knows this contact
        employee_contact = EmployeeContact.query.filter_by(
            contact_id=contact_id,
            organisation_id=current_user.organisation_id
        ).first()
        
        if not employee_contact:
            return jsonify({
                'success': False,
                'error': 'No employee in your organization knows this contact'
            }), 404
        
        # Get the employee who knows this contact
        employee = User.query.get(employee_contact.employee_id)
        if not employee:
            return jsonify({
                'success': False,
                'error': 'Employee not found'
            }), 404
        
        # Create referral request
        referral = Referral(
            organisation_id=current_user.organisation_id,
            requester_id=current_user.id,
            employee_id=employee.id,
            contact_id=contact_id,
            job_title=job_title,
            job_description=job_description,
            requester_message=requester_message,
            status='pending'
        )
        db.session.add(referral)
        db.session.commit()
        
        # Send email notification to employee via SendGrid
        if email_service:
            try:
                # Update email service with organization's email settings
                if current_user.organisation.from_email:
                    email_service.from_email = current_user.organisation.from_email
                if current_user.organisation.from_name:
                    email_service.from_name = current_user.organisation.from_name
                
                # Create contact data for email
                contact_data = [{
                    'name': f"{contact.first_name} {contact.last_name}",
                    'position': contact.position or 'N/A',
                    'company': contact.company or 'N/A',
                    'location': contact.location or 'N/A',
                    'linkedin_url': contact.linkedin_url or 'N/A'
                }]
                
                # Send individual referral email
                email_result = email_service.send_referral_email(
                    employee_name=employee.name,
                    contacts=contact_data,
                    job_title=job_title,
                    job_location=data.get('jobLocation', 'N/A')
                )
                
                if email_result['success']:
                    secure_log(f"📧 Referral email sent to {employee.name} ({employee.email}) for {contact.first_name} {contact.last_name}")
                else:
                    secure_log(f"⚠️ Failed to send email to {employee.name}: {email_result.get('error', 'Unknown error')}")
                    
            except Exception as email_error:
                secure_log(f"⚠️ Email service error: {str(email_error)}")
        else:
            secure_log(f"📧 Referral request logged (email service not available) to {employee.name} ({employee.email}) for {contact.first_name} {contact.last_name}")
        
        return jsonify({
            'success': True,
            'message': f'Referral request sent to {employee.name}',
            'referral_id': referral.id,
            'employee_name': employee.name,
            'employee_email': employee.email
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/send-bulk-referral-emails', methods=['POST'])
def send_bulk_referral_emails():
    """Send bulk referral emails to employees for multiple contacts."""
    try:
        data = request.get_json()
        selected_contacts = data.get('selectedContacts', [])
        job_title = data.get('jobTitle', '')
        job_location = data.get('jobLocation', '')
        
        if not selected_contacts:
            return jsonify({
                'success': False,
                'error': 'No contacts selected'
            }), 400
        
        # Get current user
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Not authenticated'
            }), 401
        
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Group contacts by employee
        contacts_by_employee = {}
        successful_emails = 0
        total_emails = 0
        
        for contact_data in selected_contacts:
            contact_id = contact_data.get('contactId')
            if not contact_id:
                continue
                
            # Get the contact
            contact = Contact.query.get(contact_id)
            if not contact:
                continue
            
            # Find which employee knows this contact
            employee_contact = EmployeeContact.query.filter_by(
                contact_id=contact_id,
                organisation_id=current_user.organisation_id
            ).first()
            
            if not employee_contact:
                continue
            
            # Get the employee
            employee = User.query.get(employee_contact.employee_id)
            if not employee:
                continue
            
            # Add to employee's contact list
            if employee.name not in contacts_by_employee:
                contacts_by_employee[employee.name] = []
            
            contacts_by_employee[employee.name].append({
                'name': f"{contact.first_name} {contact.last_name}",
                'position': contact.position or 'N/A',
                'company': contact.company or 'N/A',
                'location': contact.location or 'N/A',
                'linkedin_url': contact.linkedin_url or 'N/A'
            })
        
        # Send emails to each employee
        if email_service and contacts_by_employee:
            # Update email service with organization's email settings
            if current_user.organisation.from_email:
                email_service.from_email = current_user.organisation.from_email
            if current_user.organisation.from_name:
                email_service.from_name = current_user.organisation.from_name
                
            email_results = email_service.send_bulk_referral_emails(
                contacts_by_employee=contacts_by_employee,
                job_title=job_title,
                job_location=job_location
            )
            
            successful_emails = email_results.get('successful_emails', 0)
            total_emails = email_results.get('total_emails', 0)
            
            secure_log(f"📧 Bulk referral emails sent: {successful_emails}/{total_emails} successful")
        else:
            secure_log(f"📧 Bulk referral emails logged (email service not available): {len(contacts_by_employee)} employees")
            successful_emails = len(contacts_by_employee)
            total_emails = len(contacts_by_employee)
        
        return jsonify({
            'success': True,
            'message': f'Bulk referral emails sent to {len(contacts_by_employee)} employees',
            'successful_emails': successful_emails,
            'total_emails': total_emails,
            'employees_contacted': list(contacts_by_employee.keys())
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/my-referrals', methods=['GET'])
def get_my_referrals():
    """Get all referrals for the current user."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Not authenticated'
            }), 401
        
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Get referrals where user is either requester or employee
        referrals = Referral.query.filter(
            (Referral.requester_id == current_user.id) | 
            (Referral.employee_id == current_user.id)
        ).filter_by(organisation_id=current_user.organisation_id).all()
        
        referral_data = []
        for referral in referrals:
            # Get contact details
            contact = Contact.query.get(referral.contact_id)
            requester = User.query.get(referral.requester_id)
            employee = User.query.get(referral.employee_id)
            
            referral_data.append({
                'id': referral.id,
                'contact_name': f"{contact.first_name} {contact.last_name}" if contact else "Unknown",
                'contact_company': contact.company if contact else "",
                'contact_position': contact.position if contact else "",
                'job_title': referral.job_title,
                'requester_name': requester.name if requester else "Unknown",
                'employee_name': employee.name if employee else "Unknown",
                'status': referral.status,
                'requester_message': referral.requester_message,
                'created_at': referral.created_at.isoformat() if referral.created_at else None,
                'is_my_request': referral.requester_id == current_user.id,
                'is_my_referral': referral.employee_id == current_user.id
            })
        
        return jsonify({
            'success': True,
            'referrals': referral_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/update-referral-status', methods=['POST'])
def update_referral_status():
    """Update the status of a referral (employee response)."""
    try:
        data = request.get_json()
        referral_id = data.get('referralId')
        new_status = data.get('status')  # 'accepted', 'declined', 'completed'
        employee_message = data.get('employeeMessage', '')
        
        if not referral_id or not new_status:
            return jsonify({
                'success': False,
                'error': 'Referral ID and status are required'
            }), 400
        
        # Get current user
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Not authenticated'
            }), 401
        
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Get the referral
        referral = Referral.query.get(referral_id)
        if not referral:
            return jsonify({
                'success': False,
                'error': 'Referral not found'
            }), 404
        
        # Check if user is the employee for this referral
        if referral.employee_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'You can only update referrals assigned to you'
            }), 403
        
        # Update referral status
        referral.status = new_status
        if employee_message:
            referral.employee_message = employee_message
        referral.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Log the update
        print(f"📝 Referral {referral_id} status updated to {new_status} by {current_user.name}")
        if employee_message:
            print(f"   Message: {employee_message}")
        
        return jsonify({
            'success': True,
            'message': f'Referral status updated to {new_status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/logout')
@require_auth
def logout():
    """User logout."""
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("🚀 Starting Referral Matching Web App...")
    print("📊 System loaded and ready")
    print("🌐 Open http://localhost:5000 in your browser")
    
    # Get port from environment variable (for Heroku)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
