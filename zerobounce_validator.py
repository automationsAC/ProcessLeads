#!/usr/bin/env python3
"""
ZeroBounce Email Validation Module
Processes leads in batches and validates emails using ZeroBounce API
"""

import requests
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from supabase import create_client, Client
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zerobounce_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ZeroBounceValidator:
    def __init__(self, api_key: str, supabase_client: Client):
        self.api_key = api_key
        self.supabase = supabase_client
        self.base_url = "https://api.zerobounce.net/v2"
        
    def get_priority_config(self, priority_api_key: str = None) -> Dict:
        """Get current priority configuration from your system"""
        try:
            # Your actual domain
            url = "https://clay-lead-validator-7c1354ad.base44.app/functions/getCurrentPriorities"
            
            headers = {}
            if priority_api_key:
                headers['Authorization'] = f'Bearer {priority_api_key}'
                
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"Retrieved priority config: {result.get('total_active_countries', 0)} active countries")
                return result
            else:
                logger.error(f"Priority API returned error: {result}")
                return self._get_fallback_priorities()
                
        except Exception as e:
            logger.error(f"Failed to get priority config: {e}")
            return self._get_fallback_priorities()
    
    def _get_fallback_priorities(self) -> Dict:
        """Fallback priority configuration"""
        return {
            "success": True,
            "priorities": [
                {
                    "country": "pl",
                    "country_name": "Poland",
                    "priority_level": 1,
                    "target_daily_evaluations": 1000,
                    "is_active": True,
                    "current_stats": {"total": 3187, "unassigned": 3187, "assigned": 0, "evaluated": 0}
                },
                {
                    "country": "de", 
                    "country_name": "Germany",
                    "priority_level": 2,
                    "target_daily_evaluations": 500,
                    "is_active": True,
                    "current_stats": {"total": 1348, "unassigned": 1348, "assigned": 0, "evaluated": 0}
                },
                {
                    "country": "es",
                    "country_name": "Spain", 
                    "priority_level": 3,
                    "target_daily_evaluations": 200,
                    "is_active": True,
                    "current_stats": {"total": 470, "unassigned": 470, "assigned": 0, "evaluated": 0}
                }
            ],
            "total_active_countries": 3
        }
    
    def fetch_leads_batch(self, batch_size: int = 100, country_priority: str = None) -> List[Dict]:
        """Fetch a batch of leads ready for validation"""
        logger.info(f"Fetching {batch_size} leads for validation (country: {country_priority or 'all'})...")
        
        # Use lightweight query to avoid timeout
        query = self.supabase.table('contacts_grid_view').select('id, email, country, zerobounce_status, humanfit, added_to_instantly')
        
        # Add country filter if specified
        if country_priority:
            query = query.eq('country', country_priority)
        
        # Order by ID for consistent batching
        query = query.order('id', desc=False)
        query = query.limit(batch_size * 10)  # Fetch more to filter client-side
        
        try:
            result = query.execute()
            all_leads = result.data
            
            # Filter client-side for leads that match all criteria:
            # 1. Has email
            # 2. Not yet validated by ZeroBounce
            # 3. NOT humanfit = false (exclude false, allow true and null)
            # 4. NOT (added_to_instantly = true AND humanfit = null)
            leads = [
                lead for lead in all_leads
                if lead.get('email')  # Has email
                and not lead.get('zerobounce_status')  # Not yet validated
                and lead.get('humanfit') != False  # Exclude humanfit = false
                and not (lead.get('added_to_instantly') == True and lead.get('humanfit') is None)  # Exclude added_to_instantly=true + humanfit=null
            ][:batch_size]
            
            logger.info(f"Fetched {len(leads)} leads for validation (from {len(all_leads)} total, filtered by humanfit rules)")
            return leads
        except Exception as e:
            logger.error(f"Failed to fetch leads: {e}")
            return []
    
    def mark_leads_as_processing(self, lead_ids: List[int]) -> bool:
        """Mark leads as being processed by ZeroBounce"""
        try:
            # Mark as processing
            update_data = {
                'zerobounce_processed': False
            }
            
            result = self.supabase.table('contacts_grid_view').update(update_data).in_('id', lead_ids).execute()
            logger.info(f"Marked {len(lead_ids)} leads as processing")
            return True
        except Exception as e:
            logger.error(f"Failed to mark leads as processing: {e}")
            return False
    
    def validate_emails_batch(self, emails: List[str]) -> Dict:
        """Validate emails using ZeroBounce batch API"""
        logger.info(f"Validating {len(emails)} emails with ZeroBounce...")
        
        url = f"{self.base_url}/validatebatch"
        
        payload = {
            "api_key": self.api_key,
            "email_batch": [{"email_address": email} for email in emails]
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"ZeroBounce validation completed: {result.get('total', 0)} emails processed")
            return result
        except Exception as e:
            logger.error(f"ZeroBounce validation failed: {e}")
            return {"error": str(e)}
    
    def update_validation_results(self, leads: List[Dict], validation_results: Dict) -> int:
        """Update leads with validation results"""
        if "error" in validation_results:
            logger.error("Cannot update results due to validation error")
            return 0
            
        updated_count = 0
        
        # Debug: print the actual response structure
        logger.info(f"ZeroBounce response structure: {validation_results}")
        
        # Handle different response formats
        email_batch = validation_results.get("email_batch", [])
        if not email_batch:
            # Try alternative response format
            email_batch = validation_results.get("results", [])
        
        # Create email mapping - handle different field names
        email_results = {}
        for item in email_batch:
            email = item.get("email_address") or item.get("email") or item.get("address")
            if email:
                email_results[email] = item
        
        logger.info(f"Parsed {len(email_results)} email results")
        
        for lead in leads:
            email = lead['email']
            if email in email_results:
                result = email_results[email]
                
                # Use existing fields to store validation results
                validation_status = result.get('status', 'unknown')
                sub_status = result.get('sub_status', '')
                
                # Treat role-based "do_not_mail" as valid for outreach
                if validation_status == 'do_not_mail' and sub_status == 'role_based':
                    effective_status = 'valid'
                    validation_error = ''
                elif validation_status == 'invalid' or validation_status == 'catch-all':
                    effective_status = 'invalid'
                    validation_error = sub_status or validation_status
                else:
                    effective_status = validation_status
                    validation_error = sub_status
                
                update_data = {
                    'zerobounce_status': effective_status,
                    'zerobounce_sub_status': validation_error,
                    'zerobounce_validated_at': datetime.now().isoformat(),
                    'zerobounce_processed': False
                }
                
                try:
                    self.supabase.table('contacts_grid_view').update(update_data).eq('id', lead['id']).execute()
                    updated_count += 1
                    logger.info(f"Updated lead {lead['id']}: {effective_status} ({validation_status})")
                except Exception as e:
                    logger.error(f"Failed to update lead {lead['id']}: {e}")
            else:
                logger.warning(f"No validation result found for email: {email}")
        
        logger.info(f"Updated {updated_count} leads with validation results")
        return updated_count
    
    def get_next_priority_country(self, priority_config: Dict) -> Optional[str]:
        """Get the next country to process based on priority and stats"""
        priorities = priority_config.get('priorities', [])
        
        # Sort by priority level (1 = highest priority)
        sorted_priorities = sorted(priorities, key=lambda x: x.get('priority_level', 999))
        
        for priority in sorted_priorities:
            if not priority.get('is_active', False):
                continue
                
            stats = priority.get('current_stats', {})
            unassigned = stats.get('unassigned', 0)
            
            if unassigned > 0:
                logger.info(f"Next priority country: {priority['country']} ({priority['country_name']}) - {unassigned} unassigned")
                return priority['country']
        
        logger.info("No countries with unassigned leads found")
        return None
    
    def process_batch(self, batch_size: int = 100, country_priority: str = None) -> Dict:
        """Process a single batch of leads through ZeroBounce validation"""
        logger.info(f"Starting batch processing (size: {batch_size}, country: {country_priority})")
        
        # Fetch leads
        leads = self.fetch_leads_batch(batch_size, country_priority)
        if not leads:
            return {"error": "No leads found to process"}
        
        # Mark as processing
        lead_ids = [lead['id'] for lead in leads]
        if not self.mark_leads_as_processing(lead_ids):
            return {"error": "Failed to mark leads as processing"}
        
        # Extract emails
        emails = [lead['email'] for lead in leads if lead.get('email')]
        
        # Validate with ZeroBounce
        validation_results = self.validate_emails_batch(emails)
        
        # Update results
        updated_count = self.update_validation_results(leads, validation_results)
        
        return {
            "leads_processed": len(leads),
            "emails_validated": len(emails),
            "results_updated": updated_count,
            "validation_results": validation_results
        }
    
    def process_by_priority(self, batch_size: int = 100, priority_api_key: str = None) -> Dict:
        """Process leads based on current priority configuration"""
        # Get priority configuration
        priority_config = self.get_priority_config(priority_api_key)
        
        # Get next country to process
        next_country = self.get_next_priority_country(priority_config)
        
        if not next_country:
            return {"error": "No countries available for processing"}
        
        # Process batch for the priority country
        result = self.process_batch(batch_size, next_country)
        result["priority_country"] = next_country
        result["priority_config"] = priority_config
        
        return result

