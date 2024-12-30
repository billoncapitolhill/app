-- Add missing columns to ai_summaries table
ALTER TABLE ai_summaries
ADD COLUMN IF NOT EXISTS perspective TEXT,
ADD COLUMN IF NOT EXISTS key_points JSONB,
ADD COLUMN IF NOT EXISTS estimated_cost_impact TEXT,
ADD COLUMN IF NOT EXISTS government_growth_analysis TEXT,
ADD COLUMN IF NOT EXISTS market_impact_analysis TEXT,
ADD COLUMN IF NOT EXISTS liberty_impact_analysis TEXT;

-- Drop existing columns that are no longer needed
ALTER TABLE ai_summaries
DROP COLUMN IF EXISTS analysis,
DROP COLUMN IF EXISTS sentiment; 