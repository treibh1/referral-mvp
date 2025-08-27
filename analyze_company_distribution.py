import pandas as pd

# Load tagged contacts
df = pd.read_csv("tagged_contacts2.csv")

print("🏢 Company Distribution Analysis")
print("=" * 50)

# Get company counts
company_counts = df['Company'].value_counts()

print("Top 15 companies by contact count:")
print(company_counts.head(15))

# Check Zendesk specifically
zendesk_contacts = df[df['Company'].str.contains('Zendesk', case=False, na=False)]
print(f"\n📊 Zendesk Analysis:")
print(f"Total Zendesk contacts: {len(zendesk_contacts)}")
print(f"Total contacts: {len(df)}")
print(f"Zendesk percentage: {len(zendesk_contacts)/len(df)*100:.1f}%")

# Check what roles Zendesk people have
print(f"\n🎯 Zendesk Role Distribution:")
zendesk_roles = zendesk_contacts['Position'].value_counts()
print(zendesk_roles.head(10))

# Check if Zendesk people have better skills/platforms
print(f"\n🔍 Zendesk Skills Analysis:")
zendesk_with_skills = zendesk_contacts[zendesk_contacts['skills_tag'].apply(lambda x: len(eval(str(x))) > 0)]
print(f"Zendesk contacts with skills: {len(zendesk_with_skills)}")
print(f"Percentage of Zendesk with skills: {len(zendesk_with_skills)/len(zendesk_contacts)*100:.1f}%")

# Compare with overall database
all_with_skills = df[df['skills_tag'].apply(lambda x: len(eval(str(x))) > 0)]
print(f"\n📈 Overall Database Skills:")
print(f"Total contacts with skills: {len(all_with_skills)}")
print(f"Percentage of all contacts with skills: {len(all_with_skills)/len(df)*100:.1f}%")

# Check average skills per Zendesk contact vs overall
zendesk_avg_skills = zendesk_contacts['skills_tag'].apply(lambda x: len(eval(str(x)))).mean()
overall_avg_skills = df['skills_tag'].apply(lambda x: len(eval(str(x)))).mean()
print(f"\n📊 Average Skills Comparison:")
print(f"Zendesk average skills per contact: {zendesk_avg_skills:.1f}")
print(f"Overall average skills per contact: {overall_avg_skills:.1f}")

# Check if Zendesk people have more technical skills
print(f"\n🔧 Technical Skills Analysis:")
technical_skills = ['python', 'machine learning', 'data science', 'software engineering', 'architecture', 'system design']
zendesk_technical = 0
overall_technical = 0

for idx, row in zendesk_contacts.iterrows():
    skills = eval(str(row.get("skills_tag", "[]")))
    if any(tech_skill in ' '.join(skills).lower() for tech_skill in technical_skills):
        zendesk_technical += 1

for idx, row in df.iterrows():
    skills = eval(str(row.get("skills_tag", "[]")))
    if any(tech_skill in ' '.join(skills).lower() for tech_skill in technical_skills):
        overall_technical += 1

print(f"Zendesk contacts with technical skills: {zendesk_technical}")
print(f"Overall contacts with technical skills: {overall_technical}")
print(f"Zendesk technical percentage: {zendesk_technical/len(zendesk_contacts)*100:.1f}%")
print(f"Overall technical percentage: {overall_technical/len(df)*100:.1f}%") 