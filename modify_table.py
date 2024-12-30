from src.services.database import DatabaseService

# Initialize database service with service role key
db = DatabaseService(
    url='https://diocwaxswaomlxvkqpjz.supabase.co',
    key='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRpb2N3YXhzd2FvbWx4dmtxcGp6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNTQwMTUzNiwiZXhwIjoyMDUwOTc3NTM2fQ.9iJpgBVp2jfpEI9l5lono9wM5XNnqr38E9kxdm4_Ad0'
)

# Execute RPC to modify table
try:
    result = db.client.rpc(
        'modify_ai_summaries_table',
        {
            'sql': '''
            ALTER TABLE ai_summaries
            ADD COLUMN IF NOT EXISTS perspective TEXT,
            ADD COLUMN IF NOT EXISTS key_points JSONB,
            ADD COLUMN IF NOT EXISTS estimated_cost_impact TEXT,
            ADD COLUMN IF NOT EXISTS government_growth_analysis TEXT,
            ADD COLUMN IF NOT EXISTS market_impact_analysis TEXT,
            ADD COLUMN IF NOT EXISTS liberty_impact_analysis TEXT;

            ALTER TABLE ai_summaries
            DROP COLUMN IF EXISTS analysis,
            DROP COLUMN IF EXISTS sentiment;
            '''
        }
    ).execute()
    print("Table modified successfully:", result)
except Exception as e:
    print("Error modifying table:", str(e)) 