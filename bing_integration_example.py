#!/usr/bin/env python3
"""
Bing Location Enrichment Integration Example
Shows how to integrate Bing API location enrichment with the existing contact upload process.
"""

import os
import pandas as pd
from bing_location_enricher import BingLocationEnricher
from enhanced_contact_tagger import EnhancedContactTagger

class BingEnrichedContactProcessor:
    """
    Enhanced contact processor that combines tagging with Bing location enrichment.
    """
    
    def __init__(self, bing_api_key: str = None):
        """Initialize with optional Bing API key."""
        self.bing_api_key = bing_api_key or os.environ.get('BING_API_KEY')
        self.tagger = EnhancedContactTagger()
        
        # Initialize Bing enricher if API key is available
        self.bing_enricher = None
        if self.bing_api_key:
            self.bing_enricher = BingLocationEnricher(self.bing_api_key)
            print("✅ Bing Location Enricher initialized")
        else:
            print("⚠️ No Bing API key found - location enrichment disabled")
    
    def process_contacts_with_location_enrichment(self, contacts_df: pd.DataFrame, enable_location_enrichment: bool = True, max_contacts_for_enrichment: int = 100) -> pd.DataFrame:
        """
        Process contacts with both tagging and optional location enrichment.
        
        Args:
            contacts_df: Raw contact DataFrame
            enable_location_enrichment: Whether to enable Bing location enrichment
            max_contacts_for_enrichment: Maximum contacts to enrich (for cost control)
            
        Returns:
            Fully processed DataFrame with tags and location data
        """
        print(f"🚀 Starting enhanced contact processing for {len(contacts_df)} contacts...")
        
        # Step 1: Tag contacts (existing functionality)
        print("📊 Step 1: Tagging contacts...")
        tagged_df = self.tagger.tag_contacts(contacts_df)
        
        # Step 2: Location enrichment (new functionality)
        if enable_location_enrichment and self.bing_enricher:
            print("🌍 Step 2: Enriching with location data...")
            enriched_df = self.bing_enricher.enrich_contacts_bulk(
                tagged_df, 
                max_contacts=max_contacts_for_enrichment
            )
            
            # Get enrichment statistics
            stats = self.bing_enricher.get_enrichment_stats(enriched_df)
            print(f"📈 Location Enrichment Stats: {stats}")
            
            return enriched_df
        else:
            print("⏭️ Skipping location enrichment (disabled or no API key)")
            return tagged_df
    
    def get_processing_summary(self, processed_df: pd.DataFrame) -> dict:
        """
        Get comprehensive summary of processing results.
        
        Args:
            processed_df: Processed contact DataFrame
            
        Returns:
            Summary dictionary
        """
        summary = {
            'total_contacts': len(processed_df),
            'tagging_summary': {
                'roles': processed_df['role_tag'].value_counts().to_dict(),
                'functions': processed_df['function_tag'].value_counts().to_dict(),
                'seniority': processed_df['seniority_tag'].value_counts().to_dict()
            }
        }
        
        # Add location enrichment summary if available
        if 'location_raw' in processed_df.columns:
            location_stats = {
                'enriched_contacts': processed_df['location_raw'].notna().sum(),
                'enrichment_rate': processed_df['location_raw'].notna().sum() / len(processed_df),
                'high_confidence': processed_df[processed_df['location_confidence'] >= 0.7]['location_raw'].notna().sum(),
                'location_sources': processed_df['location_source'].value_counts().to_dict()
            }
            summary['location_enrichment'] = location_stats
        
        return summary


