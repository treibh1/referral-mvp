import pandas as pd
import json
from collections import Counter
import re
from rapidfuzz import process, fuzz
from typing import Dict, List, Tuple, Optional, Set
import time
from location_hierarchy import location_hierarchy, LocationMatchType

try:
	from bright_data_enricher import BrightDataEnricher
	_HAS_BRIGHT = True
except Exception:
	_HAS_BRIGHT = False

class UnifiedReferralMatcher:
    """
    Unified system for matching job descriptions to potential referral candidates.
    Consolidates all matching logic into one robust, configurable system.
    """
    
    def __init__(self, contacts_file: str = "enhanced_tagged_contacts.csv"):
        """Initialize the matcher with contacts and enrichment data."""
        print("🚀 Initializing Unified Referral Matcher...")
        
        # Load contacts
        self.df = pd.read_csv(contacts_file)
        print(f"📊 Loaded {len(self.df)} contacts from {contacts_file}")
        
        # Load enrichment data
        self._load_enrichment_data()
        
        # Pre-defined scoring weights (consistent across all jobs)
        self.scoring_weights = {
            'skill_match': 3.0,      # Skills are most important
            'role_match': 5.0,       # Role matching is critical
            'company_match': 2.0,    # Company matching is good
            'industry_match': 1.0,   # Industry matching is nice to have
            'seniority_bonus': 1.5,  # Seniority alignment bonus
            'exact_role_bonus': 3.0, # Bonus for exact role match
            'company_preference_bonus': 5.0,  # Bonus for preferred companies
            'industry_preference_bonus': 3.0, # Bonus for preferred industries
            'location_match': 2.0    # Location matching bonus
        }
        
        print("✅ Matcher initialized successfully")
    
    def _load_enrichment_data(self):
        """Load all enrichment JSON files."""
        try:
            with open("role_enrichment.json", "r") as f:
                self.role_enrichment = json.load(f)
            
            with open("title_aliases.json", "r") as f:
                self.title_aliases = json.load(f)
            
            with open("company_industry_tags_usev2.json", "r") as f:
                self.company_industry_tags = json.load(f)
            
            # Extract master skill/platform lists
            self.all_skills = set()
            self.all_platforms = set()
            for entry in self.role_enrichment.values():
                self.all_skills.update(entry.get("skills", []))
                self.all_platforms.update(entry.get("platforms", []))
            
            print(f"📊 Loaded {len(self.all_skills)} skills and {len(self.all_platforms)} platforms")
            
        except FileNotFoundError as e:
            print(f"❌ Error loading enrichment data: {e}")
            raise
    
    def extract_job_requirements(self, jd_text: str) -> Dict:
        """
        Extract all relevant information from a job description.
        Returns a structured dict with skills, platforms, role, company, etc.
        """
        jd_text_lower = jd_text.lower()
        
        # Enhanced role detection with confidence scoring
        role_matches = self._detect_role_with_confidence(jd_text_lower)
        detected_role = role_matches['primary_role']
        role_confidence = role_matches['confidence']
        suggested_roles = role_matches['suggestions']
        
        # Extract skills with role-aware prioritization
        matched_skills = []
        role_skills = set()
        
        # If we detected a role, get its skills first
        if detected_role:
            role_key = f"any:{detected_role}"
            if role_key in self.role_enrichment:
                role_skills = set(self.role_enrichment[role_key].get("skills", []))
        
        # Extract skills with role-aware filtering
        for skill in self.all_skills:
            skill_lower = skill.lower()
            
            # Check if skill appears in job description
            skill_found = False
            if skill_lower in jd_text_lower:
                skill_found = True
            elif skill_lower.replace(' ', '') in jd_text_lower.replace(' ', ''):
                skill_found = True
            elif any(word in jd_text_lower for word in skill_lower.split()):
                skill_found = True
            
            if skill_found:
                # If we have a detected role, prioritize its skills and limit others
                if detected_role and skill in role_skills:
                    matched_skills.insert(0, skill)  # Add role skills to beginning
                elif detected_role:
                    # For non-role skills, be very selective
                    # Only add if we don't have enough role skills yet
                    role_skills_found = len([s for s in matched_skills if s in role_skills])
                    if role_skills_found < 3:  # Only add non-role skills if we have less than 3 role skills
                        matched_skills.append(skill)
                else:
                    # No role detected, add all skills
                    matched_skills.append(skill)
        
        # Limit total skills to prevent overwhelming matches
        if detected_role:
            # Keep all role skills, but limit non-role skills to prevent overwhelming
            role_skills_found = [s for s in matched_skills if s in role_skills]
            non_role_skills = [s for s in matched_skills if s not in role_skills][:10]  # Increased limit to 10 non-role skills
            matched_skills = role_skills_found + non_role_skills
        
        # Extract platforms (removed - was adding noise)
        matched_platforms = []
        

        
        # Detect company with context awareness
        company_variations = {
            'freshworks': ['freshworks', 'fresh works', 'freshworks logo'],
            'zendesk': ['zendesk', 'zen desk'],
            'intercom': ['intercom'],
            'salesforce': ['salesforce', 'sales force'],
            'hubspot': ['hubspot', 'hub spot'],
            'stripe': ['stripe'],
            'figma': ['figma'],
            'mongodb': ['mongodb', 'mongo db'],
            'lever': ['lever'],
            'zenefits': ['zenefits'],
            'ramp': ['ramp'],
            'synthesia': ['synthesia']
        }
        
        detected_company = None
        
        # First, look for hiring company context (e.g., "at Company", "join Company", "Company is hiring")
        hiring_company_indicators = [
            'at ', 'join ', ' is hiring', ' is looking for', ' is seeking',
            'we are ', 'our team', 'our company', 'our organization'
        ]
        
        for company, variations in company_variations.items():
            for variation in variations:
                for indicator in hiring_company_indicators:
                    if f"{indicator}{variation}" in jd_text_lower:
                        detected_company = company
                        break
                if detected_company:
                    break
            if detected_company:
                break
        
        # If no hiring company found, look for any company mention (but this is less reliable)
        if not detected_company:
            for company, variations in company_variations.items():
                if any(variation in jd_text_lower for variation in variations):
                    detected_company = company
                    break
        

        
        # Get company industry tags
        company_tags = self.company_industry_tags.get(detected_company, []) if detected_company else []
        
        # Detect seniority level
        seniority_indicators = {
            'senior': ['senior', 'sr.', 'sr ', 'experienced', 'expert'],
            'lead': ['lead', 'principal', 'staff'],
            'director': ['director', 'head of', 'vp', 'vice president'],
            'manager': ['manager', 'management'],
            'junior': ['junior', 'jr.', 'jr ', 'entry', 'associate']
        }
        
        detected_seniority = None
        for level, indicators in seniority_indicators.items():
            if any(indicator in jd_text_lower for indicator in indicators):
                detected_seniority = level
                break
        
        # Convert detected role to canonical form using title_aliases
        canonical_role = detected_role
        if detected_role:
            # Find the canonical form for this role
            for alias, canonical in self.title_aliases.items():
                if alias.lower() == detected_role.lower():
                    canonical_role = canonical
                    break
        
        return {
            'skills': matched_skills,
            'platforms': matched_platforms,  # Kept for compatibility but always empty
            'role': canonical_role,  # Use canonical form
            'role_confidence': role_confidence,
            'suggested_roles': suggested_roles,
            'company': detected_company,
            'company_tags': company_tags,
            'seniority': detected_seniority,
            'raw_text': jd_text
        }
    
    def score_contact(self, contact_row: pd.Series, job_reqs: Dict, preferred_companies: List[str] = None, preferred_industries: List[str] = None, job_location: str = None, job_title: str = None, alternative_titles: List[str] = None) -> Dict:
        """
        Score a single contact against job requirements.
        Returns detailed scoring breakdown.
        
        Args:
            contact_row: Contact data row
            job_reqs: Job requirements
            preferred_companies: List of preferred company names for bonus scoring
            preferred_industries: List of preferred industries for bonus scoring
        """
        # Extract contact data
        contact_skills = eval(contact_row.get("skills_tag", "[]"))
        contact_title = str(contact_row.get("Position", "")).lower()
        contact_company = str(contact_row.get("Company", "")).lower().strip()
        contact_company_tags = eval(contact_row.get("company_industry_tags", "[]"))
        contact_seniority = str(contact_row.get("seniority_tag", "")).lower()
        contact_function = str(contact_row.get("function_tag", "")).lower()
        
        # Initialize scoring components
        scores = {
            'skill_score': 0,
            'role_score': 0,
            'company_score': 0,
            'industry_score': 0,
            'seniority_bonus': 0,
            'location_score': 0,
            'total_score': 0,
            'tagged_boost': 0
        }
        
        # Skill matching
        skill_matches = set(contact_skills) & set(job_reqs['skills'])
        scores['skill_score'] = len(skill_matches) * self.scoring_weights['skill_match']
        
        # Role matching with enhanced logic for job title and alternative titles
        matched_contact_role = self._match_title_alias(contact_title)
        role_score = 0
        
        # Check against primary job title (highest priority)
        if job_title:
            job_title_lower = job_title.lower()
            matched_job_role = self._match_title_alias(job_title_lower)  # Convert job title to canonical form
            
            # For SDR roles, be very strict about what constitutes a good match
            if matched_job_role == 'sdr':
                # Check if contact has an exact SDR title
                exact_sdr_titles = [
                    'sales development representative',
                    'sdr',
                    'strategic sales development representative',
                    'outbound sales development representative',
                    'inbound sales development representative',
                    'senior strategic sdr'
                ]
                
                contact_title_lower = contact_title.lower()
                is_exact_sdr = any(exact_title in contact_title_lower for exact_title in exact_sdr_titles)
                
                if is_exact_sdr:
                    role_score = self.scoring_weights['role_match'] + self.scoring_weights['exact_role_bonus'] + 3.0  # Maximum bonus for exact SDR
                elif matched_contact_role == 'sdr':
                    role_score = self.scoring_weights['role_match'] + 1.0  # Moderate bonus for canonical SDR match
                elif matched_contact_role and self._fuzzy_role_match(matched_contact_role, job_title_lower):
                    role_score = self.scoring_weights['role_match'] * 0.5  # Reduced bonus for fuzzy SDR match
                else:
                    role_score = 0  # No credit for non-SDR roles
            else:
                # For non-SDR roles, use the original logic
                if matched_contact_role and matched_contact_role == matched_job_role:
                    role_score = self.scoring_weights['role_match'] + self.scoring_weights['exact_role_bonus'] + 2.0
                elif matched_contact_role and self._fuzzy_role_match(matched_contact_role, job_title_lower):
                    role_score = self.scoring_weights['role_match'] + 1.0
        
        # Check against alternative titles (lower priority)
        if alternative_titles and role_score == 0:
            for alt_title in alternative_titles:
                alt_title_lower = alt_title.lower()
                if matched_contact_role and matched_contact_role == alt_title_lower:
                    role_score = self.scoring_weights['role_match'] + 1.0  # Good bonus for exact alternative title match
                    break
                elif matched_contact_role and self._fuzzy_role_match(matched_contact_role, alt_title_lower):
                    role_score = self.scoring_weights['role_match'] * 0.6  # Moderate bonus for fuzzy alternative title match
                    break
        
        # Fallback to original logic if no manual titles provided
        if not job_title and not alternative_titles:
            if matched_contact_role and matched_contact_role == job_reqs['role']:
                role_score = self.scoring_weights['role_match'] + self.scoring_weights['exact_role_bonus']
            elif matched_contact_role and self._fuzzy_role_match(matched_contact_role, job_reqs['role']):
                role_score = self.scoring_weights['role_match'] + 1.0  # High bonus for fuzzy match
            elif matched_contact_role:
                # Only give partial credit for related roles, not all roles
                related_roles = {
                    'payroll specialist': ['accountant', 'financial analyst'],
                    'accountant': ['payroll specialist', 'financial analyst'],
                    'financial analyst': ['accountant', 'payroll specialist'],
                    'software engineer': ['data scientist', 'product manager'],
                    'data scientist': ['software engineer'],
                    'product manager': ['software engineer'],
                    'account executive': ['customer success manager', 'marketing manager'],
                    'customer success manager': ['account executive', 'marketing manager'],
                    'marketing manager': ['account executive', 'customer success manager'],
                    'sales engineer': ['solutions architect', 'pre-sales engineer', 'technical sales'],
                    'solutions architect': ['sales engineer', 'pre-sales engineer', 'technical sales'],
                                        'pre-sales engineer': ['sales engineer', 'solutions architect', 'technical sales'],
                    'technical sales': ['sales engineer', 'solutions architect', 'pre-sales engineer'],
                    'sdr': ['bdr'],  # SDR and BDR are related (using canonical forms)
                    'bdr': ['sdr']   # BDR and SDR are related (using canonical forms)
                }
                
                if (job_reqs['role'] in related_roles and 
                    matched_contact_role in related_roles[job_reqs['role']]):
                    role_score = self.scoring_weights['role_match'] * 0.4  # Related role
                else:
                    role_score = 0  # No credit for unrelated roles
        
        scores['role_score'] = role_score
        
        # SENIORITY PENALTY: Exclude managers when looking for individual contributors
        if job_reqs['role'] == 'sdr':
            # Check if contact is a manager or senior position (not suitable for entry-level SDR)
            manager_indicators = [
                'head of', 'manager', 'director', 'vp', 'vice president', 'senior vice president',
                'regional vice president', 'senior manager', 'principal', 'lead', 'team lead',
                'head of sales development', 'manager, sales development', 'sales development manager',
                'manager, inside sales business development', 'senior manager, sales'
            ]
            contact_title_lower = contact_title.lower()
            
            for indicator in manager_indicators:
                if indicator in contact_title_lower:
                    # Heavy penalty for managers when looking for entry-level SDRs
                    role_score = -50
                    scores['role_score'] = role_score
                    break
        
        # Company matching and similarity scoring
        company_similarity_score = 0
        
        # CRITICAL: Exclude candidates from the same company as the job posting
        if contact_company == job_reqs['company']:
            # Return a very low score to effectively exclude same-company candidates
            return {
                'skill_score': 0,
                'role_score': 0,
                'company_score': -100,  # Heavy penalty for same company
                'industry_score': 0,
                'seniority_bonus': 0,
                'location_score': 0,
                'total_score': -100,  # This will exclude them from results
                'skill_matches': [],
                'matched_role': None,
                'industry_matches': [],
                'tagged_boost': 0
            }
        
        # Company similarity scoring based on industry/domain (for different companies)
        if job_reqs['company'] and contact_company:
            # Define company similarity groups
            company_similarity_groups = {
                # Customer Service/Support Tech
                'zendesk': ['intercom', 'freshdesk', 'freshworks', 'helpscout', 'gorgias', 'klaviyo'],
                'intercom': ['zendesk', 'freshdesk', 'freshworks', 'helpscout', 'gorgias', 'klaviyo'],
                'freshdesk': ['zendesk', 'intercom', 'freshworks', 'helpscout', 'gorgias', 'klaviyo'],
                'freshworks': ['zendesk', 'intercom', 'freshdesk', 'helpscout', 'gorgias', 'klaviyo'],
                'helpscout': ['zendesk', 'intercom', 'freshdesk', 'freshworks', 'gorgias', 'klaviyo'],
                'gorgias': ['zendesk', 'intercom', 'freshdesk', 'freshworks', 'helpscout', 'klaviyo'],
                'klaviyo': ['zendesk', 'intercom', 'freshdesk', 'freshworks', 'helpscout', 'gorgias'],
                
                # CRM/Sales Tech
                'salesforce': ['hubspot', 'pipedrive', 'close', 'outreach', 'salesloft', 'apollo'],
                'hubspot': ['salesforce', 'pipedrive', 'close', 'outreach', 'salesloft', 'apollo'],
                'pipedrive': ['salesforce', 'hubspot', 'close', 'outreach', 'salesloft', 'apollo'],
                'close': ['salesforce', 'hubspot', 'pipedrive', 'outreach', 'salesloft', 'apollo'],
                'outreach': ['salesforce', 'hubspot', 'pipedrive', 'close', 'salesloft', 'apollo'],
                'salesloft': ['salesforce', 'hubspot', 'pipedrive', 'close', 'outreach', 'apollo'],
                'apollo': ['salesforce', 'hubspot', 'pipedrive', 'close', 'outreach', 'salesloft'],
                
                # Marketing Tech
                'mailchimp': ['constant contact', 'sendgrid', 'activecampaign', 'convertkit', 'drip'],
                'constant contact': ['mailchimp', 'sendgrid', 'activecampaign', 'convertkit', 'drip'],
                'sendgrid': ['mailchimp', 'constant contact', 'activecampaign', 'convertkit', 'drip'],
                'activecampaign': ['mailchimp', 'constant contact', 'sendgrid', 'convertkit', 'drip'],
                'convertkit': ['mailchimp', 'constant contact', 'sendgrid', 'activecampaign', 'drip'],
                'drip': ['mailchimp', 'constant contact', 'sendgrid', 'activecampaign', 'convertkit'],
                
                # Fintech/Payments
                'stripe': ['square', 'paypal', 'adyen', 'braintree', 'plaid', 'robinhood'],
                'square': ['stripe', 'paypal', 'adyen', 'braintree', 'plaid', 'robinhood'],
                'paypal': ['stripe', 'square', 'adyen', 'braintree', 'plaid', 'robinhood'],
                'adyen': ['stripe', 'square', 'paypal', 'braintree', 'plaid', 'robinhood'],
                'braintree': ['stripe', 'square', 'paypal', 'adyen', 'plaid', 'robinhood'],
                'plaid': ['stripe', 'square', 'paypal', 'adyen', 'braintree', 'robinhood'],
                'robinhood': ['stripe', 'square', 'paypal', 'adyen', 'braintree', 'plaid'],
                
                # Cloud/Infrastructure
                'aws': ['azure', 'google cloud', 'heroku', 'vercel', 'netlify', 'digitalocean'],
                'azure': ['aws', 'google cloud', 'heroku', 'vercel', 'netlify', 'digitalocean'],
                'google cloud': ['aws', 'azure', 'heroku', 'vercel', 'netlify', 'digitalocean'],
                'heroku': ['aws', 'azure', 'google cloud', 'vercel', 'netlify', 'digitalocean'],
                'vercel': ['aws', 'azure', 'google cloud', 'heroku', 'netlify', 'digitalocean'],
                'netlify': ['aws', 'azure', 'google cloud', 'heroku', 'vercel', 'digitalocean'],
                'digitalocean': ['aws', 'azure', 'google cloud', 'heroku', 'vercel', 'netlify'],
                
                # Development Tools
                'github': ['gitlab', 'bitbucket', 'atlassian', 'gitkraken', 'sourcetree'],
                'gitlab': ['github', 'bitbucket', 'atlassian', 'gitkraken', 'sourcetree'],
                'bitbucket': ['github', 'gitlab', 'atlassian', 'gitkraken', 'sourcetree'],
                'atlassian': ['github', 'gitlab', 'bitbucket', 'gitkraken', 'sourcetree'],
                'gitkraken': ['github', 'gitlab', 'bitbucket', 'atlassian', 'sourcetree'],
                'sourcetree': ['github', 'gitlab', 'bitbucket', 'atlassian', 'gitkraken'],
                
                # Analytics/Data
                'google': ['facebook', 'amazon', 'microsoft', 'apple', 'netflix', 'spotify'],
                'facebook': ['google', 'amazon', 'microsoft', 'apple', 'netflix', 'spotify'],
                'amazon': ['google', 'facebook', 'microsoft', 'apple', 'netflix', 'spotify'],
                'microsoft': ['google', 'facebook', 'amazon', 'apple', 'netflix', 'spotify'],
                'apple': ['google', 'facebook', 'amazon', 'microsoft', 'netflix', 'spotify'],
                'netflix': ['google', 'facebook', 'amazon', 'microsoft', 'apple', 'spotify'],
                'spotify': ['google', 'facebook', 'amazon', 'microsoft', 'apple', 'netflix']
            }
            
            # Check for company similarity
            hiring_company = job_reqs['company'].lower()
            candidate_company = contact_company.lower()
            
            if hiring_company in company_similarity_groups:
                if candidate_company in company_similarity_groups[hiring_company]:
                    company_similarity_score = self.scoring_weights['company_match'] * 0.8  # High similarity bonus
                elif candidate_company in company_similarity_groups:
                    # Check if they're in the same group
                    for group_company, similar_companies in company_similarity_groups.items():
                        if candidate_company in similar_companies and hiring_company in similar_companies:
                            company_similarity_score = self.scoring_weights['company_match'] * 0.6  # Medium similarity bonus
                            break
        
        scores['company_score'] = company_similarity_score
        
        # Industry tag matching with enhanced scoring
        industry_matches = set(contact_company_tags) & set(job_reqs['company_tags'])
        industry_score = len(industry_matches) * self.scoring_weights['industry_match']
        
        # Additional industry similarity bonus
        if job_reqs['company'] and contact_company:
            # Define industry similarity bonuses
            industry_similarity_bonus = 0
            
            # Customer Service/Support industry bonus
            support_industries = ['customer service', 'support tech', 'customer experience', 'saas']
            if any(industry in contact_company_tags for industry in support_industries) and job_reqs['role'] in ['customer success manager', 'account executive']:
                industry_similarity_bonus += 1.0
            
            # SaaS industry bonus
            saas_industries = ['saas', 'software', 'tech', 'enterprise software']
            if any(industry in contact_company_tags for industry in saas_industries):
                industry_similarity_bonus += 0.5
            
            # Fintech industry bonus
            fintech_industries = ['fintech', 'payment tech', 'financial services']
            if any(industry in contact_company_tags for industry in fintech_industries) and job_reqs['role'] in ['accountant', 'financial analyst']:
                industry_similarity_bonus += 1.0
            
            industry_score += industry_similarity_bonus
        
        scores['industry_score'] = industry_score
        
        # Seniority bonus
        if (job_reqs['seniority'] and contact_seniority and 
            job_reqs['seniority'] in contact_seniority):
            scores['seniority_bonus'] = self.scoring_weights['seniority_bonus']
        
        # Company preference bonus
        company_preference_bonus = 0
        if preferred_companies:
            for preferred_company in preferred_companies:
                if preferred_company.lower() in contact_company:
                    company_preference_bonus += self.scoring_weights.get('company_preference_bonus', 5.0)
                    break
        
        # Industry preference bonus
        industry_preference_bonus = 0
        if preferred_industries:
            for preferred_industry in preferred_industries:
                if preferred_industry.lower() in [tag.lower() for tag in contact_company_tags]:
                    industry_preference_bonus += self.scoring_weights.get('industry_preference_bonus', 3.0)
                    break
        
        # Location scoring with hierarchy logic
        if job_location and job_location.lower() != 'remote':
            contact_location = str(contact_row.get('location_raw', ''))
            if contact_location and contact_location != 'nan':
                # Use location hierarchy for intelligent matching
                location_match = location_hierarchy.match_locations(job_location, contact_location)
                scores['location_score'] = location_match.score
                scores['location_match_details'] = location_match.details
                scores['location_match_type'] = location_match.match_type.value
            else:
                scores['location_score'] = 0.0
                scores['location_match_details'] = "No contact location data"
                scores['location_match_type'] = LocationMatchType.NO_MATCH.value
        elif job_location and job_location.lower() == 'remote':
            # For remote jobs, location is less important but still give some credit for having location data
            contact_location = str(contact_row.get('location_raw', ''))
            if contact_location and contact_location != 'nan':
                scores['location_score'] = self.scoring_weights['location_match'] * 0.5  # Small bonus for remote jobs
                scores['location_match_details'] = "Remote job - location data available"
                scores['location_match_type'] = "remote"
            else:
                scores['location_score'] = 0.0
                scores['location_match_details'] = "Remote job - no location data"
                scores['location_match_type'] = "remote_no_data"
        else:
            scores['location_score'] = 0.0
            scores['location_match_details'] = "No job location specified"
            scores['location_match_type'] = LocationMatchType.NO_MATCH.value
        
        # Tagged contact boost (from gamification system)
        contact_name = str(contact_row.get('First Name', '')) + ' ' + str(contact_row.get('Last Name', ''))
        tagged_boost = self._get_tagged_contact_boost(contact_name)
        scores['tagged_boost'] = tagged_boost
        
        # Calculate total score (EXCLUDING location - location is only used for filtering/organizing)
        scores['total_score'] = sum([
            scores['skill_score'],
            scores['role_score'],
            scores['company_score'],
            scores['industry_score'],
            scores['seniority_bonus'],
            # scores['location_score'],  # REMOVED - location should not affect scoring
            company_preference_bonus,
            industry_preference_bonus,
            tagged_boost
        ])
        
        # Add match details for debugging
        scores['skill_matches'] = list(skill_matches)
        scores['matched_role'] = matched_contact_role
        scores['industry_matches'] = list(industry_matches)
        
        return scores
    
    def _match_title_alias(self, title: str, threshold: int = 85) -> Optional[str]:
        """Fuzzy match title to canonical role."""
        title = title.lower().strip()
        best_match = process.extractOne(title, self.title_aliases.keys())
        if best_match and best_match[1] >= threshold:
            return self.title_aliases[best_match[0]]
        return None
    
    def _fuzzy_role_match(self, contact_role: str, target_role: str) -> bool:
        """
        Check if two roles match using fuzzy string matching.
        """
        if not contact_role or not target_role:
            return False
        
        # Direct match
        if contact_role == target_role:
            return True
        
        # Check for partial matches
        contact_words = set(contact_role.split())
        target_words = set(target_role.split())
        
        # If there's significant word overlap, consider it a match
        if contact_words & target_words:  # Intersection
            overlap_ratio = len(contact_words & target_words) / max(len(contact_words), len(target_words))
            return overlap_ratio >= 0.5  # 50% word overlap threshold
        
        return False
    
    def _detect_role_with_confidence(self, jd_text_lower: str) -> Dict:
        """
        Enhanced role detection with confidence scoring and suggestions.
        Prioritizes job titles over content analysis.
        """
        # Method 1: Direct title matching with HIGH PRIORITY
        role_counter = Counter()
        title_matches = []
        
        # Look for job titles in the text
        for alias, canonical in self.title_aliases.items():
            if alias.lower() in jd_text_lower:
                role_counter[canonical] += 3  # Give title matches 3x weight
                title_matches.append(alias)
        
        # Method 2: Look for common job title patterns
        title_patterns = {
            'sales development representative': ['sales development representative', 'sdr', 'sales development rep'],
            'business development representative': ['business development representative', 'bdr', 'business development rep'],
            'sales representative': ['sales representative', 'sales rep', 'enterprise sales', 'account executive'],
            'account executive': ['account executive', 'ae', 'enterprise account executive'],
            'customer success manager': ['customer success manager', 'csm', 'customer success'],
            'software engineer': ['software engineer', 'developer', 'engineer', 'programmer'],
            'product manager': ['product manager', 'pm', 'product owner', 'senior product manager', 'product lead'],
            'data scientist': ['data scientist', 'machine learning engineer', 'ml engineer', 'ai engineer', 'machine learning scientist'],
            'marketing manager': ['marketing manager', 'marketing specialist', 'senior marketing manager', 'marketing lead', 'digital marketing manager'],
            'payroll specialist': ['payroll specialist', 'payroll administrator'],
            'accountant': ['accountant', 'senior accountant', 'staff accountant'],
            'financial analyst': ['financial analyst', 'finance analyst'],
            'solution architect': ['solution architect', 'solutions architect', 'senior solution architect', 'senior solutions architect', 'presales solution architect', 'presales solutions architect'],
            'solution consultant': ['solution consultant', 'solutions consultant', 'solutions engineer', 'presales consultant', 'technical consultant'],
            'data engineer': ['data engineer', 'big data engineer', 'etl developer', 'data architect'],
            'devops engineer': ['devops engineer', 'site reliability engineer', 'sre'],
            'engineering manager': ['engineering manager', 'tech lead', 'technical lead', 'lead engineer'],
            'business analyst': ['business analyst', 'business systems analyst', 'functional analyst', 'senior business analyst', 'business analyst lead'],
            'data analyst': ['data analyst', 'business intelligence analyst', 'bi analyst', 'senior data analyst', 'data analyst lead', 'business intelligence analyst'],
            'quality assurance': ['qa engineer', 'test engineer', 'quality assurance engineer', 'software tester'],
            'research scientist': ['research scientist', 'applied scientist', 'machine learning scientist', 'ai researcher'],
            # Finance and GTM roles
            'financial planning & analysis manager': ['financial planning & analysis manager', 'fp&a manager', 'financial planning manager', 'fp&a analyst'],
            'revenue operations manager': ['revenue operations manager', 'revops manager', 'revenue ops manager', 'sales operations manager'],
            'gtm finance manager': ['gtm finance manager', 'go-to-market finance manager', 'gtm financial manager'],
            'strategic finance manager': ['strategic finance manager', 'strategic financial manager', 'finance strategy manager'],
            'business finance manager': ['business finance manager', 'business financial manager', 'corporate finance manager'],
            'financial operations manager': ['financial operations manager', 'finance operations manager', 'financial ops manager'],
            'revenue strategy manager': ['revenue strategy manager', 'revenue strategy analyst', 'revenue planning manager'],
            'business intelligence manager': ['business intelligence manager', 'bi manager', 'business analytics manager'],
            'data analytics manager': ['data analytics manager', 'analytics manager', 'data analysis manager'],
            'corporate finance manager': ['corporate finance manager', 'corporate financial manager', 'corporate finance analyst'],
            # Strategy roles
            'strategy manager': ['strategy manager', 'strategic manager', 'business strategy manager'],
            'business strategy manager': ['business strategy manager', 'corporate strategy manager', 'strategic planning manager'],
            'strategic planning manager': ['strategic planning manager', 'strategy planning manager', 'strategic initiatives manager'],
            'corporate strategy manager': ['corporate strategy manager', 'corporate strategic manager', 'enterprise strategy manager'],
            'business development manager': ['business development manager', 'biz dev manager', 'business development'],
            'strategic initiatives manager': ['strategic initiatives manager', 'strategic initiatives', 'strategic projects manager'],
            'business operations manager': ['business operations manager', 'business ops manager', 'operational manager'],
            'strategic partnerships manager': ['strategic partnerships manager', 'partnerships manager', 'strategic alliances manager'],
            # Operations roles
            'operations manager': ['operations manager', 'operational manager', 'business operations manager'],
            'process improvement manager': ['process improvement manager', 'process optimization manager', 'continuous improvement manager'],
            'operational excellence manager': ['operational excellence manager', 'operational excellence', 'excellence manager'],
            'business process manager': ['business process manager', 'process manager', 'business process analyst'],
            'operations strategy manager': ['operations strategy manager', 'operational strategy manager', 'operations planning manager'],
            'operational analytics manager': ['operational analytics manager', 'operations analytics manager', 'operational intelligence manager']
        }
        
        # Check for title patterns with HIGH PRIORITY
        for role, patterns in title_patterns.items():
            for pattern in patterns:
                if pattern in jd_text_lower:
                    role_counter[role] += 5  # Give pattern matches 5x weight
                    title_matches.append(pattern)
        
        # Method 3: Content-based role detection (LOWER PRIORITY)
        content_based_roles = self._detect_role_from_content(jd_text_lower)
        
        # Combine methods with title prioritization
        all_role_scores = Counter()
        all_role_scores.update(role_counter)  # High priority titles first
        all_role_scores.update(content_based_roles)  # Lower priority content analysis
        
        if not all_role_scores:
            return {
                'primary_role': None,
                'confidence': 0.0,
                'suggestions': self._get_role_suggestions_from_content(jd_text_lower)
            }
        
        # Get top roles
        top_roles = all_role_scores.most_common(3)
        primary_role = top_roles[0][0]
        primary_score = top_roles[0][1]
        
        # Calculate confidence based on whether we found clear title matches
        if title_matches:
            # High confidence if we found explicit job titles
            confidence = min(1.0, 0.8 + (primary_score / 20))
        else:
            # Lower confidence if only content-based detection
            confidence = min(1.0, primary_score / 15)
        
        # If confidence is low, provide suggestions
        suggestions = []
        if confidence < 0.3:
            suggestions = self._get_role_suggestions_from_content(jd_text_lower)
        else:
            # Still provide top alternatives
            suggestions = [role for role, score in top_roles[1:4] if score > 0]
        
        return {
            'primary_role': primary_role,
            'confidence': round(confidence, 2),
            'suggestions': suggestions
        }
    
    def _detect_role_from_content(self, jd_text_lower: str) -> Counter:
        """
        Detect role based on job description content (skills, responsibilities, etc.)
        """
        role_scores = Counter()
        
        # Define role-specific keywords and phrases with weights
        role_keywords = {

            'sales development representative': [
                # High-weight SDR indicators (from actual job descriptions)
                ('sales development representative', 3), ('sdr', 3), ('sales development rep', 3),
                ('inbound sales development representative', 3), ('business development representative', 3), ('bdr', 3),
                # Core SDR activities (from job descriptions)
                ('qualifying leads', 3), ('prospecting', 3), ('cold calling', 3), ('outbound', 3),
                ('lead qualification', 3), ('lead generation', 3), ('setting meetings', 3),
                ('active listener', 3), ('customer requirements', 3), ('goal-oriented', 3),
                # SDR-specific skills (from job descriptions)
                ('sales calls', 2), ('email outreach', 2), ('lead nurturing', 2), ('sales pipeline', 2),
                ('working with account executives', 2), ('fast-paced', 2), ('self-starter', 2),
                # Lower-weight indicators (avoid false positives)
                ('sales', 1), ('development', 1), ('representative', 1), ('leads', 1)
            ],
            'account executive': [
                # High-weight AE indicators (very specific to AE role)
                ('account executive', 5), ('ae', 5), ('enterprise account executive', 5),
                ('quota', 4), ('booking goals', 4), ('sales cycle', 4), ('closing deals', 4),
                ('pipeline management', 4), ('revenue generation', 4), ('account plans', 4),
                ('sales methodologies', 4), ('meddic', 4), ('closing', 4), ('deals', 4),
                # Medium-weight indicators (common in AE but not exclusive)
                ('account management', 3), ('client relationship', 3), ('customer acquisition', 3),
                ('negotiation', 3), ('enterprise sales', 3), ('key accounts', 3), ('complex accounts', 3),
                ('acv', 3), ('annual contract value', 3), ('deal size', 3), ('sales process', 3),
                # Lower-weight indicators (avoid false positives)
                ('sales', 1), ('account', 1), ('executive', 1)
            ],
            'customer success manager': [
                # High-weight CSM indicators
                ('customer success', 3), ('customer retention', 3), ('customer health', 3),
                ('success metrics', 3), ('customer satisfaction', 3), ('onboarding', 3),
                # Medium-weight indicators
                ('account management', 2), ('customer experience', 2), ('support', 2),
                ('training', 2), ('customer advocacy', 2), ('renewal', 2),
                # Lower-weight indicators
                ('customer', 1), ('client', 1), ('success', 1)
            ],
            'software engineer': [
                # High-weight engineering indicators
                ('coding', 3), ('programming', 3), ('development', 3), ('engineering', 3),
                ('backend', 3), ('frontend', 3), ('fullstack', 3), ('api', 3),
                ('code review', 3), ('debugging', 3), ('testing', 3),
                # Medium-weight indicators
                ('software', 2), ('database', 2), ('algorithm', 2), ('technical', 2),
                ('architecture', 2), ('deployment', 2), ('infrastructure', 2),
                # Lower-weight indicators (avoid false positives)
                ('developer', 1), ('engineer', 1), ('programmer', 1)
            ],
            'data scientist': [
                # High-weight data science indicators
                ('machine learning', 3), ('ml', 3), ('ai', 3), ('artificial intelligence', 3),
                ('data science', 3), ('statistical analysis', 3), ('predictive modeling', 3),
                ('algorithm development', 3), ('tensorflow', 3), ('pytorch', 3),
                # Medium-weight indicators
                ('python', 2), ('r', 2), ('jupyter', 2), ('data analysis', 2),
                ('modeling', 2), ('analytics', 2), ('data mining', 2),
                # Lower-weight indicators
                ('data', 1), ('analysis', 1), ('statistics', 1)
            ],
            'product manager': [
                # High-weight PM indicators
                ('product management', 3), ('product strategy', 3), ('roadmap', 3),
                ('user stories', 3), ('feature prioritization', 3), ('product vision', 3),
                ('market research', 3), ('product development', 3),
                # Medium-weight indicators
                ('agile', 2), ('scrum', 2), ('stakeholder management', 2),
                ('product owner', 2), ('requirements', 2), ('product lifecycle', 2),
                # Lower-weight indicators
            ],
            'financial planning & analysis manager': [
                # High-weight FP&A indicators
                ('financial planning', 3), ('fp&a', 3), ('budgeting', 3), ('forecasting', 3),
                ('financial analysis', 3), ('financial modeling', 3), ('budget planning', 3),
                ('financial reporting', 3), ('variance analysis', 3), ('financial planning & analysis', 3),
                # Medium-weight indicators
                ('finance', 2), ('budget', 2), ('forecast', 2), ('financial', 2),
                ('planning', 2), ('analysis', 2), ('modeling', 2), ('reporting', 2),
                # Lower-weight indicators
                ('financials', 1), ('plan', 1), ('analyze', 1)
            ],
            'revenue operations manager': [
                # High-weight RevOps indicators
                ('revenue operations', 3), ('revops', 3), ('sales operations', 3),
                ('revenue optimization', 3), ('sales process', 3), ('revenue analytics', 3),
                ('sales enablement', 3), ('revenue strategy', 3), ('sales operations manager', 3),
                # Medium-weight indicators
                ('revenue', 2), ('sales ops', 2), ('operations', 2), ('sales process', 2),
                ('revenue management', 2), ('sales analytics', 2), ('sales enablement', 2),
                # Lower-weight indicators
                ('sales', 1), ('operations', 1), ('revenue', 1)
            ],
            'gtm finance manager': [
                # High-weight GTM Finance indicators
                ('gtm finance', 3), ('go-to-market finance', 3), ('gtm financial', 3),
                ('gtm strategy', 3), ('go-to-market strategy', 3), ('gtm planning', 3),
                ('gtm budgeting', 3), ('gtm forecasting', 3), ('gtm financial planning', 3),
                # Medium-weight indicators
                ('gtm', 2), ('go-to-market', 2), ('finance', 2), ('financial', 2),
                ('strategy', 2), ('planning', 2), ('budgeting', 2), ('forecasting', 2),
                # Lower-weight indicators
                ('gtm', 1), ('market', 1), ('finance', 1)
            ],
            'strategic finance manager': [
                # High-weight Strategic Finance indicators
                ('strategic finance', 3), ('strategic financial', 3), ('finance strategy', 3),
                ('strategic planning', 3), ('strategic analysis', 3), ('strategic financial planning', 3),
                ('strategic budgeting', 3), ('strategic forecasting', 3), ('strategic financial analysis', 3),
                # Medium-weight indicators
                ('strategic', 2), ('finance', 2), ('financial', 2), ('strategy', 2),
                ('planning', 2), ('analysis', 2), ('budgeting', 2), ('forecasting', 2),
                # Lower-weight indicators
                ('strategic', 1), ('finance', 1), ('strategy', 1)
            ],
            'business intelligence manager': [
                # High-weight BI indicators
                ('business intelligence', 3), ('bi', 3), ('business analytics', 3),
                ('data analytics', 3), ('business intelligence manager', 3), ('bi manager', 3),
                ('data visualization', 3), ('business reporting', 3), ('analytics manager', 3),
                # Medium-weight indicators
                ('analytics', 2), ('intelligence', 2), ('data analysis', 2), ('reporting', 2),
                ('visualization', 2), ('business analytics', 2), ('data insights', 2),
                # Lower-weight indicators
                ('business', 1), ('intelligence', 1), ('analytics', 1)
            ],
            'strategy manager': [
                # High-weight Strategy indicators
                ('strategy manager', 3), ('strategic manager', 3), ('business strategy', 3),
                ('strategic planning', 3), ('strategic initiatives', 3), ('corporate strategy', 3),
                ('strategic analysis', 3), ('strategic development', 3), ('strategic management', 3),
                # Medium-weight indicators
                ('strategy', 2), ('strategic', 2), ('planning', 2), ('initiatives', 2),
                ('corporate', 2), ('business', 2), ('analysis', 2), ('development', 2),
                # Lower-weight indicators
                ('strategy', 1), ('strategic', 1), ('plan', 1)
            ],
            'operations manager': [
                # High-weight Operations indicators
                ('operations manager', 3), ('operational manager', 3), ('business operations', 3),
                ('operational excellence', 3), ('process improvement', 3), ('operational strategy', 3),
                ('operational planning', 3), ('operational analysis', 3), ('operational management', 3),
                # Medium-weight indicators
                ('operations', 2), ('operational', 2), ('process', 2), ('excellence', 2),
                ('improvement', 2), ('strategy', 2), ('planning', 2), ('analysis', 2),
                # Lower-weight indicators
                ('operations', 1), ('operational', 1), ('process', 1)
            ],
            'marketing manager': [
                # High-weight marketing indicators
                ('marketing', 3), ('campaign management', 3), ('digital marketing', 3),
                ('content marketing', 3), ('lead generation', 3), ('brand management', 3),
                ('social media', 3), ('email marketing', 3), ('seo', 3), ('sem', 3),
                # Medium-weight indicators
                ('analytics', 2), ('conversion optimization', 2), ('marketing automation', 2),
                ('growth marketing', 2), ('demand generation', 2), ('event marketing', 2),
                # Lower-weight indicators
                ('campaign', 1), ('brand', 1), ('advertising', 1)
            ],
            'payroll specialist': [
                # High-weight payroll indicators
                ('payroll', 3), ('payroll processing', 3), ('tax compliance', 3),
                ('benefits administration', 3), ('payroll reconciliation', 3),
                ('payroll reporting', 3), ('payroll systems', 3), ('payroll audits', 3),
                # Medium-weight indicators
                ('hr', 2), ('human resources', 2), ('compensation', 2),
                ('payroll specialist', 2), ('payroll administrator', 2),
                # Lower-weight indicators
                ('benefits', 1), ('tax', 1), ('compensation', 1)
            ],
            'accountant': [
                # High-weight accounting indicators
                ('accounting', 3), ('financial reporting', 3), ('general ledger', 3),
                ('journal entries', 3), ('reconciliation', 3), ('tax preparation', 3),
                ('audit', 3), ('bookkeeping', 3), ('financial statements', 3),
                # Medium-weight indicators
                ('compliance', 2), ('cost accounting', 2), ('accountant', 2),
                ('senior accountant', 2), ('staff accountant', 2),
                # Lower-weight indicators
                ('financial', 1), ('reporting', 1), ('ledger', 1)
            ],
            'solution architect': [
                # High-weight solution architect indicators
                ('solution architect', 5), ('solutions architect', 5), ('solution design', 3),
                ('technical architecture', 3), ('system architecture', 3), ('solution design', 3),
                ('presales', 3), ('technical sales', 3), ('solution consulting', 3),
                # Medium-weight indicators
                ('architecture', 2), ('technical design', 2), ('solution development', 2),
                ('integration', 2), ('technical consulting', 2), ('solution strategy', 2),
                ('professional services', 2), ('implementation planning', 2),
                # Lower-weight indicators
                ('technical', 1), ('design', 1), ('consulting', 1)
            ],
            'solution consultant': [
                # High-weight solution consultant indicators
                ('solution consultant', 5), ('solutions consultant', 5), ('presales consultant', 3),
                ('technical consultant', 3), ('solutions engineer', 3), ('technical sales', 3),
                ('demo', 3), ('proof of concept', 3), ('technical presentation', 3),
                # Medium-weight indicators
                ('technical consulting', 2), ('solution design', 2), ('customer requirements', 2),
                ('technical demonstration', 2), ('solution presentation', 2), ('presales', 2),
                # Lower-weight indicators
                ('consulting', 1), ('technical', 1), ('presentation', 1)
            ],
            'data engineer': [
                # High-weight data engineering indicators
                ('data engineer', 5), ('etl', 3), ('data pipeline', 3), ('data warehouse', 3),
                ('big data', 3), ('data infrastructure', 3), ('data modeling', 3),
                ('data architecture', 3), ('data integration', 3), ('data processing', 3),
                # Medium-weight indicators
                ('data engineering', 2), ('data platform', 2), ('data lake', 2),
                ('data transformation', 2), ('data quality', 2), ('data governance', 2),
                # Lower-weight indicators
                ('data', 1), ('engineering', 1), ('pipeline', 1)
            ],
            'devops engineer': [
                # High-weight devops indicators
                ('devops', 5), ('site reliability engineer', 5), ('sre', 5),
                ('ci/cd', 3), ('continuous integration', 3), ('continuous deployment', 3),
                ('infrastructure as code', 3), ('kubernetes', 3), ('docker', 3),
                # Medium-weight indicators
                ('automation', 2), ('monitoring', 2), ('logging', 2), ('cloud infrastructure', 2),
                ('deployment', 2), ('system administration', 2), ('infrastructure', 2),
                # Lower-weight indicators
                ('operations', 1), ('infrastructure', 1), ('automation', 1)
            ],
            'business analyst': [
                # High-weight BA indicators
                ('business analyst', 5), ('business analysis', 3), ('requirements gathering', 3),
                ('business requirements', 3), ('functional requirements', 3), ('process analysis', 3),
                ('business process', 3), ('stakeholder management', 3), ('business systems', 3),
                # Medium-weight indicators
                ('requirements', 2), ('analysis', 2), ('process mapping', 2), ('documentation', 2),
                ('business systems analyst', 2), ('functional analyst', 2), ('business process analyst', 2),
                # Lower-weight indicators
                ('business', 1), ('analysis', 1), ('requirements', 1)
            ],
            'data analyst': [
                # High-weight Data Analyst indicators
                ('data analyst', 5), ('data analysis', 3), ('business intelligence', 3),
                ('bi analyst', 3), ('data reporting', 3), ('data visualization', 3),
                ('sql', 3), ('excel', 3), ('tableau', 3), ('power bi', 3),
                # Medium-weight indicators
                ('analytics', 2), ('reporting', 2), ('data insights', 2), ('dashboard', 2),
                ('business intelligence analyst', 2), ('data reporting analyst', 2),
                # Lower-weight indicators
                ('data', 1), ('analysis', 1), ('reporting', 1)
            ],
            'quality assurance': [
                # High-weight QA indicators
                ('quality assurance', 5), ('qa engineer', 5), ('test engineer', 5),
                ('software testing', 3), ('test automation', 3), ('manual testing', 3),
                ('test cases', 3), ('bug tracking', 3), ('quality control', 3),
                # Medium-weight indicators
                ('testing', 2), ('test planning', 2), ('test execution', 2), ('defect tracking', 2),
                ('quality assurance engineer', 2), ('software tester', 2),
                # Lower-weight indicators
                ('testing', 1), ('quality', 1), ('test', 1)
            ],
            'research scientist': [
                # High-weight Research Scientist indicators
                ('research scientist', 5), ('applied scientist', 5), ('machine learning scientist', 5),
                ('ai researcher', 5), ('research', 3), ('machine learning', 3), ('artificial intelligence', 3),
                ('algorithm development', 3), ('scientific research', 3), ('research methodology', 3),
                # Medium-weight indicators
                ('ml', 2), ('ai', 2), ('algorithm', 2), ('scientific', 2), ('research paper', 2),
                ('machine learning scientist', 2), ('ai researcher', 2),
                # Lower-weight indicators
                ('research', 1), ('scientist', 1), ('algorithm', 1)
            ],
            'engineering manager': [
                # High-weight Engineering Manager indicators
                ('engineering manager', 5), ('tech lead', 5), ('technical lead', 5),
                ('lead engineer', 5), ('engineering leadership', 3), ('team leadership', 3),
                ('technical leadership', 3), ('engineering team', 3), ('code review', 3),
                # Medium-weight indicators
                ('team management', 2), ('technical direction', 2), ('engineering process', 2),
                ('mentoring', 2), ('technical guidance', 2), ('engineering strategy', 2),
                # Lower-weight indicators
                ('engineering', 1), ('leadership', 1), ('technical', 1)
            ],
            'financial analyst': [
                # High-weight Financial Analyst indicators
                ('financial analyst', 5), ('finance analyst', 5), ('financial analysis', 3),
                ('financial modeling', 3), ('financial reporting', 3), ('budget analysis', 3),
                ('financial planning', 3), ('financial forecasting', 3), ('financial statements', 3),
                # Medium-weight indicators
                ('financial', 2), ('analysis', 2), ('modeling', 2), ('reporting', 2),
                ('budget', 2), ('forecasting', 2), ('financial planning', 2),
                # Lower-weight indicators
                ('financial', 1), ('analysis', 1), ('finance', 1)
            ]
        }
        
        # Score roles based on weighted keyword matches
        for role, keywords in role_keywords.items():
            score = 0
            for keyword, weight in keywords:
                if keyword in jd_text_lower:
                    score += weight
            if score > 0:
                role_scores[role] = score
        
        return role_scores
    
    def _get_role_suggestions_from_content(self, jd_text_lower: str) -> List[str]:
        """
        Get role suggestions based on job description content when confidence is low.
        """
        # Analyze the content and suggest the most likely roles
        suggestions = []
        
        # Check for common patterns
        if any(word in jd_text_lower for word in ['sales', 'account', 'revenue', 'quota']):
            suggestions.append('account executive')
        if any(word in jd_text_lower for word in ['customer', 'client', 'success', 'support']):
            suggestions.append('customer success manager')
        if any(word in jd_text_lower for word in ['marketing', 'campaign', 'brand', 'lead generation']):
            suggestions.append('marketing manager')
        if any(word in jd_text_lower for word in ['product', 'roadmap', 'strategy', 'agile']):
            suggestions.append('product manager')
        if any(word in jd_text_lower for word in ['software', 'development', 'coding', 'engineering']):
            suggestions.append('software engineer')
        if any(word in jd_text_lower for word in ['data', 'analysis', 'machine learning', 'statistics']):
            suggestions.append('data scientist')
        if any(word in jd_text_lower for word in ['payroll', 'hr', 'compensation', 'benefits']):
            suggestions.append('payroll specialist')
        if any(word in jd_text_lower for word in ['accounting', 'financial', 'bookkeeping', 'audit']):
            suggestions.append('accountant')
        if any(word in jd_text_lower for word in ['solution architect', 'solutions architect', 'technical architecture', 'solution design', 'presales']):
            suggestions.append('solution architect')
        if any(word in jd_text_lower for word in ['solution consultant', 'solutions consultant', 'presales consultant', 'technical consultant']):
            suggestions.append('solution consultant')
        if any(word in jd_text_lower for word in ['data engineer', 'etl', 'data pipeline', 'data warehouse']):
            suggestions.append('data engineer')
        if any(word in jd_text_lower for word in ['devops', 'site reliability engineer', 'sre', 'ci/cd']):
            suggestions.append('devops engineer')
        
        # Remove duplicates and limit to top 3
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:3]
    
    def _get_tagged_contact_boost(self, contact_name):
        """Get score boost for contacts tagged in the gamification system."""
        try:
            # In a real implementation, this would check a database
            # For now, we'll simulate with a simple check
            # This could be enhanced to check localStorage or a backend storage
            
            # Sample tagged contacts (in real app, this would come from database/storage)
            tagged_contacts = {
                'Sarah Johnson': {'tags': ['best-salesperson', 'people-manager'], 'boost': 15},
                'Michael Chen': {'tags': ['technical-expert', 'problem-solver'], 'boost': 12},
                'Emily Rodriguez': {'tags': ['best-salesperson'], 'boost': 10},
                'David Kim': {'tags': ['technical-expert'], 'boost': 8},
                'Lisa Thompson': {'tags': ['culture-fit', 'team-player'], 'boost': 10}
            }
            
            # Check if contact is tagged
            if contact_name in tagged_contacts:
                return tagged_contacts[contact_name]['boost']
            
            return 0
            
        except Exception as e:
            print(f"Error getting tagged contact boost: {e}")
            return 0
    
    def find_top_candidates(self, jd_text: str, top_n: int = 10, preferred_companies: List[str] = None, preferred_industries: List[str] = None, job_location: str = None, enable_location_enrichment: bool = False, serpapi_key: str = None, job_title: str = None, alternative_titles: List[str] = None, job_reqs: Dict = None) -> pd.DataFrame:
        """
        Main function to find top candidates for a job description.
        Returns DataFrame with top candidates and their scores.
        
        Args:
            jd_text: Job description text
            top_n: Number of top candidates to return
            preferred_companies: List of preferred company names for bonus scoring
            preferred_industries: List of preferred industries for bonus scoring
        """
        start_time = time.time()
        
        # Use provided job_reqs or extract them
        if job_reqs is None:
            print(f"🔍 Analyzing job description...")
            job_reqs = self.extract_job_requirements(jd_text)
            
            print(f"📋 Job Requirements Extracted:")
            print(f"   Skills: {len(job_reqs['skills'])} found")
            print(f"   Platforms: {len(job_reqs['platforms'])} found")
            print(f"   Role: {job_reqs['role']} (Confidence: {job_reqs['role_confidence']})")
            if job_reqs['role_confidence'] < 0.3 and job_reqs['suggested_roles']:
                print(f"   ⚠️  Low confidence! Suggested roles: {', '.join(job_reqs['suggested_roles'])}")
            print(f"   Company: {job_reqs['company']}")
            print(f"   Seniority: {job_reqs['seniority']}")
        else:
            # Job requirements already provided (e.g., from manual job title)
            print(f"📋 Using provided job requirements:")
            print(f"   Skills: {len(job_reqs['skills'])} found")
            print(f"   Platforms: {len(job_reqs['platforms'])} found")
            print(f"   Role: {job_reqs['role']} (Confidence: {job_reqs['role_confidence']})")
            print(f"   Company: {job_reqs['company']}")
            print(f"   Seniority: {job_reqs['seniority']}")
        
        print(f"🎯 Scoring {len(self.df)} contacts...")
        
        # Score all contacts with role-based filtering
        scored_contacts = []
        
        # Define role-specific thresholds and filters
        role_thresholds = {
            'sdr': {
                'min_role_score': 6.0,  # Higher threshold - must have good role match
                'min_total_score': 10.0,  # Higher threshold - must have excellent overall score
                'exclude_seniority': ['vp', 'director', 'head of', 'regional vice president', 'senior vice president', 'senior manager', 'principal'],
                'preferred_seniority': ['entry', 'junior', 'associate', 'representative']
            },
            'account executive': {
                'min_role_score': 5.0,
                'min_total_score': 8.0,
                'exclude_seniority': ['vp', 'director', 'head of', 'regional vice president'],
                'preferred_seniority': ['representative', 'associate', 'junior']
            },
            'customer success manager': {
                'min_role_score': 5.0,
                'min_total_score': 8.0,
                'exclude_seniority': ['vp', 'director', 'head of'],
                'preferred_seniority': ['manager', 'representative', 'associate']
            },
            'software engineer': {
                'min_role_score': 5.0,
                'min_total_score': 8.0,
                'exclude_seniority': ['vp', 'director', 'head of', 'cto', 'chief'],
                'preferred_seniority': ['engineer', 'developer', 'junior', 'associate']
            }
        }
        
        # Get thresholds for the target role
        target_role = job_reqs.get('role', '').lower()
        thresholds = role_thresholds.get(target_role, {
            'min_role_score': 3.0,
            'min_total_score': 6.0,
            'exclude_seniority': ['vp', 'director', 'head of'],
            'preferred_seniority': []
        })
        
        print(f"🎯 Role-specific filtering for '{target_role}':")
        print(f"   Min role score: {thresholds['min_role_score']}")
        print(f"   Min total score: {thresholds['min_total_score']}")
        print(f"   Exclude seniority: {thresholds['exclude_seniority']}")
        
        for idx, row in self.df.iterrows():
            scores = self.score_contact(row, job_reqs, preferred_companies, preferred_industries, job_location, job_title, alternative_titles)
            
            # Apply role-based filtering
            contact_title = str(row.get('Position', '')).lower()
            contact_seniority = str(row.get('seniority_tag', '')).lower()
            
            # Skip if role score is too low
            if scores['role_score'] < thresholds['min_role_score']:
                continue
                
            # Skip if total score is too low
            if scores['total_score'] < thresholds['min_total_score']:
                continue
                
            # Skip if contact has excluded seniority for this role
            if any(excluded in contact_title for excluded in thresholds['exclude_seniority']):
                continue
                
            # Apply seniority bonus for preferred seniority levels
            seniority_bonus = 0
            if any(preferred in contact_title or preferred in contact_seniority for preferred in thresholds['preferred_seniority']):
                seniority_bonus = 2.0
                scores['total_score'] += seniority_bonus
            
            contact_data = {
                'First Name': row['First Name'],
                'Last Name': row['Last Name'],
                'Position': row['Position'],
                'Company': row['Company'],
                'Email': row.get('Email', ''),
                'LinkedIn': row.get('LinkedIn', ''),
                'location_raw': row.get('location_raw', ''),  # Add location data
                'employee_connection': row.get('employee_connection', ''),  # Add employee connection
                'match_score': round(scores['total_score'], 2),
                'skill_score': round(scores['skill_score'], 2),
                'role_score': round(scores['role_score'], 2),
                'company_score': round(scores['company_score'], 2),
                'industry_score': round(scores['industry_score'], 2),
                'seniority_bonus': round(scores['seniority_bonus'] + seniority_bonus, 2),
                'location_score': round(scores.get('location_score', 0), 2),
                'location_match_details': scores.get('location_match_details', ''),
                'location_match_type': scores.get('location_match_type', ''),
                'skill_matches': scores['skill_matches'],
                'matched_role': scores['matched_role'],
                'industry_matches': scores['industry_matches'],
                'tagged_boost': scores['tagged_boost']
            }
            scored_contacts.append(contact_data)
        
        # Sort by score and get top candidates
        scored_df = pd.DataFrame(scored_contacts)
        if len(scored_df) > 0:
            # Final quality check - only return candidates above quality threshold
            quality_threshold = thresholds['min_total_score']
            qualified_candidates = scored_df[scored_df['match_score'] >= quality_threshold]
            # Optional: enrich missing locations using Bright Data (cap at 10)
            if job_location and len(qualified_candidates) > 0 and _HAS_BRIGHT:
                missing = []
                for _, row in qualified_candidates.iterrows():
                    loc_raw = str(row.get('location_raw', '') or '').strip()
                    if not loc_raw or loc_raw.lower() == 'nan':
                        full_name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                        missing.append({
                            'key': f"{row.get('First Name','')}-{row.get('Last Name','')}-{row.get('Company','')}",
                            'full_name': full_name,
                            'company': str(row.get('Company', ''))
                        })
                if len(missing) > 0:
                    try:
                        enricher = BrightDataEnricher()
                        updates = BrightDataEnricher.enrich_batch_missing_locations(enricher, missing, max_queries=10)
                        if updates:
                            # Apply updates in-memory and also reflect in self.df if columns exist
                            for idx, row in qualified_candidates.iterrows():
                                key = f"{row.get('First Name','')}-{row.get('Last Name','')}-{row.get('Company','')}"
                                if key in updates:
                                    qualified_candidates.at[idx, 'location_raw'] = updates[key]
                                    qualified_candidates.at[idx, 'location_match_details'] = f"Enriched: {updates[key]}"
                            # Also push back to source df where key matches
                            for src_idx, src_row in self.df.iterrows():
                                key = f"{src_row.get('First Name','')}-{src_row.get('Last Name','')}-{src_row.get('Company','')}"
                                if key in updates:
                                    self.df.at[src_idx, 'location_raw'] = updates[key]
                    except Exception as _enrich_err:
                        # Fail soft — continue without enrichment
                        pass
            if len(qualified_candidates) == 0:
                print(f"⚠️ No candidates meet the quality threshold of {quality_threshold}")
                print(f"   Found {len(scored_df)} candidates, but none scored high enough")
                # Return empty DataFrame
                top_candidates = pd.DataFrame()
            else:
                print(f"✅ Found {len(qualified_candidates)} qualified candidates (score >= {quality_threshold})")
                top_candidates = qualified_candidates.sort_values('match_score', ascending=False).head(top_n)
        else:
            print(f"⚠️ No candidates passed the initial filtering criteria")
            top_candidates = pd.DataFrame()
            
            # Location enrichment for top candidates (if enabled)
            if enable_location_enrichment and job_location:
                try:
                    from bright_data_enricher import BrightDataEnricher
                    
                    print(f"🌍 Starting location enrichment for top {len(top_candidates)} candidates...")
                    
                    # Check which candidates need location enrichment
                    candidates_needing_enrichment = []
                    candidates_with_locations = []
                    
                    for idx, candidate in top_candidates.iterrows():
                        current_location = candidate.get('Location', '')
                        
                        # Check if location is missing or invalid
                        if not current_location or current_location.lower() in ['nan', 'none', 'n/a', '']:
                            candidates_needing_enrichment.append(idx)
                            print(f"   📍 {candidate['First Name']} {candidate['Last Name']} needs location enrichment")
                        else:
                            candidates_with_locations.append(idx)
                            print(f"   ✅ {candidate['First Name']} {candidate['Last Name']} already has location: {current_location}")
                    
                    # Enrich locations for candidates that need it
                    if candidates_needing_enrichment:
                        print(f"🔍 Enriching locations for {len(candidates_needing_enrichment)} candidates...")
                        
                        # Get the candidates that need enrichment
                        candidates_to_enrich = top_candidates.loc[candidates_needing_enrichment].copy()
                        
                        # Initialize the Bright Data enricher
                        enricher = BrightDataEnricher()
                        
                        # Enrich locations
                        enriched_candidates = enricher.enrich_contact_locations(candidates_to_enrich)
                        
                        # Update the main dataframe with enriched locations
                        for idx, enriched_candidate in enriched_candidates.iterrows():
                            if enriched_candidate.get('serp_location'):
                                # Update the location in the main dataframe
                                top_candidates.at[idx, 'Location'] = enriched_candidate['serp_location']
                                print(f"   ✅ Enriched {enriched_candidate['First Name']} {enriched_candidate['Last Name']}: {enriched_candidate['serp_location']}")
                                
                                # Also update the database file
                                self._update_contact_location_in_database(idx, enriched_candidate['serp_location'])
                    
                    # Now categorize candidates by location match
                    exact_location_matches = []
                    other_location_matches = []
                    
                    for idx, candidate in top_candidates.iterrows():
                        candidate_location = candidate.get('Location', '')
                        
                        if candidate_location and self._is_location_match(candidate_location, job_location):
                            exact_location_matches.append(idx)
                        else:
                            other_location_matches.append(idx)
                    
                    # Re-sort candidates: exact location matches first, then others
                    exact_matches_df = top_candidates.loc[exact_location_matches].copy()
                    other_matches_df = top_candidates.loc[other_location_matches].copy()
                    
                    # Sort each group by match score
                    exact_matches_df = exact_matches_df.sort_values('match_score', ascending=False)
                    other_matches_df = other_matches_df.sort_values('match_score', ascending=False)
                    
                    # Combine them back
                    top_candidates = pd.concat([exact_matches_df, other_matches_df])
                    
                    print(f"🌍 Location enrichment completed:")
                    print(f"   📍 Exact location matches: {len(exact_location_matches)}")
                    print(f"   🌐 Other location matches: {len(other_location_matches)}")
                    
                except Exception as e:
                    print(f"⚠️ Location enrichment failed: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        elapsed_time = time.time() - start_time
        print(f"✅ Found {len(top_candidates)} candidates in {elapsed_time:.2f} seconds")
        
        return top_candidates
    
    def display_results(self, top_candidates: pd.DataFrame, job_reqs: Dict):
        """Display formatted results."""
        if len(top_candidates) == 0:
            print("❌ No matching candidates found")
            return
        
        print(f"\n🏆 TOP {len(top_candidates)} REFERRAL CANDIDATES")
        print("=" * 80)
        
        for idx, row in top_candidates.iterrows():
            print(f"\n#{idx+1}: {row['First Name']} {row['Last Name']}")
            print(f"   Position: {row['Position']}")
            print(f"   Company: {row['Company']}")
            print(f"   Total Score: {row['match_score']}")
            print(f"   Breakdown:")
            print(f"     Skills: {row['skill_matches']} (score: {row['skill_score']})")
            print(f"     Platforms: {row['platform_matches']} (score: {row['platform_score']})")
            print(f"     Role: {row['matched_role']} (score: {row['role_score']})")
            print(f"     Company match: {row['company_score']}")
            print(f"     Industry: {row['industry_matches']} (score: {row['industry_score']})")
            print(f"     Seniority bonus: {row['seniority_bonus']}")
            if row.get('Email'):
                print(f"   Email: {row['Email']}")
            if row.get('LinkedIn'):
                print(f"   LinkedIn: {row['LinkedIn']}")
    
    def save_results(self, top_candidates: pd.DataFrame, filename: str = "referral_matches.csv"):
        """Save results to CSV."""
        if len(top_candidates) > 0:
            # Save detailed version
            detailed_columns = [
                'First Name', 'Last Name', 'Position', 'Company', 'Email', 'LinkedIn',
                'match_score', 'skill_score', 'platform_score', 'role_score', 
                'company_score', 'industry_score', 'seniority_bonus',
                'skill_matches', 'platform_matches', 'matched_role', 'industry_matches'
            ]
            top_candidates[detailed_columns].to_csv(f"detailed_{filename}", index=False)
            
            # Save simple version
            simple_columns = ['First Name', 'Last Name', 'Position', 'Company', 'match_score']
            top_candidates[simple_columns].to_csv(filename, index=False)
            
            print(f"📄 Results saved to {filename} and detailed_{filename}")
    
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
    
    def _update_contact_location_in_database(self, contact_index: int, new_location: str):
        """Update a contact's location in the database file."""
        try:
            # Load the current database
            df = pd.read_csv(self.contacts_file)
            
            # Update the location for the specific contact
            if contact_index < len(df):
                df.at[contact_index, 'Location'] = new_location
                
                # Save back to file
                df.to_csv(self.contacts_file, index=False)
                print(f"   💾 Updated database: Contact {contact_index} location set to '{new_location}'")
            else:
                print(f"   ⚠️ Contact index {contact_index} out of range for database update")
                
        except Exception as e:
            print(f"   ⚠️ Failed to update database: {str(e)}")


def main():
    """Main function for command-line usage."""
    print("🎯 Unified Referral Matching System")
    print("=" * 50)
    
    # Initialize matcher
    matcher = UnifiedReferralMatcher()
    
    # Get job description
    print("\n📋 Paste the job description (end with ENTER + CTRL-D):")
    jd_text = ""
    try:
        while True:
            jd_text += input() + "\n"
    except EOFError:
        pass
    
    if not jd_text.strip():
        print("❌ No job description provided")
        return
    
    # Find candidates
    top_candidates = matcher.find_top_candidates(jd_text, top_n=10)
    
    # Extract job requirements for display
    job_reqs = matcher.extract_job_requirements(jd_text)
    
    # Display results
    matcher.display_results(top_candidates, job_reqs)
    
    # Save results
    matcher.save_results(top_candidates)


if __name__ == "__main__":
    main()
