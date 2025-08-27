#!/usr/bin/env python3
"""
Enhanced location validator using comprehensive location databases.
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from rapidfuzz import fuzz, process

@dataclass
class LocationInfo:
    """Location information with confidence and metadata."""
    city: str
    region: str  # State/Country
    region_type: str  # "US-STATE" or "COUNTRY"
    confidence: float
    is_capital: bool
    rank_by_population: Optional[float]
    source: str

class EnhancedLocationValidator:
    def __init__(self):
        """Initialize with comprehensive location databases."""
        self.locations = {}
        self.cities_to_regions = {}
        self.regions_to_cities = {}
        self.city_aliases = {}
        
        # Load all location databases
        self._load_us_states_cities()
        self._load_europe_countries_cities()
        self._load_middle_east_countries_cities()
        self._load_asia_countries_cities()
        
        # Build lookup dictionaries
        self._build_lookup_tables()
        
        print(f"✅ Loaded {len(self.locations)} unique locations")
        print(f"   📍 Cities: {len(self.cities_to_regions)}")
        print(f"   🌍 Regions: {len(self.regions_to_cities)}")
    
    def _load_us_states_cities(self):
        """Load US states and cities data."""
        try:
            df = pd.read_csv('us_states_cities_optionA.csv')
            for _, row in df.iterrows():
                city = row['city_name'].strip()
                region = row['region_name'].strip()
                region_type = row['region_type']
                is_capital = row['is_capital']
                rank = row['rank_by_population_in_region']
                
                key = f"{city}_{region}"
                self.locations[key] = {
                    'city': city,
                    'region': region,
                    'region_type': region_type,
                    'is_capital': is_capital,
                    'rank_by_population': rank,
                    'source': 'US States'
                }
        except Exception as e:
            print(f"⚠️ Error loading US states data: {e}")
    
    def _load_europe_countries_cities(self):
        """Load European countries and cities data."""
        try:
            df = pd.read_csv('europe_countries_cities_optionA.csv')
            for _, row in df.iterrows():
                city = row['city_name'].strip()
                region = row['region_name'].strip()
                region_type = row['region_type']
                is_capital = row['is_capital']
                rank = row['rank_by_population_in_region']
                
                key = f"{city}_{region}"
                self.locations[key] = {
                    'city': city,
                    'region': region,
                    'region_type': region_type,
                    'is_capital': is_capital,
                    'rank_by_population': rank,
                    'source': 'Europe'
                }
        except Exception as e:
            print(f"⚠️ Error loading Europe data: {e}")
    
    def _load_middle_east_countries_cities(self):
        """Load Middle East countries and cities data."""
        try:
            df = pd.read_csv('middle_east_countries_cities_optionA.csv')
            for _, row in df.iterrows():
                city = row['city_name'].strip()
                region = row['region_name'].strip()
                region_type = row['region_type']
                is_capital = row['is_capital']
                rank = row['rank_by_population_in_region']
                
                key = f"{city}_{region}"
                self.locations[key] = {
                    'city': city,
                    'region': region,
                    'region_type': region_type,
                    'is_capital': is_capital,
                    'rank_by_population': rank,
                    'source': 'Middle East'
                }
        except Exception as e:
            print(f"⚠️ Error loading Middle East data: {e}")
    
    def _load_asia_countries_cities(self):
        """Load Asian countries and cities data."""
        try:
            df = pd.read_csv('asia_countries_cities_optionA.csv')
            for _, row in df.iterrows():
                city = row['city_name'].strip()
                region = row['region_name'].strip()
                region_type = row['region_type']
                is_capital = row['is_capital']
                rank = row['rank_by_population_in_region']
                
                key = f"{city}_{region}"
                self.locations[key] = {
                    'city': city,
                    'region': region,
                    'region_type': region_type,
                    'is_capital': is_capital,
                    'rank_by_population': rank,
                    'source': 'Asia'
                }
        except Exception as e:
            print(f"⚠️ Error loading Asia data: {e}")
    
    def _build_lookup_tables(self):
        """Build efficient lookup tables for fast location matching."""
        for key, location in self.locations.items():
            city = location['city']
            region = location['region']
            
            # City to regions mapping
            if city not in self.cities_to_regions:
                self.cities_to_regions[city] = []
            self.cities_to_regions[city].append(location)
            
            # Region to cities mapping
            if region not in self.regions_to_cities:
                self.regions_to_cities[region] = []
            self.regions_to_cities[region].append(location)
            
            # Create city aliases (common variations)
            city_lower = city.lower()
            if city_lower not in self.city_aliases:
                self.city_aliases[city_lower] = city
            
            # Add common abbreviations
            if city == "New York":
                self.city_aliases["nyc"] = city
                self.city_aliases["new york city"] = city
            elif city == "Los Angeles":
                self.city_aliases["la"] = city
                self.city_aliases["los angeles"] = city
            elif city == "San Francisco":
                self.city_aliases["sf"] = city
                self.city_aliases["san fran"] = city
            elif city == "United Arab Emirates":
                self.city_aliases["uae"] = city
            elif city == "United States":
                self.city_aliases["usa"] = city
                self.city_aliases["us"] = city
            elif city == "United Kingdom":
                self.city_aliases["uk"] = city
                self.city_aliases["england"] = city
                self.city_aliases["britain"] = city
    
    def validate_location(self, text: str) -> Optional[LocationInfo]:
        """
        Validate and extract location information from text.
        
        Args:
            text: Text to extract location from
            
        Returns:
            LocationInfo if valid location found, None otherwise
        """
        if not text or len(text.strip()) < 2:
            return None
        
        text = text.strip()
        
        # Try exact matches first
        location_info = self._exact_match(text)
        if location_info:
            return location_info
        
        # Try fuzzy matching
        location_info = self._fuzzy_match(text)
        if location_info:
            return location_info
        
        # Try parsing multi-part locations (e.g., "City, State, Country")
        location_info = self._parse_multi_part_location(text)
        if location_info:
            return location_info
        
        return None
    
    def _exact_match(self, text: str) -> Optional[LocationInfo]:
        """Try exact matching against known locations."""
        text_lower = text.lower()
        
        # Check city aliases first
        if text_lower in self.city_aliases:
            city = self.city_aliases[text_lower]
            if city in self.cities_to_regions:
                # Return the most populous city if multiple regions
                locations = self.cities_to_regions[city]
                best_location = max(locations, key=lambda x: x['rank_by_population'] or 999)
                return LocationInfo(
                    city=best_location['city'],
                    region=best_location['region'],
                    region_type=best_location['region_type'],
                    confidence=1.0,
                    is_capital=best_location['is_capital'],
                    rank_by_population=best_location['rank_by_population'],
                    source=best_location['source']
                )
        
        # Check exact city name
        if text in self.cities_to_regions:
            locations = self.cities_to_regions[text]
            best_location = max(locations, key=lambda x: x['rank_by_population'] or 999)
            return LocationInfo(
                city=best_location['city'],
                region=best_location['region'],
                region_type=best_location['region_type'],
                confidence=1.0,
                is_capital=best_location['is_capital'],
                rank_by_population=best_location['rank_by_population'],
                source=best_location['source']
            )
        
        return None
    
    def _fuzzy_match(self, text: str, threshold: float = 85.0) -> Optional[LocationInfo]:
        """Try fuzzy matching against known locations."""
        # Get all unique city names
        all_cities = list(self.cities_to_regions.keys())
        
        # Find best match
        best_match = process.extractOne(text, all_cities, scorer=fuzz.ratio)
        
        if best_match and best_match[1] >= threshold:
            city = best_match[0]
            locations = self.cities_to_regions[city]
            best_location = max(locations, key=lambda x: x['rank_by_population'] or 999)
            
            return LocationInfo(
                city=best_location['city'],
                region=best_location['region'],
                region_type=best_location['region_type'],
                confidence=best_match[1] / 100.0,
                is_capital=best_location['is_capital'],
                rank_by_population=best_location['rank_by_population'],
                source=best_location['source']
            )
        
        return None
    
    def _parse_multi_part_location(self, text: str) -> Optional[LocationInfo]:
        """Parse multi-part locations like 'City, State, Country'."""
        # Split by common separators
        parts = re.split(r'[,·—\-•|*]', text)
        parts = [part.strip() for part in parts if part.strip()]
        
        if len(parts) < 2:
            return None
        
        # Try to match each part
        matched_parts = []
        for part in parts:
            location_info = self._exact_match(part) or self._fuzzy_match(part, threshold=80.0)
            if location_info:
                matched_parts.append(location_info)
        
        if not matched_parts:
            return None
        
        # Return the most confident match
        best_match = max(matched_parts, key=lambda x: x.confidence)
        return best_match
    
    def search_locations(self, query: str, limit: int = 10) -> List[LocationInfo]:
        """
        Search for locations matching a query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching LocationInfo objects
        """
        if not query or len(query.strip()) < 2:
            return []
        
        query = query.strip()
        results = []
        
        # Get all unique city names
        all_cities = list(self.cities_to_regions.keys())
        
        # Find matches using fuzzy search
        matches = process.extract(query, all_cities, scorer=fuzz.ratio, limit=limit*2)
        
        for match in matches:
            if isinstance(match, tuple) and len(match) >= 2:
                city, score = match[0], match[1]
            else:
                continue
            if score >= 70:  # Minimum threshold
                locations = self.cities_to_regions[city]
                best_location = max(locations, key=lambda x: x['rank_by_population'] or 999)
                
                location_info = LocationInfo(
                    city=best_location['city'],
                    region=best_location['region'],
                    region_type=best_location['region_type'],
                    confidence=score / 100.0,
                    is_capital=best_location['is_capital'],
                    rank_by_population=best_location['rank_by_population'],
                    source=best_location['source']
                )
                results.append(location_info)
        
        # Sort by confidence and limit results
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:limit]
    
    def get_cities_in_region(self, region: str) -> List[str]:
        """Get all cities in a specific region."""
        if region in self.regions_to_cities:
            return [loc['city'] for loc in self.regions_to_cities[region]]
        return []
    
    def get_regions_for_city(self, city: str) -> List[str]:
        """Get all regions that contain a specific city."""
        if city in self.cities_to_regions:
            return [loc['region'] for loc in self.cities_to_regions[city]]
        return []
    
    def is_valid_location(self, text: str) -> bool:
        """Check if text represents a valid location."""
        return self.validate_location(text) is not None

def test_enhanced_validator():
    """Test the enhanced location validator."""
    validator = EnhancedLocationValidator()
    
    test_cases = [
        "Dubai",
        "Dubai, United Arab Emirates",
        "New York",
        "NYC",
        "San Francisco",
        "London",
        "Paris, France",
        "Tokyo, Japan",
        "Invalid Location",
        "Random Text",
        "SF",
        "LA",
        "UK",
        "USA"
    ]
    
    print("\n🧪 Testing Enhanced Location Validator")
    print("=" * 50)
    
    for test_case in test_cases:
        result = validator.validate_location(test_case)
        if result:
            print(f"✅ '{test_case}' -> {result.city}, {result.region} ({result.confidence:.2f})")
        else:
            print(f"❌ '{test_case}' -> No match")
    
    # Test search functionality
    print(f"\n🔍 Testing location search for 'Dubai':")
    search_results = validator.search_locations("Dubai", limit=5)
    for i, result in enumerate(search_results, 1):
        print(f"   {i}. {result.city}, {result.region} ({result.confidence:.2f})")

if __name__ == "__main__":
    test_enhanced_validator()
