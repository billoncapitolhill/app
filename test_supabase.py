import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def test_supabase_connection():
    """Test Supabase client connection and basic operations."""
    print("\nTesting Supabase client connection...")
    try:
        # Initialize client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        supabase: Client = create_client(url, key)
        
        # Test a simple query
        result = supabase.table("bills").select("id").limit(1).execute()
        print("Supabase connection successful!")
        print(f"Query result: {result}")
        
        # Test table existence
        tables = ["bills", "amendments", "ai_summaries", "processing_status"]
        for table in tables:
            result = supabase.table(table).select("id").limit(1).execute()
            print(f"Table '{table}' exists and is accessible")
            
        return True
    except Exception as e:
        print(f"Supabase connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_supabase_connection() 