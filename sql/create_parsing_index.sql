-- Create optimized index for parsing_completed queries
-- This makes "WHERE parsing_completed = FALSE" queries FAST
-- Run this in Supabase SQL Editor

-- Drop old index if exists
DROP INDEX IF EXISTS idx_contacts_parsing_completed;

-- Create new partial index - only indexes unparsed records
CREATE INDEX IF NOT EXISTS idx_contacts_parsing_incomplete 
ON public.contacts_grid_view(id) 
WHERE parsing_completed = FALSE AND scrap_data IS NOT NULL;

-- Verify index was created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'contacts_grid_view'
AND indexname = 'idx_contacts_parsing_incomplete';
