#!/usr/bin/env python3
"""
Smart Geo Enricher - Location enrichment at job search time.
Uses Brave Search API as primary method with SerpAPI fallback.
"""

import pandas as pd
import hashlib
import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Import our location enrichers
from brave_location_enricher import BraveLocationEnricher, LocationMatch, LocationMatchType
from location_enricher import LocationEnricher  # SerpAPI fallback

class SmartGeoEnricher:
    """
    Smart Geo Enricher that performs location enrichment at job search time.
    Uses Brave Search API as primary method with SerpAPI fallback.
    """
    
    def __init__(self, brave_api_key: str = None, serpapi_key: str = None):
        """
        Initialize Smart Geo Enricher.
        
        Args:
            brave_api_key: Brave Search API key (primary method)
            serpapi_key: SerpAPI key (fallback method)
        """
        self.brave_enricher = BraveLocationEnricher(api_key=brave_api_key)
        self.serpapi_enricher = LocationEnricher(api_key=serpapi_key) if serpapi_key else None
        
        # Role-based caching
        self.role_cache = {}
        self.role_cache_ttl = 86400  # 24 hours
        
        # Contact-level caching
        self.contact_cache = {}
        self.contact_cache_ttl = 86400  # 24 hours
    
    def _get_role_cache_key(self, job_description: str) -> str:
        """Generate cache key for job role."""
        # Extract key terms from job description for role identification
        key_terms = self._extract_role_key_terms(job_description)
        return hashlib.md5('|'.join(key_terms).encode()).hexdigest()
    
    def _extract_role_key_terms(self, job_description: str) -> List[str]:
        """Extract key terms from job description for role identification."""
        # Simple extraction - could be enhanced with NLP
        words = job_description.lower().split()
        key_terms = []
        
        # Common role keywords
        role_keywords = [
            'engineer', 'developer', 'manager', 'director', 'executive', 'analyst',
            'designer', 'architect', 'consultant', 'specialist', 'lead', 'senior',
            'principal', 'head', 'chief', 'vp', 'cto', 'ceo', 'cfo'
        ]
        
        for word in words:
            if word in role_keywords:
                key_terms.append(word)
        
        # Add first few words as context
        key_terms.extend(words[:5])
        
        return key_terms[:10]  # Limit to 10 terms
    
    def _get_contact_cache_key(self, full_name: str, company: str) -> str:
        """Generate cache key for individual contact."""
        key_string = f"{full_name.lower()}|{company.lower()}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_data: Dict, ttl: int) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - cache_data['timestamp'] < ttl
    
    def enrich_contacts_for_job(self, 
                               contacts_df: pd.DataFrame, 
                               job_description: str,
                               job_location: str = None,
                               desired_location: str = None,
                               acceptable_locations: List[str] = None) -> pd.DataFrame:
        """
        Enrich contacts with location data for a specific job search.
        
        Args:
            contacts_df: DataFrame with contact information
            job_description: Job description text
            job_location: Job location (e.g., "London, UK")
            desired_location: Desired location for the role
            acceptable_locations: List of acceptable locations
            
        Returns:
            DataFrame with enriched location data
        """
        print(f"🔍 Smart Geo Enrichment for job search")
        print(f"  Job Location: {job_location}")
        print(f"  Desired Location: {desired_location}")
        print(f"  Acceptable Locations: {acceptable_locations}")
        print(f"  Contacts to process: {len(contacts_df)}")
        
        # Get role cache key
        role_cache_key = self._get_role_cache_key(job_description)
        
        # Check if we've already enriched contacts for this role
        if role_cache_key in self.role_cache and self._is_cache_valid(self.role_cache[role_cache_key], self.role_cache_ttl):
            print(f"  ✅ Found cached enrichment for this role")
            cached_contacts = self.role_cache[role_cache_key]['contacts']
            return self._apply_location_matching(cached_contacts, job_location, desired_location, acceptable_locations)
        
        # Prepare contacts for enrichment
        contacts_to_enrich = []
        for _, row in contacts_df.iterrows():
            full_name = f"{row['First Name']} {row['Last Name']}"
            company = row['Company']
            
            # Check if we already have location data for this contact
            contact_cache_key = self._get_contact_cache_key(full_name, company)
            if contact_cache_key in self.contact_cache and self._is_cache_valid(self.contact_cache[contact_cache_key], self.contact_cache_ttl):
                print(f"  ✅ Found cached location for {full_name}")
                continue
            
            # Check if contact already has location data
            if pd.notna(row.get('location_raw', pd.NA)):
                print(f"  ✅ {full_name} already has location: {row['location_raw']}")
                continue
            
            contacts_to_enrich.append({
                'full_name': full_name,
                'company': company,
                'contact_id': str(row.name),  # Use DataFrame index as contact ID
                'row_index': row.name
            })
        
        print(f"  📊 Contacts needing enrichment: {len(contacts_to_enrich)}")
        
        if not contacts_to_enrich:
            print(f"  ✅ All contacts already have location data")
            return self._apply_location_matching(contacts_df, job_location, desired_location, acceptable_locations)
        
        # Enrich contacts with location data
        enriched_contacts = self._enrich_contacts_bulk(contacts_to_enrich, job_location)
        
        # Update DataFrame with enriched data
        enriched_df = contacts_df.copy()
        for location_match in enriched_contacts:
            row_index = int(location_match.contact_id)
            if row_index in enriched_df.index:
                enriched_df.loc[row_index, 'location_raw'] = location_match.location_raw
                enriched_df.loc[row_index, 'location_city'] = location_match.location_city
                enriched_df.loc[row_index, 'location_country'] = location_match.location_country
                enriched_df.loc[row_index, 'location_confidence'] = location_match.location_confidence
                enriched_df.loc[row_index, 'location_source'] = location_match.location_source
                enriched_df.loc[row_index, 'location_url'] = location_match.location_url
                enriched_df.loc[row_index, 'enriched_at'] = location_match.enriched_at
        
        # Cache the enriched contacts for this role
        self.role_cache[role_cache_key] = {
            'contacts': enriched_df,
            'timestamp': time.time()
        }
        
        print(f"  ✅ Enriched {len(enriched_contacts)} contacts")
        
        # Apply location matching and return
        return self._apply_location_matching(enriched_df, job_location, desired_location, acceptable_locations)
    
    def _enrich_contacts_bulk(self, contacts: List[Dict], job_location: str = None) -> List[LocationMatch]:
        """
        Enrich multiple contacts with location data using Brave Search API with SerpAPI fallback.
        
        Args:
            contacts: List of contact dictionaries
            job_location: Job location for match type determination
            
        Returns:
            List of LocationMatch objects
        """
        results = []
        
        for i, contact in enumerate(contacts):
            print(f"  🔍 Enriching {i+1}/{len(contacts)}: {contact['full_name']} at {contact['company']}")
            
            # Try Brave Search API first
            location_match = self.brave_enricher.locate_contact(
                contact['full_name'], 
                contact['company'], 
                contact['contact_id']
            )
            
            # If Brave Search fails and we have SerpAPI fallback, try that
            if not location_match and self.serpapi_enricher:
                print(f"    ⚠️ Brave Search failed, trying SerpAPI fallback...")
                try:
                    serpapi_result = self.serpapi_enricher.locate_contact(
                        contact['full_name'], 
                        contact['company']
                    )
                    if serpapi_result:
                        # Convert SerpAPI result to LocationMatch format
                        location_match = LocationMatch(
                            contact_id=contact['contact_id'],
                            location_raw=serpapi_result['location_raw'],
                            location_city=serpapi_result['location_city'],
                            location_country=serpapi_result['location_country'],
                            location_confidence=serpapi_result['location_confidence'],
                            location_source='serpapi_fallback',
                            location_url=serpapi_result.get('location_url'),
                            match_type=LocationMatchType.UNKNOWN,
                            query_used=serpapi_result.get('query_used', ''),
                            enriched_at=serpapi_result['enriched_at']
                        )
                except Exception as e:
                    print(f"    ❌ SerpAPI fallback also failed: {str(e)}")
            
            if location_match:
                # Determine match type based on job location
                if job_location:
                    location_match.match_type = self.brave_enricher._determine_match_type(
                        location_match.location_raw, job_location
                    )
                
                results.append(location_match)
                print(f"    ✅ Found: {location_match.location_raw} ({location_match.location_source})")
                
                # Cache the result
                contact_cache_key = self._get_contact_cache_key(contact['full_name'], contact['company'])
                self.contact_cache[contact_cache_key] = {
                    'data': {
                        'location_raw': location_match.location_raw,
                        'location_city': location_match.location_city,
                        'location_country': location_match.location_country,
                        'location_confidence': location_match.location_confidence,
                        'location_source': location_match.location_source,
                        'location_url': location_match.location_url,
                        'query_used': location_match.query_used,
                        'enriched_at': location_match.enriched_at
                    },
                    'timestamp': time.time()
                }
            else:
                print(f"    ❌ No location found")
        
        return results
    
    def _apply_location_matching(self, 
                                contacts_df: pd.DataFrame, 
                                job_location: str = None,
                                desired_location: str = None,
                                acceptable_locations: List[str] = None) -> pd.DataFrame:
        """
        Apply location matching logic and group results.
        
        Args:
            contacts_df: DataFrame with contact information
            job_location: Job location
            desired_location: Desired location
            acceptable_locations: List of acceptable locations
            
        Returns:
            DataFrame with location matching applied
        """
        print(f"  📍 Applying location matching...")
        
        # Add location match type column
        contacts_df['location_match_type'] = 'unknown'
        
        if job_location:
            for idx, row in contacts_df.iterrows():
                if pd.notna(row.get('location_raw', pd.NA)):
                    match_type = self.brave_enricher._determine_match_type(
                        row['location_raw'], job_location
                    )
                    contacts_df.loc[idx, 'location_match_type'] = match_type.value
        
        # Add fuzzy location matching if desired/acceptable locations provided
        if desired_location or acceptable_locations:
            contacts_df['fuzzy_location_match'] = False
            
            for idx, row in contacts_df.iterrows():
                if pd.notna(row.get('location_raw', pd.NA)):
                    contact_location = row['location_raw'].lower()
                    
                    # Check desired location
                    if desired_location and self._fuzzy_location_match(contact_location, desired_location.lower()):
                        contacts_df.loc[idx, 'fuzzy_location_match'] = True
                        continue
                    
                    # Check acceptable locations
                    if acceptable_locations:
                        for acceptable in acceptable_locations:
                            if self._fuzzy_location_match(contact_location, acceptable.lower()):
                                contacts_df.loc[idx, 'fuzzy_location_match'] = True
                                break
        
        return contacts_df
    
    def _fuzzy_location_match(self, contact_location: str, target_location: str) -> bool:
        """
        Perform fuzzy location matching.
        
        Args:
            contact_location: Contact's location
            target_location: Target location to match against
            
        Returns:
            True if locations match
        """
        # Simple fuzzy matching - could be enhanced with more sophisticated algorithms
        contact_words = set(contact_location.split())
        target_words = set(target_location.split())
        
        # Check for word overlap
        overlap = contact_words.intersection(target_words)
        if len(overlap) > 0:
            return True
        
        # Check for substring matching
        if target_location in contact_location or contact_location in target_location:
            return True
        
        return False
    
    def get_location_grouped_results(self, contacts_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Group results by location match type.
        
        Args:
            contacts_df: DataFrame with enriched contact data
            
        Returns:
            Dictionary with grouped results
        """
        grouped_results = {
            'exact_matches': pd.DataFrame(),
            'nearby_matches': pd.DataFrame(),
            'remote_candidates': pd.DataFrame(),
            'unknown_location': pd.DataFrame()
        }
        
        if 'location_match_type' in contacts_df.columns:
            # Group by match type
            for match_type in ['exact', 'nearby', 'remote', 'unknown']:
                mask = contacts_df['location_match_type'] == match_type
                if match_type == 'exact':
                    grouped_results['exact_matches'] = contacts_df[mask]
                elif match_type == 'nearby':
                    grouped_results['nearby_matches'] = contacts_df[mask]
                elif match_type == 'remote':
                    grouped_results['remote_candidates'] = contacts_df[mask]
                elif match_type == 'unknown':
                    grouped_results['unknown_location'] = contacts_df[mask]
        
        return grouped_results

# Example usage
if __name__ == "__main__":
    # Test the smart geo enricher
    enricher = SmartGeoEnricher()
    
    # Sample contacts
    contacts_data = {
        'First Name': ['Shane', 'Cian', 'Andrew', 'Annabel'],
        'Last Name': ['McCallion', 'Dowling', 'Paige', 'Moody'],
        'Company': ['Calypsoai', 'Synthesia', 'BrightData', 'Zendesk'],
        'Position': ['CEO', 'Engineer', 'Manager', 'Consultant']
    }
    
    contacts_df = pd.DataFrame(contacts_data)
    
    # Test enrichment
    job_description = "Senior Software Engineer with experience in Python and machine learning"
    job_location = "London, UK"
    
    enriched_df = enricher.enrich_contacts_for_job(
        contacts_df, 
        job_description, 
        job_location,
        desired_location="London",
        acceptable_locations=["Greater London", "Manchester", "Birmingham"]
    )
    
    print("\n📋 Enriched Results:")
    print(enriched_df[['First Name', 'Last Name', 'Company', 'location_raw', 'location_match_type']])
    
    # Get grouped results
    grouped = enricher.get_location_grouped_results(enriched_df)
    
    print("\n📍 Grouped Results:")
    for group_name, group_df in grouped.items():
        if not group_df.empty:
            print(f"  {group_name}: {len(group_df)} contacts")
