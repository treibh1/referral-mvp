#!/usr/bin/env python3
"""
Background Worker for Multi-Tenant Referral System
Handles location enrichment, data processing, and other background tasks
"""

import os
import sys
import time
import logging
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bright_data_enricher import BrightDataEnricher
from unified_matcher import UnifiedMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BackgroundWorker:
    def __init__(self):
        """Initialize the background worker with database connection and services"""
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.bright_data_key = os.getenv('BRIGHT_DATA_API_KEY')
        if not self.bright_data_key:
            logger.warning("BRIGHT_DATA_API_KEY not found - location enrichment disabled")
        
        self.enricher = BrightDataEnricher(self.bright_data_key) if self.bright_data_key else None
        self.max_enrichments_per_run = 10  # Limit to avoid API costs
        
    def get_db_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.db_url)
    
    def get_contacts_needing_location_enrichment(self, limit: int = 10) -> List[Dict]:
        """Get contacts that need location enrichment"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT c.id, c.full_name, c.current_company, c.current_title
                FROM contacts c
                WHERE c.location IS NULL OR c.location = ''
                ORDER BY c.created_at ASC
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            
            contacts = []
            for row in results:
                contacts.append({
                    'id': row[0],
                    'full_name': row[1],
                    'current_company': row[2],
                    'current_title': row[3]
                })
            
            cursor.close()
            conn.close()
            
            return contacts
            
        except Exception as e:
            logger.error(f"Error getting contacts for enrichment: {e}")
            return []
    
    def enrich_contact_location(self, contact: Dict) -> Optional[str]:
        """Enrich a single contact's location using Bright Data"""
        if not self.enricher:
            logger.warning("Bright Data enricher not available")
            return None
        
        try:
            # Build search query
            search_query = f"{contact['full_name']} - {contact['current_company']} - linkedin profile"
            
            logger.info(f"Enriching location for {contact['full_name']} at {contact['current_company']}")
            
            # Get location from Bright Data
            location = self.enricher.get_location_from_search(search_query)
            
            if location:
                logger.info(f"Found location for {contact['full_name']}: {location}")
                return location
            else:
                logger.warning(f"No location found for {contact['full_name']}")
                return None
                
        except Exception as e:
            logger.error(f"Error enriching location for {contact['full_name']}: {e}")
            return None
    
    def update_contact_location(self, contact_id: int, location: str, success: bool = True):
        """Update contact location in database and log the enrichment"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Update contact location
            if success:
                update_query = """
                    UPDATE contacts 
                    SET location = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                cursor.execute(update_query, (location, contact_id))
            
            # Log enrichment activity
            log_query = """
                INSERT INTO location_enrichment_log 
                (contact_id, success, location_found, api_used, cost)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(log_query, (
                contact_id, 
                success, 
                location if success else None,
                'bright_data_serp',
                0.01  # Approximate cost per search
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Updated contact {contact_id} with location: {location}")
            
        except Exception as e:
            logger.error(f"Error updating contact location: {e}")
    
    def run_location_enrichment(self):
        """Run location enrichment for contacts that need it"""
        if not self.enricher:
            logger.info("Skipping location enrichment - no Bright Data API key")
            return
        
        logger.info("Starting location enrichment process")
        
        # Get contacts needing enrichment
        contacts = self.get_contacts_needing_location_enrichment(self.max_enrichments_per_run)
        
        if not contacts:
            logger.info("No contacts need location enrichment")
            return
        
        logger.info(f"Found {len(contacts)} contacts needing location enrichment")
        
        enriched_count = 0
        for contact in contacts:
            try:
                # Enrich location
                location = self.enrich_contact_location(contact)
                
                # Update database
                if location:
                    self.update_contact_location(contact['id'], location, success=True)
                    enriched_count += 1
                else:
                    self.update_contact_location(contact['id'], None, success=False)
                
                # Small delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing contact {contact['id']}: {e}")
                self.update_contact_location(contact['id'], None, success=False)
        
        logger.info(f"Location enrichment complete. Enriched {enriched_count}/{len(contacts)} contacts")
    
    def run_data_cleanup(self):
        """Run data cleanup tasks"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Clean old search history (older than 30 days)
            cleanup_query = """
                DELETE FROM search_history 
                WHERE search_date < CURRENT_TIMESTAMP - INTERVAL '30 days'
            """
            cursor.execute(cleanup_query)
            deleted_count = cursor.rowcount
            
            # Clean old location enrichment logs (older than 90 days)
            cleanup_logs_query = """
                DELETE FROM location_enrichment_log 
                WHERE enrichment_date < CURRENT_TIMESTAMP - INTERVAL '90 days'
            """
            cursor.execute(cleanup_logs_query)
            deleted_logs_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Data cleanup complete. Deleted {deleted_count} old searches, {deleted_logs_count} old logs")
            
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
    
    def run_health_check(self):
        """Run health check on the system"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check database connectivity
            cursor.execute("SELECT COUNT(*) FROM contacts")
            contact_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM organisations")
            org_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            logger.info(f"Health check: {contact_count} contacts, {org_count} organizations, {user_count} users")
            
            return {
                'status': 'healthy',
                'contacts': contact_count,
                'organizations': org_count,
                'users': user_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run(self):
        """Main worker loop"""
        logger.info("Starting background worker")
        
        while True:
            try:
                # Run location enrichment
                self.run_location_enrichment()
                
                # Run data cleanup (once per day)
                if datetime.now().hour == 2:  # Run at 2 AM
                    self.run_data_cleanup()
                
                # Run health check
                health = self.run_health_check()
                logger.info(f"Health check: {health['status']}")
                
                # Sleep for 5 minutes before next run
                logger.info("Worker cycle complete. Sleeping for 5 minutes...")
                time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("Worker stopped by user")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    worker = BackgroundWorker()
    worker.run()
