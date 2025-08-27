#!/usr/bin/env python3
"""
DuckDuckGo Web Search API implementation for location enrichment - FIXED VERSION.
"""

import requests
import re
import time
import json
from typing import Dict, List, Optional
from unidecode import unidecode

class DuckDuckGoWebEnricherFixed:
    """
    DuckDuckGo web search implementation for location enrichment - FIXED VERSION.
    """
    
    def __init__(self):
        """Initialize DuckDuckGo web enricher."""
        # Use the main DuckDuckGo search endpoint
        self.search_url = "https://duckduckgo.com/"
        
        # Location extraction patterns - more specific
        self.location_patterns = [
            r"Location:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "Location: Dublin"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[·—\-•|]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "Name · Location"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})",  # City, State
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z][a-z]+)",  # City, Country
        ]
        
        # Common location separators
        self.separators = ['·', '—', '-', '•', '|']
        
        # Gazetteer of common locations
        self.gazetteer = {
            'cities': ['London', 'New York', 'San Francisco', 'Austin', 'Seattle', 'Boston', 'Chicago', 'Los Angeles', 'Dublin', 'Amsterdam', 'Berlin', 'Paris'],
            'regions': ['Greater London', 'Bay Area', 'Silicon Valley', 'Greater Boston', 'Greater Chicago'],
            'countries': ['United Kingdom', 'United States', 'Canada', 'Australia', 'Germany', 'France', 'Ireland', 'Netherlands']
        }
    
    def search_duckduckgo_web(self, query: str) -> Optional[str]:
        """
        Search DuckDuckGo web and return HTML results.
        
        Args:
            query: Search query
            
        Returns:
            HTML content or None
        """
        try:
            params = {
                'q': query,
                't': 'h_',  # Use HTML results
                'ia': 'web'  # Web search
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(self.search_url, params=params, headers=headers)
            response.raise_for_status()
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ DuckDuckGo web search error for query '{query}': {str(e)}")
            return None
    
    def clean_html_content(self, html_content: str) -> str:
        """
        Clean HTML content to remove scripts and focus on text content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned text content
        """
        if not html_content:
            return ""
        
        # Remove script tags and their content
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove style tags and their content
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags but keep text
        html_content = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Remove extra whitespace
        html_content = re.sub(r'\s+', ' ', html_content)
        
        # Normalize text
        html_content = unidecode(html_content)
        
        return html_content.strip()
    
    def extract_location_from_html(self, html_content: str) -> Optional[str]:
        """
        Extract location from cleaned HTML content.
        
        Args:
            html_content: HTML content from DuckDuckGo search
            
        Returns:
            Extracted location or None
        """
        if not html_content:
            return None
        
        # Clean the HTML content
        cleaned_content = self.clean_html_content(html_content)
        
        print(f"  📄 Cleaned content preview: {cleaned_content[:200]}...")
        
        # Method 1: Look for "Location:" pattern (most reliable)
        location_pattern = r"Location:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        matches = re.findall(location_pattern, cleaned_content)
        if matches:
            location = matches[0].strip()
            if self._is_location_like(location):
                print(f"  🎯 Found location via 'Location:' pattern: {location}")
                return location
        
        # Method 2: Look for LinkedIn profile patterns
        linkedin_patterns = [
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[·—\-•|]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "Name · Location"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})",  # City, State
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z][a-z]+)",  # City, Country
        ]
        
        for pattern in linkedin_patterns:
            matches = re.findall(pattern, cleaned_content)
            for match in matches:
                if isinstance(match, tuple):
                    location_parts = [part.strip() for part in match if part.strip()]
                    if location_parts:
                        location = ' '.join(location_parts)
                        if self._is_location_like(location):
                            print(f"  🎯 Found location via LinkedIn pattern: {location}")
                            return location
                else:
                    if self._is_location_like(match):
                        print(f"  🎯 Found location via pattern: {match.strip()}")
                        return match.strip()
        
        # Method 3: Look for separators in text
        for separator in self.separators:
            if separator in cleaned_content:
                parts = cleaned_content.split(separator)
                for part in parts:
                    part = part.strip()
                    if self._is_location_like(part):
                        print(f"  🎯 Found location via separator '{separator}': {part}")
                        return part
        
        return None
    
    def _is_location_like(self, text: str) -> bool:
        """
        Check if text looks like a location using gazetteer.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be a location
        """
        if not text or len(text) < 3:
            return False
        
        # Skip if it contains JavaScript-like content
        if any(js_indicator in text.lower() for js_indicator in ['script', 'var ', 'function', 'backend', 'experiment']):
            return False
        
        text_lower = text.lower()
        
        # Check against gazetteer
        for category, locations in self.gazetteer.items():
            for location in locations:
                if location.lower() in text_lower:
                    return True
        
        # Check for location indicators
        indicators = ['area', 'region', 'county', 'state', 'country', 'city', 'greater']
        for indicator in indicators:
            if indicator in text_lower:
                return True
        
        return False
    
    def locate_contact(self, full_name: str, company: str) -> Optional[Dict]:
        """
        Locate a contact using DuckDuckGo web search.
        
        Args:
            full_name: Contact's full name
            company: Contact's company
            
        Returns:
            Location data dictionary or None
        """
        print(f"🔍 Searching for {full_name} at {company}...")
        
        # Use the working pattern: "full name + company + linkedin"
        query = f"{full_name} {company} linkedin"
        print(f"  Query: {query}")
        
        # Search DuckDuckGo web
        html_content = self.search_duckduckgo_web(query)
        if html_content:
            print(f"  ✅ Got HTML response ({len(html_content)} characters)")
            
            # Extract location from HTML
            location = self.extract_location_from_html(html_content)
            if location:
                print(f"  📍 Found location: {location}")
                return {
                    'location_raw': location,
                    'location_source': 'duckduckgo_web',
                    'location_url': f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
                    'location_confidence': 0.8,
                    'enriched_at': time.time()
                }
            else:
                print(f"  ❌ No location found in HTML")
        else:
            print(f"  ❌ Failed to get HTML response")
        
        return None

