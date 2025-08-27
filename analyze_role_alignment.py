import pandas as pd
import json
from collections import Counter
import re
from rapidfuzz import process, fuzz

print("🎯 Role Alignment Analysis: ML Engineer vs Software Developer vs Solution Architect")
print("=" * 80)

# Load tagged contacts
df = pd.read_csv("tagged_contacts2.csv")

# Load enrichment terms
with open("role_enrichment.json", "r") as f:
    role_enrichment = json.load(f)

with open("title_aliases.json", "r") as f:
    title_aliases = json.load(f)

# Define the three role types we want to compare
target_roles = {
    'machine learning engineer': 'ML/AI Engineer',
    'software engineer': 'Software Engineer', 
    'solution architect': 'Solution Architect'
}

# Get contacts for each role type
role_contacts = {}
for role_key, role_name in target_roles.items():
    # Find contacts with this role in their title
    role_contacts[role_name] = df[df['Position'].str.contains(role_key, case=False, na=False)]
    print(f"\n📊 {role_name} Analysis:")
    print(f"   Found {len(role_contacts[role_name])} contacts")
    if len(role_contacts[role_name]) > 0:
        print(f"   Sample titles: {list(role_contacts[role_name]['Position'].head(5))}")

# Analyze skills for each role type
print(f"\n🔍 Skills Analysis by Role Type:")
for role_name, contacts in role_contacts.items():
    if len(contacts) > 0:
        # Get all skills for this role type
        all_skills = []
        for idx, row in contacts.iterrows():
            skills = eval(str(row.get("skills_tag", "[]")))
            all_skills.extend(skills)
        
        # Count most common skills
        skill_counts = Counter(all_skills)
        print(f"\n📋 {role_name} - Top 10 Skills:")
        for skill, count in skill_counts.most_common(10):
            print(f"   - {skill}: {count}")

# Analyze platforms for each role type
print(f"\n🔧 Platforms Analysis by Role Type:")
for role_name, contacts in role_contacts.items():
    if len(contacts) > 0:
        # Get all platforms for this role type
        all_platforms = []
        for idx, row in contacts.iterrows():
            platforms = eval(str(row.get("platforms_tag", "[]")))
            all_platforms.extend(platforms)
        
        # Count most common platforms
        platform_counts = Counter(all_platforms)
        print(f"\n📱 {role_name} - Top 10 Platforms:")
        for platform, count in platform_counts.most_common(10):
            print(f"   - {platform}: {count}")

# Check what skills are in the role_enrichment for ML Engineer
print(f"\n🎯 ML Engineer Role Enrichment Analysis:")
ml_engineer_skills = role_enrichment.get('any:machine learning engineer', {}).get('skills', [])
ml_engineer_platforms = role_enrichment.get('any:machine learning engineer', {}).get('platforms', [])

print(f"ML Engineer skills in enrichment: {len(ml_engineer_skills)}")
print(f"ML Engineer platforms in enrichment: {len(ml_engineer_platforms)}")
print(f"Sample ML Engineer skills: {ml_engineer_skills[:10]}")
print(f"Sample ML Engineer platforms: {ml_engineer_platforms[:10]}")

# Check what skills are in the role_enrichment for Software Engineer
print(f"\n💻 Software Engineer Role Enrichment Analysis:")
software_engineer_skills = role_enrichment.get('any:software engineer', {}).get('skills', [])
software_engineer_platforms = role_enrichment.get('any:software engineer', {}).get('platforms', [])

print(f"Software Engineer skills in enrichment: {len(software_engineer_skills)}")
print(f"Software Engineer platforms in enrichment: {len(software_engineer_platforms)}")
print(f"Sample Software Engineer skills: {software_engineer_skills[:10]}")
print(f"Sample Software Engineer platforms: {software_engineer_platforms[:10]}")

# Check what skills are in the role_enrichment for Solution Architect
print(f"\n🏗️ Solution Architect Role Enrichment Analysis:")
solution_architect_skills = role_enrichment.get('any:solution architect', {}).get('skills', [])
solution_architect_platforms = role_enrichment.get('any:solution architect', {}).get('platforms', [])

print(f"Solution Architect skills in enrichment: {len(solution_architect_skills)}")
print(f"Solution Architect platforms in enrichment: {len(solution_architect_platforms)}")
print(f"Sample Solution Architect skills: {solution_architect_skills[:10]}")
print(f"Sample Solution Architect platforms: {solution_architect_platforms[:10]}")

# Compare overlap with ML Engineer requirements
print(f"\n🔍 Skill Overlap Analysis:")
ml_required_skills = ['python', 'machine learning', 'deep learning', 'data science', 'ai', 'artificial intelligence', 'pytorch', 'tensorflow', 'scikit-learn', 'xgboost', 'spark', 'mlops', 'model training', 'model deployment', 'data pipelines', 'feature engineering']

for role_name, contacts in role_contacts.items():
    if len(contacts) > 0:
        # Get all skills for this role type
        all_skills = []
        for idx, row in contacts.iterrows():
            skills = eval(str(row.get("skills_tag", "[]")))
            all_skills.extend(skills)
        
        # Check overlap with ML required skills
        all_skills_lower = [skill.lower() for skill in all_skills]
        ml_overlap = 0
        for ml_skill in ml_required_skills:
            if any(ml_skill in skill for skill in all_skills_lower):
                ml_overlap += 1
        
        print(f"\n{role_name}:")
        print(f"   Total skills: {len(set(all_skills))}")
        print(f"   ML skill overlap: {ml_overlap}/{len(ml_required_skills)} ({ml_overlap/len(ml_required_skills)*100:.1f}%)")
        
        # Show which ML skills they have
        found_ml_skills = []
        for ml_skill in ml_required_skills:
            if any(ml_skill in skill for skill in all_skills_lower):
                found_ml_skills.append(ml_skill)
        print(f"   Found ML skills: {found_ml_skills}") 