from unified_matcher import UnifiedReferralMatcher
from typing import Dict, List, Optional
import json
import pandas as pd

class ReferralAPI:
    """
    Simple API wrapper for the referral matching system.
    Provides clean methods for web applications to use.
    """
    
    def __init__(self, contacts_file: str = "enhanced_tagged_contacts.csv"):
        """Initialize the API with the unified matcher."""
        self.matcher = UnifiedReferralMatcher(contacts_file)
    
    def match_job(self, job_description: str, job_title: str = None, alternative_titles: List[str] = None, top_n: int = 10, preferred_companies: List[str] = None, preferred_industries: List[str] = None, job_location: str = None, enable_location_enrichment: bool = False, serpapi_key: str = None) -> Dict:
        """
        Match a job description to potential referral candidates.
        
        Args:
            job_description: The full job description text
            top_n: Number of top candidates to return (default: 10)
            preferred_companies: List of preferred company names for bonus scoring
            preferred_industries: List of preferred industries for bonus scoring
            
        Returns:
            Dict containing:
            - success: boolean
            - candidates: list of candidate dicts
            - job_analysis: extracted job requirements
            - processing_time: time taken
            - error: error message if any
        """
        import time
        start_time = time.time()
        
        try:
            # Debug: Log what we received
            print(f"🔍 Debug - Job description length: {len(job_description) if job_description else 0}")
            print(f"🔍 Debug - Job description preview: {job_description[:100] if job_description else 'None'}")
            
            # Validate job description - be more lenient
            if not job_description or len(job_description.strip()) < 20:  # Reduced to 20 characters
                return {
                    'success': False,
                    'error': 'Job description is too short or empty. Please check the URL or paste the job description manually.',
                    'matches': [],
                    'analysis': {
                        'role_detected': 'N/A',
                        'role_confidence': 0,
                        'company_detected': 'N/A',
                        'seniority_detected': 'N/A',
                        'skills_found': 0,
                        'platforms_found': 0,
                        'processing_time': 0
                    }
                }
            
            # Always extract job requirements for analysis, regardless of manual title
            auto_reqs = self.matcher.extract_job_requirements(job_description)
            
            # If job title is provided, use it directly for matching but keep auto-detection for analysis
            if job_title:
                print(f"🎯 Using provided job title: {job_title}")
                
                # Convert manual job title to canonical form
                canonical_job_title = job_title.lower()
                for alias, canonical in self.matcher.title_aliases.items():
                    if alias.lower() == job_title.lower():
                        canonical_job_title = canonical
                        break
                
                # Create job requirements with canonical manual title for matching
                job_reqs = {
                    'role': canonical_job_title,  # Use canonical form
                    'role_confidence': 1.0,  # High confidence for manual input
                    'suggested_roles': auto_reqs['suggested_roles'],  # Keep auto-detection suggestions
                    'skills': auto_reqs['skills'],
                    'platforms': auto_reqs['platforms'],
                    'company': auto_reqs['company'],
                    'company_tags': auto_reqs.get('company_tags', []),  # Add missing company_tags
                    'seniority': auto_reqs['seniority']
                }
                print(f"🔍 Auto-detected role from description: {auto_reqs['role']} (Confidence: {auto_reqs['role_confidence']})")
            else:
                # Use auto-detected requirements
                job_reqs = auto_reqs
            
            # Find candidates with company/industry preferences and location enrichment
            top_candidates = self.matcher.find_top_candidates(
                job_description, top_n, preferred_companies, preferred_industries,
                job_location, enable_location_enrichment, serpapi_key,
                job_title=job_title, alternative_titles=alternative_titles,
                job_reqs=job_reqs  # Pass the job requirements we already extracted
            )
            
            # Convert to list of dicts for JSON serialization
            candidates = []
            for _, row in top_candidates.iterrows():
                # Helper function to handle NaN values safely
                def clean_value(value):
                    try:
                        if pd.isna(value) or str(value).lower() in ['nan', 'none', '']:
                            return ''
                        return str(value)
                    except:
                        return ''
                
                # Helper function to safely convert to float
                def safe_float(value, default=0.0):
                    try:
                        if pd.isna(value) or str(value).lower() in ['nan', 'none', '']:
                            return default
                        return float(value)
                    except:
                        return default
                
                # Helper function to safely get list
                def safe_list(value, default=[]):
                    try:
                        # Check if it's a list first (before pd.isna)
                        if isinstance(value, list):
                            return value
                        # Then check for NaN/None values
                        if pd.isna(value):
                            return default
                        if str(value).lower() in ['nan', 'none', '']:
                            return default
                        return default
                    except Exception as e:
                        print(f"safe_list error: {e} for value {value}")
                        return default
                
                candidate = {
                    'first_name': clean_value(row['First Name']),
                    'last_name': clean_value(row['Last Name']),
                    'position': clean_value(row['Position']),
                    'company': clean_value(row['Company']),
                    'email': clean_value(row.get('Email', '')),
                    'linkedin': clean_value(row.get('LinkedIn', '')),
                    'location': clean_value(row.get('location_raw', '')),
                    'employee_connection': clean_value(row.get('employee_connection', '')),
                    'match_score': safe_float(row['match_score']),
                    'skill_matches': safe_list(row['skill_matches']),
                    'matched_role': clean_value(row['matched_role']),
                    'industry_matches': safe_list(row.get('industry_matches', [])),
                    'location_match_details': clean_value(row.get('location_match_details', '')),
                    'location_match_type': clean_value(row.get('location_match_type', '')),
                    'score_breakdown': {
                        'skill_score': safe_float(row['skill_score']),
                        'role_score': safe_float(row['role_score']),
                        'company_score': safe_float(row['company_score']),
                        'industry_score': safe_float(row['industry_score']),
                        'seniority_bonus': safe_float(row['seniority_bonus']),
                        'location_score': safe_float(row.get('location_score', 0)),
                        'tagged_boost': safe_float(row.get('tagged_boost', 0))
                    }
                }
                candidates.append(candidate)
            
            processing_time = time.time() - start_time
            
            # Convert candidates to matches format for frontend and categorize by location
            exact_location_matches = []
            other_location_matches = []
            
            for candidate in candidates:
                match = {
                    'name': f"{candidate['first_name']} {candidate['last_name']}",
                    'company': candidate['company'],
                    'position': candidate['position'],
                    'score': candidate['match_score'],
                    'location': candidate.get('location', ''),
                    'email': candidate.get('email', ''),
                    'linkedin': candidate.get('linkedin', ''),
                    'employee_connection': candidate.get('employee_connection', ''),
                    'skill_matches': candidate['skill_matches'],
                    'matched_role': candidate['matched_role'],
                    'location_match_details': candidate.get('location_match_details', ''),
                    'location_match_type': candidate.get('location_match_type', ''),
                    'score_breakdown': candidate['score_breakdown']
                }
                
                # Categorize by location match
                candidate_location = candidate.get('location', '')
                if candidate_location and self._is_location_match(candidate_location, job_location or ''):
                    exact_location_matches.append(match)
                else:
                    other_location_matches.append(match)
            
            # Combine matches with exact location matches first
            matches = exact_location_matches + other_location_matches
            
            # Prepare analysis data - show both manual and auto-detected roles
            analysis_data = {
                'skills_found': job_reqs['skills'],
                'platforms_found': job_reqs['platforms'],
                'role_detected': job_reqs['role'],
                'role_confidence': job_reqs['role_confidence'],
                'suggested_roles': job_reqs['suggested_roles'],
                'company_detected': job_reqs['company'],
                'seniority_detected': job_reqs['seniority']
            }
            
            # If manual title was provided, also show auto-detected role for comparison
            if job_title and auto_reqs['role'] != job_reqs['role']:
                analysis_data['auto_detected_role'] = auto_reqs['role']
                analysis_data['auto_detected_confidence'] = auto_reqs['role_confidence']
            
            return {
                'success': True,
                'matches': matches,
                'candidates': candidates,  # Keep for backward compatibility
                'job_analysis': analysis_data,
                'processing_time': round(processing_time, 2),
                'total_candidates_found': len(candidates),
                'exact_location_count': len(exact_location_matches),
                'other_location_count': len(other_location_matches)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'candidates': [],
                'job_analysis': {},
                'processing_time': time.time() - start_time
            }
    
    def _is_location_match(self, candidate_location: str, job_location: str) -> bool:
        """Check if candidate location matches job location."""
        if not candidate_location or not job_location:
            return False
        
        # Normalize locations for comparison
        candidate_loc = candidate_location.lower().strip()
        job_loc = job_location.lower().strip()
        
        # Direct match
        if candidate_loc == job_loc:
            return True
        
        # Check if job location is contained in candidate location
        if job_loc in candidate_loc:
            return True
        
        # Check if candidate location is contained in job location
        if candidate_loc in job_loc:
            return True
        
        # Check for common location patterns
        location_patterns = {
            'ireland': ['ireland', 'dublin', 'cork', 'galway', 'limerick'],
            'united kingdom': ['uk', 'united kingdom', 'england', 'london', 'manchester', 'birmingham'],
            'usa': ['usa', 'united states', 'new york', 'california', 'texas'],
            'australia': ['australia', 'sydney', 'melbourne', 'brisbane'],
            'germany': ['germany', 'berlin', 'munich', 'hamburg'],
            'france': ['france', 'paris', 'lyon', 'marseille'],
            'spain': ['spain', 'madrid', 'barcelona', 'valencia']
        }
        
        for country, cities in location_patterns.items():
            if job_loc in cities and candidate_loc in cities:
                return True
        
        return False
    
    def get_system_stats(self) -> Dict:
        """Get system statistics."""
        return {
            'total_contacts': len(self.matcher.df),
            'total_skills': len(self.matcher.all_skills),
            'total_platforms': len(self.matcher.all_platforms),
            'scoring_weights': self.matcher.scoring_weights
        }
    
    def test_connection(self) -> Dict:
        """Test if the system is working properly."""
        try:
            stats = self.get_system_stats()
            return {
                'success': True,
                'message': 'System is ready',
                'stats': stats
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Example usage for web applications
def create_api_instance():
    """Factory function to create API instance."""
    return ReferralAPI()


# Example Flask/Web app usage:
"""
from flask import Flask, request, jsonify
from referral_api import create_api_instance

app = Flask(__name__)
api = create_api_instance()

@app.route('/match', methods=['POST'])
def match_job():
    data = request.get_json()
    job_description = data.get('job_description', '')
    top_n = data.get('top_n', 10)
    
    if not job_description:
        return jsonify({'error': 'Job description is required'}), 400
    
    result = api.match_job(job_description, top_n)
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify(api.test_connection())

if __name__ == '__main__':
    app.run(debug=True)
"""
