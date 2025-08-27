#!/usr/bin/env python3
"""
Location-based search and matching system for the referral app.
"""

import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enhanced_location_validator import EnhancedLocationValidator, LocationInfo
from rapidfuzz import fuzz

@dataclass
class LocationMatch:
    """Location match result."""
    contact_id: str
    contact_name: str
    contact_location: str
    job_location: str
    match_type: str  # 'exact', 'nearby', 'remote', 'unknown'
    confidence: float
    distance_score: float

class LocationSearchSystem:
    """Location-based search and matching system."""
    
    def __init__(self):
        """Initialize the location search system."""
        self.location_validator = EnhancedLocationValidator()
        
        # Location proximity mappings
        self.nearby_locations = {
            'london': ['greater london', 'uk', 'united kingdom', 'england', 'britain'],
            'dublin': ['ireland', 'republic of ireland'],
            'new york': ['nyc', 'manhattan', 'brooklyn', 'queens', 'usa', 'united states'],
            'san francisco': ['sf', 'bay area', 'silicon valley', 'california', 'usa'],
            'amsterdam': ['netherlands', 'holland'],
            'berlin': ['germany'],
            'paris': ['france'],
            'dubai': ['uae', 'united arab emirates'],
            'madrid': ['spain'],
            'boston': ['massachusetts', 'ma', 'usa', 'united states'],
            'toronto': ['ontario', 'canada'],
            'sydney': ['new south wales', 'australia'],
            'singapore': ['sg'],
            'tokyo': ['japan'],
            'mumbai': ['india'],
            'shanghai': ['china']
        }
    
    def search_contacts_by_location(self, contacts_df: pd.DataFrame, job_location: str, 
                                   match_type: str = 'all') -> List[LocationMatch]:
        """
        Search contacts by location proximity to job location.
        
        Args:
            contacts_df: DataFrame with contact information
            job_location: Job location to match against
            match_type: Type of matches to return ('exact', 'nearby', 'remote', 'all')
            
        Returns:
            List of LocationMatch objects
        """
        if not job_location or contacts_df.empty:
            return []
        
        # Validate job location
        job_location_info = self.location_validator.validate_location(job_location)
        if not job_location_info:
            print(f"⚠️ Invalid job location: {job_location}")
            return []
        
        matches = []
        
        for _, contact in contacts_df.iterrows():
            contact_location = contact.get('location', '')
            if not contact_location:
                continue
            
            # Validate contact location
            contact_location_info = self.location_validator.validate_location(contact_location)
            if not contact_location_info:
                continue
            
            # Determine match type and confidence
            match_type_result, confidence, distance_score = self._calculate_location_match(
                contact_location_info, job_location_info
            )
            
            # Filter by requested match type
            if match_type != 'all' and match_type_result != match_type:
                continue
            
            match = LocationMatch(
                contact_id=str(contact.get('contact_id', '')),
                contact_name=f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip(),
                contact_location=contact_location,
                job_location=job_location,
                match_type=match_type_result,
                confidence=confidence,
                distance_score=distance_score
            )
            matches.append(match)
        
        # Sort by confidence and distance score
        matches.sort(key=lambda x: (x.confidence, x.distance_score), reverse=True)
        return matches
    
    def _calculate_location_match(self, contact_location: LocationInfo, 
                                 job_location: LocationInfo) -> Tuple[str, float, float]:
        """
        Calculate location match between contact and job locations.
        
        Args:
            contact_location: Contact's location info
            job_location: Job location info
            
        Returns:
            Tuple of (match_type, confidence, distance_score)
        """
        # Exact match
        if (contact_location.city.lower() == job_location.city.lower() and 
            contact_location.region.lower() == job_location.region.lower()):
            return 'exact', 1.0, 1.0
        
        # Same city, different region (e.g., different states in same city)
        if contact_location.city.lower() == job_location.city.lower():
            return 'exact', 0.9, 0.9
        
        # Same region/country
        if contact_location.region.lower() == job_location.region.lower():
            return 'nearby', 0.8, 0.8
        
        # Check for nearby locations
        contact_city_lower = contact_location.city.lower()
        job_city_lower = job_location.city.lower()
        
        # Check if job city has nearby locations
        if job_city_lower in self.nearby_locations:
            nearby_list = self.nearby_locations[job_city_lower]
            if any(nearby in contact_city_lower for nearby in nearby_list):
                return 'nearby', 0.7, 0.7
            if any(nearby in contact_location.region.lower() for nearby in nearby_list):
                return 'nearby', 0.6, 0.6
        
        # Check if contact city has nearby locations
        if contact_city_lower in self.nearby_locations:
            nearby_list = self.nearby_locations[contact_city_lower]
            if any(nearby in job_city_lower for nearby in nearby_list):
                return 'nearby', 0.7, 0.7
            if any(nearby in job_location.region.lower() for nearby in nearby_list):
                return 'nearby', 0.6, 0.6
        
        # Same country but different cities
        if contact_location.region_type == 'COUNTRY' and job_location.region_type == 'COUNTRY':
            if contact_location.region.lower() == job_location.region.lower():
                return 'remote', 0.5, 0.5
        
        # Fuzzy matching for similar city names
        city_similarity = fuzz.ratio(contact_city_lower, job_city_lower) / 100.0
        if city_similarity > 0.8:
            return 'nearby', city_similarity * 0.8, city_similarity * 0.8
        
        return 'remote', 0.1, 0.1
    
    def get_location_suggestions(self, query: str, limit: int = 10) -> List[LocationInfo]:
        """
        Get location suggestions for autocomplete.
        
        Args:
            query: Search query
            limit: Maximum number of suggestions
            
        Returns:
            List of LocationInfo objects
        """
        return self.location_validator.search_locations(query, limit)
    
    def validate_and_normalize_location(self, location_text: str) -> Optional[LocationInfo]:
        """
        Validate and normalize location text.
        
        Args:
            location_text: Raw location text
            
        Returns:
            Normalized LocationInfo or None if invalid
        """
        return self.location_validator.validate_location(location_text)
    
    def get_contacts_in_location(self, contacts_df: pd.DataFrame, 
                                location: str) -> pd.DataFrame:
        """
        Get all contacts in a specific location.
        
        Args:
            contacts_df: DataFrame with contact information
            location: Location to filter by
            
        Returns:
            Filtered DataFrame
        """
        location_info = self.location_validator.validate_location(location)
        if not location_info:
            return pd.DataFrame()
        
        # Filter contacts by location
        filtered_contacts = []
        
        for _, contact in contacts_df.iterrows():
            contact_location = contact.get('location', '')
            if not contact_location:
                continue
            
            contact_location_info = self.location_validator.validate_location(contact_location)
            if not contact_location_info:
                continue
            
            # Check if contact is in the same location
            if (contact_location_info.city.lower() == location_info.city.lower() or
                contact_location_info.region.lower() == location_info.region.lower()):
                filtered_contacts.append(contact)
        
        return pd.DataFrame(filtered_contacts) if filtered_contacts else pd.DataFrame()

