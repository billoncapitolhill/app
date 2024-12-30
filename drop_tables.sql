-- Drop tables in reverse order of dependencies
DROP TABLE IF EXISTS processing_status;
DROP TABLE IF EXISTS ai_summaries;
DROP TABLE IF EXISTS amendments;
DROP TABLE IF EXISTS bills;

-- Drop the trigger function
DROP FUNCTION IF EXISTS update_updated_at_column; 