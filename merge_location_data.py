#!/usr/bin/env python3
"""
Script to extract location data from existing Brave API test results
and merge it into the main contacts file.
"""

import json
import pandas as pd
import glob
import os
from datetime import datetime
from typing import Dict, List, Optional

def load_location_test_results() -> Dict[int, Dict]:
    """
    Load all location test results and extract location data.
    Returns a dictionary mapping row_number to location data.
    """
    location_data = {}
    
    # Find all location extraction JSON files
    json_files = glob.glob("location_extraction_*.json")
    json_files.extend(glob.glob("improved_location_extraction_*.json"))
    json_files.extend(glob.glob("linkedin_url_location_extraction_*.json"))
    
    print(f"📁 Found {len(json_files)} location test result files")
    
    for json_file in sorted(json_files, reverse=True):  # Process most recent first
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📄 Processing {json_file} ({data.get('test_info', {}).get('timestamp', 'unknown')})")
            
            for result in data.get('results', []):
                row_number = result.get('row_number')
                if row_number and result.get('location_found'):
                    # Only update if we don't have data for this row or if this is more recent
                    if row_number not in location_data:
                        location_data[row_number] = {
                            'location_raw': result.get('location_raw'),
                            'location_city': result.get('location_city'),
                            'location_country': result.get('location_country'),
                            'location_confidence': result.get('location_confidence'),
                            'location_source': result.get('location_source'),
                            'location_url': result.get('location_url'),
                            'source_file': json_file,
                            'timestamp': data.get('test_info', {}).get('timestamp')
                        }
                        print(f"  ✅ Row {row_number}: {result.get('location_raw')}")
            
        except Exception as e:
            print(f"❌ Error processing {json_file}: {e}")
    
    return location_data

def merge_location_data_to_contacts(location_data: Dict[int, Dict]) -> None:
    """
    Merge location data into the main contacts file.
    """
    # Load the main contacts file
    contacts_file = 'enhanced_tagged_contacts.csv'
    if not os.path.exists(contacts_file):
        print(f"❌ {contacts_file} not found!")
        return
    
    print(f"📊 Loading {contacts_file}...")
    df = pd.read_csv(contacts_file)
    print(f"📊 Loaded {len(df)} contacts")
    
    # Add location columns if they don't exist
    location_columns = ['location_raw', 'location_city', 'location_country', 
                       'location_confidence', 'location_source', 'location_url']
    
    for col in location_columns:
        if col not in df.columns:
            df[col] = None
    
    # Merge location data
    updated_count = 0
    for row_number, location_info in location_data.items():
        # Adjust for 0-based indexing (row_number is 1-based)
        if row_number <= len(df):
            idx = row_number - 1
            for col in location_columns:
                if col in location_info:
                    df.at[idx, col] = location_info[col]
            updated_count += 1
    
    print(f"✅ Updated {updated_count} contacts with location data")
    
    # Save the enriched contacts file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"enhanced_tagged_contacts_with_locations_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    print(f"💾 Saved enriched contacts to {output_file}")
    
    # Also save as the main file
    df.to_csv('enhanced_tagged_contacts.csv', index=False)
    print(f"💾 Updated main contacts file")
    
    # Print summary statistics
    location_stats = {
        'total_contacts': len(df),
        'with_location': len(df[df['location_raw'].notna()]),
        'location_sources': df['location_source'].value_counts().to_dict(),
        'countries': df['location_country'].value_counts().head(10).to_dict(),
        'cities': df['location_city'].value_counts().head(10).to_dict()
    }
    
    print(f"\n📊 Location Data Summary:")
    print(f"   Total Contacts: {location_stats['total_contacts']}")
    print(f"   With Location: {location_stats['with_location']} ({location_stats['with_location']/location_stats['total_contacts']*100:.1f}%)")
    print(f"   Location Sources: {location_stats['location_sources']}")
    
    return df

def main():
    """Main function to extract and merge location data."""
    print("🚀 Starting Location Data Merge Process")
    print("=" * 50)
    
    # Step 1: Extract location data from test results
    location_data = load_location_test_results()
    print(f"\n📊 Extracted location data for {len(location_data)} contacts")
    
    # Step 2: Merge into main contacts file
    if location_data:
        df = merge_location_data_to_contacts(location_data)
        print(f"\n✅ Location data merge completed successfully!")
    else:
        print(f"\n⚠️  No location data found in test results")

if __name__ == "__main__":
    main()

