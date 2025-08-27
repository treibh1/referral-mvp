#!/usr/bin/env python3
"""
DuckDuckGo Lite Enricher - Server-rendered HTML approach.
Based on developer friend's solution.
"""

import requests
import re
import time
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
from unidecode import unidecode

class DuckDuckGoLiteEnricher:
    """
    DuckDuckGo Lite enricher using server-rendered HTML endpoints.
    """
    
    def __init__(self):
        """Initialize DuckDuckGo Lite enricher."""
        # Use server-rendered endpoints
        # self.search_url = "https://duckduckgo.com/html/"      # works, heavier
        self.search_url = "https://lite.duckduckgo.com/lite/"   # fastest/minimal
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        }
        
        # Tiny starter gazetteer; replace with a proper city/country set
        self.cities = {c.lower() for c in [
            "London", "Dublin", "Berlin", "Paris", "Amsterdam", "New York", "San Francisco",
            "Toronto", "Manchester", "Birmingham", "Edinburgh", "Austin", "Seattle", "Chicago", 
            "Los Angeles", "Boston", "Austin", "Seattle", "Boston", "Chicago", "Los Angeles"
        ]}
        
        self.countries = {c.lower() for c in [
            "United Kingdom", "United States", "Ireland", "Germany", "France", "Netherlands", 
            "Canada", "Australia", "UK", "USA", "US"
        ]}
        
        self.sep_re = re.compile(r"[•\u00B7\-\—\|\·]")  # bullet/middot/dash/pipe
        self.loc_label = re.compile(r"\bLocation:\s*([^\-\—\|\·•]+)", re.I)

    def _ddg_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Fetch results from DDG lite and return [{'title','url','snippet'}].
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of result dictionaries
        """
        try:
            r = requests.get(self.search_url, params={"q": query}, headers=self.headers, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            items = []
            # lite layout: results in <a class="result-link"> with a following <div> snippet
            for a in soup.select("a.result-link"):
                url = a.get("href")
                title = a.get_text(" ", strip=True)
                # snippet is usually the next sibling td/div; grab nearest text
                snippet_el = a.find_parent("td")
                snippet = ""
                if snippet_el:
                    snippet = snippet_el.get_text(" ", strip=True)
                if url and title:
                    items.append({"title": title, "url": url, "snippet": snippet})
                if len(items) >= max_results:
                    break
            return items
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ DuckDuckGo search error: {str(e)}")
            return []

    def _normalize(self, s: str) -> str:
        """Normalize text by removing extra whitespace and accents."""
        return re.sub(r"\s+", " ", unidecode(s or "").strip())

    def _is_city(self, token: str) -> bool:
        """Check if token is a known city."""
        return token.lower() in self.cities

    def _is_country(self, token: str) -> bool:
        """Check if token is a known country."""
        t = token.lower().replace("u.k.", "united kingdom").replace("uk", "united kingdom") \
                         .replace("u.s.", "united states").replace("usa", "united states")
        return t in self.countries

    def _extract_location_from_snippet(self, snippet: str) -> Optional[str]:
        """
        Extract location from a search result snippet.
        
        Args:
            snippet: Text snippet from search result
            
        Returns:
            Extracted location or None
        """
        if not snippet:
            return None
        s = self._normalize(snippet)

        # 1) explicit "Location:" label
        m = self.loc_label.search(s)
        if m:
            cand = self._normalize(m.group(1))
            # stop at first separator, if any
            cand = self.sep_re.split(cand)[0].strip()
            if self._is_city(cand) or self._is_country(cand):
                return cand

        # 2) look for tokens separated by · — - | (scan right-to-left)
        parts = [p.strip() for p in self.sep_re.split(s) if p.strip()]
        for part in reversed(parts):
            # City, Country pattern
            m2 = re.search(r"([A-Za-z][A-Za-z \-']+),\s*([A-Za-z\. ]+)$", part)
            if m2:
                city = self._normalize(m2.group(1))
                country = self._normalize(m2.group(2))
                if self._is_city(city) or self._is_country(country):
                    return f"{city}, {country}"
            # Single city/country token
            if self._is_city(part) or self._is_country(part):
                return part

        return None

    def locate_contact(self, full_name: str, company: str) -> Optional[Dict]:
        """
        Locate a contact using DuckDuckGo Lite search.
        
        Args:
            full_name: Contact's full name
            company: Contact's company
            
        Returns:
            Location data dictionary or None
        """
        print(f"🔍 Searching for {full_name} at {company}...")
        
        # Use LinkedIn-specific query
        query = f'site:linkedin.com/in "{full_name}" "{company}"'
        print(f"  Query: {query}")
        
        results = self._ddg_search(query, max_results=6)
        print(f"  ✅ Found {len(results)} results")

        for i, r in enumerate(results):
            print(f"    Result {i+1}: {r.get('title', 'No title')[:50]}...")
            
            if "linkedin.com/in" not in (r["url"] or ""):
                print(f"      ⏭️ Skipping non-LinkedIn URL")
                continue
                
            loc = self._extract_location_from_snippet(r.get("snippet", ""))
            if loc:
                print(f"      📍 Found location: {loc}")
                # crude confidence; improve with fuzzy name/company checks
                return {
                    "location_raw": loc,
                    "location_city": loc.split(",")[0].strip() if "," in loc else (loc if self._is_city(loc) else None),
                    "location_country": (loc.split(",")[-1].strip() if "," in loc else (loc if self._is_country(loc) else None)),
                    "location_confidence": 0.7,
                    "location_source": "duckduckgo_lite_snippet",
                    "location_url": r["url"],
                    "query_used": query,
                    "enriched_at": time.time()
                }
            else:
                print(f"      ❌ No location found in snippet")
        
        print(f"  ❌ No location found in any results")
        return None

def test_duckduckgo_lite():
    """Test DuckDuckGo Lite enricher with real people."""
    print("🦆 Testing DuckDuckGo Lite Enricher")
    print("=" * 50)
    
    enricher = DuckDuckGoLiteEnricher()
    
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
        time.sleep(2)
    
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
    test_duckduckgo_lite()



