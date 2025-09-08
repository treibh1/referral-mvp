#!/usr/bin/env python3
"""
Simple Flask web application for the referral matching system.
Demonstrates how to integrate the unified matcher into a web interface.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from referral_api import ReferralAPI
from enhanced_contact_tagger import EnhancedContactTagger
from email_service import ReferralEmailService
from user_management import UserManager
from email_notifications import EmailNotifier
import pandas as pd
import os
import json
import time
from werkzeug.utils import secure_filename

# Location enrichment temporarily disabled
# from smart_geo_enricher import SmartGeoEnricher

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

api = ReferralAPI()
tagger = EnhancedContactTagger()
user_manager = UserManager()
email_notifier = EmailNotifier()
email_service = ReferralEmailService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gamification')
def gamification():
    return render_template('gamification.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        
        # For MVP, simple session-based auth (no file writes)
        session['user_id'] = 'demo_user_123'
        session['user_email'] = email or 'demo@example.com'
        session['user_name'] = name or 'Demo User'
        
        # Skip email sending for MVP
        print(f"User logged in: {name} ({email})")
        
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """User dashboard."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = user_manager.get_user(user_id)
    pending_referrals = user_manager.get_pending_referrals(user_id)
    
    return render_template('dashboard.html', user=user, pending_referrals=pending_referrals)

@app.route('/import')
def import_page():
    """Contact import page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('import.html')

@app.route('/enrichment')
def enrichment_page():
    """Contact enrichment page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('contact_enrichment.html')

@app.route('/job-descriptions')
def job_descriptions_page():
    """Job descriptions management page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('job_descriptions.html')

@app.route('/referrals')
def referrals_page():
    """Referrals dashboard page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('referrals.html')

@app.route('/api/match', methods=['POST'])
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
        
        # For MVP, skip authentication check
        user_id = session.get('user_id', 'demo_user_123')
        
        # For now, use all contacts from the main CSV file
        try:
            contacts_df = pd.read_csv('enhanced_tagged_contacts.csv')
            print(f"📊 Using {len(contacts_df)} contacts from enhanced_tagged_contacts.csv")
        except Exception as e:
            print(f"❌ Error loading contacts: {e}")
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
        
        # Use the existing API instance (already configured with enhanced_tagged_contacts.csv)
        results = api.match_job(
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
        return jsonify(results)
            
    except Exception as e:
        print(f"Error in job matching: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/import-contacts', methods=['POST'])
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
        
        # Add contact IDs for tracking
        tagged_df['contact_id'] = [f"contact_{int(time.time())}_{i}" for i in range(len(tagged_df))]
        
        # Save tagged contacts
        output_filename = f"enhanced_tagged_contacts_{int(time.time())}.csv"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        tagged_df.to_csv(output_path, index=False)
        
        # Assign contacts to user
        if 'user_id' in session:
            user_id = session['user_id']
            contact_ids = tagged_df['contact_id'].tolist()
            user_manager.assign_contacts_to_user(user_id, contact_ids, filename)
        
        # Get summary statistics
        summary = tagger._print_tagging_summary(tagged_df)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported and tagged {len(tagged_df)} contacts',
            'filename': output_filename,
            'total_contacts': len(tagged_df),
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

@app.route('/api/stats')
def get_stats():
    """Get system statistics."""
    return jsonify(api.get_system_stats())

@app.route('/api/request-referral', methods=['POST'])
def request_referral():
    """Request referral for selected candidates."""
    try:
        data = request.get_json()
        contact_ids = data.get('contact_ids', [])
        job_description = data.get('job_description', '')
        company = data.get('company', '')
        
        # Get user ID from session
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        user_id = session['user_id']
        user = user_manager.get_user(user_id)
        
        # Record referral request
        referral_id = user_manager.record_referral_request(
            user_id, contact_ids, job_description, company
        )
        
        # Get contact details for email
        contact_details = []
        for contact_id in contact_ids:
            # This would need to be implemented to get contact details from the database
            # For now, we'll use placeholder data
            contact_details.append({
                'First Name': 'Contact',
                'Last Name': 'Name',
                'Position': 'Position',
                'Company': 'Company',
                'match_score': 85.0
            })
        
        # Send email notification
        email_notifier.send_referral_notification(
            user['email'], user['name'], contact_details, 
            job_description, company, referral_id
        )
        
        # Mark as notified
        user_manager.mark_referral_notified(referral_id)
        
        return jsonify({
            'success': True,
            'referral_id': referral_id,
            'message': f'Referral request sent to {user["email"]}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/referrals/<referral_id>')
def view_referral(referral_id):
    """View specific referral request."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # This would load the referral details
    # For now, return a placeholder page
    return render_template('referral_detail.html', referral_id=referral_id)

@app.route('/api/fetch-job', methods=['POST'])
def fetch_job_description():
    """Fetch job description from a URL."""
    try:
        data = request.get_json()
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

@app.route('/api/contacts')
def get_contacts():
    """Get all contacts for the gamification page."""
    try:
        # Check if CSV file exists
        csv_file = 'enhanced_tagged_contacts.csv'
        if not os.path.exists(csv_file):
            # Return empty contacts if file doesn't exist
            return jsonify({
                'success': True,
                'contacts': [],
                'total': 0,
                'message': 'No contacts file found - returning empty list'
            })
        
        # Load contacts from the CSV file
        df = pd.read_csv(csv_file)
        
        # Clean NaN values
        df = df.fillna('')
        
        # Convert to list of dictionaries
        contacts = df.to_dict('records')
        
        return jsonify({
            'success': True,
            'contacts': contacts,
            'total': len(contacts)
        })
    except Exception as e:
        print(f"Error in /api/contacts: {e}")
        # Return empty contacts on error instead of 500
        return jsonify({
            'success': True,
            'contacts': [],
            'total': 0,
            'message': f'Error loading contacts: {str(e)}'
        })

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

@app.route('/logout')
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
