-- Add fields for parsed scrap_data
-- Run this SQL in your Supabase SQL editor

-- Add parsed data fields
ALTER TABLE public.contacts_grid_view 
ADD COLUMN IF NOT EXISTS parsed_images jsonb,
ADD COLUMN IF NOT EXISTS parsed_description text,
ADD COLUMN IF NOT EXISTS parsed_latitude float,
ADD COLUMN IF NOT EXISTS parsed_longitude float,
ADD COLUMN IF NOT EXISTS parsing_completed boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS parsing_processed_at timestamp with time zone;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_contacts_parsing_completed 
ON public.contacts_grid_view(parsing_completed) 
WHERE parsing_completed IS NOT TRUE;

CREATE INDEX IF NOT EXISTS idx_contacts_parsed_location 
ON public.contacts_grid_view(parsed_latitude, parsed_longitude) 
WHERE parsed_latitude IS NOT NULL AND parsed_longitude IS NOT NULL;

-- Verify the fields were added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'contacts_grid_view' 
AND column_name IN ('parsed_images', 'parsed_description', 'parsed_latitude', 'parsed_longitude', 'parsing_completed', 'parsing_processed_at')
ORDER BY column_name;
