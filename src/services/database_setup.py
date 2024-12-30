import logging
from typing import Optional, Dict
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
import os

logger = logging.getLogger(__name__)

# Set these environment variables or replace with your actual values.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize the Supabase client
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=ClientOptions()
)

def ensure_tables_exist() -> None:
    """
    Checks if the 'bills' and 'amendments' tables exist in the database.
    If they do not exist, creates them using SQL via a Postgres function call.
    """
    # You need to create a Postgres function that can run arbitrary SQL
    # for this approach. For example, in your Supabase SQL Editor:
    #
    #   CREATE OR REPLACE FUNCTION public.run_sql(query text)
    #   RETURNS void
    #   LANGUAGE plpgsql
    #   AS $$
    #   BEGIN
    #       EXECUTE query;
    #   END;
    #   $$;
    #
    # This function allows you to execute arbitrary SQL statements from Supabase RPC calls.
    # Then you can call it here to create the tables if they don't exist.

    create_tables_sql = """
    CREATE TABLE IF NOT EXISTS public.bills (
        id BIGSERIAL PRIMARY KEY,
        congress INT NOT NULL,
        type VARCHAR(10) NOT NULL,
        number VARCHAR(50) NOT NULL,
        title TEXT,
        update_date DATE
    );

    CREATE TABLE IF NOT EXISTS public.amendments (
        id BIGSERIAL PRIMARY KEY,
        congress INT NOT NULL,
        type VARCHAR(10) NOT NULL,
        number VARCHAR(50) NOT NULL,
        description TEXT,
        purpose TEXT,
        action_date DATE,
        action_text TEXT
    );
    """

    try:
        # Call your Postgres function to run the SQL script
        response = supabase.rpc("run_sql", {"query": create_tables_sql}).execute()
        if "error" in response or response.get("status_code", 200) != 200:
            logger.error("Failed to create tables: %s", response)
        else:
            logger.info("Ensured 'bills' and 'amendments' tables exist.")
    except Exception as e:
        logger.error("Error ensuring tables exist: %s", e) 