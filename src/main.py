import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
import traceback

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
    allow_origins=["http://localhost:5173"],
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
                    # Check if we already have an AI summary for this bill
                    try:
                        existing_bill = db_service.get_bill_with_summaries(
                            congress=bill["congress"],
                            bill_type=bill["type"],
                            bill_number=bill["number"]
                        )
                    except Exception as e:
                        logger.error(f"Error checking existing bill {bill.get('type')}{bill.get('number')}: {str(e)}\n{traceback.format_exc()}")
                        continue

                    # Check if bill already has a summary and hasn't been updated
                    if existing_bill and existing_bill.get("ai_summaries"):
                        try:
                            # Convert both dates to UTC timezone-aware datetime objects
                            bill_update_date = datetime.fromisoformat(bill.get("updateDate", "").replace('Z', '+00:00'))
                            # Make summary_date timezone-aware by assuming UTC
                            summary_date_str = existing_bill["ai_summaries"][0]["created_at"]
                            if summary_date_str.endswith('Z'):
                                summary_date = datetime.fromisoformat(summary_date_str.replace('Z', '+00:00'))
                            elif '+' not in summary_date_str and '-' not in summary_date_str[10:]:
                                summary_date = datetime.fromisoformat(summary_date_str + '+00:00')
                            else:
                                summary_date = datetime.fromisoformat(summary_date_str)
                            
                            if bill_update_date <= summary_date:
                                logger.info(f"Bill {bill['type']}{bill['number']} already has up-to-date AI summary")
                                continue
                            else:
                                logger.info(f"Bill {bill['type']}{bill['number']} has been updated, generating new summary")
                        except Exception as e:
                            logger.error(f"Error comparing dates for bill {bill.get('type')}{bill.get('number')}: {str(e)}\n{traceback.format_exc()}")
                            continue

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
                    except Exception as e:
                        logger.error(f"Error storing bill {bill.get('type')}{bill.get('number')}: {str(e)}\n{traceback.format_exc()}")
                        continue
                    
                    # Generate AI summary
                    try:
                        summary = await ai_service.generate_bill_summary(bill_details)
                    except Exception as e:
                        logger.error(f"Error generating summary for bill {bill.get('type')}{bill.get('number')}: {str(e)}\n{traceback.format_exc()}")
                        continue
                    
                    # Store AI summary
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
    return {"status": "healthy"}

@app.get("/api/v1/bills/recent")
async def get_recent_bills(limit: int = 10):
    """Get recent bills with their AI summaries."""
    try:
        bills = db_service.get_recent_summaries(limit=limit)
        return {"bills": bills}
    except Exception as e:
        logger.error(f"Error getting recent bills: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/bills/{congress}/{bill_type}/{bill_number}")
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/summaries/recent")
async def get_recent_summaries(limit: int = 10):
    """Get recent AI summaries."""
    try:
        summaries = db_service.get_recent_summaries(limit=limit)
        return {"summaries": summaries}
    except Exception as e:
        logger.error(f"Error getting recent summaries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 