import pandas as pd
import json
from collections import Counter
import re
from rapidfuzz import process, fuzz

print("🎯 Generic Role-Agnostic Job Matcher")
print("=" * 50)

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

print(f"📊 Loaded {len(all_skills)} skills and {len(all_platforms)} platforms")

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
        # ML/AI roles (highest priority)
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
        
        # Customer Success roles
        'customer success': 'customer success manager',
        'customer success manager': 'customer success manager',
        'csm': 'customer success manager',
        'implementation specialist': 'implementation specialist',
        'onboarding specialist': 'implementation specialist',
        
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
    
    # Check for exact role matches (prioritize ML/AI roles)
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

def fuzzy_match_title(title, aliases, threshold=85):
    """Fuzzy match title to canonical role"""
    title = title.lower().strip()
    best_match = process.extractOne(title, aliases.keys())
    if best_match and best_match[1] >= threshold:
        return aliases[best_match[0]]
    return None

def calculate_role_similarity(jd_role, contact_role):
    """Calculate similarity between JD role and contact role"""
    if not jd_role or not contact_role:
        return 0.0
    
    jd_words = set(jd_role.lower().split())
    contact_words = set(contact_role.lower().split())
    
    # Exact match
    if jd_role.lower() == contact_role.lower():
        return 1.0
    
    # High similarity (most words match)
    common_words = jd_words & contact_words
    if len(common_words) >= min(len(jd_words), len(contact_words)) * 0.7:
        return 0.8
    
    # Medium similarity (some words match)
    if len(common_words) >= 1:
        return 0.5
    
    return 0.0

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

def score_contact_generic(row, jd_skills, jd_platforms, jd_role, jd_company, jd_text):
    """Generic scoring function that works for any role"""
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
    
    # 1. Skill matching (weight: 3.0) - Improved matching
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
    
    # 2. Platform matching (weight: 2.0) - Improved matching
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
    
    # 3. Role matching (weight: 5.0)
    if jd_role:
        # Try to match contact title to canonical role
        contact_canonical_role = fuzzy_match_title(contact_title, title_aliases)
        if contact_canonical_role:
            role_similarity = calculate_role_similarity(jd_role, contact_canonical_role)
            role_score = role_similarity * 5.0
        
        # Also check for exact title matches
        if jd_role.lower() in contact_title:
            role_score += 3.0
    
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
    
    # Store debug info
    row['_skill_matches'] = list(skill_matches)
    row['_platform_matches'] = list(platform_matches)
    row['_skill_score'] = skill_score
    row['_platform_score'] = platform_score
    row['_role_score'] = role_score
    row['_company_score'] = company_score
    row['_seniority_score'] = seniority_score
    row['_function_score'] = function_score
    
    return round(total_score, 2)

def match_job_to_contacts(jd_text):
    """Main function to match job description to contacts"""
    print(f"\n🔍 Analyzing job description...")
    
    # Extract information from JD
    jd_skills, jd_platforms = extract_tags_from_jd(jd_text)
    jd_role = detect_role_from_jd(jd_text)
    jd_company = detect_target_company(jd_text)
    
    print(f"📊 JD Analysis Results:")
    print(f"   Skills found: {jd_skills}")
    print(f"   Platforms found: {jd_platforms}")
    print(f"   Role detected: {jd_role}")
    print(f"   Target company: {jd_company}")
    
    # Score all contacts
    print(f"\n🎯 Scoring {len(df)} contacts...")
    df["match_score"] = df.apply(
        lambda row: score_contact_generic(row, jd_skills, jd_platforms, jd_role, jd_company, jd_text), 
        axis=1
    )
    
    # Store debug info
    df["_skill_score"] = df.apply(lambda row: row.get('_skill_score', 0), axis=1)
    df["_platform_score"] = df.apply(lambda row: row.get('_platform_score', 0), axis=1)
    df["_role_score"] = df.apply(lambda row: row.get('_role_score', 0), axis=1)
    df["_company_score"] = df.apply(lambda row: row.get('_company_score', 0), axis=1)
    df["_seniority_score"] = df.apply(lambda row: row.get('_seniority_score', 0), axis=1)
    df["_function_score"] = df.apply(lambda row: row.get('_function_score', 0), axis=1)
    
    # Get top matches
    top_matches = df[df["match_score"] > 0].sort_values(by="match_score", ascending=False).head(10)
    
    print(f"\n✅ Top {len(top_matches)} Matches:")
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
        print(f"   Skill Score: {row.get('_skill_score', 0)}")
        print(f"   Platform Score: {row.get('_platform_score', 0)}")
        print(f"   Role Score: {row.get('_role_score', 0)}")
        print(f"   Company Score: {row.get('_company_score', 0)}")
        print(f"   Seniority: {row.get('seniority_tag', 'N/A')}")
        print(f"   Function: {row.get('function_tag', 'N/A')}")
    
    print(f"\n📊 Summary:")
    print(f"   Total contacts processed: {len(df)}")
    print(f"   Contacts with scores > 0: {len(df[df['match_score'] > 0])}")
    print(f"   Average score: {df['match_score'].mean():.2f}")
    print(f"   Max score: {df['match_score'].max():.2f}")
    print(f"   Min score: {df['match_score'].min():.2f}")
    
    return top_matches

