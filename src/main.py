import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.services.congress_client import CongressClient
from src.services.ai_summarizer import AISummarizer
from src.services.database import DatabaseService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Congress Bill Analysis Platform")

# Initialize services
try:
    congress_client = CongressClient()
    ai_summarizer = AISummarizer()
    db_service = DatabaseService()
    logger.info("Successfully initialized all services")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    raise

# Initialize scheduler
scheduler = AsyncIOScheduler()

async def process_bill(bill_data: Dict) -> None:
    """Process a bill and generate AI summary."""
    try:
        congress = bill_data.get("congress")
        bill_type = bill_data.get("type")
        bill_number = bill_data.get("number")
        bill_id = bill_data.get("billId")
        
        if not all([congress, bill_type, bill_number, bill_id]):
            logger.error("Missing required fields for bill: congress=%s, type=%s, number=%s, id=%s",
                        congress, bill_type, bill_number, bill_id)
            return
        
        logger.info("Starting to process bill %s%s from Congress %s", 
                   bill_type, bill_number, congress)
        
        # Get detailed bill information
        logger.info("Fetching detailed information for bill %s%s", 
                   bill_type, bill_number)
        bill_details = congress_client.get_bill_details(
            congress,
            bill_type,
            bill_number
        ).get("bill", {})
        
        if not bill_details:
            logger.error("Failed to get details for bill %s%s", bill_type, bill_number)
            return
        
        # Generate AI summary
        logger.info("Generating AI summary for bill %s%s", 
                   bill_type, bill_number)
        summary = ai_summarizer.summarize_bill(bill_details.get("text", ""))
        
        # Update database
        logger.info("Updating database with bill %s%s and its summary", 
                   bill_type, bill_number)
        db_service.upsert_bill(bill_details)
        db_service.upsert_ai_summary({
            "target_id": bill_id,
            "target_type": "bill",
            **summary
        })
        
        # Update processing status
        logger.info("Updating processing status for bill %s%s", 
                   bill_type, bill_number)
        db_service.update_processing_status({
            "target_id": bill_id,
            "target_type": "bill",
            "status": "completed",
            "last_processed": datetime.utcnow()
        })
        logger.info("Successfully processed bill %s%s", 
                   bill_type, bill_number)
        
    except Exception as e:
        logger.error("Error processing bill: %s", str(e))
        if bill_id:
            db_service.update_processing_status({
                "target_id": bill_id,
                "target_type": "bill",
                "status": "error",
                "error_message": str(e),
                "last_processed": datetime.utcnow()
            })

async def process_amendment(amendment_data: Dict) -> None:
    """Process an amendment and generate AI summary."""
    try:
        congress = amendment_data.get("congress")
        amendment_type = amendment_data.get("type")
        amendment_number = amendment_data.get("number")
        amendment_id = amendment_data.get("amendmentId")
        associated_bill = amendment_data.get("associatedBill", {})
        
        if not all([congress, amendment_type, amendment_number, amendment_id]):
            logger.error("Missing required fields for amendment: congress=%s, type=%s, number=%s, id=%s",
                        congress, amendment_type, amendment_number, amendment_id)
            return
        
        logger.info("Starting to process amendment %s%s from Congress %s",
                   amendment_type, amendment_number, congress)
        
        # Get detailed amendment information
        logger.info("Fetching detailed information for amendment %s%s",
                   amendment_type, amendment_number)
        amendment_details = congress_client.get_amendment_details(
            congress,
            amendment_type,
            amendment_number
        ).get("amendment", {})
        
        if not amendment_details:
            logger.error("Failed to get details for amendment %s%s", amendment_type, amendment_number)
            return
        
        # Get associated bill if available
        bill_details = None
        if associated_bill:
            logger.info("Fetching associated bill details for amendment %s%s",
                       amendment_type, amendment_number)
            bill = db_service.get_bill_with_summaries(
                associated_bill.get("congress"),
                associated_bill.get("type"),
                associated_bill.get("number")
            )
            if bill:
                bill_details = bill.get("text")
                logger.info("Found associated bill %s%s for amendment %s%s",
                           associated_bill.get("type"), associated_bill.get("number"),
                           amendment_type, amendment_number)
        
        # Generate AI summary
        logger.info("Generating AI summary for amendment %s%s",
                   amendment_type, amendment_number)
        summary = ai_summarizer.summarize_amendment(
            amendment_details.get("text", ""),
            bill_details
        )
        
        # Update database
        logger.info("Updating database with amendment %s%s and its summary",
                   amendment_type, amendment_number)
        db_service.upsert_amendment(amendment_details)
        db_service.upsert_ai_summary({
            "target_id": amendment_id,
            "target_type": "amendment",
            **summary
        })
        
        # Update processing status
        logger.info("Updating processing status for amendment %s%s",
                   amendment_type, amendment_number)
        db_service.update_processing_status({
            "target_id": amendment_id,
            "target_type": "amendment",
            "status": "completed",
            "last_processed": datetime.utcnow()
        })
        logger.info("Successfully processed amendment %s%s",
                   amendment_type, amendment_number)
        
    except Exception as e:
        logger.error("Error processing amendment: %s", str(e))
        if amendment_id:
            db_service.update_processing_status({
                "target_id": amendment_id,
                "target_type": "amendment",
                "status": "error",
                "error_message": str(e),
                "last_processed": datetime.utcnow()
            })

