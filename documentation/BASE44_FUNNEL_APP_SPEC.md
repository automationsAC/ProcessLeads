# 📊 Lead Funnel Tracking App - Base44 Specification

## Problem
Need to track lead processing funnel across hundreds of thousands of records without slow queries or timeouts.

## Solution Architecture

### **Approach: Pre-calculated Statistics Table**

Instead of counting records on-demand (slow), maintain a **statistics table** that updates incrementally.

---

## 🗄️ Database Schema

### **New Table: `lead_funnel_stats`**

```sql
CREATE TABLE IF NOT EXISTS public.lead_funnel_stats (
  id SERIAL PRIMARY KEY,
  snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
  snapshot_hour INTEGER NOT NULL DEFAULT EXTRACT(HOUR FROM NOW()),
  
  -- Overall counts
  total_leads INTEGER DEFAULT 0,
  total_with_email INTEGER DEFAULT 0,
  
  -- ZeroBounce pipeline
  zerobounce_pending INTEGER DEFAULT 0,
  zerobounce_valid INTEGER DEFAULT 0,
  zerobounce_invalid INTEGER DEFAULT 0,
  zerobounce_do_not_mail INTEGER DEFAULT 0,
  zerobounce_abuse INTEGER DEFAULT 0,
  zerobounce_unknown INTEGER DEFAULT 0,
  zerobounce_processed_true INTEGER DEFAULT 0,
  
  -- HubSpot pipeline
  hubspot_pending INTEGER DEFAULT 0,
  hubspot_completed INTEGER DEFAULT 0,
  hubspot_unique INTEGER DEFAULT 0,
  hubspot_duplicate INTEGER DEFAULT 0,
  hubspot_contact_duplicate INTEGER DEFAULT 0,
  hubspot_deal_exists INTEGER DEFAULT 0,
  hubspot_new_lead INTEGER DEFAULT 0,
  needs_hubspot_deal INTEGER DEFAULT 0,
  
  -- Parsing pipeline
  parsing_pending INTEGER DEFAULT 0,
  parsing_completed INTEGER DEFAULT 0,
  has_images INTEGER DEFAULT 0,
  has_location INTEGER DEFAULT 0,
  
  -- Breakdown by country (JSONB for flexibility)
  country_breakdown JSONB,
  
  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  UNIQUE(snapshot_date, snapshot_hour)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_funnel_stats_date 
ON public.lead_funnel_stats(snapshot_date DESC, snapshot_hour DESC);
```

---

## 🔄 Statistics Update Strategy

### **Option 1: Supabase Function (Recommended)**

Create a Supabase Edge Function that runs every hour:

