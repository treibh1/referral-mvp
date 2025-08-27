#!/usr/bin/env python3
"""
Smart Geo Integration for Job Matching
Integrates smart geo enrichment with the existing job matching system.
"""

import os
import pandas as pd
from typing import Dict, List, Optional, Tuple
from smart_geo_enricher import SmartGeoEnricher, LocationMatchType
from unified_matcher import UnifiedReferralMatcher

class SmartGeoJobMatcher:
    """
    Enhanced job matcher that integrates smart geo enrichment with location-based result grouping.
    """
    
    def __init__(self, bing_api_key: str = None, serpapi_key: str = None):
        """Initialize with optional API keys."""
        self.geo_enricher = SmartGeoEnricher(bing_api_key, serpapi_key)
        self.unified_matcher = UnifiedReferralMatcher()
        
        print("✅ Smart Geo Job Matcher initialized")
    
    def find_top_candidates_with_location_grouping(self,
                                                 contacts_df: pd.DataFrame,
                                                 job_description: str,
                                                 top_n: int = 10,
                                                 preferred_companies: List[str] = None,
                                                 preferred_industries: List[str] = None,
                                                 desired_location: str = None,
                                                 acceptable_locations: List[str] = None,
                                                 role_type: str = None) -> Dict:
        """
        Find top candidates with smart geo enrichment and location-based grouping.
        
        Args:
            contacts_df: DataFrame with contact data
            job_description: Job description
            top_n: Number of top candidates to return
            preferred_companies: List of preferred companies
            preferred_industries: List of preferred industries
            desired_location: Primary desired location
            acceptable_locations: List of acceptable locations
            role_type: Optional role type override
            
        Returns:
            Dictionary with grouped results and metadata
        """
        print(f"🎯 Smart job matching with location grouping...")
        
        # Step 1: Enrich contacts with location data (only if needed)
        enriched_df = self.geo_enricher.enrich_contacts_for_job_search(
            contacts_df=contacts_df,
            job_description=job_description,
            desired_location=desired_location,
            acceptable_locations=acceptable_locations,
            role_type=role_type
        )
        
        # Step 2: Find top candidates using existing matching logic
        # We need to set the contacts DataFrame first
        self.unified_matcher.df = enriched_df
        top_candidates = self.unified_matcher.find_top_candidates(
            job_description,
            top_n * 3,  # Get more candidates for grouping
            preferred_companies,
            preferred_industries
        )
        
        # Step 3: Group candidates by location match
        if desired_location:
            location_groups = self.geo_enricher.group_contacts_by_location(
                top_candidates,
                desired_location,
                acceptable_locations
            )
            
            # Create grouped results
            grouped_results = self._create_grouped_results(location_groups, top_n)
        else:
            # No location specified, return ungrouped results
            grouped_results = {
                'ungrouped': top_candidates.head(top_n).to_dict('records'),
                'location_stats': {
                    'total_candidates': len(top_candidates),
                    'with_location': top_candidates['location_raw'].notna().sum(),
                    'without_location': top_candidates['location_raw'].isna().sum()
                }
            }
        
        return grouped_results
    
    def _create_grouped_results(self, location_groups: Dict, top_n: int) -> Dict:
        """Create grouped results with metadata."""
        results = {
            'exact_matches': [],
            'nearby_matches': [],
            'remote_matches': [],
            'unknown_location': [],
            'location_stats': {
                'exact_count': len(location_groups.get('exact', [])),
                'nearby_count': len(location_groups.get('nearby', [])),
                'remote_count': len(location_groups.get('remote', [])),
                'unknown_count': len(location_groups.get('unknown', [])),
                'total_candidates': sum(len(group) for group in location_groups.values())
            }
        }
        
        # Convert LocationMatch objects to dictionaries and add to results
        for match_type, matches in location_groups.items():
            if match_type == 'exact':
                results['exact_matches'] = [self._location_match_to_dict(match) for match in matches[:top_n]]
            elif match_type == 'nearby':
                results['nearby_matches'] = [self._location_match_to_dict(match) for match in matches[:top_n]]
            elif match_type == 'remote':
                results['remote_matches'] = [self._location_match_to_dict(match) for match in matches[:top_n]]
            elif match_type == 'unknown':
                results['unknown_location'] = [self._location_match_to_dict(match) for match in matches[:top_n]]
        
        return results
    
    def _location_match_to_dict(self, location_match) -> Dict:
        """Convert LocationMatch object to dictionary."""
        return {
            'contact_id': location_match.contact_id,
            'location_raw': location_match.location_raw,
            'location_city': location_match.location_city,
            'location_region': location_match.location_region,
            'location_country': location_match.location_country,
            'match_type': location_match.match_type.value,
            'confidence': location_match.confidence,
            'distance_score': location_match.distance_score
        }


def integrate_with_flask_api():
    """
    Example of how to integrate this with the existing Flask API.
    This would replace/modify the current /api/match endpoint.
    """
    
    integration_code = '''
    # In app.py, modify the /api/match endpoint:
    
    from smart_geo_integration import SmartGeoJobMatcher
    
    # Initialize the smart matcher
    smart_matcher = SmartGeoJobMatcher(
        bing_api_key=os.environ.get('BING_API_KEY'),
        serpapi_key=os.environ.get('SERPAPI_KEY')
    )
    
    @app.route('/api/match', methods=['POST'])
    def match_job():
        """Enhanced API endpoint for job matching with location grouping."""
        try:
            data = request.get_json()
            job_description = data.get('job_description', '')
            top_n = data.get('top_n', 10)
            preferred_companies = data.get('preferred_companies', [])
            preferred_industries = data.get('preferred_industries', [])
            
            # New location parameters
            desired_location = data.get('desired_location', '')
            acceptable_locations = data.get('acceptable_locations', [])
            role_type = data.get('role_type', None)
            
            if not job_description.strip():
                return jsonify({
                    'success': False,
                    'error': 'Job description is required'
                }), 400
            
            # Load contacts (you'll need to implement this based on your data storage)
            contacts_df = load_user_contacts(session.get('user_id'))
            
            # Find candidates with smart geo enrichment
            results = smart_matcher.find_top_candidates_with_location_grouping(
                contacts_df=contacts_df,
                job_description=job_description,
                top_n=top_n,
                preferred_companies=preferred_companies,
                preferred_industries=preferred_industries,
                desired_location=desired_location,
                acceptable_locations=acceptable_locations,
                role_type=role_type
            )
            
            return jsonify({
                'success': True,
                'results': results,
                'metadata': {
                    'total_candidates': results.get('location_stats', {}).get('total_candidates', 0),
                    'has_location_data': bool(desired_location),
                    'grouping_enabled': bool(desired_location)
                }
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    '''
    
    return integration_code