async def update_congress_data() -> None:
    """Update bills and amendments from Congress.gov."""
    try:
        # Get recent bills from the current Congress (118th)
        logger.info("Fetching recent bills from the 118th Congress")
        
        response = congress_client.get_recent_bills(118, limit=50)
        logger.debug("Raw API response: %s", response)
        
        # The response structure is different than expected
        # It returns a list directly under 'bills'
        bills = response.get("bills", []) if isinstance(response.get("bills"), list) else []
        amendments = []
        
        # For each bill, get its amendments if we have the required fields
        for bill in bills:
            try:
                # Extract bill information
                congress = bill.get("congress")
                bill_type = bill.get("type")
                bill_number = bill.get("number")
                bill_id = bill.get("id")
                
                if not all([congress, bill_type, bill_number, bill_id]):
                    logger.warning("Skipping bill %d/%d due to missing required fields",
                                 i, len(bills))
                    continue
                
                logger.info("Fetching amendments for bill %s%s from Congress %s",
                          bill_type, bill_number, congress)
                
                amendment_response = congress_client.get_bill_amendments(
                    congress,
                    bill_type,
                    bill_number
                )
                
                # Handle the amendments response structure
                bill_amendments = amendment_response.get("amendments", [])
                if isinstance(bill_amendments, dict):
                    bill_amendments = bill_amendments.get("amendment", [])
                
                amendments.extend(bill_amendments if isinstance(bill_amendments, list) else [])
                logger.info("Found %d amendments for bill %s%s",
                          len(bill_amendments) if isinstance(bill_amendments, list) else 0,
                          bill_type, bill_number)
                
            except Exception as e:
                logger.error("Error fetching amendments for bill: %s", str(e))
        
        logger.info("Received %d bills to process", len(bills))
        
        # Process bills
        for i, bill in enumerate(bills, 1):
            try:
                congress = bill.get("congress")
                bill_type = bill.get("type")
                bill_number = bill.get("number")
                
                if not all([congress, bill_type, bill_number]):
                    logger.warning("Skipping bill %d/%d due to missing required fields", i, len(bills))
                    continue
                
                logger.info("Processing bill %d of %d (%s%s)", i, len(bills), bill_type, bill_number)
                await process_bill(bill)
                
                # Fetch and process amendments for this bill
                amendments = congress_client.get_bill_amendments(congress, bill_type, bill_number)
                if amendments:
                    for amendment in amendments:
                        await process_amendment(amendment)
                else:
                    logger.info("No amendments to process for bill %s%s", bill_type, bill_number)
                
            except Exception as e:
                logger.error("Error processing bill %d/%d: %s", i, len(bills), str(e))
        
        logger.info("Successfully completed Congress data update")
            
    except Exception as e:
        logger.error("Error updating Congress data: %s", str(e))

def run_async_job():
    """Helper function to run async job in the event loop."""
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the coroutine
        loop.run_until_complete(update_congress_data())
        
        # Clean up
        loop.close()
    except Exception as e:
        logger.error(f"Error in scheduler job: {str(e)}")

# Schedule daily updates
scheduler.add_job(
    run_async_job,
    trigger=IntervalTrigger(hours=24),
    next_run_time=datetime.now()
)

@app.on_event("startup")
async def startup_event():
    """Start the scheduler on application startup."""
    try:
        scheduler.start()
        logger.info("Successfully started scheduler")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Shut down the scheduler on application shutdown."""
    try:
        scheduler.shutdown()
        logger.info("Successfully shut down scheduler")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}")

@app.get("/bills/{congress}/{bill_type}/{bill_number}")
async def get_bill(congress: int, bill_type: str, bill_number: int):
    """Get a bill with its AI summaries and amendments."""
    try:
        return db_service.get_bill_with_summaries(congress, bill_type, bill_number)
    except Exception as e:
        logger.error(f"Error getting bill: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/amendments/{congress}/{amendment_type}/{amendment_number}")
async def get_amendment(congress: int, amendment_type: str, amendment_number: int):
    """Get an amendment with its AI summaries."""
    try:
        return db_service.get_amendment_with_summaries(congress, amendment_type, amendment_number)
    except Exception as e:
        logger.error(f"Error getting amendment: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/summaries/recent")
async def get_recent_summaries(limit: int = 10):
    """Get the most recent AI summaries."""
    try:
        return db_service.get_recent_summaries(limit)
    except Exception as e:
        logger.error(f"Error getting recent summaries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/errors")
async def get_processing_errors():
    """Get items with processing errors."""
    try:
        return db_service.get_processing_errors()
    except Exception as e:
        logger.error(f"Error getting processing errors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 