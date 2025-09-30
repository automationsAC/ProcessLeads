# 🚀 Render Cron Jobs Setup Guide

## Overview
This guide walks you through setting up automated cron jobs on Render for the lead processing pipeline.

---

## 📋 Prerequisites

1. ✅ GitHub repository: `git@github.com:automationsAC/ProcessLeads.git`
2. ✅ Render account (sign up at https://render.com)
3. ✅ All credentials ready from `config.py`

---

## 🔧 Step 1: Connect GitHub Repository to Render

1. **Log in to Render:** https://dashboard.render.com
2. **Click "New +"** in top right
3. **Select "Cron Job"**
4. **Connect GitHub:**
   - Click "Connect account" (if first time)
   - Authorize Render to access your GitHub
   - Select repository: `automationsAC/ProcessLeads`

---

## ⚙️ Step 2: Create Cron Jobs

You'll create **3 separate cron jobs**:

### **Cron Job 1: ZeroBounce Email Validator**

**Settings:**
- **Name:** `zerobounce-validator`
- **Region:** Choose closest to your Supabase (e.g., Frankfurt for EU)
- **Branch:** `main`
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python3 zerobounce_validator.py`
- **Schedule:** `*/30 * * * *` (Every 30 minutes)

Click **"Create Cron Job"**

---

### **Cron Job 2: HubSpot Duplicate Checker**

**Settings:**
- **Name:** `hubspot-duplicate-checker`
- **Region:** Same as Job 1
- **Branch:** `main`
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python3 hubspot_duplicate_checker.py`
- **Schedule:** `15,45 * * * *` (At :15 and :45 past each hour - offset from ZB)

Click **"Create Cron Job"**

---

### **Cron Job 3: Scrap Data Parser**

**Settings:**
- **Name:** `scrap-data-parser`
- **Region:** Same as Job 1
- **Branch:** `main`
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python3 parse_scrap_data.py`
- **Schedule:** `0 */6 * * *` (Every 6 hours)

Click **"Create Cron Job"**

---

## 🔐 Step 3: Add Environment Variables

For **EACH cron job**, add these environment variables:

1. Click on the cron job name
2. Go to **"Environment"** tab
3. Click **"Add Environment Variable"**
4. Add each variable:

```
SUPABASE_URL = your_supabase_url
SUPABASE_ANON_KEY = your_supabase_anon_key

ZEROBOUNCE_API_KEY = your_zerobounce_api_key

PRIORITY_API_KEY = your_priority_api_key
PRIORITY_API_URL = your_priority_api_url

HUBSPOT_TOKEN = your_hubspot_token

AIRTABLE_TOKEN = your_airtable_token
AIRTABLE_BASE = your_airtable_base_id
```

**💡 Get your actual values from your local `config.py` file**

**Important:** 
- Click the 🔒 lock icon to make sensitive values (API keys, tokens) **Secret**
- Variables marked as secret won't be visible in logs

---

## 📝 Step 4: Update config.py to Use Environment Variables

Render needs to read from environment variables, not a local `config.py` file.

Update your `config.py`:

```python
import os

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

# ZeroBounce Configuration
ZEROBOUNCE_API_KEY = os.environ.get('ZEROBOUNCE_API_KEY')

# Priority API Configuration
PRIORITY_API_KEY = os.environ.get('PRIORITY_API_KEY')
PRIORITY_API_URL = os.environ.get('PRIORITY_API_URL')

# HubSpot Configuration
HUBSPOT_TOKEN = os.environ.get('HUBSPOT_TOKEN')

# Airtable Configuration
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE = os.environ.get('AIRTABLE_BASE')
```

Commit and push this change!

---

## ⏰ Cron Schedule Explained

### Schedule Format: `minute hour day month weekday`

**Examples:**
- `*/30 * * * *` - Every 30 minutes
- `15,45 * * * *` - At :15 and :45 past every hour
- `0 */6 * * *` - Every 6 hours (at :00)
- `0 9 * * *` - Daily at 9:00 AM
- `0 9 * * 1` - Weekly on Monday at 9:00 AM

**Our Schedule:**
```
zerobounce-validator:      */30 * * * *     (Every 30 min)
hubspot-duplicate-checker: 15,45 * * * *    (Offset by 15 min)
scrap-data-parser:         0 */6 * * *      (Every 6 hours)
```

**Why offset?** Ensures ZeroBounce finishes before HubSpot checker runs.

---

## 📊 Step 5: Monitor First Runs

### View Logs:

1. Go to Render Dashboard
2. Click on a cron job
3. Click **"Logs"** tab
4. Watch real-time output

### What to Look For:

✅ **Success indicators:**
```
Starting batch...
Fetched 100 leads
Successfully updated: 100
Duration: 35.2 seconds
```

⚠️ **Warning (OK):**
```
No leads found to process - all leads may already be checked
```

❌ **Errors to investigate:**
```
ERROR - Failed to fetch leads
ERROR - API authentication failed
ERROR - Database connection failed
```

---

## 🔍 Step 6: Verify Data in Supabase

After 1-2 hours, check Supabase:

```sql
-- Check ZeroBounce progress
SELECT 
  zerobounce_status,
  COUNT(*) as count
FROM contacts_grid_view
WHERE zerobounce_status IS NOT NULL
GROUP BY zerobounce_status
ORDER BY count DESC;

-- Check HubSpot progress
SELECT 
  hubspot_duplicate_check_2,
  COUNT(*) as count
FROM contacts_grid_view
WHERE hubspot_duplicate_check_2 IS NOT NULL
GROUP BY hubspot_duplicate_check_2;

-- Check parsing progress
SELECT 
  COUNT(*) as total_parsed,
  SUM(CASE WHEN parsed_images IS NOT NULL THEN 1 ELSE 0 END) as with_images,
  SUM(CASE WHEN parsed_latitude IS NOT NULL THEN 1 ELSE 0 END) as with_location
FROM contacts_grid_view
WHERE parsing_completed = TRUE;

-- Leads ready for Instantly
SELECT COUNT(*) as ready_for_instantly
FROM contacts_grid_view
WHERE hubspot_duplicate_check_2 = 'unique'
  AND zerobounce_status = 'valid';
```

---

## 🛠️ Troubleshooting

### Cron Job Not Running

**Check:**
1. Job is not paused (toggle in Render)
2. Schedule is correct (use crontab.guru to verify)
3. Build command succeeded (check Build logs)

### "Module not found" Errors

**Fix:**
- Ensure `requirements.txt` is in repo root
- Build command is: `pip install -r requirements.txt`
- Check Build logs for pip errors

### "Config not found" Errors

**Fix:**
- Ensure all environment variables are added
- Click 🔒 to make them secret
- Redeploy the cron job

### Rate Limiting

**Symptoms:**
- 429 errors in logs
- ZeroBounce credits depleting fast

**Fix:**
- Reduce schedule frequency
- Change to `0 */2 * * *` (every 2 hours)

### Timeout Errors

**Symptoms:**
- "Statement timeout" in logs
- Jobs taking > 5 minutes

**Fix:**
- Already handled in code with batch processing
- If persistent, reduce batch_size to 50 in script

---

## 📈 Expected Processing Rate

### Per Run:
- **ZeroBounce:** 100 leads (~30 seconds)
- **HubSpot:** 100 leads (~60 seconds)
- **Parser:** 100 leads (~30 seconds)

### Daily (with suggested schedule):
- **ZeroBounce:** ~4,800 leads/day (48 runs × 100)
- **HubSpot:** ~4,800 leads/day
- **Parser:** ~400 leads/day (4 runs × 100)

### To Process Entire Database (88,000 leads):
- **Email validation:** ~18 days at current rate
- **HubSpot checking:** ~18 days (runs after validation)
- **Parsing:** Can run in parallel, ~220 days (but optional)

**To speed up:** Increase schedule frequency or run manual batches.

---

## 🎯 Manual Batch Processing (Optional)

If you want to process faster initially:

```bash
# SSH into Render or run locally
for i in {1..100}; do
  echo "Batch $i/100"
  python3 zerobounce_validator.py
  sleep 10
  python3 hubspot_duplicate_checker.py
  sleep 10
done
```

---

## 📊 Monitoring Dashboard

### Create a Supabase Query for Monitoring:

```sql
CREATE OR REPLACE VIEW processing_stats AS
SELECT 
  COUNT(*) as total_leads,
  COUNT(CASE WHEN zerobounce_status IS NOT NULL THEN 1 END) as zerobounce_completed,
  COUNT(CASE WHEN zerobounce_status = 'valid' THEN 1 END) as valid_emails,
  COUNT(CASE WHEN hubspot_duplicate_check_2 IS NOT NULL THEN 1 END) as hubspot_completed,
  COUNT(CASE WHEN hubspot_duplicate_check_2 = 'unique' THEN 1 END) as unique_leads,
  COUNT(CASE WHEN needs_hubspot_deal = TRUE THEN 1 END) as needs_deals,
  COUNT(CASE WHEN parsing_completed = TRUE THEN 1 END) as parsing_completed
FROM contacts_grid_view;
```

Then query: `SELECT * FROM processing_stats;`

---

## 🎛️ Render Dashboard Tips

### Useful Features:

1. **Manual Trigger:** Run cron job immediately (don't wait for schedule)
2. **Pause/Resume:** Temporarily stop a job
3. **Logs:** View last 1000 lines of output
4. **Metrics:** See run history and success/failure
5. **Notifications:** Set up alerts for failures

### Best Practices:

- ✅ Enable email notifications for failures
- ✅ Check logs daily for first week
- ✅ Monitor API credit usage (ZeroBounce)
- ✅ Review stats weekly in Supabase

---

## 📞 Support & Resources

- **Render Docs:** https://render.com/docs/cronjobs
- **Cron Schedule Tester:** https://crontab.guru
- **Repository:** https://github.com/automationsAC/ProcessLeads

---

## ✅ Deployment Checklist

**Before First Run:**
- [ ] All 3 cron jobs created in Render
- [ ] All environment variables added to each job
- [ ] Sensitive values marked as Secret (🔒)
- [ ] `config.py` updated to use `os.environ.get()`
- [ ] Changes committed and pushed to GitHub

**After First Run:**
- [ ] Check logs for errors
- [ ] Verify Supabase fields updating
- [ ] Check API credits (ZeroBounce, HubSpot)
- [ ] Monitor for 24 hours

**Weekly Monitoring:**
- [ ] Review processing stats
- [ ] Check error rates
- [ ] Verify unique lead count growing
- [ ] Plan next phase (Instantly integration)

---

## 🎯 Next Phase (After Deployment Stable)

1. **Instantly Integration** - Add unique leads to campaigns
2. **HubSpot Deal Creation** - Create deals for contact duplicates
3. **Reporting Dashboard** - Track metrics over time

---

**Repository:** https://github.com/automationsAC/ProcessLeads
**Status:** ✅ READY FOR RENDER DEPLOYMENT
