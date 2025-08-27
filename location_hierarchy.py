#!/usr/bin/env python3
"""
Location Hierarchy System for intelligent location matching.
Handles location relationships like "Alabama" qualifies for "USA" jobs,
but "USA" doesn't qualify for "Alabama" jobs.
"""

import pandas as pd
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import re

class LocationMatchType(Enum):
    """Types of location matches."""
    EXACT = "exact"
    CITY_IN_COUNTRY = "city_in_country"
    CITY_IN_STATE = "city_in_state"
    STATE_IN_COUNTRY = "state_in_country"
    COUNTRY_MATCH = "country_match"
    NO_MATCH = "no_match"

@dataclass
class LocationMatch:
    """Result of location matching."""
    match_type: LocationMatchType
    confidence: float
    score: float
    details: str

class LocationHierarchy:
    """
    Manages location hierarchy and matching logic.
    """
    
    def __init__(self):
        """Initialize the location hierarchy system."""
        self.countries = set()
        self.states = {}  # country -> set of states
        self.cities = {}  # state -> set of cities
        self.country_cities = {}  # country -> set of cities (for countries without states)
        self.aliases = {}  # common aliases for locations
        
        # Load location data
        self._load_location_data()
        self._build_aliases()
    
    def _load_location_data(self):
        """Load location data from CSV files."""
        print("🌍 Loading location hierarchy data...")
        
        # Load US states and cities
        try:
            us_data = pd.read_csv('us_states_cities_optionA.csv')
            self._process_us_data(us_data)
        except FileNotFoundError:
            print("⚠️ US location data not found")
        
        # Load European countries and cities
        try:
            eu_data = pd.read_csv('europe_countries_cities_optionA.csv')
            self._process_europe_data(eu_data)
        except FileNotFoundError:
            print("⚠️ European location data not found")
        
        # Load Asian countries and cities
        try:
            asia_data = pd.read_csv('asia_countries_cities_optionA.csv')
            self._process_asia_data(asia_data)
        except FileNotFoundError:
            print("⚠️ Asian location data not found")
        
        # Load Middle East countries and cities
        try:
            me_data = pd.read_csv('middle_east_countries_cities_optionA.csv')
            self._process_middle_east_data(me_data)
        except FileNotFoundError:
            print("⚠️ Middle East location data not found")
        
        print(f"✅ Loaded {len(self.countries)} countries, {len(self.states)} state mappings")
    
    def _process_us_data(self, data: pd.DataFrame):
        """Process US location data."""
        # Add USA to countries
        self.countries.add("USA")
        self.countries.add("United States")
        self.countries.add("United States of America")
        
        # Group by state
        for state in data['region_name'].unique():
            state_cities = data[data['region_name'] == state]['city_name'].tolist()
            
            # Add state to USA
            if "USA" not in self.states:
                self.states["USA"] = set()
            self.states["USA"].add(state)
            
            # Add cities to state
            if state not in self.cities:
                self.cities[state] = set()
            self.cities[state].update(state_cities)
    
    def _process_europe_data(self, data: pd.DataFrame):
        """Process European location data."""
        for country in data['region_name'].unique():
            country_cities = data[data['region_name'] == country]['city_name'].tolist()
            
            # Add country
            self.countries.add(country)
            
            # Add cities directly to country (no states in this data)
            if country not in self.country_cities:
                self.country_cities[country] = set()
            self.country_cities[country].update(country_cities)
    
    def _process_asia_data(self, data: pd.DataFrame):
        """Process Asian location data."""
        for country in data['region_name'].unique():
            country_cities = data[data['region_name'] == country]['city_name'].tolist()
            
            # Add country
            self.countries.add(country)
            
            # Add cities directly to country
            if country not in self.country_cities:
                self.country_cities[country] = set()
            self.country_cities[country].update(country_cities)
    
    def _process_middle_east_data(self, data: pd.DataFrame):
        """Process Middle East location data."""
        for country in data['region_name'].unique():
            country_cities = data[data['region_name'] == country]['city_name'].tolist()
            
            # Add country
            self.countries.add(country)
            
            # Add cities directly to country
            if country not in self.country_cities:
                self.country_cities[country] = set()
            self.country_cities[country].update(country_cities)
    
    def _build_aliases(self):
        """Build common location aliases."""
        self.aliases = {
            # Country aliases
            "USA": ["United States", "United States of America", "US", "America"],
            "UK": ["United Kingdom", "Great Britain", "England", "Britain"],
            "Ireland": ["Republic of Ireland", "Eire"],
            "Germany": ["Deutschland"],
            "France": ["République française"],
            "Spain": ["España"],
            "Italy": ["Italia"],
            "Netherlands": ["Holland", "The Netherlands"],
            "Switzerland": ["Schweiz", "Suisse", "Svizzera"],
        }
        
        # Add aliases to countries set
        for canonical, aliases in self.aliases.items():
            if canonical in self.countries:
                for alias in aliases:
                    self.countries.add(alias)
            # Also add canonical names to countries set if they're not already there
            if canonical not in self.countries:
                self.countries.add(canonical)
        
        # Add state aliases
        state_aliases = {
            "California": ["CA", "Cal"],
            "New York": ["NY"],
            "Texas": ["TX"],
            "Florida": ["FL"],
            "Illinois": ["IL"],
            "Pennsylvania": ["PA"],
            "Ohio": ["OH"],
            "Georgia": ["GA"],
            "North Carolina": ["NC"],
            "Michigan": ["MI"],
        }
        
        # Add city aliases
        city_aliases = {
            "New York": ["NYC", "New York City"],
            "Los Angeles": ["LA", "L.A."],
            "San Francisco": ["SF", "San Fran"],
            "Washington": ["DC", "Washington DC", "Washington D.C."],
            "London": ["Greater London"],
            "Dublin": ["Baile Átha Cliath"],
            "Paris": ["Ville de Paris"],
            "Berlin": ["Berlin, Germany"],
            "Amsterdam": ["Amsterdam, Netherlands"],
        }
        
        # Combine all aliases
        self.aliases.update(state_aliases)
        self.aliases.update(city_aliases)
    
    def normalize_location(self, location: str) -> str:
        """Normalize location string for comparison."""
        if not location or pd.isna(location):
            return ""
        
        location = str(location).strip().lower()
        
        # Remove common suffixes
        suffixes = [" city", " town", " county", " state", " country", " region"]
        for suffix in suffixes:
            if location.endswith(suffix):
                location = location[:-len(suffix)]
        
        return location.strip()
    
    def resolve_alias_to_canonical(self, location: str) -> str:
        """Resolve a location alias to its canonical name."""
        normalized = self.normalize_location(location)
        
        # Check if this is an alias for a canonical name
        for canonical, aliases in self.aliases.items():
            if normalized == self.normalize_location(canonical):
                return canonical
            for alias in aliases:
                if normalized == self.normalize_location(alias):
                    return canonical
        
        # If not found, return the original location
        return location
    
    def find_location_hierarchy(self, location: str) -> Dict:
        """Find the hierarchy for a given location."""
        # First resolve any aliases to canonical names
        canonical_location = self.resolve_alias_to_canonical(location)
        normalized = self.normalize_location(canonical_location)
        
        # Check if it's a country
        for country in self.countries:
            if self.normalize_location(country) == normalized:
                return {
                    "type": "country",
                    "name": country,
                    "cities": self.country_cities.get(country, set())
                }
        
        # Check if it's a state
        for country, states in self.states.items():
            for state in states:
                if self.normalize_location(state) == normalized:
                    return {
                        "type": "state",
                        "name": state,
                        "country": country,
                        "cities": self.cities.get(state, set())
                    }
        
        # Check if it's a city
        # First check in states
        for state, cities in self.cities.items():
            for city in cities:
                if self.normalize_location(city) == normalized:
                    return {
                        "type": "city",
                        "name": city,
                        "state": state,
                        "country": "USA"  # Assuming US cities for now
                    }
        
        # Check in country cities
        for country, cities in self.country_cities.items():
            for city in cities:
                if self.normalize_location(city) == normalized:
                    return {
                        "type": "city",
                        "name": city,
                        "country": country
                    }
        
        return None
    
    def match_locations(self, job_location: str, contact_location: str) -> LocationMatch:
        """
        Match job location with contact location using hierarchy logic.
        
        Args:
            job_location: Location from job posting
            contact_location: Location from contact profile
            
        Returns:
            LocationMatch object with match details
        """
        if not job_location or not contact_location:
            return LocationMatch(
                match_type=LocationMatchType.NO_MATCH,
                confidence=0.0,
                score=0.0,
                details="No location data"
            )
        
        job_hierarchy = self.find_location_hierarchy(job_location)
        contact_hierarchy = self.find_location_hierarchy(contact_location)
        
        if not job_hierarchy or not contact_hierarchy:
            # Fallback to simple string matching
            return self._simple_location_match(job_location, contact_location)
        
        # Exact match
        if (job_hierarchy["type"] == contact_hierarchy["type"] and 
            job_hierarchy["name"] == contact_hierarchy["name"]):
            return LocationMatch(
                match_type=LocationMatchType.EXACT,
                confidence=1.0,
                score=4.0,
                details=f"Exact {job_hierarchy['type']} match: {job_hierarchy['name']}"
            )
        
        # City in country match
        if (job_hierarchy["type"] == "country" and 
            contact_hierarchy["type"] == "city"):
            # Check if contact's country matches job country (including aliases)
            contact_country = contact_hierarchy.get("country", "")
            job_country = job_hierarchy["name"]
            
            # Direct match
            if contact_country == job_country:
                return LocationMatch(
                    match_type=LocationMatchType.CITY_IN_COUNTRY,
                    confidence=0.9,
                    score=3.0,
                    details=f"Contact in {contact_hierarchy['name']}, {job_country}"
                )
            
            # Check aliases - if job country is in aliases and contact country matches
            if job_country in self.aliases and contact_country in self.aliases[job_country]:
                return LocationMatch(
                    match_type=LocationMatchType.CITY_IN_COUNTRY,
                    confidence=0.9,
                    score=3.0,
                    details=f"Contact in {contact_hierarchy['name']}, {job_country} (via alias)"
                )
            
            # Check reverse aliases - if contact country is in aliases and job country matches
            if contact_country in self.aliases and job_country in self.aliases[contact_country]:
                return LocationMatch(
                    match_type=LocationMatchType.CITY_IN_COUNTRY,
                    confidence=0.9,
                    score=3.0,
                    details=f"Contact in {contact_hierarchy['name']}, {job_country} (via reverse alias)"
                )
        
        # City in state match
        if (job_hierarchy["type"] == "state" and 
            contact_hierarchy["type"] == "city" and
            contact_hierarchy.get("state") == job_hierarchy["name"]):
            return LocationMatch(
                match_type=LocationMatchType.CITY_IN_STATE,
                confidence=0.95,
                score=3.5,
                details=f"Contact in {contact_hierarchy['name']}, {job_hierarchy['name']}"
            )
        
        # State in country match
        if (job_hierarchy["type"] == "country" and 
            contact_hierarchy["type"] == "state"):
            # Check if contact's country matches job country (including aliases)
            contact_country = contact_hierarchy.get("country", "")
            job_country = job_hierarchy["name"]
            
            # Direct match
            if contact_country == job_country:
                return LocationMatch(
                    match_type=LocationMatchType.STATE_IN_COUNTRY,
                    confidence=0.8,
                    score=2.5,
                    details=f"Contact in {contact_hierarchy['name']}, {job_country}"
                )
            
            # Check aliases
            if job_country in self.aliases and contact_country in self.aliases[job_country]:
                return LocationMatch(
                    match_type=LocationMatchType.STATE_IN_COUNTRY,
                    confidence=0.8,
                    score=2.5,
                    details=f"Contact in {contact_hierarchy['name']}, {job_country} (via alias)"
                )
            
            # Check reverse aliases
            if contact_country in self.aliases and job_country in self.aliases[contact_country]:
                return LocationMatch(
                    match_type=LocationMatchType.STATE_IN_COUNTRY,
                    confidence=0.8,
                    score=2.5,
                    details=f"Contact in {contact_hierarchy['name']}, {job_country} (via reverse alias)"
                )
        
        # Country match (same country, different cities)
        if (job_hierarchy["type"] == "country" and 
            contact_hierarchy["type"] == "country"):
            job_country = job_hierarchy["name"]
            contact_country = contact_hierarchy["name"]
            
            # Direct match
            if job_country == contact_country:
                return LocationMatch(
                    match_type=LocationMatchType.COUNTRY_MATCH,
                    confidence=0.7,
                    score=2.0,
                    details=f"Same country: {job_country}"
                )
            
            # Check aliases
            if job_country in self.aliases and contact_country in self.aliases[job_country]:
                return LocationMatch(
                    match_type=LocationMatchType.COUNTRY_MATCH,
                    confidence=0.7,
                    score=2.0,
                    details=f"Same country: {job_country} (via alias)"
                )
            
            # Check reverse aliases
            if contact_country in self.aliases and job_country in self.aliases[contact_country]:
                return LocationMatch(
                    match_type=LocationMatchType.COUNTRY_MATCH,
                    confidence=0.7,
                    score=2.0,
                    details=f"Same country: {job_country} (via reverse alias)"
                )
        
        return LocationMatch(
            match_type=LocationMatchType.NO_MATCH,
            confidence=0.0,
            score=0.0,
            details="No hierarchical match found"
        )
    
    def _simple_location_match(self, job_location: str, contact_location: str) -> LocationMatch:
        """Fallback to simple string matching."""
        job_norm = self.normalize_location(job_location)
        contact_norm = self.normalize_location(contact_location)
        
        # Exact match
        if job_norm == contact_norm:
            return LocationMatch(
                match_type=LocationMatchType.EXACT,
                confidence=0.8,
                score=3.0,
                details=f"Simple exact match: {job_location}"
            )
        
        # Contains match
        if job_norm in contact_norm or contact_norm in job_norm:
            return LocationMatch(
                match_type=LocationMatchType.CITY_IN_COUNTRY,
                confidence=0.6,
                score=2.0,
                details=f"Contains match: {job_location} in {contact_location}"
            )
        
        return LocationMatch(
            match_type=LocationMatchType.NO_MATCH,
            confidence=0.0,
            score=0.0,
            details="No simple match found"
        )

# Global instance
location_hierarchy = LocationHierarchy()
