#!/usr/bin/env python3
"""
Improved location enricher that validates the person actually works at the specified company.
"""

import requests
import re
import time
import json
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

class LocationMatchType(Enum):
    """Location match types for smart geo system."""
    EXACT = "exact"
    NEARBY = "nearby"
    REMOTE = "remote"
    UNKNOWN = "unknown"

@dataclass
class LocationInfo:
    """Location information data structure."""
    location_raw: str
    city: Optional[str]
    country: Optional[str]
    confidence: float
    source: str
    search_url: Optional[str]
    result_index: Optional[int]

class ImprovedLocationEnricher:
    """
    Improved Brave Search API implementation with company validation.
    """
    
    def __init__(self, api_key: str = None):
        """Initialize the improved enricher."""
        self.api_key = api_key or "BSA__pkv8YSpwoJZZp-2FCrwsZZjj4N"
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        
        # Profile indicators that suggest this is a LinkedIn profile
        self.profile_indicators = [
            'linkedin.com/in/', 'professional profile', 'connections on linkedin',
            'view profile', '500+ connections', '1,000+ connections'
        ]
        
        # Generic phrases that suggest this is NOT a specific profile
        self.generic_phrases = [
            'linkedin.com/company/', 'company page', 'followers on linkedin',
            'billion members', 'professional network', 'manage your professional'
        ]
    
    def brave_search(self, query: str, max_results: int = 10) -> Optional[Dict]:
        """Perform a Brave Search API request."""
        try:
            params = {
                'q': query,
                'country': 'US',
                'count': str(max_results),
                'search_lang': 'en',
                'ui_lang': 'en-US'
            }
            
            headers = {
                'Accept': 'application/json',
                'X-Subscription-Token': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Brave API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error in Brave search: {e}")
            return None
    
    def validate_person_match(self, full_name: str, company: str, title: str, description: str) -> bool:
        """
        Validate that a search result is actually for the right person.
        
        Args:
            full_name: Expected full name
            company: Expected company
            title: Search result title
            description: Search result description
            
        Returns:
            True if this appears to be the right person
        """
        # Normalize text for comparison
        title_lower = title.lower()
        description_lower = description.lower()
        full_name_lower = full_name.lower()
        company_lower = company.lower()
        
        # Check if the name appears in the result
        name_parts = full_name_lower.split()
        if len(name_parts) >= 2:
            first_name, last_name = name_parts[0], name_parts[1]
            
            # Both first and last name should appear
            if first_name not in title_lower and first_name not in description_lower:
                return False
            if last_name not in title_lower and last_name not in description_lower:
                return False
        
        # Check if company appears in the result
        company_found = False
        if company_lower in title_lower or company_lower in description_lower:
            company_found = True
        
        # If company is not found, this is likely the wrong person
        if not company_found:
            return False
        
        # Check for profile indicators
        has_profile_indicators = any(indicator in description_lower for indicator in self.profile_indicators)
        
        # Check for generic phrases (should be minimal)
        has_generic_phrases = any(phrase in description_lower for phrase in self.generic_phrases)
        
        # Prefer results with profile indicators and minimal generic phrases
        if has_profile_indicators and not has_generic_phrases:
            return True
        
        # If no profile indicators but company is found, still consider it
        if company_found:
            return True
        
        return False
    
    def extract_location_from_description(self, description: str) -> Optional[str]:
        """Extract location from search result description."""
        if not description:
            return None
        
        # Clean the description
        clean_description = re.sub(r'<[^>]+>', '', description)
        
        # Look for explicit "Location:" pattern first
        location_pattern = r'Location:\s*([^·\n]+?)(?:\s*[·—\-•|*]|\s*on\s+LinkedIn|\s*500\+|\s*connections|\s*View|\s*professional|\s*community|\s*[0-9]+\+|\s*View\s+profile|\s*[0-9]+\s+connections)'
        match = re.search(location_pattern, clean_description, re.IGNORECASE)
        
        if match:
            location = match.group(1).strip()
            return location
        
        # Also look for location patterns like "City, State, Country · Job Title"
        location_with_bullet_pattern = r'([A-Z][a-zA-Z\s,]+?)\s*·\s*(?:[A-Z][a-zA-Z\s]+(?:\s*·\s*[A-Z][a-zA-Z\s]+)?)'
        match = re.search(location_with_bullet_pattern, clean_description)
        
        if match:
            location = match.group(1).strip()
            # Basic check: if it contains commas, it's likely a location (City, State, Country)
            if ',' in location:
                return location
        
        return None
    
    def locate_contact(self, full_name: str, company: str) -> Optional[Dict]:
        """Locate a contact using Brave Search API with improved validation."""
        try:
            # Use the exact search format from the playground that worked
            search_query = f"{full_name} - {company} - LinkedIn Profile"
            
            # Get search results
            response = self.brave_search(search_query, max_results=10)
            
            if not response:
                return None
            
            search_results = response.get('web', {}).get('results', [])
            
            if not search_results:
                return None
            
            # First pass: Look for results with explicit "Location:" patterns AND company validation
            for i, result in enumerate(search_results):
                title = result.get('title', '')
                description = result.get('description', '')
                
                if not description:
                    continue
                
                # Validate this is the right person
                if not self.validate_person_match(full_name, company, title, description):
                    continue
                
                # Check for explicit "Location:" pattern
                clean_description = re.sub(r'<[^>]+>', '', description)
                location_pattern = r'Location:\s*([^·\n]+?)(?:\s*[·—\-•|*]|\s*on\s+LinkedIn|\s*500\+|\s*connections|\s*View|\s*professional|\s*community|\s*[0-9]+\+|\s*View\s+profile|\s*[0-9]+\s+connections)'
                match = re.search(location_pattern, clean_description, re.IGNORECASE)
                
                if match:
                    location = match.group(1).strip()
                    return {
                        'location': location,
                        'confidence': 0.9,  # Higher confidence for validated results
                        'source': 'Brave Search API (Google) - Validated',
                        'url': f"https://www.google.com/search?q={search_query.replace(' ', '+')}",
                        'result_index': i
                    }
            
            # Second pass: Look for bullet patterns if no explicit location found
            for i, result in enumerate(search_results):
                title = result.get('title', '')
                description = result.get('description', '')
                
                if not description:
                    continue
                
                # Validate this is the right person
                if not self.validate_person_match(full_name, company, title, description):
                    continue
                
                # Extract location from description (bullet patterns)
                location = self.extract_location_from_description(description)
                
                if location:
                    return {
                        'location': location,
                        'confidence': 0.8,
                        'source': 'Brave Search API (Google) - Validated',
                        'url': f"https://www.google.com/search?q={search_query.replace(' ', '+')}",
                        'result_index': i
                    }
            
            return None
            
        except Exception as e:
            print(f"❌ Error locating contact {full_name}: {e}")
            return None

def test_improved_enricher():
    """Test the improved enricher with Ben Orr."""
    print("🧪 Testing Improved Location Enricher")
    print("=" * 50)
    
    enricher = ImprovedLocationEnricher()
    
    # Test Ben Orr
    full_name = "Ben Orr"
    company = "Synthesia"
    
    print(f"Testing: {full_name} - {company}")
    
    location_info = enricher.locate_contact(full_name, company)
    
    if location_info:
        print(f"✅ Location Found: {location_info['location']}")
        print(f"   Confidence: {location_info['confidence']}")
        print(f"   Source: {location_info['source']}")
        print(f"   Result Index: {location_info['result_index']}")
    else:
        print("❌ No location found")

if __name__ == "__main__":
    test_improved_enricher()

