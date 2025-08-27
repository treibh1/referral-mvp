#!/usr/bin/env python3
"""
Migration script to move existing CSV data to PostgreSQL database
"""

import os
import sys
import pandas as pd
import psycopg2
import json
from datetime import datetime
from typing import List, Dict

class DatabaseMigrator:
    def __init__(self):
        """Initialize the migrator with database connection"""
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Load existing CSV data
        self.csv_file = 'enhanced_tagged_contacts.csv'
        if not os.path.exists(self.csv_file):
            raise FileNotFoundError(f"CSV file {self.csv_file} not found")
        
        self.df = pd.read_csv(self.csv_file)
        print(f"Loaded {len(self.df)} contacts from CSV")
    
    def get_db_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.db_url)
    
    def create_demo_organization(self) -> int:
        """Create a demo organization and return its ID"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Create demo organization
            org_query = """
                INSERT INTO organisations (name, domain, subscription_plan)
                VALUES (%s, %s, %s)
                RETURNING id
            """
            cursor.execute(org_query, ('Demo Organization', 'demo.com', 'free'))
            org_id = cursor.fetchone()[0]
            
            # Create demo user
            user_query = """
                INSERT INTO users (organisation_id, email, name, role)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """
            cursor.execute(user_query, (org_id, 'admin@demo.com', 'Demo Admin', 'admin'))
            user_id = cursor.fetchone()[0]
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"Created demo organization (ID: {org_id}) and admin user (ID: {user_id})")
            return org_id
            
        except Exception as e:
            print(f"Error creating demo organization: {e}")
            raise
    
    def migrate_contacts(self) -> List[int]:
        """Migrate contacts from CSV to database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            contact_ids = []
            
            for index, row in self.df.iterrows():
                try:
                    # Prepare skills as JSON
                    skills = []
                    if pd.notna(row.get('skills')):
                        if isinstance(row['skills'], str):
                            skills = [skill.strip() for skill in row['skills'].split(',') if skill.strip()]
                    
                    # Insert contact
                    contact_query = """
                        INSERT INTO contacts (
                            full_name, current_company, current_title, location,
                            linkedin_url, skills, industry, seniority_level, years_experience
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """
                    
                    cursor.execute(contact_query, (
                        row.get('full_name', ''),
                        row.get('current_company', ''),
                        row.get('current_title', ''),
                        row.get('location', ''),
                        row.get('linkedin_url', ''),
                        json.dumps(skills),
                        row.get('industry', ''),
                        row.get('seniority_level', ''),
                        row.get('years_experience', None)
                    ))
                    
                    contact_id = cursor.fetchone()[0]
                    contact_ids.append(contact_id)
                    
                    if (index + 1) % 100 == 0:
                        print(f"Migrated {index + 1} contacts...")
                
                except Exception as e:
                    print(f"Error migrating contact {row.get('full_name', 'Unknown')}: {e}")
                    continue
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"Successfully migrated {len(contact_ids)} contacts")
            return contact_ids
            
        except Exception as e:
            print(f"Error migrating contacts: {e}")
            raise
    
    def create_demo_employee_and_links(self, org_id: int, contact_ids: List[int]):
        """Create a demo employee and link all contacts"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Create demo employee (first contact)
            if contact_ids:
                demo_contact_id = contact_ids[0]
                
                employee_query = """
                    INSERT INTO employees (
                        organisation_id, contact_id, employee_id, department
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING id
                """
                cursor.execute(employee_query, (org_id, demo_contact_id, 'EMP001', 'Engineering'))
                employee_id = cursor.fetchone()[0]
                
                # Link all other contacts to this employee
                for contact_id in contact_ids[1:100]:  # Limit to first 100 for demo
                    link_query = """
                        INSERT INTO employee_contacts (
                            employee_id, contact_id, relationship_type, relationship_strength
                        ) VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(link_query, (employee_id, contact_id, 'colleague', 3))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                print(f"Created demo employee and linked {min(100, len(contact_ids)-1)} contacts")
            
        except Exception as e:
            print(f"Error creating demo employee: {e}")
            raise
    
    def migrate_core_job_roles(self):
        """Migrate core job roles"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Define some core job roles
            core_roles = [
                {
                    'title': 'Software Engineer',
                    'category': 'Engineering',
                    'industry': 'Technology',
                    'required_skills': ['Python', 'JavaScript', 'SQL'],
                    'preferred_skills': ['React', 'Node.js', 'AWS'],
                    'seniority_level': 'Mid'
                },
                {
                    'title': 'Sales Development Representative',
                    'category': 'Sales',
                    'industry': 'Technology',
                    'required_skills': ['Sales', 'Communication', 'CRM'],
                    'preferred_skills': ['B2B Sales', 'Lead Generation', 'Salesforce'],
                    'seniority_level': 'Entry'
                },
                {
                    'title': 'Product Manager',
                    'category': 'Product',
                    'industry': 'Technology',
                    'required_skills': ['Product Management', 'Agile', 'User Research'],
                    'preferred_skills': ['Data Analysis', 'A/B Testing', 'Roadmapping'],
                    'seniority_level': 'Mid'
                },
                {
                    'title': 'Customer Success Manager',
                    'category': 'Customer Success',
                    'industry': 'Technology',
                    'required_skills': ['Customer Service', 'Account Management', 'Communication'],
                    'preferred_skills': ['CRM', 'Customer Onboarding', 'Retention'],
                    'seniority_level': 'Mid'
                }
            ]
            
            for role in core_roles:
                role_query = """
                    INSERT INTO core_job_roles (
                        title, category, industry, required_skills, preferred_skills, seniority_level
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(role_query, (
                    role['title'],
                    role['category'],
                    role['industry'],
                    json.dumps(role['required_skills']),
                    json.dumps(role['preferred_skills']),
                    role['seniority_level']
                ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"Migrated {len(core_roles)} core job roles")
            
        except Exception as e:
            print(f"Error migrating core job roles: {e}")
            raise
    
    def run_migration(self):
        """Run the complete migration"""
        print("Starting database migration...")
        
        try:
            # Create demo organization
            org_id = self.create_demo_organization()
            
            # Migrate contacts
            contact_ids = self.migrate_contacts()
            
            # Create demo employee and links
            self.create_demo_employee_and_links(org_id, contact_ids)
            
            # Migrate core job roles
            self.migrate_core_job_roles()
            
            print("Migration completed successfully!")
            print(f"Created organization ID: {org_id}")
            print(f"Migrated {len(contact_ids)} contacts")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrator = DatabaseMigrator()
    migrator.run_migration()

