import pandas as pd

# Load tagged contacts
df = pd.read_csv("tagged_contacts2.csv")

print("🔍 Checking contact skills...")
print("=" * 50)

# Find contacts with skills
contacts_with_skills = df[df['skills_tag'].apply(lambda x: len(eval(str(x))) > 0)]

print(f"Total contacts: {len(df)}")
print(f"Contacts with skills: {len(contacts_with_skills)}")
print(f"Percentage with skills: {len(contacts_with_skills)/len(df)*100:.1f}%")

print(f"\n📋 Sample contacts with skills:")
sample_contacts = contacts_with_skills.head(5)
for idx, row in sample_contacts.iterrows():
    skills = eval(str(row["skills_tag"]))
    platforms = eval(str(row["platforms_tag"]))
    print(f"\n{row['First Name']} {row['Last Name']} - {row['Position']} at {row['Company']}")
    print(f"  Skills: {skills}")
    print(f"  Platforms: {platforms}")

# Check for ML/AI related skills
print(f"\n🔍 Looking for ML/AI related skills...")
ml_skills = ['machine learning', 'deep learning', 'python', 'pytorch', 'tensorflow', 'data science', 'ai', 'artificial intelligence']
ml_contacts = []

for idx, row in df.iterrows():
    skills = eval(str(row.get("skills_tag", "[]")))
    platforms = eval(str(row.get("platforms_tag", "[]")))
    
    # Check for ML skills
    has_ml_skills = any(ml_skill in ' '.join(skills).lower() for ml_skill in ml_skills)
    has_ml_platforms = any(ml_skill in ' '.join(platforms).lower() for ml_skill in ml_skills)
    
    if has_ml_skills or has_ml_platforms:
        ml_contacts.append({
            'name': f"{row['First Name']} {row['Last Name']}",
            'position': row['Position'],
            'company': row['Company'],
            'skills': skills,
            'platforms': platforms
        })

print(f"Found {len(ml_contacts)} contacts with ML/AI related skills/platforms:")
for contact in ml_contacts[:5]:  # Show first 5
    print(f"\n{contact['name']} - {contact['position']} at {contact['company']}")
    print(f"  Skills: {contact['skills']}")
    print(f"  Platforms: {contact['platforms']}")

# Check all unique skills
print(f"\n📊 All unique skills in database:")
all_skills = set()
for idx, row in df.iterrows():
    skills = eval(str(row.get("skills_tag", "[]")))
    all_skills.update(skills)

print(f"Total unique skills: {len(all_skills)}")
print(f"Sample skills: {list(all_skills)[:20]}")

# Check all unique platforms
print(f"\n📊 All unique platforms in database:")
all_platforms = set()
for idx, row in df.iterrows():
    platforms = eval(str(row.get("platforms_tag", "[]")))
    all_platforms.update(platforms)

print(f"Total unique platforms: {len(all_platforms)}")
print(f"Sample platforms: {list(all_platforms)[:20]}") 