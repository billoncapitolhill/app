import os
import psycopg2
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a database connection with the correct number of arguments"""
    try:
        # Parse DATABASE_URL into components
        db_url = urlparse(os.getenv('DATABASE_URL'))
        
        # Log the parsed components for debugging
        logger.debug(f"Parsed DB URL: {db_url}")

        # Create connection with only the necessary arguments
        conn = psycopg2.connect(
            dbname=db_url.path[1:],  # Remove leading slash
            user=db_url.username,
            password=db_url.password,
            host=db_url.hostname,
            port=db_url.port
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise 