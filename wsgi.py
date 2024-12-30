import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the FastAPI application
try:
    from src.main import app
    logger.info("Successfully loaded application")
except Exception as e:
    logger.error(f"Failed to load application: {str(e)}")
    raise

# This is used by gunicorn to serve the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="debug"
    ) 