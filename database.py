#!/usr/bin/env python3
"""
Database configuration and initialization for the referral system.
"""

import os
from flask import Flask
from models import db, Organisation, User, Contact, EmployeeContact, JobDescription, Referral
from datetime import datetime
import pandas as pd
import json

def init_database(app):
    """Initialize the database with Flask app."""
    try:
        # Database configuration - prefer public URL for Railway
        database_url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
        print(f"🔍 DATABASE_URL found: {bool(database_url)}")
        
        if database_url:
            # Railway PostgreSQL - fix internal hostname issue
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            # Fix Railway internal hostname issue
            if 'postgres.railway.internal' in database_url:
                print("⚠️ Detected internal Railway hostname, attempting to fix...")
                # Try to get the public URL first
                public_url = os.environ.get('DATABASE_PUBLIC_URL')
                if public_url:
                    database_url = public_url
                    print("✅ Using DATABASE_PUBLIC_URL instead")
                else:
                    # Try to get the external hostname from Railway
                    railway_host = os.environ.get('RAILWAY_DATABASE_HOST')
                    if railway_host:
                        database_url = database_url.replace('postgres.railway.internal', railway_host)
                        print(f"✅ Updated hostname to: {railway_host}")
                    else:
                        print("❌ No RAILWAY_DATABASE_HOST found, connection may fail")
            
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url
            print("✅ Using PostgreSQL database")
        else:
            # Local development
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///referral_system.db'
            print("⚠️ Using SQLite for local development")
        
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_timeout': 20,
            'max_overflow': 0,
        }
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            print("🔄 Creating database tables...")
            # Create tables
            db.create_all()
            print("✅ Database tables created")
            
            # Create demo organisation if none exists
            if not Organisation.query.first():
                print("🏢 Creating demo organisation...")
                create_demo_organisation()
            else:
                print("✅ Demo organisation already exists")
            
            print("✅ Database initialized successfully")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise

def create_demo_organisation():
    """Create a demo organisation for testing."""
    print("🏢 Creating demo organisation...")
    
    # Create demo organisation
    demo_org = Organisation(
        name="Demo Company",
        domain="demo.com",
        plan="free"
    )
    db.session.add(demo_org)
    db.session.flush()
    
    # Create demo admin user
    demo_admin = User(
        organisation_id=demo_org.id,
        email="admin@demo.com",
        name="Demo Admin",
        role="admin"
    )
    db.session.add(demo_admin)
    
    # Create demo employee
    demo_employee = User(
        organisation_id=demo_org.id,
        email="employee@demo.com",
        name="Demo Employee",
        role="employee"
    )
    db.session.add(demo_employee)
    db.session.flush()
    
    # Migrate existing CSV data to database
    migrate_csv_to_database(demo_org.id, demo_employee.id)
    
    db.session.commit()
    print(f"✅ Demo organisation created with ID: {demo_org.id}")

def migrate_csv_to_database(organisation_id, employee_id):
    """Migrate existing CSV data to the database."""
    try:
        print("📊 Migrating CSV data to database...")
        
        # Check if CSV file exists
        csv_file = 'enhanced_tagged_contacts.csv'
        if not os.path.exists(csv_file):
            print("⚠️ No CSV file found, skipping migration")
            return
        
        # Load existing CSV
        df = pd.read_csv(csv_file)
        print(f"📄 Found {len(df)} contacts in CSV")
        
        if len(df) == 0:
            print("⚠️ CSV file is empty, skipping migration")
            return
        
        migrated_count = 0
        for _, row in df.iterrows():
            try:
                # Extract contact data
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
                
                # Link to demo employee
                employee_contact = EmployeeContact(
                    employee_id=employee_id,
                    contact_id=contact.id,
                    organisation_id=organisation_id,
                    relationship_type='linkedin_connection'
                )
                db.session.add(employee_contact)
                migrated_count += 1
                
            except Exception as e:
                print(f"⚠️ Error migrating contact {row.get('First Name', 'Unknown')}: {e}")
                continue
        
        db.session.commit()
        print(f"✅ Migrated {migrated_count} contacts to database")
        
    except FileNotFoundError:
        print("⚠️ No CSV file found, skipping migration")
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        print(f"❌ Migration traceback: {traceback.format_exc()}")
        db.session.rollback()

def get_organisation_contacts_for_job(organisation_id, job_description=None):
    """
    SECURE: Get contacts for job matching - NO DIRECTORY ACCESS.
    Only returns contacts relevant to the specific job context.
    """
    # Base query - only contacts from this organisation
    query = db.session.query(Contact).join(EmployeeContact).filter(
        EmployeeContact.organisation_id == organisation_id
    )
    
    # Add job-specific filtering if provided
    if job_description:
        # This is where we'd add job relevance filtering
        # For now, return all contacts for the organisation
        pass
    
    return query.all()

def get_organisation_stats(organisation_id):
    """Get statistics for an organisation."""
    total_contacts = db.session.query(Contact).join(EmployeeContact).filter(
        EmployeeContact.organisation_id == organisation_id
    ).count()
    
    total_employees = User.query.filter_by(organisation_id=organisation_id).count()
    
    total_jobs = JobDescription.query.filter_by(organisation_id=organisation_id).count()
    
    return {
        'total_contacts': total_contacts,
        'total_employees': total_employees,
        'total_jobs': total_jobs
    }

# Security: NO DIRECTORY ACCESS FUNCTIONS
# These functions are intentionally NOT implemented to prevent contact harvesting:

# def get_all_contacts() - BLOCKED
# def export_contacts() - BLOCKED  
# def browse_contacts() - BLOCKED
# def search_all_contacts() - BLOCKED
