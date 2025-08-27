#!/usr/bin/env python3
"""
Script to merge the new Brave API accuracy test results into the main contacts file.
"""

import json
import pandas as pd
import glob
import os
from datetime import datetime

def merge_new_location_data():
    """Merge new location test results into the main contacts file."""
    
    # Find the new accuracy test files
    json_files = glob.glob("brave_accuracy_test_*.json")
    
    print(f"📁 Found {len(json_files)} new accuracy test files")
    
    # Load the main contacts file
    contacts_file = 'enhanced_tagged_contacts.csv'
    df = pd.read_csv(contacts_file)
    print(f"📊 Loaded {len(df)} contacts")
    
    # Track updates
    total_updates = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📄 Processing {json_file}")
            
            for result in data.get('results', []):
                row_number = result.get('row_number')
                if row_number and result.get('location_found'):
                    # Adjust for 0-based indexing
                    if row_number <= len(df):
                        idx = row_number - 1
                        
                        # Update location fields
                        df.at[idx, 'location_raw'] = result.get('location_raw')
                        df.at[idx, 'location_city'] = result.get('location_city')
                        df.at[idx, 'location_country'] = result.get('location_country')
                        df.at[idx, 'location_confidence'] = result.get('location_confidence')
                        df.at[idx, 'location_source'] = result.get('location_source')
                        df.at[idx, 'location_url'] = result.get('location_url')
                        
                        total_updates += 1
                        print(f"  ✅ Updated Row {row_number}: {result.get('location_raw')}")
            
        except Exception as e:
            print(f"❌ Error processing {json_file}: {e}")
    
    # Save the updated contacts file
    df.to_csv('enhanced_tagged_contacts.csv', index=False)
    print(f"\n✅ Updated {total_updates} contacts with new location data")
    
    # Print summary
    location_stats = {
        'total_contacts': len(df),
        'with_location': len(df[df['location_raw'].notna()]),
        'location_sources': df['location_source'].value_counts().to_dict()
    }
    
    print(f"\n📊 Updated Location Data Summary:")
    print(f"   Total Contacts: {location_stats['total_contacts']}")
    print(f"   With Location: {location_stats['with_location']} ({location_stats['with_location']/location_stats['total_contacts']*100:.1f}%)")
    print(f"   Location Sources: {location_stats['location_sources']}")
    
    return df

if __name__ == "__main__":
    merge_new_location_data()

