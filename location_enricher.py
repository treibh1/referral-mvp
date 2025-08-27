import requests
import re
import time
from typing import Dict, List, Optional, Tuple
import json

class LocationEnricher:
    """
    Enriches contact data with location information using SerpAPI Google Search.
    Only searches top candidates to minimize API costs.
    """
    
    def __init__(self, serpapi_key: str):
        """Initialize with SerpAPI key."""
        self.serpapi_key = serpapi_key
        self.base_url = "https://serpapi.com/search.json"
        
        # Location extraction patterns
        self.location_patterns = [
            r"Location:\s*([^·\n]+)",
            r"Based in\s*([^·\n]+)",
            r"Located in\s*([^·\n]+)",
            r"from\s*([^·\n]+)",
            r"in\s*([^·\n]+?)(?:\s*·|\s*$)",
        ]
        
        # Common location indicators to look for in snippets
        self.location_indicators = [
            "Greater", "Area", "Region", "Metropolitan", "County", "State",
            "London", "New York", "San Francisco", "Austin", "Seattle",
            "United Kingdom", "United States", "Canada", "Australia"
        ]
    
    def search_contact_location(self, full_name: str, company: str) -> Optional[str]:
        """
        Search for a contact's location using their name and company.
        
        Args:
            full_name: Contact's full name
            company: Contact's current company
            
        Returns:
            Extracted location string or None if not found
        """
        try:
            # Construct search query
            query = f"{full_name} {company}"
            
            # SerpAPI parameters
            params = {
                'engine': 'google',
                'q': query,
                'api_key': self.serpapi_key,
                'num': 1,  # Only need first result
                'gl': 'us',  # US results
                'hl': 'en'
            }
            
            # Make API request
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract location from first result
            location = self._extract_location_from_response(data)
            
            if location:
                print(f"📍 Found location for {full_name}: {location}")
            else:
                print(f"❌ No location found for {full_name}")
            
            return location
            
        except Exception as e:
            print(f"⚠️ Error searching location for {full_name}: {str(e)}")
            return None
    
    def _extract_location_from_response(self, response_data: Dict) -> Optional[str]:
        """
        Extract location from SerpAPI response.
        
        Args:
            response_data: Full SerpAPI response
            
        Returns:
            Extracted location string or None
        """
        try:
            # Check if we have organic results
            if 'organic_results' not in response_data or not response_data['organic_results']:
                return None
            
            first_result = response_data['organic_results'][0]
            
            # Method 1: Check rich snippet extensions (most reliable)
            if 'rich_snippet' in first_result and 'top' in first_result['rich_snippet']:
                extensions = first_result['rich_snippet']['top'].get('extensions', [])
                for ext in extensions:
                    if self._is_location_like(ext):
                        return ext.strip()
            
            # Method 2: Extract from snippet using patterns
            snippet = first_result.get('snippet', '')
            if snippet:
                location = self._extract_location_from_text(snippet)
                if location:
                    return location
            
            # Method 3: Check title for location hints
            title = first_result.get('title', '')
            if title:
                location = self._extract_location_from_text(title)
                if location:
                    return location
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error extracting location from response: {str(e)}")
            return None
    
    def _extract_location_from_text(self, text: str) -> Optional[str]:
        """
        Extract location from text using regex patterns.
        
        Args:
            text: Text to search for location
            
        Returns:
            Extracted location string or None
        """
        for pattern in self.location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if self._is_location_like(location):
                    return location
        
        return None
    
    def _is_location_like(self, text: str) -> bool:
        """
        Check if text looks like a location.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be a location
        """
        if not text or len(text) < 3:
            return False
        
        # Check for location indicators
        text_lower = text.lower()
        for indicator in self.location_indicators:
            if indicator.lower() in text_lower:
                return True
        
        # Check for common location patterns
        location_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Area|Region|County|State|Country)\b',
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s+[A-Z]{2}\b',  # City, State
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s+[A-Z][a-z]+\b',  # City, Country
        ]
        
        for pattern in location_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def enrich_top_candidates(self, candidates: List[Dict], max_candidates: int = 20) -> List[Dict]:
        """
        Enrich top candidates with location data.
        
        Args:
            candidates: List of candidate dictionaries
            max_candidates: Maximum number of candidates to enrich
            
        Returns:
            List of candidates with location data added
        """
        print(f"🌍 Enriching location data for top {min(len(candidates), max_candidates)} candidates...")
        
        enriched_candidates = []
        
        for i, candidate in enumerate(candidates[:max_candidates]):
            full_name = f"{candidate.get('First Name', '')} {candidate.get('Last Name', '')}".strip()
            company = candidate.get('Company', '')
            
            if full_name and company:
                location = self.search_contact_location(full_name, company)
                candidate['location'] = location
                
                # Add delay to respect API rate limits
                if i < len(candidates[:max_candidates]) - 1:
                    time.sleep(1)  # 1 second delay between requests
            else:
                candidate['location'] = None
            
            enriched_candidates.append(candidate)
        
        # Add remaining candidates without location data
        enriched_candidates.extend(candidates[max_candidates:])
        
        print(f"✅ Location enrichment complete for {len(enriched_candidates)} candidates")
        return enriched_candidates
    
    def calculate_location_score(self, candidate_location: str, job_location: str) -> float:
        """
        Calculate location match score between candidate and job.
        
        Args:
            candidate_location: Candidate's location
            job_location: Job location requirement
            
        Returns:
            Location match score (0.0 to 1.0)
        """
        if not candidate_location or not job_location:
            return 0.0
        
        candidate_lower = candidate_location.lower()
        job_lower = job_location.lower()
        
        # Exact match
        if candidate_lower == job_lower:
            return 1.0
        
        # Contains match (e.g., "Greater Brighton" contains "Brighton")
        if job_lower in candidate_lower or candidate_lower in job_lower:
            return 0.8
        
        # Same city/region
        candidate_words = set(candidate_lower.split())
        job_words = set(job_lower.split())
        common_words = candidate_words & job_words
        
        if len(common_words) >= 1:
            return 0.6
        
        # Same country/state
        countries = ['united states', 'united kingdom', 'canada', 'australia']
        states = ['california', 'texas', 'new york', 'london', 'ontario']
        
        for country in countries:
            if country in candidate_lower and country in job_lower:
                return 0.4
        
        for state in states:
            if state in candidate_lower and state in job_lower:
                return 0.3
        
        return 0.0


def main():
    """Test the location enricher."""
    # You'll need to set your SerpAPI key
    serpapi_key = "YOUR_SERPAPI_KEY"
    
    enricher = LocationEnricher(serpapi_key)
    
    # Test with the example from the user
    test_candidates = [
        {
            'First Name': 'Cian',
            'Last Name': 'Dowling',
            'Company': 'Synthesia',
            'match_score': 15.5
        }
    ]
    
    enriched = enricher.enrich_top_candidates(test_candidates)
    
    for candidate in enriched:
        print(f"{candidate['First Name']} {candidate['Last Name']}: {candidate.get('location', 'Not found')}")


if __name__ == "__main__":
    main()



