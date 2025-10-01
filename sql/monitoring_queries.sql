-- ==================================================================================
-- MONITORING QUERIES - Check Progress of All Pipelines
-- ==================================================================================

-- ==================================================================================
-- 1. OVERALL PIPELINE STATUS
-- ==================================================================================
SELECT 
  COUNT(*) as total_leads,
  
  -- ZeroBounce Status
  COUNT(*) FILTER (WHERE zerobounce_status IS NULL) as zerobounce_pending,
  COUNT(*) FILTER (WHERE zerobounce_status IS NOT NULL) as zerobounce_completed,
  COUNT(*) FILTER (WHERE zerobounce_status = 'valid') as zerobounce_valid,
  COUNT(*) FILTER (WHERE zerobounce_status = 'invalid') as zerobounce_invalid,
  COUNT(*) FILTER (WHERE zerobounce_processed = TRUE) as zerobounce_processed_true,
  
  -- HubSpot Status
  COUNT(*) FILTER (WHERE zerobounce_processed = TRUE AND hubspot_check_2_completed IS NOT TRUE) as hubspot_pending,
  COUNT(*) FILTER (WHERE hubspot_check_2_completed = TRUE) as hubspot_completed,
  COUNT(*) FILTER (WHERE hubspot_duplicate_check_2 = 'unique') as hubspot_unique,
  COUNT(*) FILTER (WHERE hubspot_duplicate_check_2 = 'duplicate') as hubspot_duplicate,
  COUNT(*) FILTER (WHERE needs_hubspot_deal = TRUE) as needs_hubspot_deal,
  
  -- Parsing Status
  COUNT(*) FILTER (WHERE parsing_completed = FALSE AND scrap_data IS NOT NULL) as parsing_pending,
  COUNT(*) FILTER (WHERE parsing_completed = TRUE) as parsing_completed,
  COUNT(*) FILTER (WHERE parsed_images IS NOT NULL) as has_images,
  COUNT(*) FILTER (WHERE parsed_latitude IS NOT NULL) as has_location
  
FROM contacts_grid_view;


-- ==================================================================================
-- 2. PIPELINE FUNNEL - See Where Leads Are Stuck
-- ==================================================================================
SELECT 
  'Step 1: Waiting for ZeroBounce' as stage,
  COUNT(*) as lead_count
FROM contacts_grid_view
WHERE zerobounce_status IS NULL 
  AND email IS NOT NULL

UNION ALL

SELECT 
  'Step 2: Waiting for HubSpot Check' as stage,
  COUNT(*) as lead_count
FROM contacts_grid_view
WHERE zerobounce_status = 'valid'
  AND zerobounce_processed = TRUE
  AND (hubspot_check_2_completed IS NULL OR hubspot_check_2_completed = FALSE)

UNION ALL

SELECT 
  'Step 3: Ready for Instantly (Unique)' as stage,
  COUNT(*) as lead_count
FROM contacts_grid_view
WHERE hubspot_duplicate_check_2 = 'unique'
  AND zerobounce_status = 'valid'

UNION ALL

SELECT 
  'Step 4: Need HubSpot Deal' as stage,
  COUNT(*) as lead_count
FROM contacts_grid_view
WHERE needs_hubspot_deal = TRUE

UNION ALL

SELECT 
  'Parallel: Waiting for Parsing' as stage,
  COUNT(*) as lead_count
FROM contacts_grid_view
WHERE parsing_completed = FALSE
  AND scrap_data IS NOT NULL

ORDER BY stage;


-- ==================================================================================
-- 3. BREAKDOWN BY COUNTRY
-- ==================================================================================
SELECT 
  country,
  COUNT(*) as total,
  
  -- ZeroBounce
  COUNT(*) FILTER (WHERE zerobounce_status IS NULL) as zb_pending,
  COUNT(*) FILTER (WHERE zerobounce_status = 'valid') as zb_valid,
  
  -- HubSpot
  COUNT(*) FILTER (WHERE hubspot_check_2_completed = TRUE) as hs_completed,
  COUNT(*) FILTER (WHERE hubspot_duplicate_check_2 = 'unique') as hs_unique,
  
  -- Parsing
  COUNT(*) FILTER (WHERE parsing_completed = TRUE) as parsed
  
FROM contacts_grid_view
GROUP BY country
ORDER BY total DESC
LIMIT 10;


-- ==================================================================================
-- 4. RECENT ACTIVITY - Last 24 Hours
-- ==================================================================================
SELECT 
  'ZeroBounce (last 24h)' as activity,
  COUNT(*) as count
FROM contacts_grid_view
WHERE zerobounce_validated_at >= NOW() - INTERVAL '24 hours'

UNION ALL

SELECT 
  'HubSpot Check (last 24h)' as activity,
  COUNT(*) as count
FROM contacts_grid_view
WHERE hubspot_checked_at_2 >= NOW() - INTERVAL '24 hours'

UNION ALL

SELECT 
  'Parsing (last 24h)' as activity,
  COUNT(*) as count
FROM contacts_grid_view
WHERE parsing_processed_at >= NOW() - INTERVAL '24 hours';


-- ==================================================================================
-- 5. DEAL CREATION REASONS BREAKDOWN
-- ==================================================================================
SELECT 
  deal_creation_reason,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
FROM contacts_grid_view
WHERE deal_creation_reason IS NOT NULL
GROUP BY deal_creation_reason
ORDER BY count DESC;


-- ==================================================================================
-- 6. QUICK HEALTH CHECK - Is Everything Working?
-- ==================================================================================
SELECT 
  CASE 
    WHEN COUNT(*) FILTER (WHERE zerobounce_validated_at >= NOW() - INTERVAL '1 hour') > 0 
    THEN '✅ Active (processed in last hour)'
    ELSE '⚠️  No activity in last hour'
  END as zerobounce_status,
  
  CASE 
    WHEN COUNT(*) FILTER (WHERE hubspot_checked_at_2 >= NOW() - INTERVAL '1 hour') > 0 
    THEN '✅ Active (processed in last hour)'
    ELSE '⚠️  No activity in last hour'
  END as hubspot_status,
  
  CASE 
    WHEN COUNT(*) FILTER (WHERE parsing_processed_at >= NOW() - INTERVAL '2 hours') > 0 
    THEN '✅ Active (processed in last 2 hours)'
    ELSE '⚠️  No activity in last 2 hours'
  END as parser_status
  
FROM contacts_grid_view;


-- ==================================================================================
-- 7. PROCESSING RATE - Hourly Stats
-- ==================================================================================
SELECT 
  DATE_TRUNC('hour', zerobounce_validated_at) as hour,
  COUNT(*) as leads_validated
FROM contacts_grid_view
WHERE zerobounce_validated_at >= NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;

