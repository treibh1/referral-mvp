#!/usr/bin/env python3
"""
Bing Location Enricher for Contact Upload
Implements geo-searching at scale using Bing Web Search API (Azure Cognitive Services).
"""

import requests
import re
import time
import hashlib
import json
from typing import Dict, List, Optional, Tuple
from unidecode import unidecode
import pandas as pd

class BingLocationEnricher:
    """
    Enriches contact data with location information using Bing Web Search API.
    Designed for bulk processing during contact upload.
    """
    
    def __init__(self, bing_api_key: str, endpoint: str = None):
        """Initialize with Bing API key and endpoint."""
        self.api_key = bing_api_key
        
        # Use provided endpoint or construct from resource name
        if endpoint:
            self.endpoint = endpoint
        else:
            # Default to Azure AI Services endpoint format
            self.endpoint = "https://api.bing.microsoft.com/v7.0/search"
        
        self.headers = {
            'Ocp-Apim-Subscription-Key': self.api_key
        }
        
        # Location extraction patterns (from user's recommendation)
        self.location_patterns = [
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[·—\-•|]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})",  # City, State
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z][a-z]+)",  # City, Country
        ]
        
        # Common location separators
        self.separators = ['·', '—', '-', '•', '|']
        
        # Gazetteer of common locations (simplified version)
        self.gazetteer = {
            'cities': ['London', 'New York', 'San Francisco', 'Austin', 'Seattle', 'Boston', 'Chicago', 'Los Angeles'],
            'regions': ['Greater London', 'Bay Area', 'Silicon Valley', 'Greater Boston', 'Greater Chicago'],
            'countries': ['United Kingdom', 'United States', 'Canada', 'Australia', 'Germany', 'France']
        }
        
        # Cache for deduplication
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour TTL
    
    def bing_search(self, query: str, mkt: str = "en-GB", count: int = 8) -> Optional[Dict]:
        """
        Perform Bing web search.
        
        Args:
            query: Search query
            mkt: Market (locale)
            count: Number of results to return
            
        Returns:
            Bing API response or None
        """
        try:
            params = {
                'q': query,
                'mkt': mkt,
                'count': count,
                'responseFilter': 'Webpages'
            }
            
            response = requests.get(self.endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Bing API error for query '{query}': {str(e)}")
            return None
    
    def extract_location(self, snippet: str) -> Optional[str]:
        """
        Extract location from snippet using heuristics.
        
        Args:
            snippet: Text snippet from Bing search result
            
        Returns:
            Extracted location or None
        """
        if not snippet:
            return None
        
        # Normalize text
        snippet = unidecode(snippet)
        
        # Method 1: Look for separators
        for separator in self.separators:
            if separator in snippet:
                parts = snippet.split(separator)
                for part in parts:
                    part = part.strip()
                    if self._is_location_like(part):
                        return part
        
        # Method 2: Use regex patterns
        for pattern in self.location_patterns:
            matches = re.findall(pattern, snippet)
            for match in matches:
                if isinstance(match, tuple):
                    # Handle multi-group patterns
                    location_parts = [part.strip() for part in match if part.strip()]
                    if location_parts:
                        location = ' '.join(location_parts)
                        if self._is_location_like(location):
                            return location
                else:
                    # Handle single-group patterns
                    if self._is_location_like(match):
                        return match.strip()
        
        # Method 3: Look for common patterns
        common_patterns = [
            r"Title at Company · Location",
            r"Name · Company · Location",
            r"Based in ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"Located in ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        ]
        
        for pattern in common_patterns:
            match = re.search(pattern, snippet, re.IGNORECASE)
            if match:
                location = match.group(1) if len(match.groups()) > 0 else match.group(0)
                if self._is_location_like(location):
                    return location.strip()
        
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
    
    def locate_contact(self, full_name: str, company: str) -> Optional[Dict]:
        """
        Locate a contact using cascading search strategy.
        
        Args:
            full_name: Contact's full name
            company: Contact's company
            
        Returns:
            Location data dictionary or None
        """
        # Check cache first
        cache_key = self._get_cache_key(full_name, company)
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if time.time() - cached_result['timestamp'] < self.cache_ttl:
                return cached_result['data']
        
        # Cascading search strategy
        queries = [
            f'"{full_name}" "{company}" site:linkedin.com/in',
            f'"{full_name}" "{company}"',
            f'{full_name} {company} location',
            f'{full_name} {company}'
        ]
        
        for query in queries:
            try:
                response = self.bing_search(query)
                if not response or 'webPages' not in response:
                    continue
                
                web_pages = response['webPages'].get('value', [])
                if not web_pages:
                    continue
                
                # Process first few results
                for page in web_pages[:3]:
                    snippet = page.get('snippet', '')
                    if snippet:
                        location = self.extract_location(snippet)
                        if location:
                            result = {
                                'location_raw': location,
                                'location_source': 'bing_search',
                                'location_url': page.get('url', ''),
                                'location_confidence': self._calculate_confidence(full_name, company, location, snippet),
                                'enriched_at': time.time()
                            }
                            
                            # Cache the result
                            self.cache[cache_key] = {
                                'data': result,
                                'timestamp': time.time()
                            }
                            
                            return result
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️ Error processing query '{query}': {str(e)}")
                continue
        
        return None
    
    def _get_cache_key(self, full_name: str, company: str) -> str:
        """Generate cache key for deduplication."""
        key_string = f"{full_name.lower()}|{company.lower()}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _calculate_confidence(self, full_name: str, company: str, location: str, snippet: str) -> float:
        """
        Calculate confidence score for location extraction.
        
        Args:
            full_name: Contact's full name
            company: Contact's company
            location: Extracted location
            snippet: Source snippet
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        score = 0.0
        
        # Name match (30%)
        if full_name.lower() in snippet.lower():
            score += 0.3
        
        # Company match (30%)
        if company.lower() in snippet.lower():
            score += 0.3
        
        # Location quality (40%)
        location_quality = 0.0
        
        # Check if location is in gazetteer
        for category, locations in self.gazetteer.items():
            for loc in locations:
                if loc.lower() in location.lower():
                    location_quality += 0.2
                    break
        
        # Check for location patterns
        if re.search(r'[A-Z][a-z]+,\s*[A-Z]{2}', location):  # City, State
            location_quality += 0.3
        elif re.search(r'[A-Z][a-z]+,\s*[A-Z][a-z]+', location):  # City, Country
            location_quality += 0.2
        
        score += min(location_quality, 0.4)
        
        return min(score, 1.0)
    
    def enrich_contacts_bulk(self, contacts_df: pd.DataFrame, max_contacts: int = None) -> pd.DataFrame:
        """
        Enrich contacts with location data in bulk during upload.
        
        Args:
            contacts_df: DataFrame with contact data
            max_contacts: Maximum number of contacts to enrich (None for all)
            
        Returns:
            DataFrame with location enrichment columns added
        """
        print(f"🌍 Starting bulk location enrichment for {len(contacts_df)} contacts...")
        
        # Initialize location columns
        contacts_df['location_raw'] = None
        contacts_df['location_city'] = None
        contacts_df['location_region'] = None
        contacts_df['location_country'] = None
        contacts_df['location_confidence'] = None
        contacts_df['location_source'] = None
        contacts_df['location_url'] = None
        contacts_df['enriched_at'] = None
        
        # Process contacts
        contacts_to_process = contacts_df.head(max_contacts) if max_contacts else contacts_df
        
        for idx, row in contacts_to_process.iterrows():
            if idx % 10 == 0:
                print(f"   Processing contact {idx + 1}/{len(contacts_to_process)}...")
            
            first_name = str(row.get('First Name', '')).strip()
            last_name = str(row.get('Last Name', '')).strip()
            company = str(row.get('Company', '')).strip()
            
            if not first_name or not last_name or not company:
                continue
            
            full_name = f"{first_name} {last_name}"
            
            # Locate contact
            location_data = self.locate_contact(full_name, company)
            
            if location_data:
                # Update DataFrame
                contacts_df.at[idx, 'location_raw'] = location_data.get('location_raw')
                contacts_df.at[idx, 'location_confidence'] = location_data.get('location_confidence')
                contacts_df.at[idx, 'location_source'] = location_data.get('location_source')
                contacts_df.at[idx, 'location_url'] = location_data.get('location_url')
                contacts_df.at[idx, 'enriched_at'] = location_data.get('enriched_at')
                
                # Parse location components (simplified)
                location_raw = location_data.get('location_raw', '')
                if location_raw:
                    parts = location_raw.split(',')
                    if len(parts) >= 1:
                        contacts_df.at[idx, 'location_city'] = parts[0].strip()
                    if len(parts) >= 2:
                        contacts_df.at[idx, 'location_region'] = parts[1].strip()
                    if len(parts) >= 3:
                        contacts_df.at[idx, 'location_country'] = parts[2].strip()
            
            # Rate limiting
            if idx < len(contacts_to_process) - 1:
                time.sleep(0.5)
        
        print(f"✅ Bulk location enrichment complete!")
        return contacts_df
    
    def get_enrichment_stats(self, contacts_df: pd.DataFrame) -> Dict:
        """
        Get statistics about location enrichment results.
        
        Args:
            contacts_df: DataFrame with enrichment data
            
        Returns:
            Statistics dictionary
        """
        total_contacts = len(contacts_df)
        enriched_contacts = contacts_df['location_raw'].notna().sum()
        high_confidence = contacts_df[contacts_df['location_confidence'] >= 0.7]['location_raw'].notna().sum()
        
        return {
            'total_contacts': total_contacts,
            'enriched_contacts': enriched_contacts,
            'enrichment_rate': enriched_contacts / total_contacts if total_contacts > 0 else 0,
            'high_confidence_contacts': high_confidence,
            'high_confidence_rate': high_confidence / total_contacts if total_contacts > 0 else 0
        }


def main():
    """Test the Bing Location Enricher."""
    # You'll need to set your Bing API key
    bing_api_key = "YOUR_BING_API_KEY"
    
    enricher = BingLocationEnricher(bing_api_key)
    
    # Test with sample data
    test_contacts = pd.DataFrame([
        {
            'First Name': 'Cian',
            'Last Name': 'Dowling',
            'Company': 'Synthesia'
        },
        {
            'First Name': 'John',
            'Last Name': 'Smith',
            'Company': 'Microsoft'
        }
    ])
    
    enriched_df = enricher.enrich_contacts_bulk(test_contacts)
    stats = enricher.get_enrichment_stats(enriched_df)
    
    print(f"Enrichment Statistics: {stats}")
    
    for idx, row in enriched_df.iterrows():
        print(f"{row['First Name']} {row['Last Name']}: {row.get('location_raw', 'Not found')}")


if __name__ == "__main__":
    main()