def integrate_with_flask_upload():
    """
    Example of how to integrate this with the existing Flask upload endpoint.
    This would replace/modify the current upload logic in app.py
    """
    
    # Example integration code (to be added to app.py)
    integration_code = '''
    # In app.py, modify the upload endpoint:
    
    from bing_location_enricher import BingLocationEnricher
    from bing_integration_example import BingEnrichedContactProcessor
    
    @app.route('/upload', methods=['POST'])
    def upload_contacts():
        try:
            # ... existing file upload logic ...
            
            # Initialize processor with Bing API key
            bing_api_key = os.environ.get('BING_API_KEY')
            processor = BingEnrichedContactProcessor(bing_api_key)
            
            # Process contacts with location enrichment
            processed_df = processor.process_contacts_with_location_enrichment(
                contacts_df=contacts_df,
                enable_location_enrichment=True,
                max_contacts_for_enrichment=100  # Limit for cost control
            )
            
            # Get comprehensive summary
            summary = processor.get_processing_summary(processed_df)
            
            # Save enriched contacts
            output_filename = f"bing_enriched_contacts_{int(time.time())}.csv"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            processed_df.to_csv(output_path, index=False)
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed {len(processed_df)} contacts with location enrichment',
                'filename': output_filename,
                'summary': summary
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    '''
    
    return integration_code


def cost_analysis():
    """
    Cost analysis comparing SerpAPI vs Bing API for location enrichment.
    """
    
    analysis = {
        'serpapi': {
            'cost_per_1000_queries': 50,  # USD
            'rate_limit': '1 query/second',
            'total_cost_1000_contacts': 50,
            'processing_time_1000_contacts': '16.7 minutes'
        },
        'bing_api': {
            'cost_per_1000_queries': 3,  # USD
            'rate_limit': '3 queries/second',
            'total_cost_1000_contacts': 3,
            'processing_time_1000_contacts': '5.6 minutes'
        },
        'savings': {
            'cost_reduction': '94%',
            'time_improvement': '66%',
            'cost_per_contact': '0.003 USD vs 0.05 USD'
        }
    }
    
    return analysis


def main():
    """Demo the Bing integration."""
    
    # Check if Bing API key is available
    bing_api_key = os.environ.get('BING_API_KEY')
    if not bing_api_key:
        print("⚠️ No BING_API_KEY environment variable found")
        print("💡 Set it with: export BING_API_KEY='your_key_here'")
        print("📖 Get a key from: https://portal.azure.com/#create/Microsoft.CognitiveServicesBingSearch-v7")
        return
    
    # Initialize processor
    processor = BingEnrichedContactProcessor(bing_api_key)
    
    # Create sample data
    sample_contacts = pd.DataFrame([
        {
            'First Name': 'Cian',
            'Last Name': 'Dowling',
            'Company': 'Synthesia',
            'Position': 'Software Engineer',
            'Email Address': 'cian@synthesia.io'
        },
        {
            'First Name': 'Sarah',
            'Last Name': 'Johnson',
            'Company': 'Microsoft',
            'Position': 'Product Manager',
            'Email Address': 'sarah@microsoft.com'
        },
        {
            'First Name': 'Alex',
            'Last Name': 'Chen',
            'Company': 'Google',
            'Position': 'Data Scientist',
            'Email Address': 'alex@google.com'
        }
    ])
    
    # Process contacts
    print("🔄 Processing sample contacts...")
    processed_df = processor.process_contacts_with_location_enrichment(
        sample_contacts,
        enable_location_enrichment=True,
        max_contacts_for_enrichment=3
    )
    
    # Display results
    print("\n📊 Processing Results:")
    summary = processor.get_processing_summary(processed_df)
    print(f"Total contacts: {summary['total_contacts']}")
    
    if 'location_enrichment' in summary:
        loc_stats = summary['location_enrichment']
        print(f"Location enrichment rate: {loc_stats['enrichment_rate']:.1%}")
        print(f"High confidence locations: {loc_stats['high_confidence']}")
    
    print("\n📍 Location Results:")
    for idx, row in processed_df.iterrows():
        name = f"{row['First Name']} {row['Last Name']}"
        location = row.get('location_raw', 'Not found')
        confidence = row.get('location_confidence', 0)
        print(f"  {name}: {location} (confidence: {confidence:.2f})")
    
    # Show cost analysis
    print("\n💰 Cost Analysis:")
    costs = cost_analysis()
    print(f"Bing API cost per 1000 contacts: ${costs['bing_api']['cost_per_1000_queries']}")
    print(f"SerpAPI cost per 1000 contacts: ${costs['serpapi']['cost_per_1000_queries']}")
    print(f"Cost savings: {costs['savings']['cost_reduction']}")


if __name__ == "__main__":
    main()



