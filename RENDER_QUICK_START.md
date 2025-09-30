# 🚀 Render Quick Start - 5 Minutes Setup

## Step-by-Step Setup

### 1. Create Render Account
- Go to: https://dashboard.render.com
- Sign up with GitHub

### 2. Create Cron Job 1 - Email Validator
1. Click **"New +"** → **"Cron Job"**
2. Connect repository: `automationsAC/ProcessLeads`
3. Fill in:
   - **Name:** `zerobounce-validator`
   - **Runtime:** Python 3
   - **Build:** `pip install -r requirements.txt`
   - **Command:** `python3 zerobounce_validator.py`
   - **Schedule:** `*/30 * * * *`
4. Click **"Create Cron Job"**

### 3. Add Environment Variables (Job 1)
Click **"Environment"** tab, add each:
```
SUPABASE_URL
SUPABASE_ANON_KEY
ZEROBOUNCE_API_KEY
PRIORITY_API_KEY
PRIORITY_API_URL
```
*(Get values from your local config.py - mark as Secret 🔒)*

### 4. Create Cron Job 2 - HubSpot Checker
1. Click **"New +"** → **"Cron Job"**
2. Connect same repository
3. Fill in:
   - **Name:** `hubspot-duplicate-checker`
   - **Runtime:** Python 3
   - **Build:** `pip install -r requirements.txt`
   - **Command:** `python3 hubspot_duplicate_checker.py`
   - **Schedule:** `15,45 * * * *`
4. Click **"Create Cron Job"**

### 5. Add Environment Variables (Job 2)
Click **"Environment"** tab, add:
```
SUPABASE_URL
SUPABASE_ANON_KEY
HUBSPOT_TOKEN
AIRTABLE_TOKEN
AIRTABLE_BASE
```

### 6. Create Cron Job 3 - Scrap Parser
1. Click **"New +"** → **"Cron Job"**
2. Connect same repository
3. Fill in:
   - **Name:** `scrap-data-parser`
   - **Runtime:** Python 3
   - **Build:** `pip install -r requirements.txt`
   - **Command:** `python3 parse_scrap_data.py`
   - **Schedule:** `0 */6 * * *`
4. Click **"Create Cron Job"**

### 7. Add Environment Variables (Job 3)
Click **"Environment"** tab, add:
```
SUPABASE_URL
SUPABASE_ANON_KEY
```

### 8. Test First Run
- Click **"Manual Trigger"** on each job
- Check **"Logs"** tab for output
- Verify success messages

### 9. Verify in Supabase
Run this query:
```sql
SELECT 
  COUNT(*) FILTER (WHERE zerobounce_status IS NOT NULL) as zerobounce_done,
  COUNT(*) FILTER (WHERE hubspot_duplicate_check_2 IS NOT NULL) as hubspot_done,
  COUNT(*) FILTER (WHERE parsing_completed = TRUE) as parsing_done
FROM contacts_grid_view;
```

---

## ✅ Done!
Your cron jobs are now running automatically!

## 📊 Check Progress
Visit Render Dashboard → Cron Jobs → Logs

---

**Full Documentation:** See `RENDER_SETUP_GUIDE.md`
