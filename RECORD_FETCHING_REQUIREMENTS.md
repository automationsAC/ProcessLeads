# 📋 Record Fetching Requirements - All Scripts

## Overview
Each script in the pipeline has specific requirements for which leads it processes.

---

## 1️⃣  ZeroBounce Validator (`zerobounce_validator.py`)

### **Fetches Leads WHERE:**
```sql
zerobounce_status IS NULL
AND email IS NOT NULL 
AND email != ''
AND country IN (priority_countries) OR country IS NULL
ORDER BY created_at ASC
LIMIT 100
```

### **Requirements:**
- ✅ Must have `email` field (not null, not empty)
- ✅ Must NOT have been validated yet (`zerobounce_status` is null)
- ✅ Prioritizes by country (from priority API)

### **After Processing, Sets:**
- `zerobounce_status` = 'valid' / 'invalid' / 'abuse' / etc.
- `zerobounce_sub_status` = error details (if any)
- `zerobounce_validated_at` = timestamp
- `zerobounce_processed` = **TRUE** ✅

### **Will NOT Fetch:**
- ❌ Leads already validated (zerobounce_status is not null)
- ❌ Leads without email
- ❌ Countries not in priority list (unless null)

---

## 2️⃣  HubSpot Duplicate Checker (`hubspot_duplicate_checker.py`)

### **Fetches Leads WHERE:**
```sql
zerobounce_status = 'valid'
AND zerobounce_processed = TRUE
AND hubspot_check_2_completed IS NULL OR hubspot_check_2_completed = FALSE
AND email IS NOT NULL
ORDER BY id ASC
LIMIT 1000 (then filters client-side to 100)
```

### **Requirements:**
- ✅ Must have VALID email (`zerobounce_status = 'valid'`)
- ✅ Must have completed ZeroBounce processing (`zerobounce_processed = TRUE`)
- ✅ Must NOT have been checked by HubSpot yet (`hubspot_check_2_completed` is null/false)
- ✅ Must have email field

### **After Processing, Sets:**
- `hubspot_duplicate_check_2` = 'unique' / 'duplicate'
- `hubspot_checked_at_2` = timestamp
- `needs_hubspot_deal` = true/false
- `deal_creation_reason` = 'new_lead' / 'contact_duplicate' / 'deal_exists' / 'alohacamp_exists'
- `hubspot_check_2_completed` = **TRUE** ✅
- Plus all match details (contact IDs, deal IDs, etc.)

### **Will NOT Fetch:**
- ❌ Invalid emails (zerobounce_status != 'valid')
- ❌ Not yet validated by ZeroBounce (zerobounce_processed = FALSE)
- ❌ Already checked by HubSpot (hubspot_check_2_completed = TRUE)

---

## 3️⃣  Scrap Data Parser (`parse_scrap_data.py`)

### **Fetches Leads WHERE:**
```sql
parsing_completed = FALSE
AND scrap_data IS NOT NULL
ORDER BY id ASC
LIMIT 100
```

### **Requirements:**
- ✅ Must have `scrap_data` field (not null)
- ✅ Must NOT have been parsed yet (`parsing_completed = FALSE`)

### **After Processing, Sets:**
- `parsed_images` = JSONB array of image URLs
- `parsed_description` = TEXT description
- `parsed_latitude` = FLOAT latitude
- `parsed_longitude` = FLOAT longitude
- `parsing_completed` = **TRUE** ✅
- `parsing_processed_at` = timestamp

### **Will NOT Fetch:**
- ❌ Already parsed (parsing_completed = TRUE)
- ❌ No scrap_data (scrap_data is null)

### **Note:**
- This runs INDEPENDENTLY of email validation and HubSpot checking
- Can process leads in parallel with the other pipelines
- Does NOT require email validation or HubSpot check to be complete

---

## 📊 Pipeline Dependencies

```
┌─────────────────────────────────┐
│  INDEPENDENT PIPELINES:         │
├─────────────────────────────────┤
│                                 │
│  Pipeline A (Sequential):       │
│  ┌──────────────────────┐       │
│  │ 1. ZeroBounce        │       │
│  │    ↓                 │       │
│  │ 2. HubSpot Check     │       │
│  └──────────────────────┘       │
│                                 │
│  Pipeline B (Independent):      │
│  ┌──────────────────────┐       │
│  │ 3. Scrap Data Parser │       │
│  └──────────────────────┘       │
│                                 │
└─────────────────────────────────┘
```

**Pipeline A:** ZeroBounce → HubSpot (sequential, dependent)  
**Pipeline B:** Parser (independent, can run anytime)

---

## 🔍 Query Performance Notes

### **Why Some Queries Are Fast:**
- ✅ Index on `parsing_completed = FALSE` 
- ✅ Simple equality checks
- ✅ Small batch sizes (100)

### **Why Some Might Timeout:**
- ⚠️  Large tables (88k+ rows)
- ⚠️  Complex WHERE clauses with multiple conditions
- ⚠️  Render has stricter timeout limits than local

### **Our Solutions:**
- ✅ Client-side filtering (fetch more, filter in Python)
- ✅ Batch size limits (100-1000)
- ✅ ID-based ordering (predictable)
- ✅ Partial indexes (only index what we need)

---

## ✅ Final Verification

### **Check What Each Script Will Process:**

**ZeroBounce:**
```sql
SELECT COUNT(*) as ready_for_zerobounce
FROM contacts_grid_view
WHERE zerobounce_status IS NULL
  AND email IS NOT NULL 
  AND email != '';
```

**HubSpot:**
```sql
SELECT COUNT(*) as ready_for_hubspot
FROM contacts_grid_view
WHERE zerobounce_status = 'valid'
  AND zerobounce_processed = TRUE
  AND (hubspot_check_2_completed IS NULL OR hubspot_check_2_completed = FALSE);
```

**Parser:**
```sql
SELECT COUNT(*) as ready_for_parsing
FROM contacts_grid_view
WHERE parsing_completed = FALSE
  AND scrap_data IS NOT NULL;
```

---

## 🎯 Summary

| Script | Requirement | Marks Complete With | Batch Size |
|--------|-------------|---------------------|------------|
| ZeroBounce | `zerobounce_status IS NULL` + has email | `zerobounce_processed = TRUE` | 100 |
| HubSpot | `zerobounce_processed = TRUE` + valid | `hubspot_check_2_completed = TRUE` | 100 |
| Parser | `parsing_completed = FALSE` + has scrap_data | `parsing_completed = TRUE` | 100 |

**All use boolean flags for tracking - simple and reliable!**