```sql
CREATE OR REPLACE FUNCTION update_funnel_stats()
RETURNS void AS $$
BEGIN
  INSERT INTO lead_funnel_stats (
    snapshot_date,
    snapshot_hour,
    total_leads,
    total_with_email,
    zerobounce_pending,
    zerobounce_valid,
    zerobounce_invalid,
    zerobounce_processed_true,
    hubspot_pending,
    hubspot_completed,
    hubspot_unique,
    hubspot_duplicate,
    needs_hubspot_deal,
    parsing_pending,
    parsing_completed,
    has_images,
    has_location,
    country_breakdown
  )
  SELECT 
    CURRENT_DATE,
    EXTRACT(HOUR FROM NOW())::INTEGER,
    COUNT(*),
    COUNT(*) FILTER (WHERE email IS NOT NULL),
    
    -- ZeroBounce
    COUNT(*) FILTER (WHERE zerobounce_status IS NULL AND email IS NOT NULL),
    COUNT(*) FILTER (WHERE zerobounce_status = 'valid'),
    COUNT(*) FILTER (WHERE zerobounce_status = 'invalid'),
    COUNT(*) FILTER (WHERE zerobounce_processed = TRUE),
    
    -- HubSpot
    COUNT(*) FILTER (WHERE zerobounce_processed = TRUE AND (hubspot_check_2_completed IS NULL OR hubspot_check_2_completed = FALSE)),
    COUNT(*) FILTER (WHERE hubspot_check_2_completed = TRUE),
    COUNT(*) FILTER (WHERE hubspot_duplicate_check_2 = 'unique'),
    COUNT(*) FILTER (WHERE hubspot_duplicate_check_2 = 'duplicate'),
    COUNT(*) FILTER (WHERE needs_hubspot_deal = TRUE),
    
    -- Parsing
    COUNT(*) FILTER (WHERE parsing_completed = FALSE AND scrap_data IS NOT NULL),
    COUNT(*) FILTER (WHERE parsing_completed = TRUE),
    COUNT(*) FILTER (WHERE parsed_images IS NOT NULL),
    COUNT(*) FILTER (WHERE parsed_latitude IS NOT NULL),
    
    -- Country breakdown
    (
      SELECT jsonb_object_agg(country, stats)
      FROM (
        SELECT 
          country,
          jsonb_build_object(
            'total', COUNT(*),
            'zerobounce_pending', COUNT(*) FILTER (WHERE zerobounce_status IS NULL),
            'hubspot_unique', COUNT(*) FILTER (WHERE hubspot_duplicate_check_2 = 'unique')
          ) as stats
        FROM contacts_grid_view
        WHERE country IS NOT NULL
        GROUP BY country
      ) country_stats
    )
  FROM contacts_grid_view
  ON CONFLICT (snapshot_date, snapshot_hour) 
  DO UPDATE SET
    total_leads = EXCLUDED.total_leads,
    total_with_email = EXCLUDED.total_with_email,
    zerobounce_pending = EXCLUDED.zerobounce_pending,
    zerobounce_valid = EXCLUDED.zerobounce_valid,
    zerobounce_invalid = EXCLUDED.zerobounce_invalid,
    zerobounce_processed_true = EXCLUDED.zerobounce_processed_true,
    hubspot_pending = EXCLUDED.hubspot_pending,
    hubspot_completed = EXCLUDED.hubspot_completed,
    hubspot_unique = EXCLUDED.hubspot_unique,
    hubspot_duplicate = EXCLUDED.hubspot_duplicate,
    needs_hubspot_deal = EXCLUDED.needs_hubspot_deal,
    parsing_pending = EXCLUDED.parsing_pending,
    parsing_completed = EXCLUDED.parsing_completed,
    has_images = EXCLUDED.has_images,
    has_location = EXCLUDED.has_location,
    country_breakdown = EXCLUDED.country_breakdown,
    created_at = NOW();
END;
$$ LANGUAGE plpgsql;
```

### **Option 2: Python Cron Job (Alternative)**

Create a 4th Render cron job that runs hourly:

```python
# funnel_stats_updater.py
# Calculates stats once per hour and stores in lead_funnel_stats table
# Base44 app queries this table instead of contacts_grid_view
```

---

## 📱 Base44 App Design

### **App Structure:**