# Test with the Figma ML/AI Engineer job description
if __name__ == "__main__":
    test_jd = """
    Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma's platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code, or iterating with AI. From idea to product, Figma empowers teams to streamline workflows, move faster, and work together in real time from anywhere in the world. If you're excited to shape the future of design and collaboration, join us!

    Figma is seeking a versatile and experienced Machine Learning / AI Engineer to join our growing AI team, working at the intersection of applied machine learning, infrastructure, and product innovation. Whether you're building intelligent search systems, crafting scalable data pipelines, or enhancing AI-powered creativity tools, your work will drive user productivity, shape new product experiences, and advance the state of AI at Figma.

    You'll collaborate closely with engineers, researchers, designers, and product managers across multiple teams to deliver high-quality ML-driven features and infrastructure. This is a high-impact, cross-functional role where you'll shape both foundational systems and user-facing capabilities.

    This is a full time role that can be held from one of our US hubs or remotely in the United States.

    What you'll do at Figma:
    Design, build, and productionize ML models for Search, Discovery, Ranking, Retrieval-Augmented Generation (RAG), and generative AI features.
    Build and maintain scalable data pipelines to collect high-quality training and evaluation datasets, including annotation systems and human-in-the-loop workflows.
    Collaborate with AI researchers to iterate on datasets, evaluation metrics, and model architectures to improve quality and relevance.
    Work with product engineers to define and deliver impactful AI features across Figma's platform.
    Partner with infrastructure engineers to develop and optimize systems for training, inference, monitoring, and deployment.
    Explore new ideas at the edge of what's technically possible and help shape the long-term AI vision at Figma.
    We'd love to hear from you If you have:
    5+ years of industry experience in software engineering, with 3+ years focused on applied machine learning or AI.
    Strong experience with end-to-end ML model development, including training, evaluation, deployment, and monitoring.
    Proficiency in Python and familiarity with ML libraries like PyTorch, TensorFlow, Scikit-learn, Spark MLlib, or XGBoost.
    Experience designing and building scalable data and annotation pipelines, as well as evaluation systems for AI model quality.
    Experience mentoring or leading others and contributing to a culture of technical excellence and innovation.
    While not required, It's an added plus if you also have:
    Familiarity with search relevance, ranking, NLP, or RAG systems.
    Experience with AI infrastructure and MLOps, including observability, CI/CD, and automation for ML workflows.
    Experience working on creative or design-focused ML applications.
    Knowledge of additional languages such as C++ or Go is a plus, but not required.
    A product mindset with the ability to tie technical work to user outcomes and business impact.
    Strong collaboration and communication skills, especially when working across functions (engineering, product, research).
    At Figma, one of our values is Grow as you go. We believe in hiring smart, curious people who are excited to learn and develop their skills. If you're excited about this role but your past experience doesn't align perfectly with the points outlined in the job description, we encourage you to apply anyways. You may be just the right candidate for this or other roles.
    Pay Transparency Disclosure

    If based in Figma's San Francisco or New York hub offices, this role has the annual base salary range stated below.
    """
    
    print(f"\n🔍 Testing with Figma ML/AI Engineer job description:")
    print("=" * 50)
    print(test_jd)
    
    top_matches = match_job_to_contacts(test_jd)
    
    # Save results
    top_matches[["First Name", "Last Name", "Position", "Company", "match_score"]].to_csv("generic_matcher_results.csv", index=False)
    print(f"\n📄 Results saved to generic_matcher_results.csv") 