def create_location_ui_components():
    """
    Example UI components for location preferences in the job search form.
    """
    
    html_components = '''
    <!-- Add to templates/index.html -->
    
    <!-- Location Preferences Section -->
    <div class="form-group">
        <label for="desiredLocation">Primary Location:</label>
        <input type="text" id="desiredLocation" 
               placeholder="e.g., London, UK or San Francisco, CA" 
               style="width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 5px;">
        <small style="color: #666;">Primary location for the role</small>
    </div>
    
    <div class="form-group">
        <label for="acceptableLocations">Acceptable Locations (optional):</label>
        <div id="acceptableLocationsContainer">
            <div class="location-input-group">
                <input type="text" class="acceptable-location" 
                       placeholder="e.g., Amsterdam, Netherlands" 
                       style="width: calc(100% - 40px); padding: 10px; border: 2px solid #ddd; border-radius: 5px; margin-bottom: 5px;">
                <button type="button" class="remove-location" 
                        style="width: 30px; height: 30px; background: #ff4444; color: white; border: none; border-radius: 3px; margin-left: 5px;">×</button>
            </div>
        </div>
        <button type="button" id="addLocation" 
                style="background: #4CAF50; color: white; padding: 5px 10px; border: none; border-radius: 3px; margin-top: 5px;">
            + Add Location
        </button>
        <small style="color: #666;">Additional locations that would be acceptable</small>
    </div>
    
    <div class="form-group">
        <label style="display: flex; align-items: center; cursor: pointer;">
            <input type="checkbox" id="enableLocationGrouping" checked style="margin-right: 10px; width: auto;">
            🌍 Enable Location-Based Grouping
        </label>
        <small style="color: #666;">Group results by location match (exact, nearby, remote)</small>
    </div>
    
    <!-- JavaScript for dynamic location inputs -->
    <script>
    document.getElementById('addLocation').addEventListener('click', function() {
        const container = document.getElementById('acceptableLocationsContainer');
        const newGroup = document.createElement('div');
        newGroup.className = 'location-input-group';
        newGroup.innerHTML = `
            <input type="text" class="acceptable-location" 
                   placeholder="e.g., Dublin, Ireland" 
                   style="width: calc(100% - 40px); padding: 10px; border: 2px solid #ddd; border-radius: 5px; margin-bottom: 5px;">
            <button type="button" class="remove-location" 
                    style="width: 30px; height: 30px; background: #ff4444; color: white; border: none; border-radius: 3px; margin-left: 5px;">×</button>
        `;
        container.appendChild(newGroup);
    });
    
    // Remove location input
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-location')) {
            e.target.parentElement.remove();
        }
    });
    
    // Update the existing fetch call to include location data
    function performJobSearch() {
        const jobDescription = document.getElementById('jobDescription').value;
        const topN = parseInt(document.getElementById('topN').value);
        const preferredCompanies = getPreferredCompanies();
        const preferredIndustries = getPreferredIndustries();
        
        // New location data
        const desiredLocation = document.getElementById('desiredLocation').value;
        const acceptableLocations = Array.from(document.querySelectorAll('.acceptable-location'))
            .map(input => input.value.trim())
            .filter(value => value.length > 0);
        const enableLocationGrouping = document.getElementById('enableLocationGrouping').checked;
        
        const requestBody = {
            job_description: jobDescription,
            top_n: topN,
            preferred_companies: preferredCompanies,
            preferred_industries: preferredIndustries,
            desired_location: desiredLocation,
            acceptable_locations: acceptableLocations,
            enable_location_grouping: enableLocationGrouping
        };
        
        // Make API call...
        fetch('/api/match', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayGroupedResults(data.results);
            } else {
                displayError(data.error);
            }
        })
        .catch(error => {
            displayError('An error occurred while searching for candidates.');
        });
    }
    
    function displayGroupedResults(results) {
        const resultsContainer = document.getElementById('results');
        resultsContainer.innerHTML = '';
        
        if (results.exact_matches && results.exact_matches.length > 0) {
            const exactSection = createLocationSection('Exact Location Matches', results.exact_matches, 'exact');
            resultsContainer.appendChild(exactSection);
        }
        
        if (results.nearby_matches && results.nearby_matches.length > 0) {
            const nearbySection = createLocationSection('Nearby Location Matches', results.nearby_matches, 'nearby');
            resultsContainer.appendChild(nearbySection);
        }
        
        if (results.remote_matches && results.remote_matches.length > 0) {
            const remoteSection = createLocationSection('Remote Candidates', results.remote_matches, 'remote');
            resultsContainer.appendChild(remoteSection);
        }
        
        if (results.unknown_location && results.unknown_location.length > 0) {
            const unknownSection = createLocationSection('Unknown Location', results.unknown_location, 'unknown');
            resultsContainer.appendChild(unknownSection);
        }
        
        // Display location statistics
        if (results.location_stats) {
            displayLocationStats(results.location_stats);
        }
    }
    
    function createLocationSection(title, candidates, type) {
        const section = document.createElement('div');
        section.className = 'location-section';
        section.style.cssText = 'margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px;';
        
        const typeColors = {
            'exact': '#4CAF50',
            'nearby': '#FF9800',
            'remote': '#2196F3',
            'unknown': '#9E9E9E'
        };
        
        section.style.borderLeft = `4px solid ${typeColors[type]}`;
        
        const titleElement = document.createElement('h3');
        titleElement.textContent = title;
        titleElement.style.margin = '0 0 15px 0';
        section.appendChild(titleElement);
        
        candidates.forEach(candidate => {
            const candidateElement = createCandidateElement(candidate, type);
            section.appendChild(candidateElement);
        });
        
        return section;
    }
    
    function createCandidateElement(candidate, type) {
        const element = document.createElement('div');
        element.className = 'candidate-item';
        element.style.cssText = 'padding: 10px; margin: 5px 0; background: #f9f9f9; border-radius: 3px;';
        
        const locationInfo = candidate.location_raw !== 'Unknown' 
            ? `<br><strong>📍 Location:</strong> ${candidate.location_raw} (${candidate.match_type})`
            : '<br><strong>📍 Location:</strong> Unknown';
        
        element.innerHTML = `
            <strong>${candidate.First_Name} ${candidate.Last_Name}</strong>
            <br><strong>Company:</strong> ${candidate.Company}
            <br><strong>Position:</strong> ${candidate.Position}
            ${locationInfo}
            <br><strong>Match Score:</strong> ${candidate.match_score?.toFixed(1) || 'N/A'}
        `;
        
        return element;
    }
    
    function displayLocationStats(stats) {
        const statsContainer = document.createElement('div');
        statsContainer.className = 'location-stats';
        statsContainer.style.cssText = 'margin: 20px 0; padding: 15px; background: #f0f0f0; border-radius: 5px;';
        
        statsContainer.innerHTML = `
            <h4>Location Statistics</h4>
            <p><strong>Total Candidates:</strong> ${stats.total_candidates}</p>
            <p><strong>Exact Matches:</strong> ${stats.exact_count}</p>
            <p><strong>Nearby Matches:</strong> ${stats.nearby_count}</p>
            <p><strong>Remote Candidates:</strong> ${stats.remote_count}</p>
            <p><strong>Unknown Location:</strong> ${stats.unknown_count}</p>
        `;
        
        document.getElementById('results').appendChild(statsContainer);
    }
    </script>
    '''
    
    return html_components


