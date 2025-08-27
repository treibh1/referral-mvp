import pandas as pd
import json
from collections import Counter
import re
from rapidfuzz import process, fuzz

print("🎯 Show CSM Results for Miro Job")
print("=" * 60)

# Load tagged contacts
df = pd.read_csv("tagged_contacts2.csv")

# Load enrichment terms
with open("role_enrichment.json", "r") as f:
    role_enrichment = json.load(f)

with open("title_aliases.json", "r") as f:
    title_aliases = json.load(f)

with open("company_industry_tags_usev2.json", "r") as f:
    company_industry_tags = json.load(f)

# Extract master skill/platform lists
all_skills = set()
all_platforms = set()
for entry in role_enrichment.values():
    all_skills.update(entry.get("skills", []))
    all_platforms.update(entry.get("platforms", []))

def extract_tags_from_jd(jd_text):
    """Extract skills and platforms from job description text"""
    jd_text_lower = jd_text.lower()
    matched_skills = []
    matched_platforms = []
    
    # Skill matching - check for exact matches and variations
    for skill in all_skills:
        skill_lower = skill.lower()
        if (skill_lower in jd_text_lower or 
            skill_lower.replace(' ', '') in jd_text_lower.replace(' ', '') or
            any(word in jd_text_lower for word in skill_lower.split())):
            matched_skills.append(skill)
    
    # Platform matching
    for platform in all_platforms:
        platform_lower = platform.lower()
        if platform_lower in jd_text_lower:
            matched_platforms.append(platform)
    
    # Add common tech terms that might not be in the platform list
    tech_terms = {
        'python': 'Python',
        'javascript': 'JavaScript', 
        'react': 'React',
        'git': 'Git',
        'postgresql': 'PostgreSQL',
        'redis': 'Redis',
        'kubernetes': 'Kubernetes',
        'docker': 'Docker',
        'aws': 'AWS',
        'elasticsearch': 'Elasticsearch',
        'graphql': 'GraphQL',
        'datadog': 'Datadog',
        'salesforce': 'Salesforce',
        'hubspot': 'HubSpot',
        'zendesk': 'Zendesk',
        'gong': 'Gong',
        'clari': 'Clari',
        'gainsight': 'Gainsight',
        'pytorch': 'PyTorch',
        'tensorflow': 'TensorFlow',
        'scikit-learn': 'Scikit-learn',
        'spark': 'Apache Spark',
        'xgboost': 'XGBoost',
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'matplotlib': 'Matplotlib',
        'seaborn': 'Seaborn',
        'jupyter': 'Jupyter',
        'mlflow': 'MLflow',
        'kubeflow': 'Kubeflow',
        'airflow': 'Apache Airflow',
        'snowflake': 'Snowflake',
        'databricks': 'Databricks',
        'tableau': 'Tableau',
        'powerbi': 'Power BI',
        'looker': 'Looker',
        'amplitude': 'Amplitude',
        'mixpanel': 'Mixpanel',
        'segment': 'Segment',
        'rudderstack': 'RudderStack',
        'fivetran': 'Fivetran',
        'dbt': 'dbt',
        'airbyte': 'Airbyte',
        'prefect': 'Prefect',
        'dagster': 'Dagster'
    }
    
    for term, platform_name in tech_terms.items():
        if term in jd_text_lower and platform_name not in matched_platforms:
            matched_platforms.append(platform_name)
    
    return matched_skills, matched_platforms

