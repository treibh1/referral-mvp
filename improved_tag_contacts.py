#!/usr/bin/env python3
"""
Improved contact tagging script that fixes skill accumulation issues
"""

import pandas as pd
import json
from rapidfuzz import process

print("✅ Improved tagging script is running")

# Load mapping files
with open("tag_mapping.json", "r") as f:
    mappings = json.load(f)

with open("company_tags.json", "r") as f:
    company_tags = json.load(f)

with open("role_enrichment.json", "r") as f:
    role_enrichment = json.load(f)

with open("title_aliases.json", "r") as f:
    title_aliases = json.load(f)

with open("company_industry_tags_usev2.json", "r") as f:
    company_industry_tags = json.load(f)

print(f"📊 Loaded {len(role_enrichment)} role enrichments")
print(f"📊 Loaded {len(title_aliases)} title aliases")

# --- Helper Functions ---

def tag_title(title):
    title = str(title).lower()
    function = next((v for k, v in mappings["function_map"].items() if k in title), None)
    seniority = next((v for k, v in mappings["seniority_map"].items() if k in title), None)
    return function, seniority

def tag_company(company):
    original = str(company)
    company = original.lower().strip()
    for suffix in [" inc", " ltd", " limited", ", inc", ", ltd", ".", ","]:
        if company.endswith(suffix):
            company = company.replace(suffix, "")
    if company in company_tags:
        return company_tags[company].get("industry"), company_tags[company].get("company_type")
    else:
        return None, None

def fuzzy_alias_lookup(title, aliases, threshold=85):
    title = title.lower().strip()
    best_match = process.extractOne(title, aliases.keys())
    if best_match and best_match[1] >= threshold:
        return aliases[best_match[0]]
    return title

def improved_tag_role_enrichment(title, company):
    """
    Improved role enrichment that prevents skill accumulation and prioritizes exact matches
    """
    raw_title = str(title).lower().strip()
    title = fuzzy_alias_lookup(raw_title, title_aliases)
    company = str(company).lower().strip()
    
    # Priority 1: Exact company-specific match
    company_specific_key = f"{company}:{title}"
    if company_specific_key in role_enrichment:
        entry = role_enrichment[company_specific_key]
        skills = entry.get("skills", [])
        platforms = entry.get("platforms", [])
        print(f"✅ Company-specific match: '{company_specific_key}' -> {len(skills)} skills, {len(platforms)} platforms")
        return skills, platforms
    
    # Priority 2: Exact generic match
    generic_key = f"any:{title}"
    if generic_key in role_enrichment:
        entry = role_enrichment[generic_key]
        skills = entry.get("skills", [])
        platforms = entry.get("platforms", [])
        print(f"✅ Generic match: '{generic_key}' -> {len(skills)} skills, {len(platforms)} platforms")
        return skills, platforms
    
    # Priority 3: Smart partial matching (only for specific role patterns)
    # Define specific role patterns that should match
    role_patterns = {
        "software engineer": ["software engineer", "senior engineer", "lead engineer", "principal engineer"],
        "data scientist": ["data scientist", "machine learning engineer", "ml engineer"],
        "data analyst": ["data analyst", "business analyst"],
        "product manager": ["product manager", "senior product manager", "principal product manager"],
        "account executive": ["account executive", "sales executive", "enterprise sales", "strategic account executive"],
        "sales manager": ["sales manager", "sales director", "revenue manager"],
        "sales development representative": ["sales development representative", "sdr", "business development representative", "bdr"],
        "customer success": ["customer success manager", "customer experience manager"],
        "solution architect": ["solution architect", "principal architect", "senior architect"],
        "devops engineer": ["devops engineer", "site reliability engineer", "platform engineer"],
        "frontend engineer": ["frontend engineer", "ui engineer", "front-end engineer"],
        "backend engineer": ["backend engineer", "api engineer", "back-end engineer"],
        "marketing manager": ["marketing manager", "senior marketing manager", "marketing director"],
        "content manager": ["content manager", "content marketing manager", "editorial manager"],
        "seo specialist": ["seo specialist", "seo manager", "search engine optimizer"],
        "ux designer": ["ux designer", "user experience designer", "senior ux designer"],
        "ui designer": ["ui designer", "user interface designer", "senior ui designer"],
        "product designer": ["product designer", "senior product designer", "principal product designer"],
        "operations manager": ["operations manager", "senior operations manager", "operations director"],
        "business operations": ["business operations", "business operations manager", "operations analyst"],
        "legal counsel": ["legal counsel", "attorney", "lawyer", "senior counsel"],
        "customer support": ["customer support", "customer service", "support specialist"],
        "technical support": ["technical support", "tech support", "support engineer"],
        "payroll specialist": ["payroll specialist", "payroll administrator", "payroll coordinator"],
        "accountant": ["accountant", "senior accountant", "staff accountant"],
        "financial analyst": ["financial analyst", "senior financial analyst", "finance analyst"]
    }
    
    # Check if title matches any of our specific patterns
    for role_name, patterns in role_patterns.items():
        for pattern in patterns:
            if pattern in title:
                # Look for the corresponding role in enrichment
                role_key = f"any:{role_name}"
                if role_key in role_enrichment:
                    entry = role_enrichment[role_key]
                    skills = entry.get("skills", [])
                    platforms = entry.get("platforms", [])
                    print(f"🔄 Pattern match: '{title}' -> '{role_key}' -> {len(skills)} skills, {len(platforms)} platforms")
                    return skills, platforms
    
    # Priority 4: Very specific word matching (only for clear cases)
    specific_words = {
        "engineer": "any:software engineer",
        "developer": "any:software engineer", 
        "scientist": "any:data scientist",
        "analyst": "any:data analyst",
        "executive": "any:account executive",
        "architect": "any:solution architect",
        "designer": "any:ux designer",
        "marketing": "any:marketing manager",
        "content": "any:content manager",
        "seo": "any:seo specialist",
        "support": "any:customer support",
        "operations": "any:operations manager",
        "legal": "any:legal counsel"
    }
    
    title_words = title.split()
    for word in title_words:
        if word in specific_words:
            role_key = specific_words[word]
            if role_key in role_enrichment:
                entry = role_enrichment[role_key]
                skills = entry.get("skills", [])
                platforms = entry.get("platforms", [])
                print(f"🎯 Word match: '{word}' in '{title}' -> '{role_key}' -> {len(skills)} skills, {len(platforms)} platforms")
                return skills, platforms
    
    # No match found
    print(f"❌ No match found for: '{title}'")
    return [], []

