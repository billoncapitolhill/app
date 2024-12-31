import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List
from dotenv import load_dotenv
import traceback
import time
from functools import wraps

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.services.congress_client import CongressClient
from src.services.database import DatabaseService
from src.services.ai_service import AIService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://orca-app-nkgpg.ondigitalocean.app",
        "https://www.orca-app-nkgpg.ondigitalocean.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
congress_api_key = os.getenv("CONGRESS_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not all([supabase_url, supabase_key, congress_api_key, openai_api_key]):
    raise ValueError("Missing required environment variables")

db_service = DatabaseService(url=supabase_url, key=supabase_key)
congress_client = CongressClient(api_key=congress_api_key)
ai_service = AIService(api_key=openai_api_key)

def ensure_utc_datetime(date_str: str) -> datetime:
    """Convert a date string to a UTC timezone-aware datetime object."""
    if not date_str:
        return datetime.now(timezone.utc)
    
    # Remove any trailing 'Z' and replace with +00:00
    date_str = date_str.replace('Z', '+00:00')
    
    try:
        # Try to parse as is (might already have timezone info)
        dt = datetime.fromisoformat(date_str)
    except ValueError:
        # If parsing fails, assume UTC and add timezone
        try:
            dt = datetime.fromisoformat(date_str + '+00:00')
        except ValueError:
            # If all else fails, return current UTC time
            return datetime.now(timezone.utc)
    
    # If datetime is naive (no timezone), make it UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt

def with_database_retry(max_retries=3, delay=5):
    """Decorator to retry database operations with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Final database operation failure after {retries} retries: {str(e)}\n{traceback.format_exc()}")
                        raise
                    wait_time = delay * (2 ** (retries - 1))  # Exponential backoff
                    logger.warning(f"Database operation failed, attempt {retries} of {max_retries}. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
            return None
        return wrapper
    return decorator

@app.on_event("startup")
async def startup_event():
    """Initialize services and start background tasks."""
    logger.info("Application startup event triggered.")
    asyncio.create_task(process_bills())

async def process_bills():
    """Background task to fetch and process bills."""
    while True:
        try:
            # Get recent bills from Congress.gov
            try:
                bills_data = congress_client.get_recent_bills(congress=118, limit=50)
                bills = bills_data.get("bills", [])
            except Exception as e:
                logger.error(f"Failed to fetch recent bills: {str(e)}\n{traceback.format_exc()}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
                continue
            
            for bill in bills:
                try:
                    # Get detailed bill information
                    try:
                        bill_details = congress_client.get_bill_details(
                            congress=bill["congress"],
                            bill_type=bill["type"],
                            bill_number=bill["number"]
                        )
                    except Exception as e:
                        logger.error(f"Error fetching details for bill {bill.get('type')}{bill.get('number')}: {str(e)}\n{traceback.format_exc()}")
                        continue
                    
                    # Store bill in database
                    try:
                        bill_data = {
                            "congress_number": bill["congress"],
                            "bill_type": bill["type"],
                            "bill_number": int(bill["number"]),
                            "title": bill.get("title"),
                            "description": bill_details.get("summary", ""),
                            "origin_chamber": bill.get("originChamber"),
                            "origin_chamber_code": bill.get("originChamberCode"),
                            "introduced_date": bill.get("introducedDate"),
                            "latest_action_date": bill.get("latestAction", {}).get("actionDate"),
                            "latest_action_text": bill.get("latestAction", {}).get("text"),
                            "update_date": bill.get("updateDate"),
                            "url": bill.get("url"),
                            "actions": bill_details.get("actions", [])
                        }
                        
                        stored_bill = db_service.upsert_bill(bill_data)
                        if not stored_bill:
                            logger.error(f"Failed to store bill {bill['type']}{bill['number']}")
                            continue
                            
                        # Process amendments if they exist
                        if bill_details.get("amendments"):
                            for amendment in bill_details["amendments"]:
                                try:
                                    amendment_data = {
                                        "bill_id": stored_bill["id"],
                                        "congress_number": amendment.get("congress"),
                                        "amendment_type": amendment.get("type"),
                                        "amendment_number": int(amendment.get("number")),
                                        "description": amendment.get("description", ""),
                                        "purpose": amendment.get("purpose", ""),
                                        "submitted_date": amendment.get("submittedDate"),
                                        "latest_action_date": amendment.get("latestAction", {}).get("actionDate"),
                                        "latest_action_text": amendment.get("latestAction", {}).get("text"),
                                        "chamber": amendment.get("chamber"),
                                        "url": amendment.get("url")
                                    }
                                    
                                    stored_amendment = db_service.upsert_amendment(amendment_data)
                                    if stored_amendment:
                                        # Generate and store amendment summary
                                        try:
                                            amendment_summary = await ai_service.generate_amendment_summary(amendment)
                                            if amendment_summary:
                                                summary_data = {
                                                    "target_id": stored_amendment["id"],
                                                    "target_type": "amendment",
                                                    "summary": amendment_summary["summary"],
                                                    "perspective": amendment_summary["perspective"],
                                                    "key_points": amendment_summary["key_points"],
                                                    "estimated_cost_impact": amendment_summary["estimated_cost_impact"],
                                                    "government_growth_analysis": amendment_summary["government_growth_analysis"],
                                                    "market_impact_analysis": amendment_summary["market_impact_analysis"],
                                                    "liberty_impact_analysis": amendment_summary["liberty_impact_analysis"]
                                                }
                                                db_service.upsert_ai_summary(summary_data)
                                        except Exception as e:
                                            logger.error(f"Error processing amendment summary: {str(e)}")
                                except Exception as e:
                                    logger.error(f"Error processing amendment: {str(e)}")
                                    continue
                                
                    except Exception as e:
                        logger.error(f"Error storing bill {bill.get('type')}{bill.get('number')}: {str(e)}\n{traceback.format_exc()}")
                        continue
                    
                    # Generate AI summary for bill
                    try:
                        summary = await ai_service.generate_bill_summary(bill_details)
                    except Exception as e:
                        logger.error(f"Error generating summary for bill {bill.get('type')}{bill.get('number')}: {str(e)}\n{traceback.format_exc()}")
                        continue
                    
                    # Store AI summary for bill
                    try:
                        summary_data = {
                            "target_id": stored_bill["id"],
                            "target_type": "bill",
                            "summary": summary["summary"],
                            "perspective": summary["perspective"],
                            "key_points": summary["key_points"],
                            "estimated_cost_impact": summary["estimated_cost_impact"],
                            "government_growth_analysis": summary["government_growth_analysis"],
                            "market_impact_analysis": summary["market_impact_analysis"],
                            "liberty_impact_analysis": summary["liberty_impact_analysis"]
                        }
                        
                        db_service.upsert_ai_summary(summary_data)
                        logger.info(f"Successfully processed bill {bill['type']}{bill['number']}")
                    except Exception as e:
                        logger.error(f"Error storing summary for bill {bill.get('type')}{bill.get('number')}: {str(e)}\n{traceback.format_exc()}")
                        continue
                    
                except Exception as e:
                    logger.error(f"Unexpected error processing bill {bill.get('type')}{bill.get('number')}: {str(e)}\n{traceback.format_exc()}")
                    continue
                
                # Sleep briefly between bills to avoid rate limiting
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Critical error in bill processing loop: {str(e)}\n{traceback.format_exc()}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying
        
        # Sleep for an hour before checking for new bills
        logger.info("Completed processing cycle, sleeping for 1 hour")
        await asyncio.sleep(3600)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        db_service.get_recent_summaries(limit=1)
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/api/v1/bills/recent")
@with_database_retry(max_retries=3, delay=5)
async def get_recent_bills(limit: int = 10):
    """Get recent bills with their AI summaries."""
    try:
        bills = db_service.get_recent_summaries(limit=limit)
        return {"bills": bills}
    except Exception as e:
        logger.error(f"Error getting recent bills: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database service temporarily unavailable",
                "message": "Please try again in a few moments"
            }
        )

@app.get("/api/v1/bills/{congress}/{bill_type}/{bill_number}")
@with_database_retry(max_retries=3, delay=5)
async def get_bill_details(congress: int, bill_type: str, bill_number: int):
    """Get details for a specific bill."""
    try:
        bill = db_service.get_bill_with_summaries(congress=congress, bill_type=bill_type, bill_number=bill_number)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        return bill
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bill details: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database service temporarily unavailable",
                "message": "Please try again in a few moments"
            }
        )

@app.get("/api/v1/summaries/recent")
@with_database_retry(max_retries=3, delay=5)
async def get_recent_summaries(limit: int = 10):
    """Get recent AI summaries."""
    try:
        summaries = db_service.get_recent_summaries(limit=limit)
        return {"summaries": summaries}
    except Exception as e:
        logger.error(f"Error getting recent summaries: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database service temporarily unavailable",
                "message": "Please try again in a few moments"
            }
        ) 