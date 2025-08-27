import pandas as pd
import json
from rapidfuzz import process

print("✅ Script is running")

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
        print(f"✅ MATCH: {original} → {company_tags[company]}")
        return company_tags[company].get("industry"), company_tags[company].get("company_type")
    else:
        print(f"❌ NO MATCH: '{original}' (normalised: '{company}')")
        return None, None

def fuzzy_alias_lookup(title, aliases, threshold=85):
    title = title.lower().strip()
    best_match = process.extractOne(title, aliases.keys())
    if best_match and best_match[1] >= threshold:
        return aliases[best_match[0]]
    return title

def tag_role_enrichment(title, company):
    raw_title = str(title).lower().strip()
    title = fuzzy_alias_lookup(raw_title, title_aliases)
    company = str(company).lower().strip()
    skills = set()
    platforms = set()

    # Generic (any company)
    if f"any:{title}" in role_enrichment:
        entry = role_enrichment[f"any:{title}"]
        skills.update(entry.get("skills", []))
        platforms.update(entry.get("platforms", []))
        print(f"✅ Found generic role enrichment for '{title}': {len(skills)} skills, {len(platforms)} platforms")

    # Company-specific
    if f"{company}:{title}" in role_enrichment:
        entry = role_enrichment[f"{company}:{title}"]
        skills.update(entry.get("skills", []))
        platforms.update(entry.get("platforms", []))
        print(f"✅ Found company-specific role enrichment for '{company}:{title}': {len(skills)} skills, {len(platforms)} platforms")

    # If no exact match, try partial matches
    if not skills and not platforms:
        # Try to match partial title components
        title_words = title.split()
        for word in title_words:
            if len(word) > 3:  # Only consider meaningful words
                for role_key, role_data in role_enrichment.items():
                    if word in role_key.lower():
                        skills.update(role_data.get("skills", []))
                        platforms.update(role_data.get("platforms", []))
                        print(f"🔄 Partial match for '{word}' in '{title}': {len(skills)} skills, {len(platforms)} platforms")
                        break

    # If still no matches, try common role patterns
    if not skills and not platforms:
        common_patterns = {
            "engineer": ["any:software engineer", "any:senior engineer", "any:lead engineer"],
            "manager": ["any:product manager", "any:project manager", "any:engineering manager"],
            "director": ["any:director", "any:senior director"],
            "executive": ["any:account executive", "any:sales executive"],
            "designer": ["any:product designer", "any:ux designer", "any:ui designer"],
            "developer": ["any:software developer", "any:senior developer"],
            "analyst": ["any:data analyst", "any:business analyst"],
            "specialist": ["any:technical specialist", "any:sales specialist"],
            "consultant": ["any:consultant", "any:senior consultant"],
            "coordinator": ["any:coordinator", "any:project coordinator"]
        }
        
        for pattern, role_keys in common_patterns.items():
            if pattern in title:
                for role_key in role_keys:
                    if role_key in role_enrichment:
                        entry = role_enrichment[role_key]
                        skills.update(entry.get("skills", []))
                        platforms.update(entry.get("platforms", []))
                        print(f"🎯 Pattern match '{pattern}' for '{title}': {len(skills)} skills, {len(platforms)} platforms")
                        break
                if skills or platforms:
                    break

    return list(skills), list(platforms)

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

print("🎯 Applying role enrichment...")
df["skills_tag"], df["platforms_tag"] = zip(*df.apply(lambda row: tag_role_enrichment(row["Position"], row["Company"]), axis=1))
df["company_industry_tags"] = df["Company"].fillna("").apply(tag_company_industry_keywords)

# Analyze tagging results
total_contacts = len(df)
contacts_with_skills = len(df[df["skills_tag"].apply(lambda x: len(eval(str(x))) > 0)])
contacts_with_platforms = len(df[df["platforms_tag"].apply(lambda x: len(eval(str(x))) > 0)])

print(f"\n📊 Tagging Results:")
print(f"   Total contacts: {total_contacts}")
print(f"   Contacts with skills: {contacts_with_skills} ({contacts_with_skills/total_contacts*100:.1f}%)")
print(f"   Contacts with platforms: {contacts_with_platforms} ({contacts_with_platforms/total_contacts*100:.1f}%)")

# Show some examples
print(f"\n📋 Sample tagged contacts:")
sample_contacts = df[df["skills_tag"].apply(lambda x: len(eval(str(x))) > 0)].head(5)
for idx, row in sample_contacts.iterrows():
    skills = eval(str(row["skills_tag"]))
    platforms = eval(str(row["platforms_tag"]))
    print(f"   {row['First Name']} {row['Last Name']} - {row['Position']}")
    print(f"     Skills: {skills[:3]}...")  # Show first 3 skills
    print(f"     Platforms: {platforms[:3]}...")  # Show first 3 platforms

# Export results
df.to_csv("tagged_contacts2.csv", index=False)
print("\n✅ Tagging complete. Output saved to tagged_contacts2.csv")
