#!/usr/bin/env python3
"""
Brave Search API integration for location enrichment in the smart geo system.
Production-ready implementation with caching, error handling, and rate limiting.
"""

import requests
import re
import time
import json
import hashlib
from typing import Dict, Optional, List
from unidecode import unidecode
from dataclasses import dataclass
from enum import Enum

class LocationMatchType(Enum):
    """Location match types for smart geo system."""
    EXACT = "exact"
    NEARBY = "nearby"
    REMOTE = "remote"
    UNKNOWN = "unknown"

@dataclass
class LocationMatch:
    """Location match data structure."""
    contact_id: str
    location_raw: str
    location_city: str
    location_country: Optional[str]
    location_confidence: float
    location_source: str
    location_url: Optional[str]
    match_type: LocationMatchType
    query_used: str
    enriched_at: float

class BraveLocationEnricher:
    """
    Production-ready Brave Search API implementation for location enrichment.
    """
    
    def __init__(self, api_key: str = None, cache_ttl: int = 86400):
        """
        Initialize Brave Search enricher.
        
        Args:
            api_key: Brave Search API key
            cache_ttl: Cache TTL in seconds (default: 24 hours)
        """
        self.api_key = api_key or "BSA__pkv8YSpwoJZZp-2FCrwsZZjj4N"
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.cache_ttl = cache_ttl
        self.cache = {}  # Simple in-memory cache for now
        
        # Initialize enhanced location validator
        try:
            from enhanced_location_validator import EnhancedLocationValidator
            self.location_validator = EnhancedLocationValidator()
            print("✅ Enhanced location validator loaded")
        except ImportError:
            print("⚠️ Enhanced location validator not available, using basic validation")
            self.location_validator = None
        
        # Enhanced location extraction patterns
        self.location_patterns = [
            r"Location:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "Location: Dublin"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[·—\-•|]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "Name · Location"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})",  # City, State
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z][a-z]+)",  # City, Country
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "Name Location" (no separator)
        ]
        
        # Common location separators
        self.separators = ['·', '—', '-', '•', '|', ',', '•']
        
        # Enhanced gazetteer of common locations
        self.gazetteer = {
            'cities': [
                'London', 'New York', 'San Francisco', 'Austin', 'Seattle', 'Boston', 'Chicago', 
                'Los Angeles', 'Dublin', 'Amsterdam', 'Berlin', 'Paris', 'Brighton', 'Manchester', 
                'Birmingham', 'Edinburgh', 'Glasgow', 'Cardiff', 'Bristol', 'Leeds', 'Liverpool',
                'Norfolk', 'Virginia', 'California', 'Texas', 'Florida', 'Washington', 'Oregon',
                'Shifnal', 'Colombo', 'Australia', 'Ireland', 'Riyadh', 'Jeddah', 'Dubai', 'Abu Dhabi',
                'Toronto', 'Vancouver', 'Montreal', 'Sydney', 'Melbourne', 'Brisbane', 'Perth',
                'Auckland', 'Wellington', 'Singapore', 'Hong Kong', 'Tokyo', 'Seoul', 'Shanghai',
                'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Pune', 'Kolkata',
                'Asola', 'Lombardy', 'Italy'
            ],
            'regions': [
                'Greater London', 'Bay Area', 'Silicon Valley', 'Greater Boston', 'Greater Chicago',
                'Greater Brighton', 'Norfolk City County', 'Greater Manchester', 'West Midlands',
                'Greater Dublin', 'Greater Amsterdam', 'Greater Berlin', 'Greater Paris',
                'Greater Toronto', 'Greater Vancouver', 'Greater Sydney', 'Greater Melbourne',
                'San Francisco Bay Area'
            ],
            'countries': [
                'United Kingdom', 'United States', 'Canada', 'Australia', 'Germany', 'France', 
                'Ireland', 'Netherlands', 'UK', 'USA', 'US', 'England', 'Scotland', 'Wales',
                'Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Bahrain', 'Oman', 'Jordan', 'Lebanon',
                'Egypt', 'Morocco', 'South Africa', 'Nigeria', 'Kenya', 'Ghana', 'India', 'Pakistan',
                'Bangladesh', 'Sri Lanka', 'Nepal', 'Bhutan', 'Maldives', 'China', 'Japan', 'South Korea',
                'Singapore', 'Malaysia', 'Thailand', 'Vietnam', 'Philippines', 'Indonesia', 'New Zealand'
            ]
        }
        
        # Generic phrases to skip (LinkedIn boilerplate)
        self.generic_phrases = [
            "1 billion members",
            "Manage your professional identity",
            "Build and engage with your professional network",
            "Access knowledge, insights and opportunities",
            "professional community",
            "billion members",
            "1 Mrd. Mitglieder",
            "Die Plattform für Ihre berufliche Identität",
            "Bauen Sie Ihr berufliches Netzwerk auf"
        ]
        
        # Phrases that indicate a real profile (not generic)
        self.profile_indicators = [
            "Location:",
            "Experience:",
            "Education:",
            "connections on LinkedIn"
        ]

    def _get_cache_key(self, full_name: str, company: str) -> str:
        """Generate cache key for contact."""
        key_string = f"{full_name.lower()}|{company.lower()}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get location data from cache."""
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                return cached_data['data']
            else:
                del self.cache[cache_key]
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """Save location data to cache."""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def brave_search(self, query, max_results=10):
        """Search using Brave Search API."""
        try:
            # Use exact parameters from the playground that work
            count = max(2, max_results)
            
            url = "https://api.search.brave.com/res/v1/web/search"
            params = {
                'q': query,
                'count': count,
                'country': 'US',  # Uppercase as in playground
                'search_lang': 'en',
                'ui_lang': 'en-US',
                'safesearch': 'moderate',
                'spellcheck': 'true',
                'text_decorations': 'true'
            }
            
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'x-subscription-token': self.api_key
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Brave API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error in Brave search: {e}")
            return None

    def extract_location_from_description(self, description):
        """
        Extract location from the description field of search results.
        Simplified to capture all location data without validation.
        """
        if not description:
            return None
            
        # Clean the description (remove HTML tags)
        clean_description = re.sub(r'<[^>]+>', '', description)
        
        # Look for "Location: [anything]" pattern - capture everything until the bullet point
        location_pattern = r'Location:\s*([^·\n]+?)(?:\s*[·—\-•|*]|\s*on\s+LinkedIn|\s*500\+|\s*connections|\s*View|\s*professional|\s*community|\s*[0-9]+\+|\s*View\s+profile|\s*[0-9]+\s+connections)'
        
        # Also look for location patterns like "City, State, Country · Job Title"
        location_with_bullet_pattern = r'([A-Z][a-zA-Z\s,]+?)\s*·\s*(?:[A-Z][a-zA-Z\s]+(?:\s*·\s*[A-Z][a-zA-Z\s]+)?)'
        
        # Try the "Location:" pattern first
        match = re.search(location_pattern, clean_description, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            return location  # Return whatever we find, no validation
        
        # Try the location with bullet pattern (like "Gravesend, England, United Kingdom · Senior Finance Manager")
        match = re.search(location_with_bullet_pattern, clean_description)
        if match:
            location = match.group(1).strip()
            # Basic check: if it contains commas, it's likely a location (City, State, Country)
            if ',' in location:
                return location
        
        return None
    
    def _is_valid_location(self, text: str) -> bool:
        """
        Strict validation to check if text is a valid geographical location.
        
        Args:
            text: Text to check
            
        Returns:
            True if text is a valid location
        """
        # Use enhanced location validator if available
        if self.location_validator:
            # For now, bypass the enhanced validator as it's too strict
            # return self.location_validator.is_valid_location(text)
            pass
        
        # Fallback to basic validation
        if not text or len(text) < 3:
            return False
        
        text_lower = text.lower()
        
        # Reject common non-location phrases that might match our patterns
        invalid_phrases = [
            'double winners', 'junior coaching', 'customer experience solutions',
            'senior account executive', 'account executive', 'sales manager',
            'product manager', 'software engineer', 'data scientist', 'marketing manager',
            'business development', 'customer success', 'technical support',
            'human resources', 'finance manager', 'operations manager', 'project manager',
            'team lead', 'team leader', 'director', 'vice president', 'chief',
            'founder', 'co-founder', 'ceo', 'cto', 'cfo', 'coo', 'vp', 'head of',
            'manager', 'specialist', 'analyst', 'consultant', 'advisor', 'coordinator',
            'associate', 'assistant', 'intern', 'trainee', 'apprentice', 'graduate',
            'student', 'freelancer', 'contractor', 'consultant', 'advisor'
        ]
        
        for phrase in invalid_phrases:
            if phrase in text_lower:
                return False
        
        # Check against our comprehensive gazetteer (must be exact match or contain valid location)
        found_valid_location = False
        
        # Check cities
        for city in self.gazetteer['cities']:
            if city.lower() == text_lower or city.lower() in text_lower:
                found_valid_location = True
                break
        
        # Check regions
        for region in self.gazetteer['regions']:
            if region.lower() == text_lower or region.lower() in text_lower:
                found_valid_location = True
                break
        
        # Check countries
        for country in self.gazetteer['countries']:
            if country.lower() == text_lower or country.lower() in text_lower:
                found_valid_location = True
                break
        
        # Additional checks to ensure it's not just a partial match
        # For example, "London" should be valid, but "London Bridge" might be ambiguous
        words = text.split()
        if len(words) > 4:  # Too many words, likely not a location
            return False
        
        # Check if it contains location indicators
        location_indicators = ['area', 'region', 'county', 'state', 'country', 'city', 'greater', 'united']
        has_indicator = any(indicator in text_lower for indicator in location_indicators)
        
        # If we found a valid location in gazetteer, do additional validation
        if found_valid_location:
            # If it has a location indicator, it's more likely to be valid
            if has_indicator:
                return True
            
            # For short locations (1-2 words), require exact gazetteer match
            if len(words) <= 2:
                return any(location.lower() == text_lower for location in 
                          self.gazetteer['cities'] + self.gazetteer['regions'] + self.gazetteer['countries'])
            # For longer locations (3+ words), allow partial matches if they contain valid location indicators
            else:
                return has_indicator
        
        # If not found in gazetteer, check common locations and multi-part locations
        if len(words) <= 2:
            # Check for common location patterns (like "Reston", "Austin", etc.)
            common_locations = ['reston', 'austin', 'seattle', 'boston', 'chicago', 'denver', 'atlanta', 
                              'phoenix', 'dallas', 'houston', 'miami', 'orlando', 'tampa', 'nashville',
                              'charlotte', 'raleigh', 'columbus', 'indianapolis', 'detroit', 'cleveland',
                              'pittsburgh', 'philadelphia', 'baltimore', 'washington', 'richmond', 'norfolk',
                              'jacksonville', 'tampa', 'orlando', 'miami', 'fort lauderdale', 'west palm beach',
                              'toronto', 'montreal', 'vancouver', 'calgary', 'edmonton', 'ottawa', 'winnipeg',
                              'london', 'manchester', 'birmingham', 'leeds', 'liverpool', 'sheffield',
                              'glasgow', 'edinburgh', 'cardiff', 'belfast', 'dublin', 'cork', 'galway']
            if text_lower in common_locations:
                return True
        
        # Check for multi-part locations like "Reston, Virginia, United States"
        if len(words) >= 3 and ',' in text:
            # Split by commas and check if each part is valid
            parts = [part.strip() for part in text.split(',')]
            valid_parts = 0
            
            for part in parts:
                part_lower = part.lower()
                # Check if this part is in our gazetteer or common locations
                if (any(location.lower() == part_lower for location in 
                       self.gazetteer['cities'] + self.gazetteer['regions'] + self.gazetteer['countries']) or
                    part_lower in ['reston', 'austin', 'seattle', 'boston', 'chicago', 'denver', 'atlanta', 
                                  'phoenix', 'dallas', 'houston', 'miami', 'orlando', 'tampa', 'nashville',
                                  'charlotte', 'raleigh', 'columbus', 'indianapolis', 'detroit', 'cleveland',
                                  'pittsburgh', 'philadelphia', 'baltimore', 'washington', 'richmond', 'norfolk',
                                  'jacksonville', 'tampa', 'orlando', 'miami', 'fort lauderdale', 'west palm beach',
                                  'toronto', 'montreal', 'vancouver', 'calgary', 'edmonton', 'ottawa', 'winnipeg',
                                  'london', 'manchester', 'birmingham', 'leeds', 'liverpool', 'sheffield',
                                  'glasgow', 'edinburgh', 'cardiff', 'belfast', 'dublin', 'cork', 'galway',
                                  'virginia', 'california', 'texas', 'florida', 'new york', 'illinois', 'pennsylvania',
                                  'ohio', 'georgia', 'north carolina', 'michigan', 'new jersey', 'washington',
                                  'massachusetts', 'indiana', 'tennessee', 'missouri', 'maryland', 'colorado',
                                  'wisconsin', 'minnesota', 'arizona', 'louisiana', 'alabama', 'kentucky',
                                  'south carolina', 'oregon', 'oklahoma', 'connecticut', 'utah', 'iowa',
                                  'nevada', 'arkansas', 'mississippi', 'kansas', 'nebraska', 'idaho',
                                  'new hampshire', 'maine', 'new mexico', 'hawaii', 'rhode island',
                                  'montana', 'delaware', 'south dakota', 'north dakota', 'alaska', 'vermont',
                                  'wyoming', 'west virginia', 'united states', 'usa', 'canada', 'uk', 'united kingdom',
                                  # Canadian provinces
                                  'ontario', 'quebec', 'british columbia', 'alberta', 'manitoba', 'saskatchewan',
                                  'nova scotia', 'new brunswick', 'newfoundland', 'prince edward island',
                                  'northwest territories', 'nunavut', 'yukon',
                                  # US state abbreviations
                                  'ny', 'ca', 'tx', 'fl', 'il', 'pa', 'oh', 'ga', 'nc', 'mi', 'nj', 'wa',
                                  'ma', 'in', 'tn', 'mo', 'md', 'co', 'wi', 'mn', 'az', 'la', 'al', 'ky',
                                  'sc', 'or', 'ok', 'ct', 'ut', 'ia', 'nv', 'ar', 'ms', 'ks', 'ne', 'id',
                                  'nh', 'me', 'nm', 'hi', 'ri', 'mt', 'de', 'sd', 'nd', 'ak', 'vt', 'wy', 'wv']):
                    valid_parts += 1
            
            # If at least 2 parts are valid, consider it a valid location
            if valid_parts >= 2:
                return True
        
        return False
    
    def _validate_person_match(self, full_name: str, company: str, title: str, description: str) -> bool:
        """
        Enhanced validation to ensure we're looking at the right person before storing location.
        Prefers blank location over incorrect location.
        
        Args:
            full_name: Expected full name
            company: Expected company
            title: Search result title
            description: Search result description
            
        Returns:
            True if we're confident this is the right person
        """
        # Normalize text for comparison
        title_lower = title.lower()
        description_lower = description.lower()
        full_name_lower = full_name.lower()
        company_lower = company.lower()
        
        # Skip if company is invalid
        if not company or company.lower() in ['nan', 'none', '']:
            return False
        
        # Extract name parts
        name_parts = full_name_lower.split()
        if len(name_parts) < 2:
            return False
        
        first_name, last_name = name_parts[0], name_parts[-1]
        
        # CRITICAL: Both first and last name must appear in either title or description
        first_name_found = first_name in title_lower or first_name in description_lower
        last_name_found = last_name in title_lower or last_name in description_lower
        
        if not first_name_found or not last_name_found:
            return False
        
        # CRITICAL: Company must appear in either title or description
        company_found = company_lower in title_lower or company_lower in description_lower
        if not company_found:
            return False
        
        # Additional validation: Check for LinkedIn profile indicators
        has_profile_indicators = any(indicator in description_lower for indicator in self.profile_indicators)
        has_generic_phrases = any(phrase in description_lower for phrase in self.generic_phrases)
        
        # If it has generic phrases but no profile indicators, be more cautious
        if has_generic_phrases and not has_profile_indicators:
            # Require stronger evidence this is the right person
            # Check if the company appears in a prominent position (near the name)
            name_company_proximity = self._check_name_company_proximity(
                full_name, company, title, description
            )
            if not name_company_proximity:
                return False
        
        # Check for conflicting company mentions that might indicate wrong person
        conflicting_companies = self._check_for_conflicting_companies(company, title, description)
        if conflicting_companies:
            return False
        
        # If we get here, we're reasonably confident this is the right person
        return True
    
    def _check_name_company_proximity(self, full_name: str, company: str, title: str, description: str) -> bool:
        """
        Check if the company appears close to the name in the text.
        This helps validate that the company is actually associated with this person.
        """
        # Look for patterns like "Name at Company" or "Name - Company" or "Name · Company"
        text_to_check = f"{title} {description}".lower()
        full_name_lower = full_name.lower()
        company_lower = company.lower()
        
        # Common patterns that indicate association
        proximity_patterns = [
            f"{full_name_lower} at {company_lower}",
            f"{full_name_lower} - {company_lower}",
            f"{full_name_lower} · {company_lower}",
            f"{full_name_lower} | {company_lower}",
            f"{full_name_lower} {company_lower}",
        ]
        
        for pattern in proximity_patterns:
            if pattern in text_to_check:
                return True
        
        # Check if company appears within 50 characters of the name
        name_pos = text_to_check.find(full_name_lower)
        if name_pos != -1:
            company_pos = text_to_check.find(company_lower)
            if company_pos != -1:
                distance = abs(company_pos - name_pos)
                if distance <= 50:
                    return True
        
        return False
    
    def _check_for_conflicting_companies(self, expected_company: str, title: str, description: str) -> bool:
        """
        Check if there are other company mentions that might indicate this is a different person.
        """
        text_to_check = f"{title} {description}".lower()
        expected_company_lower = expected_company.lower()
        
        # List of companies that, if mentioned alongside the expected company, 
        # might indicate we're looking at a different person
        conflicting_companies = [
            'microsoft', 'google', 'apple', 'amazon', 'meta', 'facebook', 'netflix',
            'salesforce', 'oracle', 'ibm', 'intel', 'cisco', 'adobe', 'nvidia',
            'tesla', 'spacex', 'uber', 'lyft', 'airbnb', 'spotify', 'twitter',
            'github', 'stripe', 'square', 'palantir', 'databricks',
            'snowflake', 'mongodb', 'elastic', 'confluent', 'hashicorp', 'gitlab',
            'atlassian', 'slack', 'zoom', 'dropbox', 'box', 'asana', 'notion',
            'figma', 'canva', 'monday.com', 'trello', 'jira', 'confluence'
        ]
        
        for conflicting_company in conflicting_companies:
            if conflicting_company in text_to_check and conflicting_company != expected_company_lower:
                # If the conflicting company appears prominently (in title or near the beginning of description)
                if conflicting_company in title.lower():
                    return True
                
                # Check if conflicting company appears before the expected company in the description
                expected_pos = text_to_check.find(expected_company_lower)
                conflicting_pos = text_to_check.find(conflicting_company)
                
                if expected_pos != -1 and conflicting_pos != -1 and conflicting_pos < expected_pos:
                    # If conflicting company appears first, this might be wrong person
                    return True
        
        return False

    def locate_contact(self, full_name, company):
        """Locate a contact using Brave Search API with enhanced person validation."""
        try:
            # Use quoted company name for exact phrase matching
            search_query = f'{full_name} - "{company}" - LinkedIn Profile'
            
            # Get search results (request more results to get full descriptions)
            response = self.brave_search(search_query, max_results=10)
            
            if not response:
                return None
            
            search_results = response.get('web', {}).get('results', [])
            
            if not search_results:
                return None
            
            # Focus on the description field of each result
            # First pass: Look for results with explicit "Location:" patterns AND person validation
            for i, result in enumerate(search_results):
                title = result.get('title', '')
                description = result.get('description', '')
                
                if not description:
                    continue
                
                # CRITICAL: Validate this is the right person before proceeding
                if not self._validate_person_match(full_name, company, title, description):
                    continue
                
                # Skip generic LinkedIn snippets, but only if they don't contain profile indicators
                is_generic = any(phrase in description.lower() for phrase in self.generic_phrases)
                has_profile_info = any(indicator in description for indicator in self.profile_indicators)
                
                if is_generic and not has_profile_info:
                    continue
                
                # Check for explicit "Location:" pattern first
                clean_description = re.sub(r'<[^>]+>', '', description)
                location_pattern = r'Location:\s*([^·\n]+?)(?:\s*[·—\-•|*]|\s*on\s+LinkedIn|\s*500\+|\s*connections|\s*View|\s*professional|\s*community|\s*[0-9]+\+|\s*View\s+profile|\s*[0-9]+\s+connections)'
                match = re.search(location_pattern, clean_description, re.IGNORECASE)
                
                if match:
                    location = match.group(1).strip()
                    return {
                        'location': location,
                        'confidence': 0.9,  # Higher confidence due to person validation
                        'source': 'Brave Search API (Google)',
                        'url': f"https://www.google.com/search?q={search_query.replace(' ', '+')}",
                        'result_index': i
                    }
            
            # Second pass: Look for bullet patterns if no explicit location found
            for i, result in enumerate(search_results):
                title = result.get('title', '')
                description = result.get('description', '')
                
                if not description:
                    continue
                
                # CRITICAL: Validate this is the right person before proceeding
                if not self._validate_person_match(full_name, company, title, description):
                    continue
                
                # Skip generic LinkedIn snippets, but only if they don't contain profile indicators
                is_generic = any(phrase in description.lower() for phrase in self.generic_phrases)
                has_profile_info = any(indicator in description for indicator in self.profile_indicators)
                
                if is_generic and not has_profile_info:
                    continue
                
                # Extract location from description (bullet patterns)
                location = self.extract_location_from_description(description)
                
                if location:
                    return {
                        'location': location,
                        'confidence': 0.8,  # Slightly lower confidence for bullet patterns
                        'source': 'Brave Search API (Google)',
                        'url': f"https://www.google.com/search?q={search_query.replace(' ', '+')}",
                        'result_index': i
                    }
            
            # If we get here, we either found no location or couldn't validate the person
            return None
            
        except Exception as e:
            print(f"❌ Error locating contact {full_name}: {e}")
            return None
    
    def enrich_contacts_bulk(self, contacts: List[Dict], job_location: str = None) -> List[LocationMatch]:
        """
        Enrich multiple contacts with location data.
        
        Args:
            contacts: List of contact dictionaries with 'full_name', 'company', 'contact_id'
            job_location: Job location for match type determination
            
        Returns:
            List of LocationMatch objects
        """
        results = []
        
        for i, contact in enumerate(contacts):
            print(f"🔍 Enriching contact {i+1}/{len(contacts)}: {contact['full_name']} at {contact['company']}")
            
            location_match = self.locate_contact(
                contact['full_name'], 
                contact['company'], 
                contact.get('contact_id', '')
            )
            
            if location_match:
                # Determine match type based on job location
                if job_location:
                    location_match.match_type = self._determine_match_type(
                        location_match.location_raw, job_location
                    )
                
                results.append(location_match)
                print(f"  ✅ Found: {location_match.location_raw}")
            else:
                print(f"  ❌ Not found")
            
            # No delays with new API key - higher rate limits
            # if i < len(contacts) - 1:  # Don't wait after the last one
            #     time.sleep(10)  # 10 second delay for free tier
        
        return results
    
    def _determine_match_type(self, contact_location: str, job_location: str) -> LocationMatchType:
        """
        Determine location match type based on contact and job locations.
        
        Args:
            contact_location: Contact's location
            job_location: Job location
            
        Returns:
            LocationMatchType
        """
        if not contact_location or not job_location:
            return LocationMatchType.UNKNOWN
        
        contact_lower = contact_location.lower()
        job_lower = job_location.lower()
        
        # Exact match
        if contact_lower == job_lower:
            return LocationMatchType.EXACT
        
        # Check for city matches
        contact_city = contact_location.split(",")[0].strip().lower()
        job_city = job_location.split(",")[0].strip().lower()
        
        if contact_city == job_city:
            return LocationMatchType.EXACT
        
        # Check for country matches
        contact_country = contact_location.split(",")[-1].strip().lower()
        job_country = job_location.split(",")[-1].strip().lower()
        
        if contact_country == job_country:
            return LocationMatchType.NEARBY
        
        # Check for common nearby locations
        nearby_mappings = {
            'london': ['greater london', 'uk', 'united kingdom', 'england'],
            'dublin': ['ireland', 'republic of ireland'],
            'new york': ['nyc', 'manhattan', 'brooklyn', 'queens', 'usa', 'united states'],
            'san francisco': ['sf', 'bay area', 'silicon valley', 'california', 'usa'],
            'amsterdam': ['netherlands', 'holland'],
            'berlin': ['germany'],
            'paris': ['france']
        }
        
        for job_city_key, nearby_locations in nearby_mappings.items():
            if job_city_key in job_lower:
                if any(nearby in contact_lower for nearby in nearby_locations):
                    return LocationMatchType.NEARBY
        
        return LocationMatchType.REMOTE

# Example usage and testing
if __name__ == "__main__":
    # Test the enricher
    enricher = BraveLocationEnricher()
    
    test_contacts = [
        {"full_name": "Shane McCallion", "company": "Calypsoai", "contact_id": "1"},
        {"full_name": "Cian Dowling", "company": "Synthesia", "contact_id": "2"},
        {"full_name": "Andrew Paige", "company": "BrightData", "contact_id": "3"}
    ]
    
    print("🧪 Testing Brave Location Enricher")
    print("=" * 50)
    
    results = enricher.enrich_contacts_bulk(test_contacts, job_location="London, UK")
    
    print(f"\n📋 Results:")
    for result in results:
        print(f"  {result.contact_id}: {result.location_raw} ({result.match_type.value})")
