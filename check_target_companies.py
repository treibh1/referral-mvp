#!/usr/bin/env python3
"""
Check target companies analysis.
"""

import pandas as pd

def check_target_companies():
    """Check how many contacts we have for each target company."""
    
    # Load contacts
    df = pd.read_csv('enhanced_tagged_contacts.csv')
    
    # Define target companies
    target_companies = ['Zendesk', 'Salesforce', 'Qualtrics', 'Synthesia']
    
    print('Target Companies Analysis:')
    print('=' * 50)
    
    total_target_contacts = 0
    
    for company in target_companies:
        company_contacts = df[df['Company'].str.lower() == company.lower()]
        with_location = len(company_contacts[company_contacts['location_raw'].notna()])
        total_target_contacts += len(company_contacts)
        
        print(f'{company}: {len(company_contacts)} contacts ({with_location} with location - {with_location/len(company_contacts)*100:.1f}%)')
        print(f'  Sample contacts:')
        
        for i, row in company_contacts.head(3).iterrows():
            location_status = f" - {row['location_raw']}" if pd.notna(row.get('location_raw')) else " - No location"
            print(f'    - {row["First Name"]} {row["Last Name"]} (Row {i+1}){location_status}')
        print()
    
    print(f'Total target contacts: {total_target_contacts}')
    print(f'Total contacts in dataset: {len(df)}')
    print(f'Target contacts percentage: {total_target_contacts/len(df)*100:.1f}%')

if __name__ == "__main__":
    check_target_companies()

