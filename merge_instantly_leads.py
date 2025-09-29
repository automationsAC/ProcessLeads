#!/usr/bin/env python3
"""
Script to merge Instantly CSV files and mark existing leads in Supabase
"""

import pandas as pd
import os
import glob
from pathlib import Path
import logging
from supabase import create_client, Client
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instantly_merge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_instantly_csvs(csv_directory):
    """Load and merge all Instantly CSV files"""
    logger.info(f"Loading CSV files from: {csv_directory}")
    
    csv_files = glob.glob(os.path.join(csv_directory, "*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files")
    
    all_dataframes = []
    
    for csv_file in csv_files:
        try:
            logger.info(f"Processing: {os.path.basename(csv_file)}")
            df = pd.read_csv(csv_file)
            
            # Add source file column
            df['source_file'] = os.path.basename(csv_file)
            
            # Extract campaign ID from filename if possible
            filename = os.path.basename(csv_file)
            if 'leads (' in filename:
                campaign_id = filename.split('leads (')[1].split(')')[0]
                df['campaign_id'] = campaign_id
            
            all_dataframes.append(df)
            logger.info(f"Loaded {len(df)} rows from {filename}")
            
        except Exception as e:
            logger.error(f"Error loading {csv_file}: {e}")
    
    if not all_dataframes:
        logger.error("No CSV files could be loaded")
        return None
    
    # Merge all dataframes
    merged_df = pd.concat(all_dataframes, ignore_index=True, sort=False)
    logger.info(f"Merged total: {len(merged_df)} rows")
    
    return merged_df

def clean_and_deduplicate(df):
    """Clean and deduplicate the merged data"""
    logger.info("Cleaning and deduplicating data...")
    
    # Remove rows with empty emails
    initial_count = len(df)
    df = df.dropna(subset=['Email'])
    df = df[df['Email'].str.strip() != '']
    logger.info(f"Removed {initial_count - len(df)} rows with empty emails")
    
    # Remove duplicates based on email
    initial_count = len(df)
    df = df.drop_duplicates(subset=['Email'], keep='first')
    logger.info(f"Removed {initial_count - len(df)} duplicate emails")
    
    # Clean email addresses
    df['Email'] = df['Email'].str.strip().str.lower()
    
    return df

def connect_to_supabase():
    """Connect to Supabase"""
    try:
        # Import config
        from config import SUPABASE_URL, SUPABASE_ANON_KEY
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("Connected to Supabase successfully")
        return supabase
    except ImportError:
        logger.error("config.py not found. Please copy config_example.py to config.py and add your credentials")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        return None

def mark_instantly_leads_in_supabase(supabase, instantly_df):
    """Mark leads in Supabase that are already in Instantly"""
    logger.info("Marking Instantly leads in Supabase...")
    
    # Get unique emails from Instantly data
    instantly_emails = set(instantly_df['Email'].tolist())
    logger.info(f"Found {len(instantly_emails)} unique emails in Instantly data")
    
    # Create a mapping of email to campaign info
    email_to_campaign = {}
    for _, row in instantly_df.iterrows():
        email = row['Email']
        campaign_name = row.get('Campaign Name', '')
        campaign_id = row.get('campaign_id', '')
        
        email_to_campaign[email] = {
            'campaign_name': campaign_name,
            'campaign_id': campaign_id
        }
    
    # Process in batches
    batch_size = 100
    total_updated = 0
    
    for i in range(0, len(instantly_emails), batch_size):
        batch_emails = list(instantly_emails)[i:i + batch_size]
        
        try:
            # Update records in Supabase
            for email in batch_emails:
                campaign_info = email_to_campaign.get(email, {})
                
                update_data = {
                    'added_to_instantly': True,
                    'instantly_campaign_id': campaign_info.get('campaign_id', ''),
                }
                
                # Update the record
                result = supabase.table('contacts_grid_view').update(update_data).eq('email', email).execute()
                
                if result.data:
                    total_updated += len(result.data)
                    logger.info(f"Updated {email} - Campaign: {campaign_info.get('campaign_name', 'Unknown')}")
                
        except Exception as e:
            logger.error(f"Error updating batch {i//batch_size + 1}: {e}")
    
    logger.info(f"Total records updated: {total_updated}")
    return total_updated

def generate_summary_report(instantly_df, updated_count):
    """Generate a summary report"""
    logger.info("Generating summary report...")
    
    # Campaign summary
    campaign_summary = instantly_df.groupby('Campaign Name').size().reset_index(name='lead_count')
    
    # Status summary
    status_summary = instantly_df.groupby('Lead Status').size().reset_index(name='count')
    
    # Country summary
    country_summary = instantly_df.groupby('country').size().reset_index(name='count')
    
    report = {
        'total_instantly_leads': len(instantly_df),
        'unique_emails': len(instantly_df['Email'].unique()),
        'supabase_records_updated': updated_count,
        'campaigns': campaign_summary.to_dict('records'),
        'lead_statuses': status_summary.to_dict('records'),
        'countries': country_summary.to_dict('records')
    }
    
    # Save report
    with open('instantly_merge_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info("Summary report saved to instantly_merge_report.json")
    return report

def main():
    """Main function"""
    logger.info("Starting Instantly leads merge and Supabase update process")
    
    # Path to CSV files
    csv_directory = "/Users/michaltuszynski/properties check/Leads from campaigns"
    
    # Load and merge CSV files
    instantly_df = load_instantly_csvs(csv_directory)
    if instantly_df is None:
        logger.error("Failed to load CSV files")
        return
    
    # Clean and deduplicate
    instantly_df = clean_and_deduplicate(instantly_df)
    
    # Save merged data
    output_file = "merged_instantly_leads.csv"
    instantly_df.to_csv(output_file, index=False)
    logger.info(f"Merged data saved to {output_file}")
    
    # Connect to Supabase
    supabase = connect_to_supabase()
    if supabase is None:
        logger.error("Failed to connect to Supabase")
        return
    
    # Mark leads in Supabase
    updated_count = mark_instantly_leads_in_supabase(supabase, instantly_df)
    
    # Generate summary report
    report = generate_summary_report(instantly_df, updated_count)
    
    logger.info("Process completed successfully!")
    logger.info(f"Summary: {report['total_instantly_leads']} Instantly leads, {updated_count} Supabase records updated")

if __name__ == "__main__":
    main()
