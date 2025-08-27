#!/usr/bin/env python3
"""
Adaptive Role Matcher - Handles both core roles and custom/niche roles
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

@dataclass
class RoleCriteria:
    """Represents the matching criteria for a role."""
    role_name: str
    role_category: str  # 'core', 'custom', 'hybrid'
    industry_context: Optional[str] = None
    
    # Core role fields
    core_role_variations: List[str] = None
    industry_specific_skills: List[str] = None
    
    # Custom role fields
    target_job_titles: List[str] = None
    required_skills: List[str] = None
    preferred_background: List[str] = None
    role_exclusions: List[str] = None
    role_description: str = ""
    
    def __post_init__(self):
        """Initialize empty lists if None."""
        if self.core_role_variations is None:
            self.core_role_variations = []
        if self.industry_specific_skills is None:
            self.industry_specific_skills = []
        if self.target_job_titles is None:
            self.target_job_titles = []
        if self.required_skills is None:
            self.required_skills = []
        if self.preferred_background is None:
            self.preferred_background = []
        if self.role_exclusions is None:
            self.role_exclusions = []

class AdaptiveRoleMatcher:
    """
    Handles adaptive role matching for both core and custom roles.
    """
    
    def __init__(self):
        # Core role patterns (existing system)
        self.core_roles = {
            'sales': {
                'patterns': ['sales', 'sdr', 'bdr', 'account executive', 'sales representative'],
                'exclusions': ['vp', 'director', 'head of', 'cto', 'chief'],
                'min_role_score': 5.0,
                'min_total_score': 8.0
            },
            'customer_success': {
                'patterns': ['customer success', 'csm', 'implementation', 'onboarding'],
                'exclusions': ['vp', 'director', 'head of'],
                'min_role_score': 5.0,
                'min_total_score': 8.0
            },
            'engineering': {
                'patterns': ['software engineer', 'developer', 'engineer', 'programmer'],
                'exclusions': ['vp', 'director', 'head of', 'cto', 'chief'],
                'min_role_score': 5.0,
                'min_total_score': 8.0
            },
            'data_science': {
                'patterns': ['data scientist', 'data analyst', 'analytics', 'machine learning'],
                'exclusions': ['vp', 'director', 'head of'],
                'min_role_score': 3.0,
                'min_total_score': 6.0
            }
        }
        
        # Industry-specific role mappings
        self.industry_roles = {
            'fashion': {
                'designer': ['fashion designer', 'apparel designer', 'textile designer', 'product designer'],
                'creative': ['creative director', 'art director', 'design manager'],
                'production': ['production manager', 'sourcing manager', 'quality control']
            },
            'fintech': {
                'compliance': ['compliance officer', 'regulatory specialist', 'risk manager'],
                'product': ['product manager', 'product owner', 'business analyst'],
                'engineering': ['software engineer', 'data engineer', 'devops engineer']
            },
            'gaming': {
                'design': ['game designer', 'level designer', 'ui/ux designer'],
                'art': ['concept artist', '3d artist', 'character artist'],
                'engineering': ['game developer', 'unity developer', 'unreal developer']
            }
        }
    
    def create_role_criteria(self, job_data: Dict) -> RoleCriteria:
        """Create role criteria from job description form data."""
        
        # Parse arrays from form data
        def parse_array(field: str) -> List[str]:
            value = job_data.get(field, '')
            if not value:
                return []
            # Handle both comma-separated and newline-separated
            items = re.split(r'[,;\n]', value)
            return [item.strip() for item in items if item.strip()]
        
        return RoleCriteria(
            role_name=job_data.get('jobTitle', ''),
            role_category=job_data.get('roleCategory', ''),
            industry_context=job_data.get('industryContext', ''),
            
            # Core role fields
            core_role_variations=parse_array('coreRoleVariations'),
            industry_specific_skills=parse_array('industrySpecificSkills'),
            
            # Custom role fields
            target_job_titles=parse_array('targetJobTitles'),
            required_skills=parse_array('requiredSkills'),
            preferred_background=parse_array('preferredBackground'),
            role_exclusions=parse_array('roleExclusions'),
            role_description=job_data.get('roleDescription', '')
        )
    
    def get_matching_criteria(self, role_criteria: RoleCriteria) -> Dict:
        """
        Generate matching criteria based on role type.
        Returns a dictionary that can be used by the main matcher.
        """
        
        if role_criteria.role_category == 'core':
            return self._get_core_role_criteria(role_criteria)
        elif role_criteria.role_category == 'custom':
            return self._get_custom_role_criteria(role_criteria)
        elif role_criteria.role_category == 'hybrid':
            return self._get_hybrid_role_criteria(role_criteria)
        else:
            # Fallback to auto-detection
            return self._auto_detect_role_criteria(role_criteria)
    
    def _get_core_role_criteria(self, role_criteria: RoleCriteria) -> Dict:
        """Generate criteria for core roles using existing patterns."""
        
        role_name_lower = role_criteria.role_name.lower()
        
        # Find matching core role
        core_role = None
        for role_key, role_data in self.core_roles.items():
            if any(pattern in role_name_lower for pattern in role_data['patterns']):
                core_role = role_data
                break
        
        if not core_role:
            # Default to generic criteria
            core_role = {
                'patterns': [role_name_lower],
                'exclusions': ['vp', 'director', 'head of', 'cto', 'chief'],
                'min_role_score': 3.0,
                'min_total_score': 6.0
            }
        
        # Build enhanced patterns with user variations
        patterns = core_role['patterns'].copy()
        if role_criteria.core_role_variations:
            patterns.extend([var.lower() for var in role_criteria.core_role_variations])
        
        # Build exclusions
        exclusions = core_role['exclusions'].copy()
        if role_criteria.industry_context:
            # Add industry-specific exclusions
            industry_exclusions = self._get_industry_exclusions(role_criteria.industry_context)
            exclusions.extend(industry_exclusions)
        
        return {
            'role_patterns': patterns,
            'role_exclusions': exclusions,
            'min_role_score': core_role['min_role_score'],
            'min_total_score': core_role['min_total_score'],
            'industry_skills': role_criteria.industry_specific_skills,
            'role_type': 'core'
        }
    
    def _get_custom_role_criteria(self, role_criteria: RoleCriteria) -> Dict:
        """Generate criteria for custom/niche roles."""
        
        # Build patterns from target job titles
        patterns = []
        if role_criteria.target_job_titles:
            patterns.extend([title.lower() for title in role_criteria.target_job_titles])
        else:
            # Fallback to role name
            patterns.append(role_criteria.role_name.lower())
        
        # Add industry-specific patterns
        if role_criteria.industry_context:
            industry_patterns = self._get_industry_patterns(role_criteria.industry_context, role_criteria.role_name)
            patterns.extend(industry_patterns)
        
        # Build exclusions
        exclusions = ['vp', 'director', 'head of', 'cto', 'chief']  # Default exclusions
        if role_criteria.role_exclusions:
            exclusions.extend([excl.lower() for excl in role_criteria.role_exclusions])
        
        return {
            'role_patterns': patterns,
            'role_exclusions': exclusions,
            'required_skills': role_criteria.required_skills,
            'preferred_background': role_criteria.preferred_background,
            'min_role_score': 2.0,  # Lower threshold for custom roles
            'min_total_score': 5.0,
            'role_type': 'custom',
            'role_description': role_criteria.role_description
        }
    
    def _get_hybrid_role_criteria(self, role_criteria: RoleCriteria) -> Dict:
        """Generate criteria for hybrid roles (combination of core + custom)."""
        
        # Start with core role criteria
        core_criteria = self._get_core_role_criteria(role_criteria)
        
        # Enhance with custom elements
        if role_criteria.required_skills:
            core_criteria['required_skills'] = role_criteria.required_skills
        
        if role_criteria.preferred_background:
            core_criteria['preferred_background'] = role_criteria.preferred_background
        
        core_criteria['role_type'] = 'hybrid'
        
        return core_criteria
    
    def _auto_detect_role_criteria(self, role_criteria: RoleCriteria) -> Dict:
        """Auto-detect role criteria when category is not specified."""
        
        role_name_lower = role_criteria.role_name.lower()
        
        # Try to match against core roles first
        for role_key, role_data in self.core_roles.items():
            if any(pattern in role_name_lower for pattern in role_data['patterns']):
                return self._get_core_role_criteria(role_criteria)
        
        # If no core match, treat as custom
        return self._get_custom_role_criteria(role_criteria)
    
    def _get_industry_patterns(self, industry: str, role_name: str) -> List[str]:
        """Get industry-specific role patterns."""
        
        industry_lower = industry.lower()
        role_lower = role_name.lower()
        
        if industry_lower in self.industry_roles:
            industry_roles = self.industry_roles[industry_lower]
            
            # Find matching role category
            for category, patterns in industry_roles.items():
                if category in role_lower or any(pattern in role_lower for pattern in patterns):
                    return patterns
        
        return []
    
    def _get_industry_exclusions(self, industry: str) -> List[str]:
        """Get industry-specific exclusions."""
        
        industry_lower = industry.lower()
        
        # Industry-specific exclusions
        exclusions = {
            'fashion': ['buyer', 'merchandiser', 'retail associate'],
            'fintech': ['teller', 'banker', 'financial advisor'],
            'gaming': ['game tester', 'qa tester', 'community manager'],
            'healthcare': ['nurse', 'doctor', 'physician', 'medical assistant']
        }
        
        return exclusions.get(industry_lower, [])
    
    def enhance_matching_weights(self, role_criteria: RoleCriteria) -> Dict[str, float]:
        """Generate enhanced scoring weights based on role criteria."""
        
        base_weights = {
            'skill_match': 0.3,
            'role_match': 0.25,
            'company_match': 0.2,
            'industry_match': 0.15,
            'seniority_bonus': 0.1
        }
        
        if role_criteria.role_category == 'custom':
            # Custom roles rely more on skills and background
            base_weights.update({
                'skill_match': 0.4,
                'role_match': 0.2,
                'company_match': 0.15,
                'industry_match': 0.15,
                'seniority_bonus': 0.1
            })
        
        elif role_criteria.role_category == 'hybrid':
            # Hybrid roles balance skills and role matching
            base_weights.update({
                'skill_match': 0.35,
                'role_match': 0.3,
                'company_match': 0.2,
                'industry_match': 0.1,
                'seniority_bonus': 0.05
            })
        
        return base_weights
    
    def validate_role_criteria(self, role_criteria: RoleCriteria) -> Tuple[bool, List[str]]:
        """Validate role criteria and return errors if any."""
        
        errors = []
        
        if not role_criteria.role_name:
            errors.append("Role name is required")
        
        if role_criteria.role_category == 'custom':
            if not role_criteria.target_job_titles and not role_criteria.required_skills:
                errors.append("Custom roles require either target job titles or required skills")
        
        return len(errors) == 0, errors

# Example usage and testing
if __name__ == "__main__":
    matcher = AdaptiveRoleMatcher()
    
    # Test with a fashion designer role
    fashion_designer_data = {
        'jobTitle': 'Fashion Designer',
        'roleCategory': 'custom',
        'industryContext': 'Fashion',
        'targetJobTitles': 'Fashion Designer, Apparel Designer, Textile Designer',
        'requiredSkills': 'Adobe Creative Suite, Fashion Design, Pattern Making',
        'preferredBackground': 'Fashion companies, Design agencies, Luxury brands',
        'roleExclusions': 'CEO, CFO, VP Marketing',
        'roleDescription': 'Creative designer for luxury fashion brand'
    }
    
    criteria = matcher.create_role_criteria(fashion_designer_data)
    matching_criteria = matcher.get_matching_criteria(criteria)
    weights = matcher.enhance_matching_weights(criteria)
    
    print("🎨 Fashion Designer Role Criteria:")
    print(json.dumps(matching_criteria, indent=2))
    print("\n⚖️ Enhanced Weights:")
    print(json.dumps(weights, indent=2))
