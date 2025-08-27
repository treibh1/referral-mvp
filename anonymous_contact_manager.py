#!/usr/bin/env python3
"""
Anonymous Contact Manager for Reddit Mode
Handles pseudonym generation and contact anonymization for bias-free evaluation.
"""

import random
import string
import hashlib
import json
from typing import Dict, List, Optional
from datetime import datetime

class AnonymousContactManager:
    def __init__(self):
        self.pseudonym_cache = {}  # In production, this would be in Redis/database
        
    def generate_pseudonym(self, contact_data: Dict) -> str:
        """
        Generate a unique, memorable pseudonym based on contact data.
        
        Args:
            contact_data: Dictionary containing contact information
            
        Returns:
            str: Generated pseudonym (e.g., "Senior_Engineer_ABC123")
        """
        # Extract role and seniority
        role = contact_data.get('role_tag', 'Professional')
        seniority = contact_data.get('seniority_tag', 'Mid')
        
        # Clean and format role name
        role_clean = role.replace(' ', '_').replace('-', '_').title()
        seniority_clean = seniority.replace(' ', '_').title()
        
        # Generate random suffix (6 characters)
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Create pseudonym
        pseudonym = f"{seniority_clean}_{role_clean}_{suffix}"
        
        return pseudonym
    
    def generate_anonymous_id(self, contact_id: str) -> str:
        """
        Generate a unique anonymous ID for tracking.
        
        Args:
            contact_id: Original contact UUID
            
        Returns:
            str: Anonymous ID (e.g., "RedditUser_ABC123")
        """
        # Create hash of contact ID for consistency
        hash_object = hashlib.md5(contact_id.encode())
        hash_hex = hash_object.hexdigest()[:6].upper()
        
        return f"RedditUser_{hash_hex}"
    
    def anonymize_contact(self, contact_data: Dict, settings: Dict) -> Dict:
        """
        Anonymize contact data based on privacy settings.
        
        Args:
            contact_data: Original contact data
            settings: Privacy settings dictionary
            
        Returns:
            Dict: Anonymized contact data
        """
        anonymized = contact_data.copy()
        
        # Hide names if enabled
        if settings.get('hide_names', True):
            anonymized['first_name'] = 'Anonymous'
            anonymized['last_name'] = ''
            anonymized['full_name'] = 'Anonymous User'
        
        # Hide email if enabled
        if settings.get('hide_emails', True):
            anonymized['email'] = 'hidden@example.com'
        
        # Hide LinkedIn URL if enabled
        if settings.get('hide_linkedin_urls', True):
            anonymized['linkedin_url'] = ''
        
        # Hide company name if enabled
        if settings.get('hide_companies', False):
            anonymized['company'] = '[Company Hidden]'
        
        # Generate pseudonym if enabled
        if settings.get('generate_pseudonyms', True):
            pseudonym = self.generate_pseudonym(contact_data)
            anonymized['anonymous_name'] = pseudonym
            anonymized['display_name'] = pseudonym
        
        # Generate anonymous ID
        if 'id' in contact_data:
            anonymized['anonymous_id'] = self.generate_anonymous_id(contact_data['id'])
        
        # Mark as anonymous
        anonymized['is_anonymous'] = True
        
        return anonymized
    
    def anonymize_contact_list(self, contacts: List[Dict], settings: Dict) -> List[Dict]:
        """
        Anonymize a list of contacts.
        
        Args:
            contacts: List of contact dictionaries
            settings: Privacy settings dictionary
            
        Returns:
            List[Dict]: List of anonymized contacts
        """
        anonymized_contacts = []
        
        for contact in contacts:
            anonymized_contact = self.anonymize_contact(contact, settings)
            anonymized_contacts.append(anonymized_contact)
        
        return anonymized_contacts
    
    def get_default_settings(self) -> Dict:
        """
        Get default anonymous mode settings.
        
        Returns:
            Dict: Default privacy settings
        """
        return {
            'hide_names': True,
            'hide_companies': False,
            'hide_emails': True,
            'hide_linkedin_urls': True,
            'generate_pseudonyms': True,
            'show_company_industry': True,
            'show_position_level': True,
            'show_skills': True,
            'show_platforms': True
        }
    
    def validate_settings(self, settings: Dict) -> bool:
        """
        Validate anonymous mode settings.
        
        Args:
            settings: Settings dictionary to validate
            
        Returns:
            bool: True if settings are valid
        """
        required_keys = ['hide_names', 'hide_emails', 'generate_pseudonyms']
        
        for key in required_keys:
            if key not in settings:
                return False
        
        # Ensure at least some identifying information is preserved
        if settings.get('hide_names', True) and settings.get('hide_companies', False):
            if not settings.get('show_company_industry', True):
                return False
        
        return True
    
    def create_audit_log(self, action: str, user_id: str, contact_ids: List[str], 
                        settings: Dict) -> Dict:
        """
        Create audit log entry for anonymous mode actions.
        
        Args:
            action: Action performed (e.g., 'anonymize', 'reveal')
            user_id: ID of user performing action
            contact_ids: List of contact IDs affected
            settings: Settings used for anonymization
            
        Returns:
            Dict: Audit log entry
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'user_id': user_id,
            'contact_count': len(contact_ids),
            'settings_used': settings,
            'session_id': self._generate_session_id()
        }
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID for audit logging."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"anon_session_{timestamp}_{random_suffix}"

class RedditModeJobMatcher:
    """
    Enhanced job matcher that supports anonymous candidate display.
    """
    
    def __init__(self, anonymous_manager: AnonymousContactManager):
        self.anonymous_manager = anonymous_manager
    
    def find_anonymous_candidates(self, job_description: str, contacts: List[Dict], 
                                settings: Dict, top_n: int = 10) -> Dict:
        """
        Find top candidates and return them in anonymous format.
        
        Args:
            job_description: Job description text
            contacts: List of contact dictionaries
            settings: Anonymous mode settings
            top_n: Number of top candidates to return
            
        Returns:
            Dict: Anonymous candidates with metadata
        """
        # This would integrate with your existing matching logic
        # For now, we'll simulate the matching process
        
        # Simulate matching scores
        scored_contacts = []
        for contact in contacts:
            # Simulate match score (in real implementation, use your scoring algorithm)
            score = random.uniform(60, 95)
            contact_with_score = contact.copy()
            contact_with_score['match_score'] = round(score, 1)
            scored_contacts.append(contact_with_score)
        
        # Sort by score and get top candidates
        top_candidates = sorted(scored_contacts, key=lambda x: x['match_score'], reverse=True)[:top_n]
        
        # Anonymize top candidates
        anonymous_candidates = self.anonymous_manager.anonymize_contact_list(top_candidates, settings)
        
        return {
            'candidates': anonymous_candidates,
            'total_candidates': len(contacts),
            'anonymous_mode': True,
            'settings_used': settings,
            'generated_at': datetime.now().isoformat()
        }
    
    def reveal_candidate_identities(self, anonymous_candidates: List[Dict], 
                                  original_contacts: List[Dict]) -> List[Dict]:
        """
        Reveal the real identities of anonymous candidates.
        
        Args:
            anonymous_candidates: List of anonymous candidate data
            original_contacts: List of original contact data
            
        Returns:
            List[Dict]: Candidates with revealed identities
        """
        revealed_candidates = []
        
        # Create mapping of anonymous IDs to original contacts
        contact_map = {contact.get('id'): contact for contact in original_contacts}
        
        for anonymous_candidate in anonymous_candidates:
            # Find original contact (this would use your actual ID mapping logic)
            original_contact = contact_map.get(anonymous_candidate.get('id'))
            
            if original_contact:
                # Merge anonymous data with original data
                revealed_candidate = original_contact.copy()
                revealed_candidate['match_score'] = anonymous_candidate.get('match_score', 0)
                revealed_candidate['was_anonymous'] = True
                revealed_candidates.append(revealed_candidate)
        
        return revealed_candidates

# Example usage
if __name__ == "__main__":
    # Initialize managers
    anonymous_manager = AnonymousContactManager()
    job_matcher = RedditModeJobMatcher(anonymous_manager)
    
    # Sample contact data
    sample_contacts = [
        {
            'id': '123e4567-e89b-12d3-a456-426614174000',
            'first_name': 'John',
            'last_name': 'Smith',
            'email': 'john.smith@example.com',
            'company': 'Tech Corp',
            'position': 'Senior Software Engineer',
            'role_tag': 'software engineer',
            'seniority_tag': 'senior',
            'skills_tag': ['python', 'react', 'aws'],
            'platforms_tag': ['github', 'jira']
        },
        {
            'id': '987fcdeb-51a2-43d1-b789-123456789abc',
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'email': 'sarah.johnson@example.com',
            'company': 'Sales Inc',
            'position': 'Account Executive',
            'role_tag': 'account executive',
            'seniority_tag': 'mid',
            'skills_tag': ['sales', 'negotiation', 'crm'],
            'platforms_tag': ['salesforce', 'hubspot']
        }
    ]
    
    # Default settings
    settings = anonymous_manager.get_default_settings()
    
    # Find anonymous candidates
    result = job_matcher.find_anonymous_candidates(
        "We're hiring a Senior Software Engineer...",
        sample_contacts,
        settings,
        top_n=2
    )
    
    print("🎭 Anonymous Candidates:")
    for candidate in result['candidates']:
        print(f"• {candidate['anonymous_name']}")
        print(f"  Position: {candidate['position']}")
        print(f"  Company: {candidate['company']}")
        print(f"  Skills: {', '.join(candidate['skills_tag'])}")
        print(f"  Match Score: {candidate['match_score']}")
        print()
    
    # Reveal identities
    revealed = job_matcher.reveal_candidate_identities(
        result['candidates'],
        sample_contacts
    )
    
    print("🔓 Revealed Identities:")
    for candidate in revealed:
        print(f"• {candidate['first_name']} {candidate['last_name']}")
        print(f"  Email: {candidate['email']}")
        print(f"  Match Score: {candidate['match_score']}")
        print()