def test_location_search_system():
    """Test the location search system."""
    system = LocationSearchSystem()
    
    # Create sample contacts data
    sample_contacts = [
        {'contact_id': '1', 'First Name': 'John', 'Last Name': 'Smith', 'location': 'San Francisco, California'},
        {'contact_id': '2', 'First Name': 'Jane', 'Last Name': 'Doe', 'location': 'New York, New York'},
        {'contact_id': '3', 'First Name': 'Bob', 'Last Name': 'Johnson', 'location': 'London, United Kingdom'},
        {'contact_id': '4', 'First Name': 'Alice', 'Last Name': 'Brown', 'location': 'Dubai, United Arab Emirates'},
        {'contact_id': '5', 'First Name': 'Charlie', 'Last Name': 'Wilson', 'location': 'Boston, Massachusetts'},
    ]
    
    contacts_df = pd.DataFrame(sample_contacts)
    
    print("🧪 Testing Location Search System")
    print("=" * 50)
    
    # Test location search
    job_location = "San Francisco, California"
    matches = system.search_contacts_by_location(contacts_df, job_location)
    
    print(f"🔍 Job Location: {job_location}")
    print(f"📊 Found {len(matches)} location matches:")
    
    for match in matches:
        print(f"   {match.contact_name}: {match.contact_location} ({match.match_type}, {match.confidence:.2f})")
    
    # Test location suggestions
    print(f"\n🔍 Location suggestions for 'Dubai':")
    suggestions = system.get_location_suggestions("Dubai", limit=3)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"   {i}. {suggestion.city}, {suggestion.region} ({suggestion.confidence:.2f})")

if __name__ == "__main__":
    test_location_search_system()
