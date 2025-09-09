#!/usr/bin/env python3
"""
Database migration script to add missing columns.
"""

import os
from flask import Flask
from models import db, Organisation, User, Contact, EmployeeContact, JobDescription, Referral

def create_app():
    """Create Flask app for migration."""
    app = Flask(__name__)
    
    # Database configuration - prefer public URL for Railway
    database_url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
    
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
    }
    
    db.init_app(app)
    return app

def migrate_database():
    """Add missing columns to existing tables."""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 Starting database migration...")
            
            # Check if columns exist and add them if missing
            from sqlalchemy import text
            
            # Check if from_email column exists
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
            
            # Check if from_name column exists
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
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("🎉 Database migration completed successfully!")
    else:
        print("💥 Database migration failed!")
        exit(1)