def tag_company_industry_keywords(company):
    company = str(company).lower().strip()
    for suffix in [" inc", " ltd", " limited", ", inc", ", ltd", ".", ","]:
        if company.endswith(suffix):
            company = company.replace(suffix, "")
    return company_industry_tags.get(company, [])

# --- Main Execution ---

# Load contacts CSV
df = pd.read_csv("linkedin-contacts2.csv")
print(f"📊 Processing {len(df)} contacts")

# Apply tagging
df["function_tag"], df["seniority_tag"] = zip(*df["Position"].fillna("").apply(tag_title))
df["industry_tag"], df["company_type_tag"] = zip(*df["Company"].fillna("").apply(tag_company))

print("🎯 Applying improved role enrichment...")
df["skills_tag"], df["platforms_tag"] = zip(*df.apply(lambda row: improved_tag_role_enrichment(row["Position"], row["Company"]), axis=1))
df["company_industry_tags"] = df["Company"].fillna("").apply(tag_company_industry_keywords)

# Analyze tagging results
total_contacts = len(df)
contacts_with_skills = len(df[df["skills_tag"].apply(lambda x: len(x) > 0)])
contacts_with_platforms = len(df[df["platforms_tag"].apply(lambda x: len(x) > 0)])

print(f"\n📊 Improved Tagging Results:")
print(f"   Total contacts: {total_contacts}")
print(f"   Contacts with skills: {contacts_with_skills} ({contacts_with_skills/total_contacts*100:.1f}%)")
print(f"   Contacts with platforms: {contacts_with_platforms} ({contacts_with_platforms/total_contacts*100:.1f}%)")

# Show distribution of skills by role type
print(f"\n📋 Skill distribution by role type:")
role_skill_counts = {}
for idx, row in df.iterrows():
    if len(row["skills_tag"]) > 0:
        role_type = row["function_tag"] if pd.notna(row["function_tag"]) else "Unknown"
        if role_type not in role_skill_counts:
            role_skill_counts[role_type] = []
        role_skill_counts[role_type].append(len(row["skills_tag"]))

for role_type, counts in sorted(role_skill_counts.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
    avg_skills = sum(counts) / len(counts)
    print(f"   {role_type}: {len(counts)} contacts, avg {avg_skills:.1f} skills")

# Show some examples
print(f"\n📋 Sample improved tagged contacts:")
sample_contacts = df[df["skills_tag"].apply(lambda x: len(x) > 0)].head(5)
for idx, row in sample_contacts.iterrows():
    skills = row["skills_tag"]
    platforms = row["platforms_tag"]
    print(f"   {row['First Name']} {row['Last Name']} - {row['Position']}")
    print(f"     Function: {row['function_tag']}")
    print(f"     Skills: {skills[:3]}...")  # Show first 3 skills
    print(f"     Platforms: {platforms[:3]}...")  # Show first 3 platforms

# Export results
df.to_csv("improved_tagged_contacts.csv", index=False)
print("\n✅ Improved tagging complete. Output saved to improved_tagged_contacts.csv")
