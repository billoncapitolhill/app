from sqlalchemy import create_engine, text

# Create database engine
engine = create_engine('postgresql://postgres:PLv0SnyPNYepruWI@db.diocwaxswaomlxvkqpjz.supabase.co:5432/postgres')

# Read migration SQL
with open('supabase/migrations/0002_add_ai_summary_columns.sql', 'r') as f:
    sql = f.read()

# Execute migration
with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()

print("Migration completed successfully") 