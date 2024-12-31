-- Drop all constraints on ai_summaries table
DO $$ 
DECLARE
    r RECORD;
BEGIN
    -- Drop all foreign key constraints
    FOR r IN (SELECT tc.constraint_name 
            FROM information_schema.table_constraints tc
            WHERE tc.table_name = 'ai_summaries'
            AND tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public') 
    LOOP
        EXECUTE 'ALTER TABLE public.ai_summaries DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name) || ' CASCADE';
    END LOOP;

    -- Drop all check constraints
    FOR r IN (SELECT tc.constraint_name 
            FROM information_schema.table_constraints tc
            WHERE tc.table_name = 'ai_summaries'
            AND tc.constraint_type = 'CHECK'
            AND tc.table_schema = 'public') 
    LOOP
        EXECUTE 'ALTER TABLE public.ai_summaries DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name) || ' CASCADE';
    END LOOP;
END $$;

-- Drop specific constraints if they still exist
ALTER TABLE public.ai_summaries
DROP CONSTRAINT IF EXISTS fk_bill_summary CASCADE;

ALTER TABLE public.ai_summaries
DROP CONSTRAINT IF EXISTS fk_amendment_summary CASCADE;

ALTER TABLE public.ai_summaries
DROP CONSTRAINT IF EXISTS check_target_exists CASCADE;

-- Drop all validation triggers
DROP TRIGGER IF EXISTS validate_target_id_trigger ON public.ai_summaries;
DROP TRIGGER IF EXISTS trg_check_target_exists_ai_summaries ON public.ai_summaries;
DROP TRIGGER IF EXISTS trg_check_target_exists ON public.ai_summaries;
DROP TRIGGER IF EXISTS trg_check_target_exists_processing_status ON public.processing_status;

-- Drop validation functions with CASCADE
DROP FUNCTION IF EXISTS validate_target_id() CASCADE;
DROP FUNCTION IF EXISTS check_target_exists() CASCADE;

-- Add check constraint for target_type
ALTER TABLE public.ai_summaries
ADD CONSTRAINT check_target_type CHECK (target_type IN ('bill', 'amendment'));

-- Create a function to validate target_id
CREATE OR REPLACE FUNCTION validate_target_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.target_type = 'bill' THEN
        IF NOT EXISTS (SELECT 1 FROM public.bills WHERE id = NEW.target_id) THEN
            RAISE EXCEPTION 'Referenced bill % does not exist', NEW.target_id;
        END IF;
    ELSIF NEW.target_type = 'amendment' THEN
        IF NOT EXISTS (SELECT 1 FROM public.amendments WHERE id = NEW.target_id) THEN
            RAISE EXCEPTION 'Referenced amendment % does not exist', NEW.target_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to validate target_id for ai_summaries
CREATE TRIGGER validate_target_id_trigger
    BEFORE INSERT OR UPDATE ON public.ai_summaries
    FOR EACH ROW
    EXECUTE FUNCTION validate_target_id();

-- Create trigger to validate target_id for processing_status
CREATE TRIGGER validate_target_id_trigger_processing_status
    BEFORE INSERT OR UPDATE ON public.processing_status
    FOR EACH ROW
    EXECUTE FUNCTION validate_target_id();

-- Verify constraints and triggers
SELECT 
    tc.table_name, 
    tc.constraint_name, 
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM 
    information_schema.table_constraints tc
    LEFT JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    LEFT JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE 
    tc.table_name = 'ai_summaries'
    AND tc.table_schema = 'public';

SELECT 
    trigger_name,
    event_manipulation,
    event_object_table,
    action_statement
FROM 
    information_schema.triggers
WHERE 
    event_object_table IN ('ai_summaries', 'processing_status')
    AND trigger_schema = 'public'; 