```
┌─────────────────────────────────────────────────────────────┐
│  LEAD PROCESSING FUNNEL DASHBOARD                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 Overview Stats (from lead_funnel_stats - latest row)    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Total Leads: 88,033                                 │   │
│  │  With Email: 79,923                                  │   │
│  │  Last Updated: 2025-09-30 17:00                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  🔄 Pipeline Progress (Visual Funnel)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ┌─────────────────────────────────────┐             │   │
│  │  │ Step 1: ZeroBounce Pending          │             │   │
│  │  │ 65,000 leads (74%)                  │             │   │
│  │  └─────────────────────────────────────┘             │   │
│  │            ↓                                          │   │
│  │  ┌────────────────────────┐                          │   │
│  │  │ Step 2: HubSpot Pending│                          │   │
│  │  │ 8,000 leads (9%)       │                          │   │
│  │  └────────────────────────┘                          │   │
│  │            ↓                                          │   │
│  │  ┌──────────────┐                                    │   │
│  │  │ Step 3: Unique│                                   │   │
│  │  │ 500 leads (1%)│                                   │   │
│  │  └──────────────┘                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  📈 Trend Chart (Last 24 Hours)                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  [Line chart showing processing rate over time]      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  🌍 Country Breakdown (from country_breakdown JSONB)        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Poland:  45,000 | Pending: 30,000 | Unique: 200     │   │
│  │  Germany: 25,000 | Pending: 18,000 | Unique: 150     │   │
│  │  Spain:   18,000 | Pending: 17,000 | Unique: 150     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ⚡ Real-time Processing Rate                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Last Hour: 4,800 leads processed                    │   │
│  │  Rate: 80 leads/minute                               │   │
│  │  ETA to complete: 18 days                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Base44 Implementation

### **Page 1: Funnel Overview**

**Data Source:** Single query to `lead_funnel_stats`
```sql
SELECT * FROM lead_funnel_stats 
ORDER BY snapshot_date DESC, snapshot_hour DESC 
LIMIT 1;
```

**Components:**
1. **KPI Cards** (4 cards)
   - Total Leads
   - ZeroBounce Pending
   - HubSpot Pending  
   - Ready for Instantly (unique)

2. **Funnel Chart** (Vertical funnel visualization)
   - Step 1: Waiting for ZeroBounce
   - Step 2: Waiting for HubSpot
   - Step 3: Ready for Instantly
   - Step 4: Needs HubSpot Deal

3. **Status Breakdown** (Pie charts)
   - ZeroBounce results (valid/invalid/abuse)
   - HubSpot results (unique/duplicate)
   - Deal reasons (new_lead/contact_duplicate/deal_exists)

---

### **Page 2: Historical Trends**

**Data Source:** Query last 24 hours from `lead_funnel_stats`
```sql
SELECT * FROM lead_funnel_stats 
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY snapshot_date DESC, snapshot_hour DESC;
```

**Components:**
1. **Line Chart** - Processing rate over time
2. **Stacked Bar Chart** - Daily breakdown by status
3. **Table** - Hourly stats

---

### **Page 3: Country Breakdown**

**Data Source:** Extract from `country_breakdown` JSONB
```sql
SELECT 
  snapshot_date,
  snapshot_hour,
  country_breakdown
FROM lead_funnel_stats 
ORDER BY snapshot_date DESC, snapshot_hour DESC 
LIMIT 1;
```

**Components:**
1. **Country Table** with columns:
   - Country
   - Total Leads
   - ZeroBounce Pending
   - HubSpot Unique
   - % Complete

2. **Progress Bars** per country

---

## ⚡ Performance Optimization

### **Why This Approach is Fast:**

1. **Pre-calculated Stats** 
   - Query runs once per hour (not on every page load)
   - Stores results in small table (~24 rows per day)
   - Base44 app queries tiny table, not 100k+ records

2. **Minimal Data Transfer**
   - Stats table: ~1 KB per row
   - Dashboard loads: <1 KB total
   - vs. counting 100k records: 10+ MB, 30+ seconds

3. **Scalability**
   - Works with 100k leads ✅
   - Works with 1M leads ✅
   - Works with 10M leads ✅
   - Performance stays constant

### **Trade-off:**
- Stats update every hour (not real-time)
- Acceptable for monitoring (don't need second-by-second updates)

---

## 🔧 Implementation Steps

### **Step 1: Create Stats Table in Supabase**

```sql
-- Run in Supabase SQL Editor
CREATE TABLE IF NOT EXISTS public.lead_funnel_stats (
  id SERIAL PRIMARY KEY,
  snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
  snapshot_hour INTEGER NOT NULL DEFAULT EXTRACT(HOUR FROM NOW()),
  
  total_leads INTEGER DEFAULT 0,
  total_with_email INTEGER DEFAULT 0,
  
  zerobounce_pending INTEGER DEFAULT 0,
  zerobounce_valid INTEGER DEFAULT 0,
  zerobounce_invalid INTEGER DEFAULT 0,
  zerobounce_processed_true INTEGER DEFAULT 0,
  
  hubspot_pending INTEGER DEFAULT 0,
  hubspot_completed INTEGER DEFAULT 0,
  hubspot_unique INTEGER DEFAULT 0,
  hubspot_duplicate INTEGER DEFAULT 0,
  needs_hubspot_deal INTEGER DEFAULT 0,
  
  parsing_pending INTEGER DEFAULT 0,
  parsing_completed INTEGER DEFAULT 0,
  has_images INTEGER DEFAULT 0,
  has_location INTEGER DEFAULT 0,
  
  country_breakdown JSONB,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  UNIQUE(snapshot_date, snapshot_hour)
);

