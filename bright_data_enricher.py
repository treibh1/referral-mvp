#!/usr/bin/env python3
"""
Production-ready location enrichment using Bright Data SERP API.
Simple and effective location extraction from organic search results.
"""

import os
import json
import requests
import pandas as pd
import time
import random
import re
from typing import Dict, Optional, List, Tuple

class BrightDataEnricher:
    """
    Production-ready location enrichment using Bright Data SERP API.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "dd87540592c790ffad86d2b626524b04ae2bbb4797e83f193832944af7e6d515"
        self.session = requests.Session()
        self.timeout = 30
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        self.endpoint = "https://api.brightdata.com/request"
    
    def build_search_query(self, contact: pd.Series) -> str:
        """Build a search query for a contact's location."""
        first_name = str(contact.get('First Name', '')).strip()
        last_name = str(contact.get('Last Name', '')).strip()
        company = str(contact.get('Company', '')).strip()
        
        # Build query: "full name - company - linkedin profile - location"
        parts = []
        
        if first_name and last_name:
            parts.append(f"{first_name} {last_name}")
        elif first_name:
            parts.append(first_name)
        elif last_name:
            parts.append(last_name)
        
        if company and company.lower() not in ['nan', 'none', '']:
            # Add company without quotes to get better search results
            parts.append(f'- {company}')
        
        parts.append('- linkedin profile')
        parts.append('- location')
        
        query = ' '.join(parts).strip()
        return query
    
    def search_location(self, query: str) -> Optional[str]:
        """Search for location using Bright Data SERP API."""
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        
        payload = {
            "zone": "serp_api1",
            "url": search_url,
            "format": "json"
        }
        
        try:
            response = self.session.post(
                self.endpoint,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return self.parse_location_from_json(response.text, query)
            else:
                print(f"❌ SERP API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ SERP request error: {e}")
            return None
    
    def parse_location_from_json(self, html_content: str, query: str) -> Optional[str]:
        """Parse location from JSON response by looking for Location: in organic results."""
        try:
            # Try to parse as JSON first
            data = json.loads(html_content)
            
            # The API returns a wrapper with status_code, headers, and body
            # The actual SERP data is in the body field
            if 'body' in data:
                # The body contains HTML, not JSON
                return self.parse_location_from_html(data['body'], query)
            else:
                # Direct JSON response
                serp_data = data
                organic_results = serp_data.get('organic', [])
                
                # Check first 3 organic results for location information
                for i, result in enumerate(organic_results[:3]):
                    description = result.get('description', '')
                    
                    # Look for various location patterns in the description
                    location_patterns = [
                        r'Location:\s*([^·|•\n]+?)(?:\s*[·|•]|\s*$|\s*\n)',  # English: "Location: Ireland"
                        r'Ort:\s*([^·|•\n]+?)(?:\s*[·|•]|\s*$|\s*\n)',      # German: "Ort: Berlin"
                        r'([A-Z][A-Za-z\-\s]+?\s+Area,\s+[A-Z][A-Za-z\-\s]+)',  # "London Area, United Kingdom"
                        r'([A-Z][A-Za-z\-\s]+?,\s+[A-Z][A-Za-z\-\s]+)',         # "City, Country"
                    ]
                    
                    for pattern in location_patterns:
                        location_match = re.search(pattern, description, flags=re.I)
                        if location_match:
                            location = location_match.group(1).strip()
                            if self.is_valid_location(location):
                                print(f"  Found location in result {i+1}: {location}")
                                return location
            
            return None
            
        except json.JSONDecodeError:
            # If not JSON, parse as HTML
            return self.parse_location_from_html(html_content, query)
    
    def parse_location_from_html(self, html_content: str, query: str) -> Optional[str]:
        """Parse location from HTML by looking for Location: patterns."""
        # First try to find Location: in the original HTML (before cleaning)
        location_match = re.search(r'Location:\s*([A-Z][A-Za-z\s]+?)(?:\s*[·|•]|\s*$|\s*\n)', html_content, flags=re.I)
        if location_match:
            location = location_match.group(1).strip()
            if self.is_valid_location(location):
                print(f"  Found Location: pattern (raw HTML): {location}")
                return location
                
        # Also try a simpler pattern for single words like "Ireland"
        location_match = re.search(r'Location:\s*([A-Z][A-Za-z]+)(?:\s*[·|•]|\s*$|\s*\n)', html_content, flags=re.I)
        if location_match:
            location = location_match.group(1).strip()
            if self.is_valid_location(location):
                print(f"  Found Location: pattern (raw HTML, single word): {location}")
                return location
        
        # If that doesn't work, try cleaning the HTML more carefully
        # Clean up HTML content
        text_content = re.sub(r'<[^>]+>', ' ', html_content)
        text_content = re.sub(r'\s+', ' ', text_content)
        
        # Look for "Location:" pattern - this is the key pattern we want
        location_match = re.search(r'Location:\s*([A-Z][A-Za-z\s]+?)(?:\s*[·|•]|\s*$|\s*\n)', text_content, flags=re.I)
        if location_match:
            location = location_match.group(1).strip()
            if self.is_valid_location(location):
                print(f"  Found Location: pattern: {location}")
                return location
                
        # Also try a simpler pattern for single words like "Ireland"
        location_match = re.search(r'Location:\s*([A-Z][A-Za-z]+)(?:\s*[·|•]|\s*$|\s*\n)', text_content, flags=re.I)
        if location_match:
            location = location_match.group(1).strip()
            if self.is_valid_location(location):
                print(f"  Found Location: pattern (single word): {location}")
                return location
        
        # First, look for specific "Location:" patterns which are most reliable
        location_specific_patterns = [
            r'Location:\s*([A-Z][A-Za-z\s]+?)(?:\s*[·|•]|\s*$|\s*\n)',  # English: "Location: Ireland"
            r'Ort:\s*([A-Z][A-Za-z\s]+?)(?:\s*[·|•]|\s*$|\s*\n)',      # German: "Ort: Berlin"
        ]
        
        for pattern in location_specific_patterns:
            matches = re.findall(pattern, text_content, flags=re.I)
            for match in matches:
                location = match.strip()
                print(f"  Found Location: pattern: {location}")
                if self.is_valid_location(location):
                    print(f"  ✅ Location is valid: {location}")
                    return location
                else:
                    print(f"  ❌ Location rejected by validation: {location}")
        
        # Then look for general location patterns
        general_location_patterns = [
            r'([A-Z][A-Za-z\-\s]+?\s+Area,\s+[A-Z][A-Za-z\-\s]+)',  # "London Area, United Kingdom"
            r'([A-Z][A-Za-z\-\s]+?,\s*[A-Z][A-Za-z\-\s]+(?:,\s*[A-Z][A-Za-z\-\s]+)?)',
            r'([A-Z][A-Za-z\-\s]+?,\s*[A-Z][A-Za-z\-\s]+)'
        ]
        
        for pattern in general_location_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    location = match[0].strip()
                else:
                    location = match.strip()
                
                print(f"  Found location pattern: {location}")
                if self.is_valid_location(location):
                    print(f"  ✅ Location is valid: {location}")
                    return location
                else:
                    print(f"  ❌ Location rejected by validation: {location}")
        
        return None
    
    def is_valid_location(self, location: str) -> bool:
        """Simple validation for location strings."""
        if not location or len(location) < 3 or len(location) > 100:
            return False
        
        # Check if it's a single country name (like "Ireland", "Germany", etc.)
        single_countries = ['ireland', 'germany', 'france', 'spain', 'italy', 'portugal', 'netherlands', 'belgium', 'austria', 'switzerland', 'denmark', 'sweden', 'norway', 'finland', 'poland', 'czech republic', 'hungary', 'romania', 'bulgaria', 'croatia', 'slovenia', 'slovakia', 'lithuania', 'latvia', 'estonia', 'greece', 'cyprus', 'malta', 'luxembourg', 'united kingdom', 'uk', 'usa', 'canada', 'australia', 'new zealand', 'japan', 'south korea', 'singapore', 'malaysia', 'thailand', 'philippines', 'indonesia', 'vietnam', 'india', 'china', 'brazil', 'argentina', 'chile', 'mexico', 'colombia', 'peru', 'venezuela', 'ecuador', 'uruguay', 'paraguay', 'bolivia', 'guyana', 'suriname', 'south africa', 'egypt', 'morocco', 'tunisia', 'algeria', 'libya', 'kenya', 'nigeria', 'ghana', 'ethiopia', 'tanzania', 'uganda', 'rwanda', 'zimbabwe', 'botswana', 'namibia', 'zambia', 'malawi', 'mozambique', 'madagascar', 'mauritius', 'seychelles']
        
        # Allow single country names or locations with commas (city, state/country format)
        if ',' not in location:
            if location.lower() not in single_countries:
                return False
        
        # Should not contain common false positives
        false_positives = [
            'true,nhs', 'false,', 'null,', 'undefined,', 'none,', 'nan,',
            'roboto,arial', 'arial,sans-serif', 'sans-serif', 'font-family',
            'css', 'style', 'class', 'div', 'span', 'html', 'body',
            'experience', 'education', 'connections', 'followers', 'kontakte',
            'sec-ch-prefers-color-scheme', 'downlink', 'rtt', 'google sans', 'helvetica',
            'oracle', 'profile', 'investors', 'funding', 'company', 'business'
        ]
        
        location_lower = location.lower()
        if any(fp in location_lower for fp in false_positives):
            return False
        
        # Should start with a capital letter
        if not location[0].isupper():
            return False
        
        # Should not be just numbers, but allow single country names
        if location.isdigit():
            return False
        
        # For non-country single words, require at least 2 words
        if len(location.split()) < 2 and location.lower() not in single_countries:
            return False
        
        # Should not contain technical terms
        technical_terms = ['sec-', 'ch-', 'prefers', 'color', 'scheme', 'downlink', 'rtt']
        if any(term in location_lower for term in technical_terms):
            return False
        
        # Should not contain business terms that are not locations
        business_terms = ['oracle', 'profile', 'investors', 'funding', 'company', 'business', 'enterprise', 'sanders', 'instagram', 'twitter', 'handle', 'account']
        if any(term in location_lower for term in business_terms):
            return False
        
        return True
    
    def enrich_contact_locations(self, contacts: pd.DataFrame, start_row: int = None, end_row: int = None) -> pd.DataFrame:
        """Enrich locations for contacts in the dataframe."""
        if start_row and end_row:
            contacts = contacts.iloc[start_row-1:end_row].copy()
        
        print(f"🔍 Starting location enrichment for {len(contacts)} contacts...")
        
        enriched_contacts = contacts.copy()
        enriched_contacts['serp_location'] = None
        enriched_contacts['search_query'] = ''
        enriched_contacts['location_confidence'] = 0.0
        
        for idx, contact in contacts.iterrows():
            print(f"\n--- Contact {idx+1} ---")
            print(f"Name: {contact.get('First Name', '')} {contact.get('Last Name', '')}")
            print(f"Company: {contact.get('Company', '')}")
            print(f"Current Location: {contact.get('Location', 'N/A')}")
            
            # Build search query
            query = self.build_search_query(contact)
            print(f"Search Query: {query}")
            
            # Search for location
            location = self.search_location(query)
            
            if location:
                print(f"✅ Found Location: {location}")
                enriched_contacts.at[idx, 'serp_location'] = location
                enriched_contacts.at[idx, 'location_confidence'] = 0.8
            else:
                print(f"❌ No location found")
            
            enriched_contacts.at[idx, 'search_query'] = query
            
            # Add delay between requests to be respectful
            if idx < len(contacts) - 1:
                delay = random.uniform(2.0, 4.0)
                print(f"⏳ Waiting {delay:.1f} seconds...")
                time.sleep(delay)
        
        return enriched_contacts
    
    def test_api_connection(self) -> bool:
        """Test the API connection with a simple search."""
        print("🧪 Testing API connection...")
        
        test_query = "pizza"
        test_url = f"https://www.google.com/search?q={requests.utils.quote(test_query)}"
        
        payload = {
            "zone": "serp_api1",
            "url": test_url,
            "format": "json"
        }
        
        try:
            response = self.session.post(
                self.endpoint,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            print(f"📥 Test Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ API connection successful! Got {len(response.text)} characters")
                return True
            else:
                print(f"❌ API test failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ API test error: {e}")
            return False

def main():
    """Test the production-ready location enrichment."""
    print("🚀 Production Location Enrichment Test")
    print("=" * 50)
    
    try:
        enricher = BrightDataEnricher()
        print("✅ Location enricher initialized")
        
        # Test API connection first
        print("\n" + "="*50)
        print("TEST 1: API Connection Test")
        print("="*50)
        
        if not enricher.test_api_connection():
            print("❌ API connection failed. Stopping tests.")
            return
        
        # Load contacts from rows 1310-1314
        print("\n" + "="*50)
        print("TEST 2: Location Enrichment")
        print("="*50)
        
        try:
            df = pd.read_csv('enhanced_tagged_contacts.csv')
            contacts = df.iloc[1309:1314].copy()  # rows 1310-1314 (0-based indexing)
            print(f"✅ Loaded {len(contacts)} contacts")
        except Exception as e:
            print(f"❌ Error loading contacts: {e}")
            return
        
        # Display original contact data
        print(f"\n📋 Original Contact Data:")
        print("=" * 50)
        for idx, contact in contacts.iterrows():
            print(f"{idx+1}. {contact.get('First Name', '')} {contact.get('Last Name', '')} - {contact.get('Company', '')} - {contact.get('Location', 'N/A')}")
        
        # Enrich locations
        enriched_contacts = enricher.enrich_contact_locations(contacts)
        
        # Display results
        print(f"\n{'='*80}")
        print("LOCATION ENRICHMENT RESULTS")
        print(f"{'='*80}")
        
        for idx, contact in enriched_contacts.iterrows():
            print(f"\n📋 Contact {idx+1}:")
            print(f"   Name: {contact.get('First Name', '')} {contact.get('Last Name', '')}")
            print(f"   Company: {contact.get('Company', '')}")
            print(f"   Current DB Location: {contact.get('Location', 'N/A')}")
            print(f"   SERP Location: {contact.get('serp_location', 'Not found')}")
            print(f"   Search Query: {contact.get('search_query', '')}")
            
            if contact.get('serp_location'):
                print(f"   ✅ Location Found!")
            else:
                print(f"   ❌ No Location Found")
        
        # Summary statistics
        found_count = enriched_contacts['serp_location'].notna().sum()
        total_count = len(enriched_contacts)
        
        print(f"\n📊 Summary:")
        print(f"   Total Contacts: {total_count}")
        print(f"   Locations Found: {found_count}")
        print(f"   Success Rate: {(found_count/total_count)*100:.1f}%")
        
        # Save results to file
        output_file = 'location_enrichment_results.csv'
        enriched_contacts.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

