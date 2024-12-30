import os
from datetime import datetime
from typing import Dict, List, Optional, Union
import logging

from supabase import Client, create_client

from src.models.congress import Amendment, Bill
from src.models.ai import AISummary, ProcessingStatus

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for interacting with the Supabase database."""

    def __init__(self, url: str = None, key: str = None):
        try:
            self.url = url or os.getenv("SUPABASE_URL")
            self.key = key or os.getenv("SUPABASE_KEY")
            
            if not self.url or not self.key:
                logger.error("Supabase URL and key are required")
                raise ValueError("Supabase URL and key are required")
            
            self.client: Client = create_client(self.url, self.key)
            logger.info(f"Successfully connected to Supabase at {self.url}")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise

    def upsert_bill(self, bill_data: Dict) -> Dict:
        """Insert or update a bill in the database."""
        try:
            return self.client.table("bills").upsert(bill_data).execute()
        except Exception as e:
            logger.error(f"Error upserting bill: {str(e)}")
            raise

    def upsert_amendment(self, amendment_data: Dict) -> Dict:
        """Insert or update an amendment in the database."""
        try:
            return self.client.table("amendments").upsert(amendment_data).execute()
        except Exception as e:
            logger.error(f"Error upserting amendment: {str(e)}")
            raise

    def upsert_ai_summary(self, summary_data: Dict) -> Dict:
        """Insert or update an AI summary in the database."""
        try:
            return self.client.table("ai_summaries").upsert(summary_data).execute()
        except Exception as e:
            logger.error(f"Error upserting AI summary: {str(e)}")
            raise

    def update_processing_status(self, status_data: Dict) -> Dict:
        """Update the processing status of a bill or amendment."""
        try:
            return self.client.table("processing_status").upsert(status_data).execute()
        except Exception as e:
            logger.error(f"Error updating processing status: {str(e)}")
            raise

    def get_bills_for_processing(self, limit: int = 100) -> List[Dict]:
        """Get bills that need to be processed or updated."""
        try:
            return (self.client.table("bills")
                    .select("*")
                    .order("updated_at", desc=True)
                    .limit(limit)
                    .execute())
        except Exception as e:
            logger.error(f"Error getting bills for processing: {str(e)}")
            raise

    def get_amendments_for_processing(self, limit: int = 100) -> List[Dict]:
        """Get amendments that need to be processed or updated."""
        try:
            return (self.client.table("amendments")
                    .select("*")
                    .order("updated_at", desc=True)
                    .limit(limit)
                    .execute())
        except Exception as e:
            logger.error(f"Error getting amendments for processing: {str(e)}")
            raise

    def get_bill_with_summaries(self, congress: int, bill_type: str, bill_number: int) -> Dict:
        """Get a bill with its AI summaries and amendments."""
        try:
            return (self.client.table("bills")
                    .select("*, ai_summaries(*), amendments(*)")
                    .eq("congress_number", congress)
                    .eq("bill_type", bill_type)
                    .eq("bill_number", bill_number)
                    .single()
                    .execute())
        except Exception as e:
            logger.error(f"Error getting bill with summaries: {str(e)}")
            raise

    def get_amendment_with_summaries(self, congress: int, amendment_type: str, amendment_number: int) -> Dict:
        """Get an amendment with its AI summaries."""
        try:
            return (self.client.table("amendments")
                    .select("*, ai_summaries(*)")
                    .eq("congress_number", congress)
                    .eq("amendment_type", amendment_type)
                    .eq("amendment_number", amendment_number)
                    .single()
                    .execute())
        except Exception as e:
            logger.error(f"Error getting amendment with summaries: {str(e)}")
            raise

    def get_recent_summaries(self, limit: int = 10) -> List[Dict]:
        """Get the most recent AI summaries."""
        try:
            return (self.client.table("ai_summaries")
                    .select("*, bills(*), amendments(*)")
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute())
        except Exception as e:
            logger.error(f"Error getting recent summaries: {str(e)}")
            raise

    def get_processing_errors(self) -> List[Dict]:
        """Get items with processing errors."""
        try:
            return (self.client.table("processing_status")
                    .select("*")
                    .eq("status", "error")
                    .execute())
        except Exception as e:
            logger.error(f"Error getting processing errors: {str(e)}")
            raise 