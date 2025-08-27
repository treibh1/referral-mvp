import pandas as pd
import json
from collections import Counter
import re
from rapidfuzz import process, fuzz 

print("✅ Script is running")

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

# Fuzzy match to title aliases
def match_title_alias(title, threshold=85):
    title = title.lower().strip()
    best_match = process.extractOne(title, title_aliases.keys())
    if best_match and best_match[1] >= threshold:
        return title_aliases[best_match[0]]
    return None

# Match JD to canonical role
def detect_role_from_jd(jd_text):
    jd_text_lower = jd_text.lower()
    role_counter = Counter()
    for alias, canonical in title_aliases.items():
        if alias.lower() in jd_text_lower:
            role_counter[canonical] += 1
    if role_counter:
        return role_counter.most_common(1)[0][0]  # Return top canonical role
    return None

# Extract tags from job description with better matching
def extract_tags_from_jd(jd_text):
    jd_text_lower = jd_text.lower()
    matched_skills = []
    matched_platforms = []
    
    # More sophisticated skill matching
    for skill in all_skills:
        skill_lower = skill.lower()
        # Check for exact matches and variations
        if (skill_lower in jd_text_lower or 
            skill_lower.replace(' ', '') in jd_text_lower.replace(' ', '') or
            any(word in jd_text_lower for word in skill_lower.split())):
            matched_skills.append(skill)
    
    # Platform matching
    for platform in all_platforms:
        platform_lower = platform.lower()
        if platform_lower in jd_text_lower:
            matched_platforms.append(platform)
    
    return matched_skills, matched_platforms

# Infer company from JD text
def detect_company_from_jd(jd_text, known_companies):
    jd_lower = jd_text.lower()
    best_match = process.extractOne(jd_lower, known_companies, scorer=fuzz.partial_ratio)
    if best_match and best_match[1] >= 85:
        return best_match[0]
    return None

# Input JD
print("📋 Paste in the full Job Description (end with ENTER + CTRL-D):")
jd = ""
try:
    while True:
        jd += input() + "\n"
except EOFError:
    pass

# Extract from JD
jd_skills, jd_platforms = extract_tags_from_jd(jd)
jd_canonical_role = detect_role_from_jd(jd)

print(f"🔍 JD Analysis:")
print(f"   Skills found: {jd_skills}")
print(f"   Platforms found: {jd_platforms}")
print(f"   Role detected: {jd_canonical_role}")

# Company bias detection
known_companies = list(company_industry_tags.keys())
target_company = detect_company_from_jd(jd, known_companies)
jd_tags_from_company = company_industry_tags.get(target_company, []) if target_company else []
if target_company:
    print(f"🏢 Matched JD company: {target_company}")

# Enhanced scoring function with detailed breakdown
def score_contact(row):
    contact_skills = eval(row.get("skills_tag", "[]"))
    contact_platforms = eval(row.get("platforms_tag", "[]"))
    contact_title = str(row.get("Position", "")).lower()
    contact_company = str(row.get("Company", "")).lower().strip()
    company_tags = eval(row.get("company_industry_tags", "[]"))
    contact_seniority = str(row.get("seniority_tag", "")).lower()
    contact_function = str(row.get("function_tag", "")).lower()
    
    # Initialize scoring components
    skill_score = 0
    platform_score = 0
    role_score = 0
    company_score = 0
    industry_score = 0
    seniority_bonus = 0
    
    # Skill matching (weighted by relevance)
    skill_matches = set(contact_skills) & set(jd_skills)
    skill_score = len(skill_matches) * 2.0  # Increased weight for skills
    
    # Platform matching
    platform_matches = set(contact_platforms) & set(jd_platforms)
    platform_score = len(platform_matches) * 1.5
    
    # Role matching with fuzzy matching
    matched_contact_role = match_title_alias(contact_title)
    if matched_contact_role and matched_contact_role == jd_canonical_role:
        role_score = 8.0  # High weight for exact role match
    elif matched_contact_role:
        # Partial role match
        role_score = 3.0
    
    # Company matching
    if contact_company == target_company:
        company_score = 3.0
    
    # Industry tag matching
    industry_matches = set(company_tags) & set(jd_tags_from_company)
    industry_score = len(industry_matches) * 0.5
    
    # Seniority bonus (prefer senior candidates for senior roles)
    if "senior" in jd.lower() and "senior" in contact_seniority:
        seniority_bonus = 2.0
    elif "lead" in jd.lower() and "lead" in contact_seniority:
        seniority_bonus = 2.0
    elif "director" in jd.lower() and "director" in contact_seniority:
        seniority_bonus = 2.0
    
    # Calculate total score
    total_score = skill_score + platform_score + role_score + company_score + industry_score + seniority_bonus
    
    # Store detailed breakdown for debugging
    row['_skill_score'] = skill_score
    row['_platform_score'] = platform_score
    row['_role_score'] = role_score
    row['_company_score'] = company_score
    row['_industry_score'] = industry_score
    row['_seniority_bonus'] = seniority_bonus
    row['_skill_matches'] = list(skill_matches)
    row['_platform_matches'] = list(platform_matches)
    row['_matched_role'] = matched_contact_role
    
    return round(total_score, 2)

# Score contacts
print("🎯 Scoring contacts...")
df["match_score"] = df.apply(score_contact, axis=1)

# Display top matches with detailed breakdown
top_matches = df[df["match_score"] > 0].sort_values(by="match_score", ascending=False).head(20)

print(f"\n✅ Top {len(top_matches)} Matches:")
print("=" * 80)

for idx, row in top_matches.iterrows():
    print(f"\n#{idx+1}: {row['First Name']} {row['Last Name']} - {row['Position']} at {row['Company']}")
    print(f"   Total Score: {row['match_score']}")
    print(f"   Skills: {row['_skill_matches']} (score: {row['_skill_score']})")
    print(f"   Platforms: {row['_platform_matches']} (score: {row['_platform_score']})")
    print(f"   Role: {row['_matched_role']} (score: {row['_role_score']})")
    print(f"   Company match: {row['_company_score']}")
    print(f"   Industry: {row['_industry_score']}")
    print(f"   Seniority bonus: {row['_seniority_bonus']}")

# Save to CSV with detailed breakdown
output_columns = ["First Name", "Last Name", "Position", "Company", "match_score", 
                  "_skill_score", "_platform_score", "_role_score", "_company_score", 
                  "_industry_score", "_seniority_bonus", "_skill_matches", "_platform_matches", "_matched_role"]
top_matches[output_columns].to_csv("jd_matches_detailed.csv", index=False)
print("\n📄 Detailed results saved to jd_matches_detailed.csv")

# Also save the original format
top_matches[["First Name", "Last Name", "Position", "Company", "match_score"]].to_csv("jd_matches.csv", index=False)
print("📄 Results saved to jd_matches.csv")
