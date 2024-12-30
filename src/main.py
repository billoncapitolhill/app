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
        # Get detailed bill information
        bill_details = congress_client.get_bill_details(
            bill_data["congress"],
            bill_data["bill_type"],
            bill_data["bill_number"]
        )
        
        # Generate AI summary
        summary = ai_summarizer.summarize_bill(bill_details["text"])
        
        # Update database
        db_service.upsert_bill(bill_details)
        db_service.upsert_ai_summary({
            "target_id": bill_details["id"],
            "target_type": "bill",
            **summary
        })
        
        # Update processing status
        db_service.update_processing_status({
            "target_id": bill_details["id"],
            "target_type": "bill",
            "status": "completed",
            "last_processed": datetime.utcnow()
        })
        logger.info(f"Successfully processed bill {bill_data['bill_type']}{bill_data['bill_number']}")
        
    except Exception as e:
        logger.error(f"Error processing bill: {str(e)}")
        db_service.update_processing_status({
            "target_id": bill_data["id"],
            "target_type": "bill",
            "status": "error",
            "error_message": str(e),
            "last_processed": datetime.utcnow()
        })

async def process_amendment(amendment_data: Dict) -> None:
    """Process an amendment and generate AI summary."""
    try:
        # Get detailed amendment information
        amendment_details = congress_client.get_amendment_details(
            amendment_data["congress"],
            amendment_data["amendment_type"],
            amendment_data["amendment_number"]
        )
        
        # Get associated bill if available
        bill_details = None
        if amendment_data.get("bill_id"):
            bill = db_service.get_bill_with_summaries(
                amendment_data["congress"],
                amendment_data["bill_type"],
                amendment_data["bill_number"]
            )
            if bill:
                bill_details = bill["text"]
        
        # Generate AI summary
        summary = ai_summarizer.summarize_amendment(
            amendment_details["text"],
            bill_details
        )
        
        # Update database
        db_service.upsert_amendment(amendment_details)
        db_service.upsert_ai_summary({
            "target_id": amendment_details["id"],
            "target_type": "amendment",
            **summary
        })
        
        # Update processing status
        db_service.update_processing_status({
            "target_id": amendment_details["id"],
            "target_type": "amendment",
            "status": "completed",
            "last_processed": datetime.utcnow()
        })
        logger.info(f"Successfully processed amendment {amendment_data['amendment_type']}{amendment_data['amendment_number']}")
        
    except Exception as e:
        logger.error(f"Error processing amendment: {str(e)}")
        db_service.update_processing_status({
            "target_id": amendment_data["id"],
            "target_type": "amendment",
            "status": "error",
            "error_message": str(e),
            "last_processed": datetime.utcnow()
        })

async def update_congress_data() -> None:
    """Update bills and amendments from Congress.gov."""
    try:
        # Get updates from the last 24 hours
        since_date = datetime.utcnow() - timedelta(days=1)
        updates = congress_client.get_updates_since(since_date)
        
        # Process bills
        for bill in updates.get("bills", []):
            await process_bill(bill)
        
        # Process amendments
        for amendment in updates.get("amendments", []):
            await process_amendment(amendment)
        logger.info("Successfully completed Congress data update")
            
    except Exception as e:
        logger.error(f"Error updating Congress data: {str(e)}")

def run_async_job():
    """Helper function to run async job in the event loop."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(update_congress_data())

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