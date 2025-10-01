# Scrap Data Parsing Guide

## Overview
This script parses the `scrap_data` JSON field into structured columns for easier querying and use in applications like Retool.

## What It Does

Extracts from `scrap_data`:
- **Images** → `parsed_images` (JSONB array)
- **Description** → `parsed_description` (TEXT)
- **Latitude** → `parsed_latitude` (FLOAT)
- **Longitude** → `parsed_longitude` (FLOAT)

Tracks progress with:
- `parsing_completed` (BOOLEAN) - TRUE when parsed
- `parsing_processed_at` (TIMESTAMP) - When it was parsed

## Setup

### 1. Add Fields to Supabase
Run the SQL script:
```bash
# Run add_parsing_fields.sql in Supabase SQL Editor
```

This adds:
- 4 parsed data columns
- 2 tracking columns
- 2 indexes for performance

### 2. Run the Parser

**Parse 100 leads (all countries):**
```bash
python3 parse_scrap_data.py
```

**Parse specific country (e.g., Spain):**
```python
# Edit parse_scrap_data.py main() function:
result = parser.process_batch(batch_size=100, country='es')
```

## Batch Processing Strategy

### Why Batches?
- Avoids Supabase rate limits
- Allows progress tracking
- Can resume if interrupted
- Processes only unparsed records

### Query Logic
Fetches leads WHERE:
```sql
parsing_completed IS NULL OR parsing_completed = FALSE
AND scrap_data IS NOT NULL
```

Only processes **once per lead** - won't reprocess.

### Rate Limiting
- 0.05 second delay between records
- 100 leads per batch = ~5-10 seconds
- Safe for Supabase free tier

## Running in Production

### Option 1: One-time Bulk Processing
```bash
# Process all leads in batches
for i in {1..100}; do
  python3 parse_scrap_data.py
  sleep 10  # 10 second pause between batches
done
```

### Option 2: Render Cron Job
```yaml
name: scrap-data-parser
command: python3 parse_scrap_data.py
schedule: "0 */6 * * *"  # Every 6 hours
```

### Option 3: Manual by Country
```python
# Priority: Spain first (smallest dataset)
result = parser.process_batch(batch_size=100, country='es')

# Then Germany
result = parser.process_batch(batch_size=100, country='de')

# Then Poland
result = parser.process_batch(batch_size=100, country='pl')

# Then all others
result = parser.process_batch(batch_size=100)
```

## Monitoring

### Logs
- **File**: `scrap_data_parsing.log`
- **Console**: Real-time output

### Log Output
```
2025-09-30 12:00:00 - INFO - Starting scrap_data parsing batch (size: 100, country: es)
2025-09-30 12:00:05 - INFO - Fetched 100 unparsed leads
2025-09-30 12:00:10 - INFO - Lead 12345: Successfully parsed scrap_data
2025-09-30 12:00:15 - INFO - Batch processing completed
2025-09-30 12:00:15 - INFO - Duration: 5.2 seconds
2025-09-30 12:00:15 - INFO - Stats: {'with_images': 85, 'with_description': 92, 'with_location': 78}
```

### Check Progress
```sql
-- Total unparsed
SELECT COUNT(*) 
FROM contacts_grid_view 
WHERE (parsing_completed IS NULL OR parsing_completed = FALSE)
  AND scrap_data IS NOT NULL;

-- Total parsed
SELECT COUNT(*) 
FROM contacts_grid_view 
WHERE parsing_completed = TRUE;

-- Breakdown by country
SELECT country, 
       COUNT(*) as total,
       SUM(CASE WHEN parsing_completed THEN 1 ELSE 0 END) as parsed,
       SUM(CASE WHEN parsed_images IS NOT NULL THEN 1 ELSE 0 END) as with_images,
       SUM(CASE WHEN parsed_latitude IS NOT NULL THEN 1 ELSE 0 END) as with_location
FROM contacts_grid_view
WHERE scrap_data IS NOT NULL
GROUP BY country
ORDER BY total DESC;
```

## Error Handling

### Handles:
- ✅ NULL scrap_data
- ✅ Empty scrap_data
- ✅ Invalid JSON
- ✅ Missing fields
- ✅ Different JSON structures
- ✅ Invalid coordinate values

### What Happens on Error:
- Lead is still marked as `parsing_completed = TRUE`
- Error logged to file
- Batch continues processing
- Won't retry same lead (prevents infinite loops)

## Data Validation

### Images
- Expects JSON array: `["url1.jpg", "url2.jpg"]`
- Stored as JSONB for querying
- Can be NULL if no images

### Description
- Stored as TEXT
- Can be NULL if no description

### Coordinates
- Must be valid floats
- Invalid values → NULL
- Both lat and lng independent

## Use Cases

### In Retool:
```javascript
// Access parsed images
{{ leftTable.selectedRow?.parsed_images?.[0] }}

// Show description
{{ leftTable.selectedRow?.parsed_description }}

// Map location
latitude: {{ leftTable.selectedRow?.parsed_latitude }}
longitude: {{ leftTable.selectedRow?.parsed_longitude }}
```

### In SQL:
```sql
-- Find leads with images
SELECT * FROM contacts_grid_view 
WHERE parsed_images IS NOT NULL 
AND jsonb_array_length(parsed_images) > 0;

-- Find leads near a location (within ~10km)
SELECT * FROM contacts_grid_view
WHERE parsed_latitude BETWEEN 50.0 AND 50.2
  AND parsed_longitude BETWEEN 14.0 AND 14.2;

-- Search descriptions
SELECT * FROM contacts_grid_view
WHERE parsed_description ILIKE '%mountain%';
```

## Performance

### Batch Size Recommendations:
- **Free tier**: 100 leads (safe)
- **Pro tier**: 500 leads
- **Enterprise**: 1000 leads

### Processing Time:
- 100 leads ≈ 5-10 seconds
- 1,000 leads ≈ 1-2 minutes
- 10,000 leads ≈ 10-20 minutes

### Database Impact:
- Minimal - only updates, no complex queries
- Indexes prevent slow queries later
- No joins or aggregations during parsing

## Troubleshooting

### "No unparsed leads found"
- ✅ All leads already parsed!
- Check: `SELECT COUNT(*) FROM contacts_grid_view WHERE parsing_completed = TRUE;`

### Slow processing
- Reduce batch_size to 50
- Increase sleep time between records
- Check Supabase connection

### JSON parsing errors
- Check scrap_data format in Supabase
- Some records may have malformed JSON
- Script will skip and continue

## Next Steps

1. Run `add_parsing_fields.sql` in Supabase
2. Test with small batch: `python3 parse_scrap_data.py`
3. Monitor logs and check Supabase
4. Scale up or add to Render cron

---

**Note:** This is independent of the email validation pipeline. Can run in parallel!
