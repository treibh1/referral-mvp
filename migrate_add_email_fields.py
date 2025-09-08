#!/usr/bin/env python3
"""
Migration script to add email fields to existing organizations.
"""

import os
import sys
from flask import Flask
from models import db, Organisation

def migrate_add_email_fields():
    """Add from_email and from_name fields to existing organizations."""
    
    # Create Flask app for database operations
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PUBLIC_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Get all organizations without email settings
            orgs_without_email = Organisation.query.filter(
                (Organisation.from_email.is_(None)) | (Organisation.from_email == '')
            ).all()
            
            print(f"Found {len(orgs_without_email)} organizations without email settings")
            
            for org in orgs_without_email:
                # Set default email settings based on organization name
                org.from_email = f"recruiting@{org.name.lower().replace(' ', '').replace('.', '')}.com"
                org.from_name = f"{org.name} Recruiting"
                
                print(f"Updated {org.name}: {org.from_email}")
            
            # Commit changes
            db.session.commit()
            print(f"✅ Successfully updated {len(orgs_without_email)} organizations")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    success = migrate_add_email_fields()
    sys.exit(0 if success else 1)
