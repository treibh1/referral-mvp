#!/usr/bin/env python3
"""
Continue location enrichment from row 151 with enhanced validation.
"""

import pandas as pd
import json
import time
from datetime import datetime
from brave_location_enricher import BraveLocationEnricher

def enrich_contacts_batch(df, start_idx, end_idx, batch_name):
    """
    Enrich a batch of contacts with location data using enhanced validation.
    """
    print(f"\n🔄 Processing Batch {batch_name}: Contacts {start_idx+1} to {end_idx}")
    print("=" * 60)
    
    # Initialize Brave enricher
    enricher = BraveLocationEnricher()
    
    results = []
    successful = 0
    failed = 0
    skipped = 0
    
    for i in range(start_idx, min(end_idx, len(df))):
        row = df.iloc[i]
        row_number = i + 1
        
        # Skip if already has location data
        if pd.notna(row.get('location_raw')):
            print(f"⏭️  Row {row_number}: Already has location ({row['location_raw']})")
            skipped += 1
            continue
        
        # Skip if name or company is missing
        if pd.isna(row['First Name']) or pd.isna(row['Last Name']) or pd.isna(row['Company']):
            print(f"⏭️  Row {row_number}: Missing name or company data")
            skipped += 1
            continue
        
        print(f"🔍 Row {row_number}: {row['First Name']} {row['Last Name']} - {row['Company']}")
        
        try:
            # Extract location using Brave API with enhanced validation
            location_info = enricher.locate_contact(
                full_name=f"{row['First Name']} {row['Last Name']}",
                company=row['Company']
            )
            
            if location_info and location_info.get('location'):
                print(f"  ✅ Location Found: {location_info['location']} (confidence: {location_info.get('confidence', 0.8)})")
                successful += 1
                
                # Update the dataframe directly
                df.at[i, 'location_raw'] = location_info['location']
                df.at[i, 'location_city'] = location_info.get('location')
                df.at[i, 'location_country'] = None  # Will be parsed later
                df.at[i, 'location_confidence'] = location_info.get('confidence', 0.8)
                df.at[i, 'location_source'] = location_info.get('source', 'Brave Search API (Google) - Enhanced Validation')
                df.at[i, 'location_url'] = location_info.get('url')
                
                results.append({
                    'row_number': row_number,
                    'full_name': f"{row['First Name']} {row['Last Name']}",
                    'company': row['Company'],
                    'location_found': True,
                    'location_raw': location_info['location'],
                    'confidence': location_info.get('confidence', 0.8),
                    'success': True
                })
            else:
                print(f"  ❌ No location found (validation likely rejected results)")
                failed += 1
                
                results.append({
                    'row_number': row_number,
                    'full_name': f"{row['First Name']} {row['Last Name']}",
                    'company': row['Company'],
                    'location_found': False,
                    'location_raw': None,
                    'success': False
                })
            
            # Small delay to be respectful to the API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            failed += 1
            
            results.append({
                'row_number': row_number,
                'full_name': f"{row['First Name']} {row['Last Name']}",
                'company': row['Company'],
                'location_found': False,
                'location_raw': None,
                'success': False,
                'error': str(e)
            })
    
    # Save batch results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_filename = f"location_enrichment_batch_{batch_name}_{timestamp}.json"
    
    batch_data = {
        'metadata': {
            'batch_name': batch_name,
            'start_idx': start_idx,
            'end_idx': end_idx,
            'timestamp': datetime.now().isoformat(),
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'success_rate': f"{successful/(successful+failed)*100:.1f}%" if (successful+failed) > 0 else "0%"
        },
        'results': results
    }
    
    with open(batch_filename, 'w', encoding='utf-8') as f:
        json.dump(batch_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Batch {batch_name} Results:")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Skipped: {skipped}")
    print(f"   Success Rate: {successful/(successful+failed)*100:.1f}%" if (successful+failed) > 0 else "0%")
    print(f"   Results saved to: {batch_filename}")
    
    return successful, failed, skipped

def main():
    """Main function to continue location enrichment from row 151."""
    print("🚀 Continuing Location Enrichment from Row 151")
    print("=" * 60)
    
    # Load contacts
    contacts_file = 'enhanced_tagged_contacts.csv'
    df = pd.read_csv(contacts_file)
    print(f"📊 Loaded {len(df)} contacts")
    
    # Check current location coverage
    current_with_location = len(df[df['location_raw'].notna()])
    print(f"📊 Current location coverage: {current_with_location} contacts ({current_with_location/len(df)*100:.1f}%)")
    
    # Start from row 151 (index 150)
    start_row = 150  # 0-indexed, so row 151
    end_row = len(df)
    
    print(f"📊 Processing from row {start_row+1} to {end_row}")
    
    # Define batch size and process in batches
    batch_size = 50  # Process 50 contacts at a time
    total_contacts_to_process = end_row - start_row
    total_batches = (total_contacts_to_process + batch_size - 1) // batch_size
    
    print(f"📊 Will process {total_contacts_to_process} contacts in {total_batches} batches of {batch_size} contacts each")
    
    # Process batches
    total_successful = 0
    total_failed = 0
    total_skipped = 0
    
    for batch_num in range(total_batches):
        batch_start_idx = start_row + (batch_num * batch_size)
        batch_end_idx = min(start_row + ((batch_num + 1) * batch_size), end_row)
        batch_name = f"batch_{batch_num+1:03d}_of_{total_batches:03d}_rows_{batch_start_idx+1}-{batch_end_idx}"
        
        print(f"\n🎯 Processing Batch {batch_num+1}/{total_batches}")
        
        successful, failed, skipped = enrich_contacts_batch(df, batch_start_idx, batch_end_idx, batch_name)
        
        total_successful += successful
        total_failed += failed
        total_skipped += skipped
        
        # Save progress after each batch
        df.to_csv('enhanced_tagged_contacts.csv', index=False)
        
        # Print progress
        current_with_location = len(df[df['location_raw'].notna()])
        print(f"📊 Progress: {current_with_location}/{len(df)} contacts with location ({current_with_location/len(df)*100:.1f}%)")
        
        # Ask user if they want to continue (for large datasets)
        if batch_num < total_batches - 1:
            response = input(f"\nContinue with next batch? (y/n, default: y): ").strip().lower()
            if response == 'n':
                print("⏹️  Stopping at user request")
                break
    
    # Final summary
    final_with_location = len(df[df['location_raw'].notna()])
    
    print(f"\n🎯 Location Enrichment Complete!")
    print(f"=" * 60)
    print(f"📊 Final Results:")
    print(f"   Total Contacts: {len(df)}")
    print(f"   With Location: {final_with_location} ({final_with_location/len(df)*100:.1f}%)")
    print(f"   New Locations Added: {final_with_location - current_with_location}")
    print(f"   Total Successful: {total_successful}")
    print(f"   Total Failed: {total_failed}")
    print(f"   Total Skipped: {total_skipped}")
    
    # Save final results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = f"enhanced_tagged_contacts_final_{timestamp}.csv"
    df.to_csv(final_filename, index=False)
    print(f"💾 Final enriched contacts saved to: {final_filename}")
    
    return df

if __name__ == "__main__":
    main()