def test_duckduckgo_web_fixed():
    """Test DuckDuckGo web search with real people."""
    print("🦆 Testing DuckDuckGo Web Search - FIXED VERSION")
    print("=" * 60)
    
    enricher = DuckDuckGoWebEnricherFixed()
    
    # Test with the people you mentioned
    test_cases = [
        ("Shane McCallion", "CalypsoAI"),
        ("Cian Dowling", "Synthesia"),
        ("Annabel Moody", "Current Company"),  # Replace with actual company
        # Add some additional test cases
        ("John Smith", "Microsoft"),
        ("Sarah Johnson", "Google")
    ]
    
    results = []
    
    for full_name, company in test_cases:
        print(f"\n🧪 Testing: {full_name} at {company}")
        
        location_data = enricher.locate_contact(full_name, company)
        
        if location_data:
            print(f"  ✅ Found location: {location_data['location_raw']}")
            print(f"  📍 Source: {location_data['location_source']}")
            print(f"  🎯 Confidence: {location_data['location_confidence']}")
            results.append({
                'name': full_name,
                'company': company,
                'location': location_data['location_raw'],
                'confidence': location_data['location_confidence']
            })
        else:
            print(f"  ❌ No location found")
            results.append({
                'name': full_name,
                'company': company,
                'location': None,
                'confidence': 0
            })
        
        # Rate limiting
        time.sleep(3)
    
    # Summary
    print(f"\n📋 Summary:")
    print(f"Total tests: {len(test_cases)}")
    successful = sum(1 for r in results if r['location'])
    print(f"Successful: {successful}")
    print(f"Success rate: {successful/len(test_cases)*100:.1f}%")
    
    print(f"\n📍 Results:")
    for result in results:
        status = "✅" if result['location'] else "❌"
        print(f"  {status} {result['name']} ({result['company']}): {result['location'] or 'Not found'}")
    
    return results

if __name__ == "__main__":
    test_duckduckgo_web_fixed()