def demo_smart_matching():
    """Demo the smart matching functionality."""
    
    # Initialize matcher
    matcher = SmartGeoJobMatcher()
    
    # Create sample data
    sample_contacts = pd.DataFrame([
        {
            'contact_id': 'contact_1',
            'First Name': 'John',
            'Last Name': 'Smith',
            'Company': 'Microsoft',
            'Position': 'Software Engineer',
            'role_tag': 'software engineer',
            'function_tag': 'engineering',
            'seniority_tag': 'senior'
        },
        {
            'contact_id': 'contact_2',
            'First Name': 'Sarah',
            'Last Name': 'Johnson',
            'Company': 'Google',
            'Position': 'Product Manager',
            'role_tag': 'product manager',
            'function_tag': 'product',
            'seniority_tag': 'mid'
        },
        {
            'contact_id': 'contact_3',
            'First Name': 'Alex',
            'Last Name': 'Chen',
            'Company': 'Amazon',
            'Position': 'Data Scientist',
            'role_tag': 'data scientist',
            'function_tag': 'data',
            'seniority_tag': 'senior'
        }
    ])
    
    # Sample job search
    job_description = "We are looking for a senior software engineer with experience in Python and machine learning."
    desired_location = "London, UK"
    acceptable_locations = ["Amsterdam, Netherlands", "Dublin, Ireland"]
    
    print("🎯 Demo: Smart Job Matching with Location Grouping")
    print("=" * 60)
    print(f"Job Description: {job_description}")
    print(f"Desired Location: {desired_location}")
    print(f"Acceptable Locations: {acceptable_locations}")
    print()
    
    # Perform matching
    results = matcher.find_top_candidates_with_location_grouping(
        contacts_df=sample_contacts,
        job_description=job_description,
        top_n=5,
        desired_location=desired_location,
        acceptable_locations=acceptable_locations
    )
    
    # Display results
    print("📊 Results:")
    for group_name, candidates in results.items():
        if group_name != 'location_stats' and candidates:
            print(f"\n{group_name.upper().replace('_', ' ')}:")
            for candidate in candidates:
                print(f"  • {candidate.get('First Name', '')} {candidate.get('Last Name', '')} at {candidate.get('Company', '')}")
                print(f"    Location: {candidate.get('location_raw', 'Unknown')} ({candidate.get('match_type', 'unknown')})")
    
    if 'location_stats' in results:
        stats = results['location_stats']
        print(f"\n📈 Location Statistics:")
        print(f"  Total Candidates: {stats.get('total_candidates', 0)}")
        print(f"  Exact Matches: {stats.get('exact_count', 0)}")
        print(f"  Nearby Matches: {stats.get('nearby_count', 0)}")
        print(f"  Remote Candidates: {stats.get('remote_count', 0)}")
        print(f"  Unknown Location: {stats.get('unknown_count', 0)}")


def main():
    """Run the demo."""
    demo_smart_matching()


if __name__ == "__main__":
    main()
