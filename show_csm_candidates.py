import pandas as pd

print("🎯 Showing Customer Success Manager Candidates")
print("=" * 60)

# Load tagged contacts
df = pd.read_csv("tagged_contacts2.csv")

# Find all Customer Success Managers
csm_candidates = df[df['Position'].str.contains('customer success', case=False, na=False)]

print(f"📊 Found {len(csm_candidates)} Customer Success Manager candidates:")
print("=" * 80)

for idx, row in csm_candidates.iterrows():
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
print(f"   Total CSM candidates: {len(csm_candidates)}")
print(f"   Companies with CSMs: {csm_candidates['Company'].nunique()}")

# Show top 10 CSM candidates by company
print(f"\n🏢 CSM Candidates by Company:")
company_counts = csm_candidates['Company'].value_counts()
for company, count in company_counts.head(10).items():
    print(f"   {company}: {count} CSMs") 