import requests
import json

# Supabase configuration
url = 'https://diocwaxswaomlxvkqpjz.supabase.co/rest/v1/rpc/modify_table'
headers = {
    'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRpb2N3YXhzd2FvbWx4dmtxcGp6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNTQwMTUzNiwiZXhwIjoyMDUwOTc3NTM2fQ.9iJpgBVp2jfpEI9l5lono9wM5XNnqr38E9kxdm4_Ad0',
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRpb2N3YXhzd2FvbWx4dmtxcGp6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNTQwMTUzNiwiZXhwIjoyMDUwOTc3NTM2fQ.9iJpgBVp2jfpEI9l5lono9wM5XNnqr38E9kxdm4_Ad0',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

# SQL to modify table
sql = '''
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

# Make the request
try:
    response = requests.post(url, headers=headers, json={'command': sql})
    print(f"Status code: {response.status_code}")
    print("Response:", response.text)
except Exception as e:
    print("Error:", str(e)) 