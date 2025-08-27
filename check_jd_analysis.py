import pandas as pd
import json
from collections import Counter
import re
from rapidfuzz import process, fuzz

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

# Test JD
jd_text = """
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

# Analyze JD
jd_skills, jd_platforms = extract_tags_from_jd(jd_text)
jd_role = detect_role_from_jd(jd_text)
jd_company = detect_target_company(jd_text)

print(f"\n📊 JD Analysis Results:")
print(f"   Skills found: {len(jd_skills)}")
print(f"   Platforms found: {len(jd_platforms)}")
print(f"   Role detected: {jd_role}")
print(f"   Target company: {jd_company}")

print(f"\n📋 Sample skills found:")
for skill in jd_skills[:20]:
    print(f"   - {skill}")

print(f"\n📋 Sample platforms found:")
for platform in jd_platforms[:20]:
    print(f"   - {platform}")

print(f"\n🎯 Role Analysis:")
print(f"   Detected role: {jd_role}")
print(f"   Company: {jd_company}") 