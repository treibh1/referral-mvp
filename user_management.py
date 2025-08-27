#!/usr/bin/env python3
"""
User management system for tracking contact ownership and referrals.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

class UserManager:
    def __init__(self, users_file: str = "users.json", contacts_ownership_file: str = "contact_ownership.json"):
        self.users_file = users_file
        self.contacts_ownership_file = contacts_ownership_file
        self.users = self._load_users()
        self.contact_ownership = self._load_contact_ownership()
    
    def _load_users(self) -> Dict:
        """Load users from JSON file."""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_users(self):
        """Save users to JSON file."""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def _load_contact_ownership(self) -> Dict:
        """Load contact ownership data."""
        try:
            with open(self.contacts_ownership_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_contact_ownership(self):
        """Save contact ownership data."""
        with open(self.contacts_ownership_file, 'w') as f:
            json.dump(self.contact_ownership, f, indent=2)
    
    def create_user(self, email: str, name: str) -> str:
        """Create a new user and return user ID."""
        user_id = str(uuid.uuid4())
        self.users[user_id] = {
            'email': email,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'total_contacts': 0,
            'total_referrals': 0
        }
        self._save_users()
        return user_id
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def assign_contacts_to_user(self, user_id: str, contact_ids: List[str], filename: str):
        """Assign contacts to a user."""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        # Update user stats
        self.users[user_id]['total_contacts'] += len(contact_ids)
        
        # Record contact ownership
        for contact_id in contact_ids:
            self.contact_ownership[contact_id] = {
                'user_id': user_id,
                'uploaded_at': datetime.now().isoformat(),
                'filename': filename
            }
        
        self._save_users()
        self._save_contact_ownership()
    
    def get_user_contacts(self, user_id: str) -> List[str]:
        """Get all contact IDs owned by a user."""
        return [contact_id for contact_id, data in self.contact_ownership.items() 
                if data['user_id'] == user_id]
    
    def record_referral_request(self, user_id: str, contact_ids: List[str], job_description: str, company: str):
        """Record when a user's contacts are selected for referral."""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        referral_id = str(uuid.uuid4())
        referral_data = {
            'referral_id': referral_id,
            'user_id': user_id,
            'contact_ids': contact_ids,
            'job_description': job_description,
            'company': company,
            'requested_at': datetime.now().isoformat(),
            'status': 'pending',
            'user_notified': False
        }
        
        # Update user stats
        self.users[user_id]['total_referrals'] += len(contact_ids)
        
        # Save referral request
        referrals_file = "referral_requests.json"
        try:
            with open(referrals_file, 'r') as f:
                referrals = json.load(f)
        except FileNotFoundError:
            referrals = {}
        
        referrals[referral_id] = referral_data
        
        with open(referrals_file, 'w') as f:
            json.dump(referrals, f, indent=2)
        
        self._save_users()
        return referral_id
    
    def get_pending_referrals(self, user_id: str) -> List[Dict]:
        """Get pending referral requests for a user."""
        try:
            with open("referral_requests.json", 'r') as f:
                referrals = json.load(f)
        except FileNotFoundError:
            return []
        
        user_referrals = []
        for referral_id, data in referrals.items():
            if data['user_id'] == user_id and data['status'] == 'pending':
                user_referrals.append(data)
        
        return user_referrals
    
    def mark_referral_notified(self, referral_id: str):
        """Mark a referral request as notified to user."""
        try:
            with open("referral_requests.json", 'r') as f:
                referrals = json.load(f)
        except FileNotFoundError:
            return
        
        if referral_id in referrals:
            referrals[referral_id]['user_notified'] = True
            referrals[referral_id]['notified_at'] = datetime.now().isoformat()
            
            with open("referral_requests.json", 'w') as f:
                json.dump(referrals, f, indent=2)
    
    def update_referral_status(self, referral_id: str, status: str, notes: str = ""):
        """Update referral status (pending, accepted, declined, completed)."""
        try:
            with open("referral_requests.json", 'r') as f:
                referrals = json.load(f)
        except FileNotFoundError:
            return
        
        if referral_id in referrals:
            referrals[referral_id]['status'] = status
            referrals[referral_id]['notes'] = notes
            referrals[referral_id]['updated_at'] = datetime.now().isoformat()
            
            with open("referral_requests.json", 'w') as f:
                json.dump(referrals, f, indent=2)

    def get_user_contacts_for_enrichment(self, user_id: str) -> List[Dict]:
        """Get contacts for enrichment interface with current data."""
        try:
            # Load the enhanced tagged contacts
            contacts_df = pd.read_csv('enhanced_tagged_contacts.csv')
            
            # Get user's contact IDs
            user_contact_ids = self.get_user_contacts(user_id)
            
            # If no contact_id column exists, create one based on index
            if 'contact_id' not in contacts_df.columns:
                contacts_df['contact_id'] = [f"contact_{i}" for i in range(len(contacts_df))]
            
            # Filter contacts belonging to this user
            user_contacts = contacts_df[contacts_df['contact_id'].isin(user_contact_ids)]
            
            # Load existing enrichment data
            enrichment_file = f"enrichment_data_{user_id}.json"
            try:
                with open(enrichment_file, 'r') as f:
                    enrichment_data = json.load(f)
            except FileNotFoundError:
                enrichment_data = {}
            
            # Convert to list of dictionaries and add enrichment data
            contacts_list = []
            for _, row in user_contacts.iterrows():
                contact_id = row['contact_id']
                contact_data = row.to_dict()
                
                # Add enrichment data if available
                if contact_id in enrichment_data:
                    contact_data.update(enrichment_data[contact_id])
                
                # Calculate enrichment score
                enrichment_score = self._calculate_enrichment_score(contact_data)
                contact_data['enrichment_score'] = enrichment_score
                
                contacts_list.append(contact_data)
            
            return contacts_list
            
        except Exception as e:
            print(f"Error loading contacts for enrichment: {e}")
            return []

    def save_contact_enrichment(self, user_id: str, contact_id: str, location: str = "", 
                               seniority: str = "", skills: List[str] = None, 
                               platforms: List[str] = None, is_superstar: bool = False, 
                               notes: str = "") -> bool:
        """Save enrichment data for a contact."""
        try:
            enrichment_file = f"enrichment_data_{user_id}.json"
            
            # Load existing enrichment data
            try:
                with open(enrichment_file, 'r') as f:
                    enrichment_data = json.load(f)
            except FileNotFoundError:
                enrichment_data = {}
            
            # Update enrichment data for this contact
            enrichment_data[contact_id] = {
                'location': location,
                'seniority': seniority,
                'skills': skills or [],
                'platforms': platforms or [],
                'is_superstar': is_superstar,
                'notes': notes,
                'enriched_at': datetime.now().isoformat()
            }
            
            # Save updated enrichment data
            with open(enrichment_file, 'w') as f:
                json.dump(enrichment_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving enrichment data: {e}")
            return False

    def _calculate_enrichment_score(self, contact_data: Dict) -> int:
        """Calculate enrichment score (0-100) based on available data."""
        score = 0
        
        # Base score from existing tagging
        if contact_data.get('role_tag'):
            score += 15
        if contact_data.get('function_tag'):
            score += 15
        if contact_data.get('seniority_tag'):
            score += 10
        if contact_data.get('skills_tag') and contact_data['skills_tag'] != '[]':
            score += 10
        if contact_data.get('platforms_tag') and contact_data['platforms_tag'] != '[]':
            score += 10
        
        # Additional score from manual enrichment
        if contact_data.get('location'):
            score += 10
        if contact_data.get('seniority'):
            score += 10
        if contact_data.get('skills') and len(contact_data['skills']) > 0:
            score += 10
        if contact_data.get('platforms') and len(contact_data['platforms']) > 0:
            score += 10
        
        return min(score, 100)
