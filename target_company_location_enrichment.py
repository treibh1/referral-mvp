#!/usr/bin/env python3
"""
Target location enrichment for specific companies: Zendesk, Salesforce, Qualtrics, Synthesia.
Using current Brave API system for test data.
"""

import pandas as pd
import json
import time
from datetime import datetime
from brave_location_enricher import BraveLocationEnricher

def enrich_target_companies(df, target_companies):
    """
    Enrich location data for contacts at specific target companies.
    """
    print(f"🎯 Targeting companies: {', '.join(target_companies)}")
    print("=" * 60)
    
    # Initialize Brave enricher
    enricher = BraveLocationEnricher()
    
    # Filter contacts for target companies
    target_contacts = df[df['Company'].str.lower().isin([company.lower() for company in target_companies])].copy()
    
    print(f"📊 Found {len(target_contacts)} contacts at target companies")
    
    # Show breakdown by company
    for company in target_companies:
        company_contacts = target_contacts[target_contacts['Company'].str.lower() == company.lower()]
        with_location = len(company_contacts[company_contacts['location_raw'].notna()])
        print(f"   {company}: {len(company_contacts)} contacts ({with_location} with location)")
    
    print("\n" + "=" * 60)
    
    results = []
    successful = 0
    failed = 0
    skipped = 0
    
    # Process each target contact
    for idx, row in target_contacts.iterrows():
        row_number = idx + 1
        
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
                df.at[idx, 'location_raw'] = location_info['location']
                df.at[idx, 'location_city'] = location_info.get('location')
                df.at[idx, 'location_country'] = None  # Will be parsed later
                df.at[idx, 'location_confidence'] = location_info.get('confidence', 0.8)
                df.at[idx, 'location_source'] = location_info.get('source', 'Brave Search API (Google) - Target Companies')
                df.at[idx, 'location_url'] = location_info.get('url')
                
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
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_filename = f"target_companies_location_enrichment_{timestamp}.json"
    
    results_data = {
        'metadata': {
            'target_companies': target_companies,
            'timestamp': datetime.now().isoformat(),
            'total_target_contacts': len(target_contacts),
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'success_rate': f"{successful/(successful+failed)*100:.1f}%" if (successful+failed) > 0 else "0%"
        },
        'results': results
    }
    
    with open(results_filename, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Target Companies Enrichment Results:")
    print(f"   Total Target Contacts: {len(target_contacts)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Skipped: {skipped}")
    print(f"   Success Rate: {successful/(successful+failed)*100:.1f}%" if (successful+failed) > 0 else "0%")
    print(f"   Results saved to: {results_filename}")
    
    return successful, failed, skipped

def main():
    """Main function to enrich location data for target companies."""
    print("🚀 Target Companies Location Enrichment")
    print("=" * 60)
    
    # Define target companies
    target_companies = ['Zendesk', 'Salesforce', 'Qualtrics', 'Synthesia']
    
    # Load contacts
    contacts_file = 'enhanced_tagged_contacts.csv'
    df = pd.read_csv(contacts_file)
    print(f"📊 Loaded {len(df)} contacts")
    
    # Check current location coverage
    current_with_location = len(df[df['location_raw'].notna()])
    print(f"📊 Current location coverage: {current_with_location} contacts ({current_with_location/len(df)*100:.1f}%)")
    
    # Enrich target companies
    successful, failed, skipped = enrich_target_companies(df, target_companies)
    
    # Save updated contacts
    df.to_csv('enhanced_tagged_contacts.csv', index=False)
    
    # Final summary
    final_with_location = len(df[df['location_raw'].notna()])
    
    print(f"\n🎯 Target Companies Enrichment Complete!")
    print(f"=" * 60)
    print(f"📊 Final Results:")
    print(f"   Total Contacts: {len(df)}")
    print(f"   With Location: {final_with_location} ({final_with_location/len(df)*100:.1f}%)")
    print(f"   New Locations Added: {final_with_location - current_with_location}")
    print(f"   Target Companies Successful: {successful}")
    print(f"   Target Companies Failed: {failed}")
    print(f"   Target Companies Skipped: {skipped}")
    
    # Show updated breakdown by target company
    print(f"\n📊 Updated Target Companies Breakdown:")
    for company in target_companies:
        company_contacts = df[df['Company'].str.lower() == company.lower()]
        with_location = len(company_contacts[company_contacts['location_raw'].notna()])
        print(f"   {company}: {len(company_contacts)} contacts ({with_location} with location - {with_location/len(company_contacts)*100:.1f}%)")
    
    # Save final results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = f"enhanced_tagged_contacts_target_companies_{timestamp}.csv"
    df.to_csv(final_filename, index=False)
    print(f"\n💾 Final enriched contacts saved to: {final_filename}")
    
    return df

if __name__ == "__main__":
    main()

