import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.services.database import DatabaseService

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