CREATE INDEX idx_funnel_stats_date 
ON public.lead_funnel_stats(snapshot_date DESC, snapshot_hour DESC);
```

### **Step 2: Create Update Function**

Use the SQL function from above or create a Python script:

```python
# funnel_stats_updater.py
# Add as 4th Render cron job - runs hourly
```

### **Step 3: Create Base44 App**

**Data Connection:**
- Connect to Supabase
- Query: `lead_funnel_stats` table

**App Pages:**
1. Overview Dashboard
2. Historical Trends  
3. Country Breakdown

---

## 📊 Base44 App Components

### **Component 1: Funnel Chart**

```javascript
// Data from latest lead_funnel_stats row
const funnelData = [
  {
    stage: 'Step 1: ZeroBounce Pending',
    count: stats.zerobounce_pending,
    percentage: (stats.zerobounce_pending / stats.total_leads * 100).toFixed(1)
  },
  {
    stage: 'Step 2: HubSpot Pending',
    count: stats.hubspot_pending,
    percentage: (stats.hubspot_pending / stats.total_leads * 100).toFixed(1)
  },
  {
    stage: 'Step 3: Unique (Ready)',
    count: stats.hubspot_unique,
    percentage: (stats.hubspot_unique / stats.total_leads * 100).toFixed(1)
  },
  {
    stage: 'Step 4: Need Deal',
    count: stats.needs_hubspot_deal,
    percentage: (stats.needs_hubspot_deal / stats.total_leads * 100).toFixed(1)
  }
];
```

### **Component 2: KPI Cards**

```javascript
// Top KPI cards
const kpis = {
  totalLeads: stats.total_leads,
  readyForInstantly: stats.hubspot_unique,
  needsDeals: stats.needs_hubspot_deal,
  parsingComplete: stats.parsing_completed
};
```

### **Component 3: Country Breakdown Table**

```javascript
// Extract from country_breakdown JSONB
const countryData = Object.entries(stats.country_breakdown).map(([country, data]) => ({
  country: country.toUpperCase(),
  total: data.total,
  pending: data.zerobounce_pending,
  unique: data.hubspot_unique,
  percentComplete: ((data.total - data.zerobounce_pending) / data.total * 100).toFixed(1)
}));
```

### **Component 4: Hourly Trend Chart**

```sql
-- Query last 24 hours
SELECT 
  snapshot_date,
  snapshot_hour,
  zerobounce_processed_true,
  hubspot_completed,
  parsing_completed