def detect_role_from_jd(jd_text):
    """Detect the primary role from job description"""
    jd_text_lower = jd_text.lower()
    
    # Enhanced role keywords for various domains
    role_keywords = {
        # Customer Success roles (highest priority for this test)
        'customer success': 'customer success manager',
        'customer success manager': 'customer success manager',
        'csm': 'customer success manager',
        'implementation specialist': 'implementation specialist',
        'onboarding specialist': 'implementation specialist',
        
        # ML/AI roles
        'machine learning engineer': 'machine learning engineer',
        'ml engineer': 'machine learning engineer',
        'ai engineer': 'machine learning engineer',
        'artificial intelligence engineer': 'machine learning engineer',
        'deep learning engineer': 'machine learning engineer',
        'machine learning': 'machine learning engineer',
        'artificial intelligence': 'machine learning engineer',
        'data scientist': 'data scientist',
        'research scientist': 'research scientist',
        'applied scientist': 'research scientist',
        'machine learning scientist': 'research scientist',
        'ai researcher': 'research scientist',
        
        # Engineering roles
        'software engineer': 'software engineer',
        'software developer': 'software engineer', 
        'senior engineer': 'senior software engineer',
        'lead engineer': 'lead software engineer',
        'full stack': 'full stack developer',
        'backend engineer': 'backend engineer',
        'frontend engineer': 'frontend engineer',
        'devops engineer': 'devops engineer',
        'data engineer': 'data engineer',
        'site reliability engineer': 'site reliability engineer',
        'sre': 'site reliability engineer',
        'quality assurance': 'quality assurance engineer',
        'qa engineer': 'quality assurance engineer',
        'test engineer': 'quality assurance engineer',
        
        # Sales roles
        'account executive': 'account executive',
        'sales executive': 'account executive',
        'sales manager': 'sales manager',
        'sales director': 'sales director',
        'sales development representative': 'sales development representative',
        'sdr': 'sales development representative',
        'business development representative': 'business development representative',
        'bdr': 'business development representative',
        
        # Product & Design roles
        'product manager': 'product manager',
        'product owner': 'product manager',
        'senior product manager': 'senior product manager',
        'technical product manager': 'technical product manager',
        'product designer': 'product designer',
        'ux designer': 'ux designer',
        'ui designer': 'ui designer',
        'designer': 'product designer',
        
        # Marketing roles
        'marketing manager': 'marketing manager',
        'growth marketer': 'growth marketing',
        'demand generation': 'demand generation',
        'content marketing': 'content marketing',
        'product marketing': 'product marketing',
        
        # Other roles
        'solution architect': 'solution architect',
        'solution consultant': 'solution consultant',
        'solutions engineer': 'solution consultant',
        'data analyst': 'data analyst',
        'business analyst': 'business analyst',
        'hr manager': 'hr manager',
        'recruiter': 'recruiter',
        'finance manager': 'finance manager',
        'customer support': 'customer support'
    }
    
    # Check for exact role matches (prioritize CSM roles)
    for keyword, canonical in role_keywords.items():
        if keyword in jd_text_lower:
            return canonical
    
    # Fallback to title aliases
    role_counter = Counter()
    for alias, canonical in title_aliases.items():
        if alias.lower() in jd_text_lower:
            role_counter[canonical] += 1
    if role_counter:
        return role_counter.most_common(1)[0][0]
    
    return None

def detect_target_company(jd_text):
    """Detect the hiring company from job description"""
    jd_lower = jd_text.lower()
    
    # Common company patterns
    company_patterns = [
        r'at\s+([A-Z][a-zA-Z\s&]+?)(?:\s|\.|,|$)',
        r'join\s+([A-Z][a-zA-Z\s&]+?)(?:\s|\.|,|$)',
        r'([A-Z][a-zA-Z\s&]+?)\s+is\s+seeking',
        r'([A-Z][a-zA-Z\s&]+?)\s+is\s+growing'
    ]
    
    for pattern in company_patterns:
        matches = re.findall(pattern, jd_text, re.IGNORECASE)
        if matches:
            company = matches[0].strip()
            # Clean up common suffixes
            for suffix in [' Inc', ' Ltd', ' Limited', ', Inc', ', Ltd', '.', ',']:
                if company.endswith(suffix):
                    company = company.replace(suffix, '')
            return company
    
    return None

def calculate_company_relevance(contact_company, jd_company, company_industry_tags):
    """Calculate company relevance score"""
    if not contact_company or not jd_company:
        return 0.0
    
    contact_lower = contact_company.lower()
    jd_lower = jd_company.lower()
    
    # Direct competitor bonus
    if contact_lower == jd_lower:
        return 0.0  # Exclude same company
    
    # Get industry tags for both companies
    contact_tags = set(company_industry_tags.get(contact_lower, []))
    jd_tags = set(company_industry_tags.get(jd_lower, []))
    
    # Calculate industry overlap
    if contact_tags and jd_tags:
        overlap = len(contact_tags & jd_tags)
        total = len(contact_tags | jd_tags)
        if total > 0:
            return (overlap / total) * 10.0  # Scale to 0-10
    
    return 0.0

