#!/usr/bin/env python3
"""
Enhanced Contact Tagging System
Comprehensively tags LinkedIn contacts with roles, companies, seniority, and industry information.
"""

import pandas as pd
import json
import re
from collections import Counter
from rapidfuzz import process, fuzz
from typing import Dict, List, Tuple, Optional
import time

class EnhancedContactTagger:
    """
    Enhanced system for tagging LinkedIn contacts with comprehensive information.
    """
    
    def __init__(self):
        """Initialize the tagger with enrichment data."""
        print("🚀 Initializing Enhanced Contact Tagger...")
        
        # Load enrichment data
        self._load_enrichment_data()
        
        print("✅ Enhanced Contact Tagger initialized successfully")
    
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
    
    def tag_contacts(self, contacts_df: pd.DataFrame) -> pd.DataFrame:
        """
        Tag all contacts with comprehensive information.
        
        Args:
            contacts_df: DataFrame with LinkedIn contacts (First Name, Last Name, Company, Position, etc.)
            
        Returns:
            DataFrame with added tagging columns
        """
        print(f"🏷️  Tagging {len(contacts_df)} contacts...")
        
        # Initialize tagging columns
        contacts_df['skills_tag'] = '[]'
        contacts_df['platforms_tag'] = '[]'
        contacts_df['role_tag'] = ''
        contacts_df['function_tag'] = ''
        contacts_df['seniority_tag'] = ''
        contacts_df['company_industry_tags'] = '[]'
        
        tagged_contacts = []
        
        for idx, row in contacts_df.iterrows():
            if idx % 100 == 0:
                print(f"   Processing contact {idx + 1}/{len(contacts_df)}...")
            
            # Extract contact information
            position = str(row.get('Position', '')).strip()
            company = str(row.get('Company', '')).strip()
            first_name = str(row.get('First Name', '')).strip()
            last_name = str(row.get('Last Name', '')).strip()
            email = str(row.get('Email Address', '')).strip()
            linkedin = str(row.get('URL', '')).strip()
            
            # Skip empty rows or header rows
            if not position or position.lower() in ['position', 'title', 'job title']:
                continue
            
            # Tag the contact
            tagged_contact = self._tag_single_contact(
                position, company, first_name, last_name, email, linkedin
            )
            
            # Add original data
            tagged_contact.update({
                'First Name': first_name,
                'Last Name': last_name,
                'Position': position,
                'Company': company,
                'Email': email,
                'LinkedIn': linkedin
            })
            
            tagged_contacts.append(tagged_contact)
        
        # Convert to DataFrame
        tagged_df = pd.DataFrame(tagged_contacts)
        
        print(f"✅ Successfully tagged {len(tagged_df)} contacts")
        return tagged_df
    
    def _tag_single_contact(self, position: str, company: str, first_name: str, 
                           last_name: str, email: str, linkedin: str) -> Dict:
        """
        Tag a single contact with comprehensive information.
        """
        position_lower = position.lower()
        company_lower = company.lower()
        
        # 1. Role Detection
        detected_role = self._detect_role(position_lower)
        
        # 2. Function Detection
        detected_function = self._detect_function(position_lower)
        
        # 3. Seniority Detection
        detected_seniority = self._detect_seniority(position_lower)
        
        # 4. Skills Tagging (based on detected role)
        skills = self._extract_skills_for_role(detected_role, position_lower)
        
        # 5. Platforms Tagging (based on detected role)
        platforms = self._extract_platforms_for_role(detected_role, position_lower)
        
        # 6. Company Industry Tags
        company_tags = self._extract_company_industry_tags(company_lower)
        
        return {
            'skills_tag': json.dumps(skills),
            'platforms_tag': json.dumps(platforms),
            'role_tag': detected_role,
            'function_tag': detected_function,
            'seniority_tag': detected_seniority,
            'company_industry_tags': json.dumps(company_tags)
        }
    
    def _detect_role(self, position: str) -> str:
        """Detect the primary role from position title."""
        # Direct title matching
        for alias, canonical in self.title_aliases.items():
            if alias.lower() in position:
                return canonical
        
        # Pattern matching for common variations
        role_patterns = {
            'account executive': [
                r'\b(?:account\s+executive|ae|sales\s+executive|enterprise\s+account\s+executive|strategic\s+account\s+executive)\b',
                r'\b(?:sales\s+representative|sales\s+rep|enterprise\s+sales)\b'
            ],
            'customer success manager': [
                r'\b(?:customer\s+success|cs\s+manager|csm|customer\s+experience\s+manager)\b',
                r'\b(?:client\s+success|account\s+manager)\b'
            ],
            'software engineer': [
                r'\b(?:software\s+engineer|developer|programmer|full\s+stack|backend|frontend)\b',
                r'\b(?:senior\s+developer|lead\s+developer|principal\s+engineer)\b'
            ],
            'product manager': [
                r'\b(?:product\s+manager|pm|product\s+owner|product\s+lead)\b',
                r'\b(?:senior\s+product\s+manager|principal\s+product\s+manager)\b'
            ],
            'data scientist': [
                r'\b(?:data\s+scientist|ml\s+engineer|machine\s+learning|ai\s+engineer)\b',
                r'\b(?:senior\s+data\s+scientist|lead\s+data\s+scientist)\b'
            ],
            'marketing manager': [
                r'\b(?:marketing\s+manager|marketing\s+lead|growth\s+marketer)\b',
                r'\b(?:digital\s+marketing|content\s+marketing|brand\s+manager)\b'
            ],
            'sales development representative': [
                r'\b(?:sdr|sales\s+development|business\s+development\s+representative|bdr)\b',
                r'\b(?:lead\s+generation|inbound\s+sales|outbound\s+sales)\b'
            ],
            'payroll specialist': [
                r'\b(?:payroll\s+specialist|payroll\s+administrator|payroll\s+coordinator)\b',
                r'\b(?:hr\s+specialist|compensation\s+specialist)\b'
            ],
            'accountant': [
                r'\b(?:accountant|senior\s+accountant|staff\s+accountant|financial\s+accountant)\b',
                r'\b(?:bookkeeper|financial\s+analyst)\b'
            ],
            'financial analyst': [
                r'\b(?:financial\s+analyst|finance\s+analyst|senior\s+financial\s+analyst)\b',
                r'\b(?:business\s+analyst|data\s+analyst)\b'
            ],
            'legal counsel': [
                r'\b(?:legal\s+counsel|attorney|lawyer|senior\s+counsel|general\s+counsel)\b',
                r'\b(?:contract\s+negotiator|contract\s+manager|paralegal|legal\s+operations)\b',
                r'\b(?:legal\s+advisor|legal\s+adviser|legal\s+specialist|legal\s+analyst)\b'
            ]
        }
        
        for role, patterns in role_patterns.items():
            for pattern in patterns:
                if re.search(pattern, position, re.IGNORECASE):
                    return role
        
        # If no specific role found, try to infer from keywords
        if any(word in position for word in ['sales', 'account', 'revenue', 'quota']):
            return 'account executive'
        elif any(word in position for word in ['customer', 'client', 'success', 'support']):
            return 'customer success manager'
        elif any(word in position for word in ['software', 'development', 'coding', 'engineering']):
            return 'software engineer'
        elif any(word in position for word in ['product', 'roadmap', 'strategy']):
            return 'product manager'
        elif any(word in position for word in ['data', 'analysis', 'machine learning', 'ai']):
            return 'data scientist'
        elif any(word in position for word in ['marketing', 'campaign', 'brand']):
            return 'marketing manager'
        elif any(word in position for word in ['payroll', 'hr', 'compensation']):
            return 'payroll specialist'
        elif any(word in position for word in ['accounting', 'financial', 'bookkeeping']):
            return 'accountant'
        elif any(word in position for word in ['legal', 'law', 'contract', 'paralegal', 'counsel']):
            return 'legal counsel'
        
        return 'other'
    
    def _detect_function(self, position: str) -> str:
        """Detect the business function from position title."""
        function_keywords = {
            'sales': ['sales', 'account', 'revenue', 'quota', 'business development'],
            'engineering': ['engineer', 'developer', 'programmer', 'software', 'technical'],
            'product': ['product', 'pm', 'product owner', 'roadmap'],
            'marketing': ['marketing', 'campaign', 'brand', 'growth', 'digital marketing'],
            'customer success': ['customer success', 'customer experience', 'client success', 'support'],
            'data': ['data', 'analytics', 'machine learning', 'ai', 'scientist'],
            'finance': ['finance', 'accounting', 'payroll', 'financial', 'bookkeeping'],
            'hr': ['hr', 'human resources', 'talent', 'recruiting', 'people'],
            'operations': ['operations', 'ops', 'process', 'strategy'],
            'design': ['design', 'ux', 'ui', 'creative', 'graphic']
        }
        
        for function, keywords in function_keywords.items():
            if any(keyword in position for keyword in keywords):
                return function
        
        return 'other'
    
    def _detect_seniority(self, position: str) -> str:
        """Detect seniority level from position title."""
        seniority_indicators = {
            'junior': ['junior', 'jr', 'entry', 'associate', 'trainee', 'graduate'],
            'mid': ['mid', 'intermediate', 'specialist', 'coordinator'],
            'senior': ['senior', 'sr', 'experienced', 'expert', 'lead'],
            'principal': ['principal', 'staff', 'senior lead'],
            'director': ['director', 'head of', 'manager', 'supervisor'],
            'executive': ['executive', 'vp', 'vice president', 'chief', 'cto', 'ceo', 'cfo']
        }
        
        for level, indicators in seniority_indicators.items():
            if any(indicator in position for indicator in indicators):
                return level
        
        return 'mid'  # Default to mid-level if unclear
    
    def _extract_skills_for_role(self, role: str, position: str) -> List[str]:
        """Extract relevant skills based on detected role."""
        skills = []
        
        # Get role-specific skills
        role_key = f"any:{role}"
        if role_key in self.role_enrichment:
            role_skills = self.role_enrichment[role_key].get("skills", [])
            # Add all role skills
            skills.extend(role_skills)
        
        # Add position-specific skills based on keywords
        position_skills = self._extract_position_specific_skills(position)
        skills.extend(position_skills)
        
        # Remove duplicates and limit to reasonable number
        unique_skills = list(dict.fromkeys(skills))
        return unique_skills[:15]  # Limit to 15 skills max
    
    def _extract_position_specific_skills(self, position: str) -> List[str]:
        """Extract skills based on specific keywords in position title."""
        skills = []
        
        # Sales-related skills
        if any(word in position for word in ['sales', 'account', 'revenue']):
            skills.extend(['sales', 'account management', 'client relationship', 'negotiation'])
        
        # Engineering-related skills
        if any(word in position for word in ['engineer', 'developer', 'software']):
            skills.extend(['software development', 'programming', 'technical skills'])
        
        # Marketing-related skills
        if any(word in position for word in ['marketing', 'campaign', 'brand']):
            skills.extend(['marketing', 'campaign management', 'digital marketing'])
        
        # Data-related skills
        if any(word in position for word in ['data', 'analytics', 'machine learning']):
            skills.extend(['data analysis', 'analytics', 'machine learning'])
        
        # Customer success skills
        if any(word in position for word in ['customer', 'client', 'success']):
            skills.extend(['customer success', 'account management', 'client relationship'])
        
        return skills
    
    def _extract_platforms_for_role(self, role: str, position: str) -> List[str]:
        """Extract relevant platforms based on detected role."""
        platforms = []
        
        # Get role-specific platforms
        role_key = f"any:{role}"
        if role_key in self.role_enrichment:
            role_platforms = self.role_enrichment[role_key].get("platforms", [])
            platforms.extend(role_platforms)
        
        # Add position-specific platforms
        position_platforms = self._extract_position_specific_platforms(position)
        platforms.extend(position_platforms)
        
        # Remove duplicates and limit
        unique_platforms = list(dict.fromkeys(platforms))
        return unique_platforms[:10]  # Limit to 10 platforms max
    
    def _extract_position_specific_platforms(self, position: str) -> List[str]:
        """Extract platforms based on specific keywords in position title."""
        platforms = []
        
        # CRM platforms
        if any(word in position for word in ['sales', 'account', 'crm']):
            platforms.extend(['Salesforce', 'HubSpot', 'Pipedrive', 'Close'])
        
        # Development platforms
        if any(word in position for word in ['engineer', 'developer', 'software']):
            platforms.extend(['GitHub', 'GitLab', 'AWS', 'Azure', 'Google Cloud'])
        
        # Marketing platforms
        if any(word in position for word in ['marketing', 'campaign', 'brand']):
            platforms.extend(['Mailchimp', 'Constant Contact', 'SendGrid', 'ActiveCampaign'])
        
        # Analytics platforms
        if any(word in position for word in ['data', 'analytics', 'analysis']):
            platforms.extend(['Google Analytics', 'Tableau', 'Power BI', 'Looker'])
        
        return platforms
    
    def _extract_company_industry_tags(self, company: str) -> List[str]:
        """Extract industry tags based on company name."""
        # Direct company match
        if company in self.company_industry_tags:
            return self.company_industry_tags[company]
        
        # Fuzzy matching for company names
        known_companies = list(self.company_industry_tags.keys())
        best_match = process.extractOne(company, known_companies, scorer=fuzz.partial_ratio)
        
        if best_match and best_match[1] >= 85:
            return self.company_industry_tags[best_match[0]]
        
        # Infer industry from company name keywords
        industry_keywords = {
            'saas': ['saas', 'software', 'tech', 'technology', 'platform'],
            'fintech': ['fintech', 'financial', 'payment', 'banking', 'stripe', 'square'],
            'ecommerce': ['ecommerce', 'retail', 'shopping', 'amazon', 'shopify'],
            'healthcare': ['health', 'medical', 'pharma', 'biotech', 'hospital'],
            'education': ['education', 'learning', 'university', 'school', 'academy'],
            'consulting': ['consulting', 'consultant', 'advisory', 'strategy'],
            'media': ['media', 'entertainment', 'publishing', 'broadcast'],
            'real estate': ['real estate', 'property', 'housing', 'construction']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in company for keyword in keywords):
                return [industry]
        
        return ['other']
    
    def save_tagged_contacts(self, tagged_df: pd.DataFrame, filename: str = "enhanced_tagged_contacts.csv"):
        """Save tagged contacts to CSV file."""
        tagged_df.to_csv(filename, index=False)
        print(f"📄 Tagged contacts saved to {filename}")
        
        # Print summary statistics
        self._print_tagging_summary(tagged_df)
    
    def _print_tagging_summary(self, tagged_df: pd.DataFrame):
        """Print summary statistics of the tagging process."""
        print(f"\n📊 TAGGING SUMMARY")
        print("=" * 50)
        
        # Role distribution
        role_counts = tagged_df['role_tag'].value_counts()
        print(f"\n🎯 Role Distribution:")
        for role, count in role_counts.head(10).items():
            print(f"   {role}: {count}")
        
        # Function distribution
        function_counts = tagged_df['function_tag'].value_counts()
        print(f"\n🏢 Function Distribution:")
        for function, count in function_counts.head(10).items():
            print(f"   {function}: {count}")
        
        # Seniority distribution
        seniority_counts = tagged_df['seniority_tag'].value_counts()
        print(f"\n📈 Seniority Distribution:")
        for seniority, count in seniority_counts.items():
            print(f"   {seniority}: {count}")
        
        # Skills per contact
        skills_counts = []
        for skills_json in tagged_df['skills_tag']:
            skills = json.loads(skills_json)
            skills_counts.append(len(skills))
        
        avg_skills = sum(skills_counts) / len(skills_counts) if skills_counts else 0
        print(f"\n💡 Average skills per contact: {avg_skills:.1f}")
        
        # Platforms per contact
        platforms_counts = []
        for platforms_json in tagged_df['platforms_tag']:
            platforms = json.loads(platforms_json)
            platforms_counts.append(len(platforms))
        
        avg_platforms = sum(platforms_counts) / len(platforms_counts) if platforms_counts else 0
        print(f"🛠️  Average platforms per contact: {avg_platforms:.1f}")


def main():
    """Main function for command-line usage."""
    print("🏷️  Enhanced Contact Tagging System")
    print("=" * 50)
    
    # Initialize tagger
    tagger = EnhancedContactTagger()
    
    # Load contacts from LinkedIn export
    try:
        contacts_df = pd.read_csv("linkedin-contacts2.csv")
        print(f"📄 Loaded {len(contacts_df)} contacts from linkedin-contacts2.csv")
    except FileNotFoundError:
        print("❌ linkedin-contacts2.csv not found. Please ensure the file exists.")
        return
    
    # Tag contacts
    tagged_df = tagger.tag_contacts(contacts_df)
    
    # Save results
    tagger.save_tagged_contacts(tagged_df, "enhanced_tagged_contacts.csv")


if __name__ == "__main__":
    main()
