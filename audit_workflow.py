"""
Audit script to verify logging and record fetching logic
"""
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_ANON_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

print('=' * 100)
print('WORKFLOW AUDIT - RECORD FETCHING & LOGGING')
print('=' * 100)

# Get sample data
sample = supabase.table('contacts_grid_view').select(
    'id, email, zerobounce_status, zerobounce_processed, '
    'hubspot_check_2_completed, hubspot_duplicate_check_2'
).order('id').limit(1000).execute()

print(f'\n📊 ANALYZING FIRST 1000 LEADS:')
print('-' * 100)

# Categorize leads
categories = {
    'no_email': 0,
    'ready_for_zerobounce': 0,
    'zerobounce_done_waiting_hubspot': 0,
    'fully_processed': 0,
    'invalid_email': 0
}

for lead in sample.data:
    email = lead.get('email')
    zb_status = lead.get('zerobounce_status')
    zb_processed = lead.get('zerobounce_processed')
    hs_completed = lead.get('hubspot_check_2_completed')
    
    if not email:
        categories['no_email'] += 1
    elif not zb_status:
        categories['ready_for_zerobounce'] += 1
    elif zb_status == 'valid' and zb_processed and not hs_completed:
        categories['zerobounce_done_waiting_hubspot'] += 1
    elif hs_completed:
        categories['fully_processed'] += 1
    else:
        categories['invalid_email'] += 1

print('\n🔍 LEAD CATEGORIES:')
for category, count in categories.items():
    print(f'  {category:40} {count:5}')

print('\n' + '=' * 100)
print('WORKFLOW FETCHING LOGIC CHECK')
print('=' * 100)

# Test ZeroBounce fetching logic
print('\n1️⃣  ZEROBOUNCE VALIDATOR - Should fetch leads with:')
print('   ✓ email IS NOT NULL')
print('   ✓ zerobounce_status IS NULL')

zb_eligible = [
    l for l in sample.data 
    if l.get('email') and not l.get('zerobounce_status')
]
print(f'\n   Found {len(zb_eligible)} eligible leads in sample')
if zb_eligible:
    print(f'   Sample: ID {zb_eligible[0]["id"]}, Email: {zb_eligible[0]["email"]}')

# Test HubSpot fetching logic
print('\n2️⃣  HUBSPOT CHECKER - Should fetch leads with:')
print('   ✓ zerobounce_status = "valid"')
print('   ✓ zerobounce_processed = TRUE')
print('   ✓ hubspot_check_2_completed IS NULL or FALSE')
print('   ✓ email IS NOT NULL')

hs_eligible = [
    l for l in sample.data 
    if l.get('zerobounce_status') == 'valid'
    and l.get('zerobounce_processed') == True
    and not l.get('hubspot_check_2_completed')
    and l.get('email')
]
print(f'\n   Found {len(hs_eligible)} eligible leads in sample')
if hs_eligible:
    print(f'   Sample: ID {hs_eligible[0]["id"]}, Email: {hs_eligible[0]["email"]}')

print('\n' + '=' * 100)
print('WORKFLOW STATUS')
print('=' * 100)
print(f'\n✅ Ready for ZeroBounce: {len(zb_eligible)} leads')
print(f'⏳ Waiting for HubSpot: {len(hs_eligible)} leads')
print(f'✅ Fully processed: {categories["fully_processed"]} leads')

print('\n' + '=' * 100)

