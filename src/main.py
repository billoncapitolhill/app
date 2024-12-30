import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.services.database import DatabaseService
from src.database.connection import get_db_connection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG during development

app = FastAPI(title="Congress Bill Analysis Platform")

# Initialize SQLAlchemy
DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
engine = create_engine(DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize services
try:
    db_service = DatabaseService()
    logger.info("Successfully initialized all services")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    raise 

@app.get("/summaries/recent")
def get_recent_summaries(limit: int = 20):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Example query - adjust according to your schema
        query = "SELECT * FROM summaries ORDER BY created_at DESC LIMIT %s"
        cursor.execute(query, (limit,))
        summaries = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {"summaries": summaries}
    except Exception as e:
        logger.error(f"Error fetching recent summaries: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error") 