def score_contact_csm_only(row, jd_skills, jd_platforms, jd_role, jd_company, jd_text):
    """Scoring function that ONLY prioritizes Customer Success Managers"""
    # Extract contact data
    contact_skills = eval(str(row.get("skills_tag", "[]")))
    contact_platforms = eval(str(row.get("platforms_tag", "[]")))
    contact_title = str(row.get("Position", "")).lower()
    contact_company = str(row.get("Company", "")).lower().strip()
    contact_seniority = str(row.get("seniority_tag", "")).lower()
    contact_function = str(row.get("function_tag", "")).lower()
    
    # Initialize scoring components
    skill_score = 0
    platform_score = 0
    role_score = 0
    company_score = 0
    seniority_score = 0
    function_score = 0
    
    # 1. Skill matching (weight: 3.0)
    skill_matches = set()
    for jd_skill in jd_skills:
        jd_skill_lower = jd_skill.lower()
        for contact_skill in contact_skills:
            contact_skill_lower = contact_skill.lower()
            # Check for exact matches and partial matches
            if (jd_skill_lower == contact_skill_lower or
                jd_skill_lower in contact_skill_lower or
                contact_skill_lower in jd_skill_lower or
                any(word in contact_skill_lower for word in jd_skill_lower.split())):
                skill_matches.add(jd_skill)
                break
    
    skill_score = len(skill_matches) * 3.0
    
    # 2. Platform matching (weight: 2.0)
    platform_matches = set()
    for jd_platform in jd_platforms:
        jd_platform_lower = jd_platform.lower()
        for contact_platform in contact_platforms:
            contact_platform_lower = contact_platform.lower()
            # Check for exact matches and partial matches
            if (jd_platform_lower == contact_platform_lower or
                jd_platform_lower in contact_platform_lower or
                contact_platform_lower in jd_platform_lower):
                platform_matches.add(jd_platform)
                break
    
    platform_score = len(platform_matches) * 2.0
    
    # 3. Role matching (weight: 1000.0) - MASSIVE weight for CSM role alignment
    if jd_role:
        # Special handling for Customer Success Manager alignment
        if jd_role == 'customer success manager':
            if 'customer success' in contact_title or 'csm' in contact_title:
                role_score += 1000.0  # MASSIVE bonus for exact CSM match
            elif 'account executive' in contact_title or 'sales' in contact_title:
                role_score += 10.0  # Small bonus for sales background
            elif 'consultant' in contact_title or 'implementation' in contact_title:
                role_score += 5.0  # Small bonus for consulting background
            elif 'software' in contact_title or 'engineer' in contact_title:
                role_score -= 50.0  # Penalty for technical roles (less relevant)
    
    # 4. Company relevance (weight: 2.0)
    if jd_company:
        company_score = calculate_company_relevance(contact_company, jd_company, company_industry_tags)
    
    # 5. Seniority matching (weight: 1.0)
    if "senior" in jd_text.lower() and "senior" in contact_seniority:
        seniority_score = 1.0
    elif "lead" in jd_text.lower() and "lead" in contact_seniority:
        seniority_score = 1.0
    elif "manager" in jd_text.lower() and "manager" in contact_title:
        seniority_score = 1.0
    
    # 6. Function matching (weight: 1.0)
    if contact_function and contact_function in jd_text.lower():
        function_score = 1.0
    
    # Calculate total score
    total_score = skill_score + platform_score + role_score + company_score + seniority_score + function_score
    
    return round(total_score, 2)

