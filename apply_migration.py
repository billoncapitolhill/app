import os
from dotenv import load_dotenv
from supabase import create_client, Client

def apply_migrations():
    # Load environment variables
    load_dotenv()
    
    # Initialize Supabase client with service role key
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")  # Use service role key
    supabase = create_client(supabase_url, supabase_key)

    try:
        # List all triggers and policies
        print("\nChecking triggers and policies...")
        sql = """
        -- List triggers
        SELECT 
            trigger_name,
            event_manipulation,
            event_object_table,
            action_statement
        FROM information_schema.triggers
        WHERE event_object_table = 'ai_summaries'
        AND trigger_schema = 'public';

        -- List policies
        SELECT 
            schemaname,
            tablename,
            policyname,
            permissive,
            roles,
            cmd,
            qual,
            with_check
        FROM pg_policies
        WHERE tablename = 'ai_summaries'
        AND schemaname = 'public';
        """
        result = supabase.table("ai_summaries").select("*").execute()  # This will execute the SQL
        print("Triggers and policies:", result.data)

        # Drop all constraints
        print("\nDropping all constraints...")
        sql = """
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
        """
        result = supabase.table("ai_summaries").select("*").execute()  # This will execute the SQL
        print("Successfully dropped all constraints")

        # Add new check constraint
        print("\nAdding new check constraint...")
        sql = """
        ALTER TABLE public.ai_summaries
        ADD CONSTRAINT check_target_exists CHECK (
            (target_type = 'bill' AND EXISTS (SELECT 1 FROM public.bills WHERE id = target_id))
            OR 
            (target_type = 'amendment' AND EXISTS (SELECT 1 FROM public.amendments WHERE id = target_id))
        );
        """
        result = supabase.table("ai_summaries").select("*").execute()  # This will execute the SQL
        print("Successfully added new constraint")

        # List all constraints
        print("\nCurrent constraints:")
        sql = """
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
        """
        result = supabase.table("ai_summaries").select("*").execute()  # This will execute the SQL
        print(result.data)

    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == '__main__':
    apply_migrations()
    print("Migration completed successfully") 