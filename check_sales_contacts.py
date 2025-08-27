#!/usr/bin/env python3
"""
Check what sales contacts we have in our database
"""

import pandas as pd

def check_sales_contacts():
    print("🔍 Checking Sales Contacts in Database...")
    
    # Load contacts
    df = pd.read_csv("improved_tagged_contacts.csv")
    
    # Look for sales-related positions
    sales_keywords = [
        'sales', 'account executive', 'ae', 'sdr', 'bdr', 'sales development', 
        'business development', 'sales representative', 'sales manager', 
        'sales director', 'sales executive', 'enterprise sales', 'inside sales',
        'field sales', 'commercial', 'revenue', 'quota'
    ]
    
    sales_contacts = []
    for idx, row in df.iterrows():
        position = str(row['Position']).lower()
        if any(keyword in position for keyword in sales_keywords):
            sales_contacts.append({
                'name': f"{row['First Name']} {row['Last Name']}",
                'position': row['Position'],
                'company': row['Company'],
                'function_tag': row['function_tag'],
                'skills_count': len(eval(row.get('skills_tag', '[]'))),
                'platforms_count': len(eval(row.get('platforms_tag', '[]'))),
                'skills': eval(row.get('skills_tag', '[]')),
                'platforms': eval(row.get('platforms_tag', '[]'))
            })
    
    print(f"\n📊 Found {len(sales_contacts)} sales-related contacts")
    
    if len(sales_contacts) > 0:
        print(f"\n🏆 TOP 10 SALES CONTACTS BY SKILL COUNT:")
        sorted_sales = sorted(sales_contacts, key=lambda x: x['skills_count'], reverse=True)
        
        for i, contact in enumerate(sorted_sales[:10], 1):
            print(f"\n#{i}: {contact['name']}")
            print(f"   Position: {contact['position']}")
            print(f"   Company: {contact['company']}")
            print(f"   Function: {contact['function_tag']}")
            print(f"   Skills: {contact['skills_count']} skills")
            print(f"   Platforms: {contact['platforms_count']} platforms")
            print(f"   Top Skills: {contact['skills'][:5]}...")
            print(f"   Top Platforms: {contact['platforms'][:3]}...")
    
    # Check what roles we have in our enrichment data
    print(f"\n🔍 CHECKING ROLE ENRICHMENT DATA:")
    
    import json
    with open("role_enrichment.json", "r") as f:
        role_enrichment = json.load(f)
    
    sales_roles = []
    for key, value in role_enrichment.items():
        if key.startswith("any:") and any(sales_word in key for sales_word in ['sales', 'account', 'sdr', 'bdr', 'executive']):
            sales_roles.append({
                'role': key,
                'skills_count': len(value.get('skills', [])),
                'platforms_count': len(value.get('platforms', [])),
                'skills': value.get('skills', [])[:5],  # First 5 skills
                'platforms': value.get('platforms', [])
            })
    
    print(f"\n📋 Found {len(sales_roles)} sales roles in enrichment data:")
    for role in sales_roles:
        print(f"   {role['role']}: {role['skills_count']} skills, {role['platforms_count']} platforms")
        print(f"     Skills: {role['skills']}...")

if __name__ == "__main__":
    check_sales_contacts()