# Test with the Miro Customer Success Manager job description
if __name__ == "__main__":
    test_jd = """
    Miro is growing its Customer Success organization, and we are looking for customer-centric individuals! An Enterprise Customer Success Manager has many responsibilities - from crafting a rollout plan to establishing key relationships with both new and existing customers to co-creating a narrative around the value achieved with Miro. You will impact our customers immensely by helping them outline their visual collaboration objectives through the creation of a joint success plan. This plan will serve as the foundation to drive value across their journey with Miro. By building significant relationships with each Enterprise customer from their first day with Miro, you will understand our customer's needs and proactively identify ways in which they can interact with Miro to achieve their goals!

    What you'll do
    Have a keen eye on ensuring retention and growing usage and adoption across your book
    Uncover key contacts willing to partner around understanding the customer's business objectives and developing strategies to achieve those objectives via co-development of a success plan
    Drive Miro product adoption by collaborating with customers to understand their various lines of business and respective use case needs - work to devise an enablement plan
    Identify, improve, and lead all aspects of the health status of each of your customers
    Analyze data and use playbooks to drive both proactive and reactive engagements with the customer in the spirit of delivering impact to the customer journey
    Become a Miro product champion and use this knowledge to effectively guide customers towards their desired outcomes
    Participate in internal initiatives that inform the future of the Customer Success program at Miro
    What you'll need
    3-5+ years working as either a consultant at a professional service organization or in a Customer Success role
    Proven experience working with large enterprise customers, minimum 1 year
    Proven experience working with and influencing key decision makers (VP level and above decision makers)
    Demonstrable experience working on complex, cross-functional projects
    Experience working in a fast-paced environment and ability to adapt to change
    Willing and able to travel as needed
    Ability to work independently and prioritize tasks
    A proactive mentality and a general curiosity to seek to understand
    Visual Collaboration, Agile methodology, and Gainsight knowledge are a plus (not required)
    What's in it for you
    401k matching + Competitive equity package
    Excellent Medical, Dental and Vision health benefits
    Fertility & Family Forming Benefits
    Flexible time off
    Lunch, snacks and drinks provided in the office
    Wellbeing benefit and WFH equipment allowance
    Annual learning and development allowance to grow your skills and career
    Up to $2,000 of charitable donation matches each year
    #LI-LW1

    About Miro
    Miro is a visual workspace for innovation that enables distributed teams of any size to build the next big thing. The platform's infinite canvas enables teams to lead engaging workshops and meetings, design products, brainstorm ideas, and more. Miro, co-headquartered in San Francisco and Amsterdam, serves more than 90M users worldwide, including 99% of the Fortune 100. Miro was founded in 2011 and currently has more than 1,600 employees in 12 hubs around the world.

    We are a team of dreamers. We look for individuals who dream big, work hard, and above all stay humble. Collaboration is at the heart of what we do and through our work together we hope to create a supportive, welcoming, and innovative environment. We strive to play as a team to win the world and create a better version of ourselves every day. If this sounds like something that excites you, we want to hear from you!

    Check out more about life at Miro: 
    """
    
    print(f"\n🔍 Testing with Miro Customer Success Manager job description:")
    print("=" * 50)
    
    # Extract information from JD
    jd_skills, jd_platforms = extract_tags_from_jd(test_jd)
    jd_role = detect_role_from_jd(test_jd)
    jd_company = detect_target_company(test_jd)
    
    print(f"📊 JD Analysis Results:")
    print(f"   Skills found: {len(jd_skills)}")
    print(f"   Platforms found: {len(jd_platforms)}")
    print(f"   Role detected: {jd_role}")
    print(f"   Target company: {jd_company}")
    
    # Score all contacts with CSM-only priority
    print(f"\n🎯 Scoring {len(df)} contacts with CSM-only priority algorithm...")
    df["match_score"] = df.apply(
        lambda row: score_contact_csm_only(row, jd_skills, jd_platforms, jd_role, jd_company, test_jd), 
        axis=1
    )
    
    # Get top matches
    top_matches = df[df["match_score"] > 0].sort_values(by="match_score", ascending=False).head(10)
    
    print(f"\n✅ Top {len(top_matches)} Matches (CSM-Only Priority Algorithm):")
    print("=" * 80)
    
    for idx, row in top_matches.iterrows():
        skills = eval(str(row.get("skills_tag", "[]")))
        platforms = eval(str(row.get("platforms_tag", "[]")))
        skill_matches = set(skills) & set(jd_skills)
        platform_matches = set(platforms) & set(jd_platforms)
        
        print(f"\n#{idx+1}: {row['First Name']} {row['Last Name']} - {row['Position']} at {row['Company']}")
        print(f"   Score: {row['match_score']}")
        print(f"   Skills: {list(skill_matches)}")
        print(f"   Platforms: {list(platform_matches)}")
        print(f"   Seniority: {row.get('seniority_tag', 'N/A')}")
        print(f"   Function: {row.get('function_tag', 'N/A')}")
    
    print(f"\n📊 Summary:")
    print(f"   Total contacts processed: {len(df)}")
    print(f"   Contacts with scores > 0: {len(df[df['match_score'] > 0])}")
    print(f"   Average score: {df['match_score'].mean():.2f}")
    print(f"   Max score: {df['match_score'].max():.2f}")
    print(f"   Min score: {df['match_score'].min():.2f}")
    
    # Save results
    top_matches[["First Name", "Last Name", "Position", "Company", "match_score"]].to_csv("csm_only_results.csv", index=False)
    print(f"\n📄 Results saved to csm_only_results.csv") 