FROM lead_funnel_stats
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY snapshot_date, snapshot_hour;
```

---

## 🔄 Update Cron Job

### **Option A: Supabase Scheduled Query**

Set up in Supabase:
```
Name: Update Funnel Stats
Schedule: 0 * * * * (every hour)
Query: SELECT update_funnel_stats();
```

### **Option B: Render Cron Job**

Create 4th cron job:
```yaml
name: funnel-stats-updater
command: python3 funnel_stats_updater.py
schedule: "0 * * * *"  # Every hour at :00
```

---

## 📈 Benefits of This Approach

### **Performance:**
- ✅ Dashboard loads in <1 second (even with 1M records)
- ✅ No timeouts (queries tiny stats table)
- ✅ Minimal database load

### **Scalability:**
- ✅ Works with any database size
- ✅ Stats table stays small (~720 rows per month)
- ✅ Can add more metrics easily

### **User Experience:**
- ✅ Instant page loads
- ✅ Historical trends
- ✅ Real-time enough (hourly updates)

### **Maintenance:**
- ✅ Self-cleaning (auto-delete old stats)
- ✅ Low storage (<1 MB per year)
- ✅ Easy to extend

---

## 🎨 Base44 App Wireframe

```
┌────────────────────────────────────────────────────────────────┐
│  🎯 Lead Processing Funnel                   Last: 17:00      │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ 88,033   │  │  3,456   │  │  1,234   │  │  87,232  │     │
│  │ Total    │  │  Unique  │  │  Deals   │  │  Parsing │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                                │
│  📊 Processing Funnel                                         │
│  ┌──────────────────────────────────────────────┐            │
│  │                                               │            │
│  │  ████████████████████ 65,000 ZB Pending      │            │
│  │  ████████ 8,000 HubSpot Pending              │            │
│  │  ██ 3,456 Unique (Ready)                     │            │
│  │  ███ 1,234 Need Deal                         │            │
│  │                                               │            │
│  └──────────────────────────────────────────────┘            │
│                                                                │
│  📈 Last 24 Hours                                             │
│  ┌──────────────────────────────────────────────┐            │
│  │   [Line chart: Processing rate over time]    │            │
│  └──────────────────────────────────────────────┘            │
│                                                                │
│  🌍 Country Breakdown                                         │
│  ┌──────────────────────────────────────────────┐            │
│  │  PL  ████████ 30,000 pending (60%)           │            │
│  │  DE  ███████ 18,000 pending (70%)            │            │
│  │  ES  ████ 17,000 pending (95%)               │            │
│  └──────────────────────────────────────────────┘            │
│                                                                │
│  [Refresh] [Export CSV] [View Details]                       │
└────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Base44 API Endpoints

### **Endpoint 1: Get Current Stats**
```
GET /api/funnel/current
Response: Single row from lead_funnel_stats (latest)
```

### **Endpoint 2: Get Historical Stats**
```
GET /api/funnel/history?days=7
Response: Array of stats for last N days
```

### **Endpoint 3: Get Country Details**
```
GET /api/funnel/countries
Response: Extracted country_breakdown from latest stats
```

### **Endpoint 4: Get Processing Rate**
```
GET /api/funnel/rate
Response: Calculated rate (leads per hour) from last 24h
```

---

## 📝 Sample Queries for Base44

### **Main Dashboard Query:**
```sql
SELECT * FROM lead_funnel_stats 
ORDER BY snapshot_date DESC, snapshot_hour DESC 
LIMIT 1;
```

### **Trend Data (Last 24 Hours):**
```sql
SELECT 
  snapshot_date,
  snapshot_hour,
  zerobounce_pending,
  hubspot_pending,
  hubspot_unique
FROM lead_funnel_stats 
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY snapshot_date, snapshot_hour;
```

### **Country Stats:**
```sql
SELECT country_breakdown 
FROM lead_funnel_stats 
ORDER BY snapshot_date DESC, snapshot_hour DESC 
LIMIT 1;
```

---

## 🎯 Summary

### **Architecture:**
- ✅ Pre-calculated stats table (updated hourly)
- ✅ Base44 queries tiny stats table (fast!)
- ✅ No complex aggregations on large table

### **Performance:**
- ✅ Sub-second dashboard loads
- ✅ Works with millions of records
- ✅ Minimal database load

### **Maintenance:**
- ✅ Automatic updates (Supabase function or cron)
- ✅ Self-cleaning (can auto-delete old data)
- ✅ Easy to extend with new metrics

---

## 📦 Deliverables

**SQL Scripts:**
1. `create_funnel_stats_table.sql` - Create stats table
2. `create_update_function.sql` - Create update function
3. `schedule_stats_update.sql` - Schedule hourly updates

**Python Script (Optional):**
- `funnel_stats_updater.py` - Python-based updater

**Base44 App:**
- Dashboard with funnel, trends, and country breakdown
- Queries only the stats table (fast)
- Auto-refreshes every hour

---

**Want me to create the SQL scripts and Python updater?**
