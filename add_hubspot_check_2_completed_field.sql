-- Add the hubspot_check_2_completed field to track completion of 2nd HubSpot duplicate check
-- Run this SQL in your Supabase SQL editor

ALTER TABLE public.contacts_grid_view 
ADD COLUMN IF NOT EXISTS hubspot_check_2_completed boolean DEFAULT false;

-- Optional: Add an index to improve query performance
CREATE INDEX IF NOT EXISTS idx_contacts_hubspot_check_2_completed 
ON public.contacts_grid_view(hubspot_check_2_completed) 
WHERE hubspot_check_2_completed IS NOT TRUE;

-- Verify the field was added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'contacts_grid_view' 
AND column_name = 'hubspot_check_2_completed';
