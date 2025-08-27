#!/usr/bin/env python3
"""
Google Search-based location enricher that scrapes Google Search results directly.
"""

import requests
import re
import time
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List
import random
from urllib.parse import quote_plus

@dataclass
class LocationMatch:
    location_raw: Optional[str]
    location_city: Optional[str]
    location_country: Optional[str]
    location_confidence: float
    location_source: str
    location_url: Optional[str]
    query_used: str

class GoogleSearchEnricher:
    def __init__(self):
        self.session = requests.Session()
        
        # More realistic browser headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        # Location patterns to extract from Google snippets
        self.location_patterns = [
            r'Location:\s*([A-Z][a-zA-Z\s,]+?)(?:\s*[·—\-•|*]|\s*on\s+LinkedIn|\s*500\+|\s*connections|\s*View|\s*professional|\s*community|\s*[0-9]+\+|\s*View\s+profile)',
            r'([A-Z][a-zA-Z\s,]+?)\s*·\s*[A-Z][a-zA-Z\s]+?\s*·\s*[A-Z][a-zA-Z\s]+',  # "City, State · Company · Title"
            r'([A-Z][a-zA-Z\s,]+?)\s*·\s*[A-Z][a-zA-Z\s]+',  # "City, State · Company"
            r'([A-Z][a-zA-Z\s,]+?)\s*·\s*[A-Z][a-zA-Z\s]+?\s*·\s*[A-Z][a-zA-Z\s]+?\s*·\s*[A-Z][a-zA-Z\s]+',  # "City, State · Company · Title · Location"
            r'([A-Z][a-zA-Z\s,]+?)\s*·\s*[A-Z][a-zA-Z\s]+?\s*·\s*[A-Z][a-zA-Z\s]+?\s*·\s*[A-Z][a-zA-Z\s]+?\s*·\s*[A-Z][a-zA-Z\s]+',  # "City, State · Company · Title · Location · Connections"
        ]
        
        # Gazetteer for validation
        self.gazetteer = {
            'cities': ['Dubai', 'London', 'New York', 'San Francisco', 'Toronto', 'Berlin', 'Paris', 'Sydney', 'Singapore', 'Amsterdam'],
            'countries': ['United States', 'United Kingdom', 'Canada', 'Germany', 'France', 'Australia', 'Singapore', 'Netherlands', 'United Arab Emirates'],
            'states': ['California', 'New York', 'Texas', 'Florida', 'Virginia', 'Washington', 'Illinois', 'Pennsylvania', 'Ohio', 'Georgia']
        }
        
    def google_search(self, query: str) -> Optional[str]:
        """Perform Google search and return HTML content."""
        try:
            # Encode the query for URL
            encoded_query = quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}&hl=en&gl=us"
            
            print(f"   🔍 Searching: {url}")
            
            # Add a small delay to be respectful
            time.sleep(2)
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            print(f"   ⚠️ Error searching Google: {e}")
            return None
    
    def extract_location_from_snippet(self, snippet: str) -> Optional[str]:
        """Extract location from Google search snippet."""
        if not snippet:
            return None
            
        # Try each pattern
        for pattern in self.location_patterns:
            match = re.search(pattern, snippet, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if self._is_valid_location(location):
                    return location
        
        return None
    
    def _is_valid_location(self, text: str) -> bool:
        """Validate if extracted text is a real location."""
        if not text or len(text) < 2:
            return False
            
        # Check against gazetteer
        text_lower = text.lower()
        for category in self.gazetteer.values():
            for location in category:
                if location.lower() in text_lower:
                    return True
        
        # Check for common location indicators
        location_indicators = ['city', 'state', 'country', 'region', 'area']
        if any(indicator in text_lower for indicator in location_indicators):
            return False  # These are usually not actual locations
            
        return False
    
    def locate_contact(self, full_name: str, company: str) -> Optional[LocationMatch]:
        """Locate contact using Google Search."""
        # Create search query: "full name - company - linkedin"
        search_query = f'"{full_name}" - {company} - linkedin'
        
        print(f"   🔍 Google Search Query: {search_query}")
        
        # Perform Google search
        html_content = self.google_search(search_query)
        if not html_content:
            return None
        
        # Extract snippets from HTML (simplified - in production you'd use BeautifulSoup)
        snippets = self._extract_snippets_from_html(html_content)
        
        for snippet in snippets:
            location = self.extract_location_from_snippet(snippet)
            if location:
                return LocationMatch(
                    location_raw=location,
                    location_city=location.split(',')[0].strip() if ',' in location else location,
                    location_country=location.split(',')[-1].strip() if ',' in location else None,
                    location_confidence=0.8,
                    location_source='Google Search',
                    location_url=f"https://www.google.com/search?q={quote_plus(search_query)}",
                    query_used=search_query
                )
        
        return None
    
    def _extract_snippets_from_html(self, html: str) -> List[str]:
        """Extract search result snippets from Google HTML."""
        snippets = []
        
        # Look for snippet patterns in Google HTML - more comprehensive patterns
        snippet_patterns = [
            r'<div[^>]*class="[^"]*snippet[^"]*"[^>]*>(.*?)</div>',
            r'<span[^>]*class="[^"]*st[^"]*"[^>]*>(.*?)</span>',
            r'<div[^>]*class="[^"]*VwiC3b[^"]*"[^>]*>(.*?)</div>',  # Google's snippet class
            r'<div[^>]*class="[^"]*LC20lb[^"]*"[^>]*>(.*?)</div>',  # Google's title class
            r'<span[^>]*class="[^"]*aCOpRe[^"]*"[^>]*>(.*?)</span>',  # Google's snippet span
        ]
        
        for pattern in snippet_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Clean HTML tags
                clean_text = re.sub(r'<[^>]+>', '', match)
                clean_text = re.sub(r'&[^;]+;', ' ', clean_text)
                clean_text = re.sub(r'&amp;', '&', clean_text)
                clean_text = re.sub(r'&lt;', '<', clean_text)
                clean_text = re.sub(r'&gt;', '>', clean_text)
                clean_text = ' '.join(clean_text.split())
                
                if clean_text and len(clean_text) > 20:
                    snippets.append(clean_text)
                    print(f"      📄 Found snippet: {clean_text[:100]}...")
        
        return snippets

def test_google_search():
    """Test the Google Search enricher."""
    enricher = GoogleSearchEnricher()
    
    # Test with Steven Toal-Lennon
    print("🧪 Testing Google Search Enricher")
    print("=" * 50)
    
    full_name = "Steven Toal-Lennon"
    company = "Zendesk"
    
    print(f"👤 Testing: {full_name} at {company}")
    
    location_match = enricher.locate_contact(full_name, company)
    
    if location_match:
        print(f"✅ Location found: {location_match.location_raw}")
        print(f"📍 City: {location_match.location_city}")
        print(f"🌍 Country: {location_match.location_country}")
        print(f"🎯 Confidence: {location_match.location_confidence}")
        print(f"🔗 Source: {location_match.location_source}")
    else:
        print("❌ No location found")

if __name__ == "__main__":
    test_google_search()
