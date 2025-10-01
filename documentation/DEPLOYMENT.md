# Deployment Guide - Lead Processing Pipeline

## Overview
This pipeline processes leads through ZeroBounce email validation and HubSpot duplicate checking before adding them to Instantly campaigns.

## Workflow

```
📥 Supabase Leads
    ↓
✉️  Step 1: ZeroBounce Email Validation
    - Validates email addresses
    - Marks: zerobounce_processed = TRUE
    ↓
🔍 Step 2: HubSpot Duplicate Check
    - Checks for contact/deal duplicates
    - Checks AlohaCamp (Airtable)
    - Marks: hubspot_check_2_completed = TRUE
    ↓
📊 Results:
    - UNIQUE → Ready for Instantly
    - DUPLICATE (contact) → Needs HubSpot deal
    - DUPLICATE (deal exists) → Skip
```

## Prerequisites

### 1. Supabase Fields Required
Run `add_hubspot_check_2_completed_field.sql` to add the tracking field.

### 2. Environment Variables
Create `config.py` from `config_example.py`:

```python
# Supabase
SUPABASE_URL = "your_url"
SUPABASE_ANON_KEY = "your_key"

# ZeroBounce
ZEROBOUNCE_API_KEY = "your_key"

# Priority API
PRIORITY_API_KEY = "your_key"
PRIORITY_API_URL = "your_url"

# HubSpot
HUBSPOT_TOKEN = "your_token"

# Airtable
AIRTABLE_TOKEN = "your_token"
AIRTABLE_BASE = "your_base_id"
```

### 3. Python Dependencies
```bash
pip install -r requirements.txt
```

## Running the Pipeline

### Locally (Testing)
```bash
# Step 1: Validate 100 emails
python3 zerobounce_validator.py

# Step 2: Check for duplicates
python3 hubspot_duplicate_checker.py
```

### Production (Render Cron Jobs)

#### Cron Job 1: Email Validation
```yaml
name: zerobounce-validator
command: python3 zerobounce_validator.py
schedule: "*/30 * * * *"  # Every 30 minutes
```

#### Cron Job 2: HubSpot Duplicate Check
```yaml
name: hubspot-duplicate-checker
command: python3 hubspot_duplicate_checker.py
schedule: "*/30 * * * *"  # Every 30 minutes (offset by 15 min from ZB)
```

## Record Fetching Logic

### ZeroBounce Validator Fetches:
```sql
WHERE:
  - country IN (priority_countries) OR country IS NULL
  - zerobounce_status IS NULL
  - email IS NOT NULL AND email != ''
ORDER BY: created_at
LIMIT: 100
```

### HubSpot Checker Fetches:
```sql
WHERE:
  - zerobounce_status = 'valid'
  - zerobounce_processed = TRUE
  - hubspot_check_2_completed IS NULL or FALSE
  - email IS NOT NULL
ORDER BY: id
LIMIT: 100
```

## Logging

Both scripts log to:
- **Console** (stdout)
- **Log files**: `zerobounce_validation.log`, `hubspot_duplicate_check.log`

### Log Format
```
2025-09-30 12:00:00 - INFO - Starting batch...
2025-09-30 12:00:05 - INFO - Processed 100 leads
2025-09-30 12:00:05 - INFO - Stats: {'unique': 5, 'duplicate': 95}
2025-09-30 12:00:05 - INFO - Duration: 5.2 seconds
```

## Monitoring

### Success Indicators
- ✅ Exit code 0
- ✅ `leads_processed > 0` in output
- ✅ No ERROR logs
- ✅ Duration < 120 seconds

### Warning Signs
- ⚠️  `No leads found to process` - Normal if all processed
- ⚠️  High error count (> 10%)
- ⚠️  Duration > 300 seconds

### Error Alerts
- ❌ Exit code 1
- ❌ Database connection failures
- ❌ API authentication failures

## Testing Checklist

Before deploying:
- [ ] `config.py` has all credentials
- [ ] Supabase field `hubspot_check_2_completed` exists
- [ ] Test run processes at least 10 leads successfully
- [ ] Logs show proper stats and timing
- [ ] No ERROR level logs for valid leads

## Render Deployment Steps

1. **Create Render account** and connect GitHub repo

2. **Add environment variables** in Render dashboard:
   - All values from `config.py`
   - Set as secret/encrypted

3. **Create cron jobs**:
   - Job 1: `zerobounce-validator` (every 30 min)
   - Job 2: `hubspot-duplicate-checker` (every 30 min, offset)

4. **Monitor first runs**:
   - Check logs in Render dashboard
   - Verify Supabase fields are updating
   - Check for errors

## Troubleshooting

### "No leads found to process"
- ✅ Normal if all leads are processed
- Check Supabase: count where `zerobounce_processed = FALSE`

### "Statement timeout" errors
- Scripts already handle this by fetching smaller batches
- If persistent, reduce `batch_size` to 50

### Rate limiting (429 errors)
- ZeroBounce: Has built-in delays
- HubSpot: 0.1s delay between requests
- Airtable: Warn-only, continues processing

### Duplicate rate very high (> 90%)
- ✅ This is actually GOOD - means data quality is high
- Most properties already in HubSpot
- Focus on the unique ones for Instantly

## Next Steps After Deployment

1. Monitor for 24 hours
2. Review processing stats
3. Implement Instantly integration (next phase)
4. Implement HubSpot deal creation (next phase)
