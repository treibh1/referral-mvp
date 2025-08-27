#!/usr/bin/env python3
"""
Demo script showing the complete contact enrichment flow.
"""

import pandas as pd
import json
import os
from user_management import UserManager
from enhanced_contact_tagger import EnhancedContactTagger

def demo_enrichment_flow():
    """Demonstrate the complete enrichment flow."""
    print("🎯 Contact Enrichment Flow Demo")
    print("=" * 50)
    
    # Initialize components
    user_manager = UserManager()
    tagger = EnhancedContactTagger()
    
    # Step 1: Create a demo user
    user_id = user_manager.create_user("demo@example.com", "Demo User")
    print(f"👤 Created demo user: {user_id}")
    
    # Step 2: Create sample contacts (simulating LinkedIn export)
    sample_contacts = pd.DataFrame({
        'First Name': ['John', 'Sarah', 'Mike', 'Emily', 'David'],
        'Last Name': ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'],
        'Company': ['Google', 'Microsoft', 'Apple', 'Amazon', 'Meta'],
        'Position': ['Senior Software Engineer', 'Product Manager', 'Data Scientist', 'UX Designer', 'DevOps Engineer'],
        'Email Address': ['john@google.com', 'sarah@microsoft.com', 'mike@apple.com', 'emily@amazon.com', 'david@meta.com'],
        'URL': ['https://linkedin.com/in/johnsmith', 'https://linkedin.com/in/sarahjohnson', 
                'https://linkedin.com/in/mikewilliams', 'https://linkedin.com/in/emilybrown', 
                'https://linkedin.com/in/davidjones']
    })
    
    print(f"📊 Created {len(sample_contacts)} sample contacts")
    
    # Step 3: Tag contacts (simulating the import process)
    tagged_contacts = tagger.tag_contacts(sample_contacts)
    
    # Add contact IDs
    tagged_contacts['contact_id'] = [f"contact_{i}" for i in range(len(tagged_contacts))]
    
    # Save tagged contacts
    tagged_contacts.to_csv('demo_tagged_contacts.csv', index=False)
    print("🏷️  Contacts tagged and saved")
    
    # Step 4: Assign contacts to user (simulating import completion)
    contact_ids = tagged_contacts['contact_id'].tolist()
    user_manager.assign_contacts_to_user(user_id, contact_ids, "demo_import.csv")
    print(f"✅ Assigned {len(contact_ids)} contacts to user")
    
    # Step 5: Show enrichment interface data
    print("\n🎯 Enrichment Interface Data:")
    print("-" * 30)
    
    contacts_for_enrichment = user_manager.get_user_contacts_for_enrichment(user_id)
    
    for i, contact in enumerate(contacts_for_enrichment, 1):
        print(f"\n{i}. {contact['First Name']} {contact['Last Name']}")
        print(f"   Company: {contact['Company']}")
        print(f"   Position: {contact['Position']}")
        print(f"   Auto-tagged Role: {contact.get('role_tag', 'N/A')}")
        print(f"   Auto-tagged Function: {contact.get('function_tag', 'N/A')}")
        print(f"   Auto-tagged Seniority: {contact.get('seniority_tag', 'N/A')}")
        print(f"   Current Enrichment Score: {contact.get('enrichment_score', 0)}/100")
    
    # Step 6: Simulate user enrichment
    print(f"\n🎮 Simulating User Enrichment:")
    print("-" * 30)
    
    # Enrich first contact
    first_contact = contacts_for_enrichment[0]
    success = user_manager.save_contact_enrichment(
        user_id=user_id,
        contact_id=first_contact['contact_id'],
        location="San Francisco, CA",
        seniority="senior",
        skills=["Python", "JavaScript", "React", "Node.js"],
        platforms=["AWS", "Docker", "Kubernetes", "GitHub"],
        is_superstar=True,
        notes="Excellent full-stack developer with strong leadership skills. Led multiple successful projects."
    )
    
    if success:
        print(f"✅ Enriched {first_contact['First Name']} {first_contact['Last Name']} as a superstar!")
    
    # Enrich second contact
    second_contact = contacts_for_enrichment[1]
    success = user_manager.save_contact_enrichment(
        user_id=user_id,
        contact_id=second_contact['contact_id'],
        location="Seattle, WA",
        seniority="manager",
        skills=["Product Management", "User Research", "Data Analysis"],
        platforms=["Figma", "Jira", "Mixpanel", "Tableau"],
        is_superstar=False,
        notes="Solid product manager with good analytical skills."
    )
    
    if success:
        print(f"✅ Enriched {second_contact['First Name']} {second_contact['Last Name']}")
    
    # Step 7: Show final results
    print(f"\n🎉 Final Enrichment Results:")
    print("-" * 30)
    
    final_contacts = user_manager.get_user_contacts_for_enrichment(user_id)
    
    total_contacts = len(final_contacts)
    enriched_contacts = sum(1 for c in final_contacts if c.get('location') or c.get('skills'))
    superstars = sum(1 for c in final_contacts if c.get('is_superstar'))
    avg_score = sum(c.get('enrichment_score', 0) for c in final_contacts) / len(final_contacts)
    
    print(f"📊 Total Contacts: {total_contacts}")
    print(f"🎯 Enriched Contacts: {enriched_contacts}")
    print(f"⭐ Superstars Found: {superstars}")
    print(f"📈 Average Enrichment Score: {avg_score:.1f}/100")
    
    # Show detailed results
    for contact in final_contacts:
        print(f"\n👤 {contact['First Name']} {contact['Last Name']}")
        print(f"   📍 Location: {contact.get('location', 'Not specified')}")
        print(f"   👑 Seniority: {contact.get('seniority', 'Not specified')}")
        print(f"   💻 Skills: {contact.get('skills', [])}")
        print(f"   🛠️  Platforms: {contact.get('platforms', [])}")
        print(f"   ⭐ Superstar: {'Yes' if contact.get('is_superstar') else 'No'}")
        print(f"   📝 Notes: {contact.get('notes', 'No notes')}")
        print(f"   🎯 Enrichment Score: {contact.get('enrichment_score', 0)}/100")
    
    # Cleanup
    try:
        os.remove('demo_tagged_contacts.csv')
        os.remove(f"enrichment_data_{user_id}.json")
        print(f"\n🧹 Cleaned up demo files")
    except FileNotFoundError:
        pass
    
    print(f"\n🎉 Demo completed! The enrichment system is ready for the web interface.")

if __name__ == "__main__":
    demo_enrichment_flow()



