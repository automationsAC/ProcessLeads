#!/usr/bin/env python3
"""
Parse scrap_data JSON field into structured columns
Processes in batches to avoid Supabase rate limits
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from supabase import create_client, Client
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scrap_data_parsing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScrapDataParser:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    def fetch_unparsed_batch(self, batch_size: int = 100, country: Optional[str] = None, start_id: int = None) -> List[Dict]:
        """Fetch leads that need scrap_data parsing"""
        logger.info(f"Fetching {batch_size} unparsed leads (country: {country or 'all'}, start_id: {start_id})...")
        
        # Simple query to avoid timeout - fetch by ID range and filter client-side
        query = self.supabase.table('contacts_grid_view').select('id, scrap_data, country, parsing_completed')
        
        # Start from specific ID if provided
        if start_id:
            query = query.gte('id', start_id)
        
        # Optional country filter (safe, indexed)
        if country:
            query = query.eq('country', country)
        
        # Order by ID and fetch more than needed
        query = query.order('id', desc=False)
        query = query.limit(batch_size * 10)  # Fetch more to compensate for filtering
        
        try:
            result = query.execute()
            all_leads = result.data
            
            # Filter client-side for unparsed records with scrap_data
            leads = [
                lead for lead in all_leads
                if lead.get('scrap_data')  # Has scrap_data
                and not lead.get('parsing_completed')  # Not yet parsed (null or false)
            ][:batch_size]
            
            logger.info(f"Fetched {len(leads)} unparsed leads (from {len(all_leads)} total)")
            return leads
        except Exception as e:
            logger.error(f"Failed to fetch leads: {e}")
            return []
    
    def parse_scrap_data(self, lead: Dict) -> Dict:
        """Parse scrap_data JSON into structured fields"""
        lead_id = lead.get('id')
        scrap_data = lead.get('scrap_data')
        
        # Initialize parsed data
        parsed = {
            'parsed_images': None,
            'parsed_description': None,
            'parsed_latitude': None,
            'parsed_longitude': None,
            'parsing_completed': True,
            'parsing_processed_at': datetime.now().isoformat()
        }
        
        # Handle different scrap_data formats
        if not scrap_data:
            logger.warning(f"Lead {lead_id}: No scrap_data found")
            return parsed
        
        try:
            # If scrap_data is a string, parse it
            if isinstance(scrap_data, str):
                if scrap_data.lower() == 'null' or scrap_data.strip() == '':
                    logger.info(f"Lead {lead_id}: scrap_data is null string")
                    return parsed
                scrap_json = json.loads(scrap_data)
            elif isinstance(scrap_data, dict):
                scrap_json = scrap_data
            else:
                logger.warning(f"Lead {lead_id}: Unexpected scrap_data type: {type(scrap_data)}")
                return parsed
            
            # Extract images (keep as JSON array)
            if 'images' in scrap_json and scrap_json['images']:
                parsed['parsed_images'] = scrap_json['images']
                logger.debug(f"Lead {lead_id}: Found {len(scrap_json['images'])} images")
            
            # Extract description
            if 'description' in scrap_json and scrap_json['description']:
                parsed['parsed_description'] = scrap_json['description']
                logger.debug(f"Lead {lead_id}: Found description")
            
            # Extract location coordinates
            if 'location' in scrap_json and isinstance(scrap_json['location'], dict):
                location = scrap_json['location']
                
                # Try different coordinate field names
                lat = location.get('lat') or location.get('latitude')
                lng = location.get('lng') or location.get('longitude') or location.get('lon')
                
                if lat is not None:
                    try:
                        parsed['parsed_latitude'] = float(lat)
                        logger.debug(f"Lead {lead_id}: Found latitude: {lat}")
                    except (ValueError, TypeError):
                        logger.warning(f"Lead {lead_id}: Invalid latitude value: {lat}")
                
                if lng is not None:
                    try:
                        parsed['parsed_longitude'] = float(lng)
                        logger.debug(f"Lead {lead_id}: Found longitude: {lng}")
                    except (ValueError, TypeError):
                        logger.warning(f"Lead {lead_id}: Invalid longitude value: {lng}")
            
            logger.info(f"Lead {lead_id}: Successfully parsed scrap_data")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Lead {lead_id}: JSON decode error - {e}")
            return parsed
        except Exception as e:
            logger.error(f"Lead {lead_id}: Unexpected error parsing scrap_data - {e}")
            return parsed
    
    def update_parsed_data(self, lead_id: int, parsed_data: Dict) -> bool:
        """Update lead with parsed data"""
        try:
            result = self.supabase.table('contacts_grid_view').update(parsed_data).eq('id', lead_id).execute()
            if result.data:
                logger.info(f"Lead {lead_id}: Updated with parsed data")
                return True
            else:
                logger.warning(f"Lead {lead_id}: Update returned no data")
                return False
        except Exception as e:
            logger.error(f"Lead {lead_id}: Failed to update - {e}")
            return False
    
    def process_batch(self, batch_size: int = 100, country: Optional[str] = None, start_id: int = None) -> Dict:
        """Process a batch of leads"""
        start_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info(f"Starting scrap_data parsing batch (size: {batch_size}, country: {country or 'all'})")
        logger.info(f"Start time: {start_time.isoformat()}")
        
        # Fetch unparsed leads
        leads = self.fetch_unparsed_batch(batch_size, country, start_id)
        
        if not leads:
            logger.warning("No unparsed leads found")
            return {
                "leads_processed": 0,
                "updated_count": 0,
                "errors": 0,
                "stats": {}
            }
        
        updated_count = 0
        errors = 0
        stats = {
            'with_images': 0,
            'with_description': 0,
            'with_location': 0,
            'empty_scrap_data': 0
        }
        
        for lead in leads:
            try:
                # Parse the scrap_data
                parsed_data = self.parse_scrap_data(lead)
                
                # Track stats
                if parsed_data.get('parsed_images'):
                    stats['with_images'] += 1
                if parsed_data.get('parsed_description'):
                    stats['with_description'] += 1
                if parsed_data.get('parsed_latitude') and parsed_data.get('parsed_longitude'):
                    stats['with_location'] += 1
                if not any([parsed_data.get('parsed_images'), parsed_data.get('parsed_description'), 
                           parsed_data.get('parsed_latitude')]):
                    stats['empty_scrap_data'] += 1
                
                # Update in Supabase
                if self.update_parsed_data(lead['id'], parsed_data):
                    updated_count += 1
                
                # Rate limiting - small delay to avoid hitting Supabase limits
                time.sleep(0.05)
                
            except Exception as e:
                errors += 1
                logger.error(f"Error processing lead {lead.get('id')}: {e}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info(f"Batch processing completed")
        logger.info(f"End time: {end_time.isoformat()}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Leads processed: {len(leads)}")
        logger.info(f"Successfully updated: {updated_count}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Stats: {stats}")
        logger.info("=" * 80)
        
        return {
            "leads_processed": len(leads),
            "updated_count": updated_count,
            "errors": errors,
            "stats": stats,
            "duration_seconds": duration,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

def main():
    """Main function to run scrap_data parsing"""
    try:
        # Import config - try local file first, then environment variables
        import os
        try:
            from config import SUPABASE_URL, SUPABASE_ANON_KEY
        except ImportError:
            # Running on Render - use environment variables
            SUPABASE_URL = os.environ.get('SUPABASE_URL')
            SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
            
            if not all([SUPABASE_URL, SUPABASE_ANON_KEY]):
                raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_ANON_KEY")
        
        # Initialize Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        # Initialize parser
        parser = ScrapDataParser(supabase)
        
        # Process batch (default 100 leads)
        # You can specify country: result = parser.process_batch(batch_size=100, country='es')
        result = parser.process_batch(batch_size=100)
        
        if "error" in result:
            logger.error(f"Batch processing failed: {result['error']}")
            exit(1)
        else:
            logger.info(f"Batch processing completed successfully: {result}")
            exit(0)
            
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
