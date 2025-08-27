#!/usr/bin/env python3
"""
Add test locations to contacts based on their first name initial.
"""

import pandas as pd
import re

def add_test_locations():
    """Add test locations to contacts without location data."""
    
    print("📍 Adding Test Locations to Contacts")
    print("=" * 50)
    
    # Test location mapping
    location_mapping = {
        "A": "Austin, Texas, USA",
        "B": "Berlin, Germany",
        "C": "Chicago, Illinois, USA",
        "D": "Dubai, United Arab Emirates",
        "E": "Edinburgh, Scotland, UK",
        "F": "Florence, Italy",
        "G": "Geneva, Switzerland",
        "H": "Hartford, Connecticut, USA",
        "I": "Indianapolis, Indiana, USA",
        "J": "Johannesburg, South Africa",
        "K": "Kraków, Poland",
        "L": "Lisbon, Portugal",
        "M": "Madrid, Spain",
        "N": "New York, New York, USA",
        "O": "Orlando, Florida, USA",
        "P": "Paris, France",
        "Q": "London, England, UK",
        "R": "Rio de Janeiro, Brazil",
        "S": "Sydney, Australia",
        "T": "Tallinn, Estonia",
        "U": "Utrecht, Netherlands",
        "V": "Vienna, Austria",
        "W": "Washington, District of Columbia, USA",
        "X": "London, England, UK",
        "Y": "Ypres, Belgium",
        "Z": "Zagreb, Croatia"
    }
    
    # Load the contacts file
    try:
        df = pd.read_csv('enhanced_tagged_contacts.csv')
        print(f"📊 Loaded {len(df)} contacts from enhanced_tagged_contacts.csv")
    except FileNotFoundError:
        print("❌ enhanced_tagged_contacts.csv not found")
        return
    
    # Check current location data
    contacts_with_location = df['location_raw'].notna() & (df['location_raw'] != '')
    contacts_without_location = ~contacts_with_location
    
    print(f"📍 Contacts with location: {contacts_with_location.sum()}")
    print(f"📍 Contacts without location: {contacts_without_location.sum()}")
    
    # Add test locations
    added_count = 0
    for idx, row in df.iterrows():
        if contacts_without_location[idx]:
            # Get first name initial
            first_name = str(row['First Name']).strip()
            last_name = str(row['Last Name']).strip()
            full_name = f"{first_name} {last_name}".strip()
            
            if first_name and first_name != 'nan':
                initial = first_name[0].upper() if first_name else 'A'
                
                # Get location for this initial
                if initial in location_mapping:
                    df.at[idx, 'location_raw'] = location_mapping[initial]
                    added_count += 1
                    if added_count <= 5:  # Show first 5 examples
                        print(f"   {full_name} → {location_mapping[initial]}")
    
    print(f"\n✅ Added test locations to {added_count} contacts")
    
    # Save the updated file
    df.to_csv('enhanced_tagged_contacts.csv', index=False)
    print("💾 Saved updated contacts to enhanced_tagged_contacts.csv")
    
    # Show summary by location
    print(f"\n📊 Location Distribution:")
    location_counts = df['location_raw'].value_counts().head(10)
    for location, count in location_counts.items():
        print(f"   {location}: {count} contacts")
    
    # Test some specific examples
    print(f"\n🧪 Testing Examples:")
    test_names = ['Alice Smith', 'Bob Johnson', 'Charlie Brown', 'David Wilson', 'Emma Davis']
    for name in test_names:
        initial = name[0].upper()
        location = location_mapping.get(initial, 'Unknown')
        print(f"   {name} ({initial}) → {location}")

if __name__ == "__main__":
    add_test_locations()
