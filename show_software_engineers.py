import pandas as pd

print("🔧 Showing Software Engineer Candidates")
print("=" * 60)

# Load tagged contacts
df = pd.read_csv("tagged_contacts2.csv")

# Find all Software Engineers
se_candidates = df[df['Position'].str.contains('software engineer|software developer|engineer', case=False, na=False)]

print(f"📊 Found {len(se_candidates)} Software Engineer candidates:")
print("=" * 80)

for idx, row in se_candidates.iterrows():
    print(f"\n#{idx+1}: {row['First Name']} {row['Last Name']}")
    print(f"   Position: {row['Position']}")
    print(f"   Company: {row['Company']}")
    print(f"   Seniority: {row.get('seniority_tag', 'N/A')}")
    print(f"   Function: {row.get('function_tag', 'N/A')}")
    
    # Show skills and platforms
    try:
        skills = eval(str(row.get("skills_tag", "[]")))
        platforms = eval(str(row.get("platforms_tag", "[]")))
        print(f"   Skills: {skills[:5]}...")  # Show first 5 skills
        print(f"   Platforms: {platforms[:5]}...")  # Show first 5 platforms
    except:
        print(f"   Skills: Error parsing")
        print(f"   Platforms: Error parsing")

print(f"\n📊 Summary:")
print(f"   Total Software Engineer candidates: {len(se_candidates)}")
print(f"   Companies with Software Engineers: {se_candidates['Company'].nunique()}")

# Show top 10 Software Engineer candidates by company
print(f"\n🏢 Software Engineer Candidates by Company:")
company_counts = se_candidates['Company'].value_counts()
for company, count in company_counts.head(10).items():
    print(f"   {company}: {count} Software Engineers")

# Show by position type
print(f"\n👨‍💻 Software Engineer Candidates by Position Type:")
position_counts = se_candidates['Position'].value_counts()
for position, count in position_counts.head(10).items():
    print(f"   {position}: {count} candidates") 