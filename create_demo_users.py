#!/usr/bin/env python3
"""
Script to create demo users for the existing organization with 2.4k contacts.
This will add demo admin and employee users to the organization that has the most contacts.
"""

import os
import sys
from flask import Flask
from models import db, Organisation, User
from database import init_database

def create_demo_users():
    """Create demo users for the organization with the most contacts."""
    app = Flask(__name__)
    
    # Set up database connection
    database_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PUBLIC_URL')
    if not database_url:
        print("❌ No DATABASE_URL found in environment variables")
        return False
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Find the organization with the most contacts
            from models import EmployeeContact
            
            # Get contact counts per organization
            org_contact_counts = db.session.query(
                EmployeeContact.organisation_id,
                db.func.count(EmployeeContact.id).label('contact_count')
            ).group_by(EmployeeContact.organisation_id).all()
            
            if not org_contact_counts:
                print("❌ No organizations with contacts found")
                return False
            
            # Find organization with most contacts
            max_contacts = max(org_contact_counts, key=lambda x: x.contact_count)
            target_org_id = max_contacts.organisation_id
            contact_count = max_contacts.contact_count
            
            print(f"📊 Found organization with {contact_count} contacts")
            
            # Get the organization
            target_org = Organisation.query.get(target_org_id)
            if not target_org:
                print("❌ Target organization not found")
                return False
            
            print(f"🏢 Target organization: {target_org.name}")
            
            # Check if demo users already exist
            existing_admin = User.query.filter_by(
                organisation_id=target_org_id,
                email="admin@demo.com"
            ).first()
            
            existing_employee = User.query.filter_by(
                organisation_id=target_org_id,
                email="employee@demo.com"
            ).first()
            
            if existing_admin and existing_employee:
                print("✅ Demo users already exist:")
                print(f"   Admin: {existing_admin.email} ({existing_admin.name})")
                print(f"   Employee: {existing_employee.email} ({existing_employee.name})")
                return True
            
            # Create demo admin user
            if not existing_admin:
                demo_admin = User(
                    organisation_id=target_org_id,
                    email="admin@demo.com",
                    name="Demo Admin",
                    role="admin"
                )
                db.session.add(demo_admin)
                print("✅ Created demo admin user")
            else:
                print("✅ Demo admin user already exists")
            
            # Create demo employee user
            if not existing_employee:
                demo_employee = User(
                    organisation_id=target_org_id,
                    email="employee@demo.com",
                    name="Demo Employee",
                    role="employee"
                )
                db.session.add(demo_employee)
                print("✅ Created demo employee user")
            else:
                print("✅ Demo employee user already exists")
            
            # Commit changes
            db.session.commit()
            
            print("\n🎉 Demo users created successfully!")
            print(f"📧 Admin: admin@demo.com (Demo Admin)")
            print(f"📧 Employee: employee@demo.com (Demo Employee)")
            print(f"🏢 Organization: {target_org.name}")
            print(f"📊 Contacts: {contact_count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating demo users: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = create_demo_users()
    sys.exit(0 if success else 1)
