#!/usr/bin/env python3
"""
Cron Jobs for Multi-Tenant Referral System
Handles scheduled tasks like data cleanup, reports, and maintenance
"""

import os
import sys
import logging
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cron.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CronJobs:
    def __init__(self):
        """Initialize cron jobs with database connection"""
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
    
    def get_db_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.db_url)
    
    def clean_old_search_history(self):
        """Clean search history older than 30 days"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = """
                DELETE FROM search_history 
                WHERE search_date < CURRENT_TIMESTAMP - INTERVAL '30 days'
            """
            cursor.execute(query)
            deleted_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Cleaned {deleted_count} old search history records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning search history: {e}")
            return 0
    
    def clean_old_location_logs(self):
        """Clean location enrichment logs older than 90 days"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = """
                DELETE FROM location_enrichment_log 
                WHERE enrichment_date < CURRENT_TIMESTAMP - INTERVAL '90 days'
            """
            cursor.execute(query)
            deleted_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Cleaned {deleted_count} old location enrichment logs")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning location logs: {e}")
            return 0
    
    def update_contact_statistics(self):
        """Update contact statistics for organizations"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get contact counts by organization
            query = """
                SELECT 
                    o.id as org_id,
                    o.name as org_name,
                    COUNT(DISTINCT c.id) as total_contacts,
                    COUNT(DISTINCT CASE WHEN c.location IS NOT NULL AND c.location != '' THEN c.id END) as contacts_with_location,
                    COUNT(DISTINCT CASE WHEN c.location IS NULL OR c.location = '' THEN c.id END) as contacts_needing_location
                FROM organisations o
                LEFT JOIN employees e ON o.id = e.organisation_id
                LEFT JOIN contacts c ON e.contact_id = c.id
                GROUP BY o.id, o.name
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            stats = []
            for row in results:
                stats.append({
                    'org_id': row[0],
                    'org_name': row[1],
                    'total_contacts': row[2] or 0,
                    'contacts_with_location': row[3] or 0,
                    'contacts_needing_location': row[4] or 0
                })
            
            cursor.close()
            conn.close()
            
            logger.info(f"Updated contact statistics for {len(stats)} organizations")
            return stats
            
        except Exception as e:
            logger.error(f"Error updating contact statistics: {e}")
            return []
    
    def check_database_health(self):
        """Check database health and connectivity"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check table counts
            tables = ['organisations', 'users', 'contacts', 'employees', 'job_descriptions', 'search_history']
            counts = {}
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            
            # Check for any orphaned records
            cursor.execute("""
                SELECT COUNT(*) FROM contacts c
                LEFT JOIN employees e ON c.id = e.contact_id
                WHERE e.id IS NULL
            """)
            orphaned_contacts = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            health_status = {
                'status': 'healthy',
                'table_counts': counts,
                'orphaned_contacts': orphaned_contacts,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Database health check: {health_status}")
            return health_status
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def archive_old_job_descriptions(self):
        """Archive job descriptions older than 6 months"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Create archive table if it doesn't exist
            create_archive_table = """
                CREATE TABLE IF NOT EXISTS job_descriptions_archive (
                    LIKE job_descriptions INCLUDING ALL
                )
            """
            cursor.execute(create_archive_table)
            
            # Move old job descriptions to archive
            archive_query = """
                INSERT INTO job_descriptions_archive 
                SELECT * FROM job_descriptions 
                WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '6 months'
            """
            cursor.execute(archive_query)
            archived_count = cursor.rowcount
            
            # Delete archived records from main table
            if archived_count > 0:
                delete_query = """
                    DELETE FROM job_descriptions 
                    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '6 months'
                """
                cursor.execute(delete_query)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Archived {archived_count} old job descriptions")
            return archived_count
            
        except Exception as e:
            logger.error(f"Error archiving job descriptions: {e}")
            return 0
    
    def generate_daily_report(self):
        """Generate daily system report"""
        try:
            # Get various statistics
            contact_stats = self.update_contact_statistics()
            health_status = self.check_database_health()
            
            # Calculate enrichment success rate
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN success = true THEN 1 END) as successful_enrichments
                FROM location_enrichment_log 
                WHERE enrichment_date >= CURRENT_DATE
            """)
            enrichment_stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            # Calculate success rate
            total_attempts = enrichment_stats[0] or 0
            successful = enrichment_stats[1] or 0
            success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0
            
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'contact_statistics': contact_stats,
                'database_health': health_status,
                'location_enrichment': {
                    'total_attempts': total_attempts,
                    'successful_enrichments': successful,
                    'success_rate': round(success_rate, 2)
                },
                'maintenance_tasks': {
                    'search_history_cleaned': self.clean_old_search_history(),
                    'location_logs_cleaned': self.clean_old_location_logs(),
                    'job_descriptions_archived': self.archive_old_job_descriptions()
                }
            }
            
            logger.info(f"Daily report generated: {json.dumps(report, indent=2)}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return None
    
    def run_daily_maintenance(self):
        """Run all daily maintenance tasks"""
        logger.info("Starting daily maintenance tasks")
        
        try:
            # Clean old data
            self.clean_old_search_history()
            self.clean_old_location_logs()
            
            # Archive old job descriptions
            self.archive_old_job_descriptions()
            
            # Update statistics
            self.update_contact_statistics()
            
            # Generate report
            report = self.generate_daily_report()
            
            logger.info("Daily maintenance tasks completed successfully")
            return report
            
        except Exception as e:
            logger.error(f"Error during daily maintenance: {e}")
            return None

if __name__ == "__main__":
    # This script can be run directly or called by a cron job
    cron = CronJobs()
    
    # Run daily maintenance
    cron.run_daily_maintenance()

