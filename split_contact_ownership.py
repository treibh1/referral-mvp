#!/usr/bin/env python3
"""
Split contacts among four recruiters and add contact ownership data.
"""

import pandas as pd
import random

def split_contact_ownership():
    """Split contacts among four recruiters."""
    
    print("👥 Assigning Employee Connections to Contacts")
    print("=" * 60)
    
    # Define the four employees who uploaded contacts
    employees = [
        "Aaron Adams",
        "Belinda Bell", 
        "Charles Cole",
        "Debbie Doyle"
    ]
    
    # Load the contacts file
    try:
        df = pd.read_csv('enhanced_tagged_contacts.csv')
        print(f"📊 Loaded {len(df)} contacts from enhanced_tagged_contacts.csv")
    except FileNotFoundError:
        print("❌ enhanced_tagged_contacts.csv not found")
        return
    
    # Check if employee_connection column already exists
    if 'employee_connection' in df.columns:
        print("⚠️ employee_connection column already exists. Overwriting...")
    
    # Split contacts evenly among employees
    total_contacts = len(df)
    contacts_per_employee = total_contacts // len(employees)
    remainder = total_contacts % len(employees)
    
    print(f"📋 Distribution Plan:")
    print(f"   Total contacts: {total_contacts}")
    print(f"   Contacts per employee: {contacts_per_employee}")
    print(f"   Remainder: {remainder}")
    
    # Create employee connection assignments with even distribution
    employee_connections = []
    
    for i in range(total_contacts):
        # Simple round-robin assignment
        employee_idx = i % len(employees)
        employee_connections.append(employees[employee_idx])
    
    # Add the employee_connection column
    df['employee_connection'] = employee_connections
    
    # Shuffle the assignments to make them more realistic
    # (so recruiters don't just get sequential blocks)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Save the updated file
    df.to_csv('enhanced_tagged_contacts.csv', index=False)
    print("💾 Saved updated contacts to enhanced_tagged_contacts.csv")
    
    # Show distribution summary
    print(f"\n📊 Contact Distribution:")
    connection_counts = df['employee_connection'].value_counts()
    for employee in employees:
        count = connection_counts.get(employee, 0)
        percentage = (count / total_contacts) * 100
        print(f"   {employee}: {count} contacts ({percentage:.1f}%)")
    
    # Show some examples
    print(f"\n🧪 Sample Assignments:")
    sample_contacts = df[['First Name', 'Last Name', 'employee_connection']].head(10)
    for _, row in sample_contacts.iterrows():
        full_name = f"{row['First Name']} {row['Last Name']}"
        print(f"   {full_name} → {row['employee_connection']}")
    
    # Show distribution by location (to see if it's well distributed)
    print(f"\n🌍 Location Distribution by Employee:")
    for employee in employees:
        employee_contacts = df[df['employee_connection'] == employee]
        top_locations = employee_contacts['location_raw'].value_counts().head(3)
        print(f"   {employee}:")
        for location, count in top_locations.items():
            print(f"     - {location}: {count} contacts")

if __name__ == "__main__":
    split_contact_ownership()