def main():
    """Main function to run ZeroBounce validation"""
    try:
        # Import config - try local file first, then environment variables
        import os
        try:
            from config import SUPABASE_URL, SUPABASE_ANON_KEY, ZEROBOUNCE_API_KEY, PRIORITY_API_KEY
        except ImportError:
            # Running on Render - use environment variables
            SUPABASE_URL = os.environ.get('SUPABASE_URL')
            SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
            ZEROBOUNCE_API_KEY = os.environ.get('ZEROBOUNCE_API_KEY')
            PRIORITY_API_KEY = os.environ.get('PRIORITY_API_KEY')
            
            if not all([SUPABASE_URL, SUPABASE_ANON_KEY, ZEROBOUNCE_API_KEY]):
                raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_ANON_KEY, ZEROBOUNCE_API_KEY")
        
        # Initialize Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        # Initialize ZeroBounce validator
        validator = ZeroBounceValidator(ZEROBOUNCE_API_KEY, supabase)
        
        # Get priority configuration
        priority_config = validator.get_priority_config(PRIORITY_API_KEY)
        logger.info(f"Priority config: {priority_config}")
        
        # Process batch by priority
        result = validator.process_by_priority(batch_size=100, priority_api_key=PRIORITY_API_KEY)
        
        if "error" in result:
            logger.error(f"Batch processing failed: {result['error']}")
            exit(1)
        else:
            logger.info(f"Batch processing completed: {result}")
            exit(0)
            
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
