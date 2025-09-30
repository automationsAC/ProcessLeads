#!/usr/bin/env python3
"""
HubSpot Duplicate Checker Module
Performs comprehensive duplicate checking against HubSpot and AlohaCamp
"""

import requests
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from supabase import create_client, Client
import time
import re
import unicodedata
from rapidfuzz import fuzz
import phonenumbers

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hubspot_duplicate_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HubSpotClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
    def search_contacts_by_email(self, email: str) -> List[Dict]:
        """Search contacts by exact email match"""
        if not email or email == "nan":
            return []
            
        url = f"{self.base_url}/crm/v3/objects/contacts/search"
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email
                }]
            }],
            "properties": ["id", "email", "firstname", "lastname", "phone", "company"],
            "limit": 10
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Error searching contacts by email {email}: {e}")
            return []
    
    def search_contacts_by_phone(self, phone_e164: str) -> List[Dict]:
        """Search contacts by phone number"""
        if not phone_e164:
            return []
            
        url = f"{self.base_url}/crm/v3/objects/contacts/search"
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "phone",
                    "operator": "EQ",
                    "value": phone_e164
                }]
            }],
            "properties": ["id", "email", "firstname", "lastname", "phone", "company"],
            "limit": 10
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Error searching contacts by phone {phone_e164}: {e}")
            return []
    
    def search_contacts_by_name(self, first_name: str, last_name: str) -> List[Dict]:
        """Search contacts by name (fuzzy matching)"""
        if not first_name and not last_name:
            return []
            
        url = f"{self.base_url}/crm/v3/objects/contacts/search"
        filters = []
        
        if first_name:
            filters.append({
                "propertyName": "firstname",
                "operator": "CONTAINS_TOKEN",
                "value": first_name
            })
        if last_name:
            filters.append({
                "propertyName": "lastname", 
                "operator": "CONTAINS_TOKEN",
                "value": last_name
            })
        
        if not filters:
            return []
            
        payload = {
            "filterGroups": [{"filters": filters}],
            "properties": ["id", "email", "firstname", "lastname", "phone", "company"],
            "limit": 20
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Error searching contacts by name {first_name} {last_name}: {e}")
            return []
    
    def search_deals_by_property_name(self, property_name: str, city: str = None) -> List[Dict]:
        """Search deals by property name with fuzzy matching"""
        if not property_name:
            return []
            
        url = f"{self.base_url}/crm/v3/objects/deals/search"
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "dealname",
                    "operator": "CONTAINS_TOKEN",
                    "value": property_name
                }]
            }],
            "properties": ["id", "dealname", "dealstage", "amount", "closedate"],
            "limit": 20
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Error searching deals by property name {property_name}: {e}")
            return []

class AirtableClient:
    def __init__(self, token: str, base_id: str):
        self.token = token
        self.base_id = base_id
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
        })
    
    def search_properties(self, property_name: str, city: str = None) -> List[Dict]:
        """Search for properties in AlohaCamp Airtable"""
        if not property_name:
            return []
            
        # Try to search - if it fails, just skip Airtable checking
        try:
            # Escape single quotes in property name for Airtable formula
            safe_name = property_name.replace("'", "\\'")
            
            url = f"https://api.airtable.com/v0/{self.base_id}/Properties%20v2"
            params = {
                "filterByFormula": f"SEARCH(LOWER('{safe_name}'), LOWER({{Property Name}}))",
                "maxRecords": 20
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("records", [])
        except Exception as e:
            # Log once but don't spam - Airtable checking is optional
            if not hasattr(self, '_airtable_error_logged'):
                logger.warning(f"Airtable checking disabled due to error: {e}")
                self._airtable_error_logged = True
            return []

class HubSpotDuplicateChecker:
    def __init__(self, hubspot_token: str, supabase_client: Client, airtable_token: str = None, airtable_base: str = None):
        self.hubspot = HubSpotClient(hubspot_token)
        self.supabase = supabase_client
        self.airtable = AirtableClient(airtable_token, airtable_base) if airtable_token and airtable_base else None
        
    def normalize_text(self, value: Optional[str]) -> str:
        """Normalize text for fuzzy matching"""
        if not isinstance(value, str):
            return ""
        s = value.strip().lower()
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = re.sub(r"[^a-z0-9\s]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s
    
    def normalize_phone(self, phone: Optional[str], country_code: Optional[str] = None) -> Optional[str]:
        """Normalize phone number to E.164 format"""
        if not isinstance(phone, str) or not phone.strip():
            return None
        raw = phone.strip()
        default = None
        if isinstance(country_code, str) and country_code.strip():
            default = country_code.upper()
        try:
            num = phonenumbers.parse(raw, default)
            if phonenumbers.is_possible_number(num) and phonenumbers.is_valid_number(num):
                return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            return None
        return None
    
    def fetch_leads_batch(self, batch_size: int = 100, start_id: int = None) -> List[Dict]:
        """Fetch leads ready for HubSpot duplicate checking"""
        logger.info(f"Fetching {batch_size} leads for HubSpot duplicate checking (start_id: {start_id})...")
        
        # Use direct SQL via RPC or a simpler approach - fetch by ID and filter client-side
        query = self.supabase.table('contacts_grid_view').select('id, email, phone, first_name, last_name, company, property_name, address_city_from_lead, country, zerobounce_status, hubspot_duplicate_check_2')
        
        # Only filter by ID range if provided
        if start_id:
            query = query.gte('id', start_id)
        
        # Order by ID and limit
        query = query.order('id', desc=False)
        query = query.limit(batch_size * 10)  # Fetch more to compensate for filtering
        
        try:
            result = query.execute()
            all_leads = result.data
            
            # Filter in Python for leads that match our criteria
            leads = [
                lead for lead in all_leads 
                if lead.get('zerobounce_status') == 'valid' 
                and lead.get('hubspot_duplicate_check_2') is None
                and lead.get('email')
            ][:batch_size]
            
            logger.info(f"Fetched {len(leads)} leads for HubSpot duplicate checking (from {len(all_leads)} total)")
            return leads
        except Exception as e:
            logger.error(f"Failed to fetch leads: {e}")
            return []
    
    def check_contact_duplicates(self, lead: Dict) -> Dict:
        """Check for contact duplicates in HubSpot"""
        email = lead.get('email', '')
        phone = lead.get('phone', '')
        first_name = lead.get('first_name', '')
        last_name = lead.get('last_name', '')
        company = lead.get('company', '')
        
        # Normalize phone
        phone_e164 = self.normalize_phone(phone, lead.get('country', ''))
        
        # Search by email first
        contact_results = self.hubspot.search_contacts_by_email(email)
        match_type = None
        
        if contact_results:
            match_type = 'email'
        elif phone_e164:
            # Fallback to phone
            contact_results = self.hubspot.search_contacts_by_phone(phone_e164)
            if contact_results:
                match_type = 'phone'
        
        # If still no results, try name matching
        if not contact_results and (first_name or last_name):
            name_results = self.hubspot.search_contacts_by_name(first_name, last_name)
            if name_results:
                # Fuzzy match names
                for contact in name_results:
                    contact_first = contact.get('properties', {}).get('firstname', '')
                    contact_last = contact.get('properties', {}).get('lastname', '')
                    
                    first_score = fuzz.ratio(self.normalize_text(first_name), self.normalize_text(contact_first)) if first_name and contact_first else 0
                    last_score = fuzz.ratio(self.normalize_text(last_name), self.normalize_text(contact_last)) if last_name and contact_last else 0
                    
                    if first_score >= 80 or last_score >= 80:
                        contact_results = [contact]
                        match_type = 'name'
                        break
        
        if contact_results:
            contact = contact_results[0]
            props = contact.get('properties', {})
            return {
                'found': True,
                'contact_id': contact.get('id'),
                'contact_email': props.get('email', ''),
                'contact_phone': props.get('phone', ''),
                'contact_name': f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                'match_type': match_type
            }
        
        return {'found': False}
    
    def check_deal_duplicates(self, lead: Dict) -> Dict:
        """Check for deal duplicates in HubSpot"""
        property_name = lead.get('property_name', '')
        city = lead.get('address_city_from_lead', '')
        
        if not property_name:
            return {'found': False}
        
        # Search for deals by property name
        deal_results = self.hubspot.search_deals_by_property_name(property_name, city)
        
        if deal_results:
            # Fuzzy match property names
            property_norm = self.normalize_text(property_name)
            best_match = None
            best_score = 0
            
            for deal in deal_results:
                deal_name = deal.get('properties', {}).get('dealname', '')
                deal_norm = self.normalize_text(deal_name)
                
                score = max(
                    fuzz.token_set_ratio(property_norm, deal_norm),
                    fuzz.partial_token_sort_ratio(property_norm, deal_norm)
                )
                
                if score > best_score:
                    best_score = score
                    best_match = deal
            
            if best_match and best_score >= 70:
                props = best_match.get('properties', {})
                return {
                    'found': True,
                    'deal_id': best_match.get('id'),
                    'deal_name': props.get('dealname', ''),
                    'deal_score': best_score
                }
        
        return {'found': False}
    
    def check_alohacamp_duplicates(self, lead: Dict) -> Dict:
        """Check for duplicates in AlohaCamp Airtable"""
        if not self.airtable:
            return {'found': False}
        
        property_name = lead.get('property_name', '')
        city = lead.get('address_city_from_lead', '')
        
        if not property_name:
            return {'found': False}
        
        # Search Airtable
        airtable_results = self.airtable.search_properties(property_name, city)
        
        if airtable_results:
            # Fuzzy match property names
            property_norm = self.normalize_text(property_name)
            best_match = None
            best_score = 0
            
            for record in airtable_results:
                record_name = record.get('fields', {}).get('Name', '')
                record_norm = self.normalize_text(record_name)
                
                score = max(
                    fuzz.token_set_ratio(property_norm, record_norm),
                    fuzz.partial_token_sort_ratio(property_norm, record_norm)
                )
                
                if score > best_score:
                    best_score = score
                    best_match = record
            
            if best_match and best_score >= 70:
                fields = best_match.get('fields', {})
                return {
                    'found': True,
                    'match_id': best_match.get('id'),
                    'match_name': fields.get('Property Name', ''),
                    'score': best_score
                }
        
        return {'found': False}
    
    def process_lead(self, lead: Dict) -> Dict:
        """Process a single lead for duplicate checking"""
        lead_id = lead.get('id')
        logger.info(f"Processing lead {lead_id}: {lead.get('email', '')}")
        
        # Check for contact duplicates
        contact_check = self.check_contact_duplicates(lead)
        
        # Check for deal duplicates
        deal_check = self.check_deal_duplicates(lead)
        
        # Check for AlohaCamp duplicates
        alohacamp_check = self.check_alohacamp_duplicates(lead)
        
        # Determine overall status
        if contact_check['found']:
            status = 'duplicate'
            needs_deal = True
            reason = 'contact_duplicate'
        elif deal_check['found']:
            status = 'duplicate'
            needs_deal = False
            reason = 'deal_exists'
        elif alohacamp_check['found']:
            status = 'duplicate'
            needs_deal = False
            reason = 'alohacamp_exists'
        else:
            status = 'unique'
            needs_deal = True
            reason = 'new_lead'
        
        # Prepare update data
        update_data = {
            'hubspot_duplicate_check_2': status,
            'hubspot_checked_at_2': datetime.now().isoformat(),
            'needs_hubspot_deal': needs_deal,
            'deal_creation_reason': reason
        }
        
        # Add contact details if found
        if contact_check['found']:
            update_data.update({
                'hubspot_contact_id_2': contact_check.get('contact_id'),
                'hubspot_contact_email_2': contact_check.get('contact_email'),
                'hubspot_contact_phone_2': contact_check.get('contact_phone'),
                'hubspot_contact_name_2': contact_check.get('contact_name'),
                'hubspot_contact_match_type_2': contact_check.get('match_type')
            })
        
        # Add deal details if found
        if deal_check['found']:
            update_data.update({
                'hubspot_deal_id_2': deal_check.get('deal_id'),
                'hubspot_deal_name_2': deal_check.get('deal_name'),
                'hubspot_deal_score_2': deal_check.get('deal_score')
            })
        
        # Add AlohaCamp details if found
        if alohacamp_check['found']:
            update_data.update({
                'alohacamp_exists_2': True,
                'alohacamp_match_id_2': alohacamp_check.get('match_id'),
                'alohacamp_match_name_2': alohacamp_check.get('match_name'),
                'alohacamp_score_2': alohacamp_check.get('score')
            })
        else:
            update_data['alohacamp_exists_2'] = False
        
        return update_data
    
    def process_batch(self, batch_size: int = 100, start_id: int = None) -> Dict:
        """Process a batch of leads for HubSpot duplicate checking"""
        logger.info(f"Starting HubSpot duplicate check batch (size: {batch_size}, start_id: {start_id})")
        
        # Fetch leads
        leads = self.fetch_leads_batch(batch_size, start_id)
        if not leads:
            return {"error": "No leads found to process"}
        
        updated_count = 0
        errors = 0
        
        for lead in leads:
            try:
                update_data = self.process_lead(lead)
                
                # Update Supabase
                result = self.supabase.table('contacts_grid_view').update(update_data).eq('id', lead['id']).execute()
                if result.data:
                    updated_count += 1
                    logger.info(f"Updated lead {lead['id']}: {update_data['hubspot_duplicate_check_2']}")
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                errors += 1
                logger.error(f"Error processing lead {lead.get('id')}: {e}")
        
        return {
            "leads_processed": len(leads),
            "updated_count": updated_count,
            "errors": errors
        }

def main():
    """Main function to run HubSpot duplicate checking"""
    try:
        # Import config
        from config import SUPABASE_URL, SUPABASE_ANON_KEY, HUBSPOT_TOKEN, AIRTABLE_TOKEN, AIRTABLE_BASE
        
        # Initialize Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        # Initialize HubSpot duplicate checker
        checker = HubSpotDuplicateChecker(
            hubspot_token=HUBSPOT_TOKEN,
            supabase_client=supabase,
            airtable_token=AIRTABLE_TOKEN,
            airtable_base=AIRTABLE_BASE
        )
        
        # Process batch
        result = checker.process_batch(batch_size=100)
        
        if "error" in result:
            logger.error(f"Batch processing failed: {result['error']}")
        else:
            logger.info(f"Batch processing completed: {result}")
            
    except Exception as e:
        logger.error(f"Main execution failed: {e}")

if __name__ == "__main__":
    main()
