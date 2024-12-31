import os
import logging
from datetime import datetime
from typing import Dict, Optional, List
import json
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for interacting with the Supabase database."""

    def __init__(self, url: str, key: str):
        """Initialize the database service with Supabase credentials."""
        self.client = create_client(url, key)
        logger.info("Successfully connected to Supabase at %s", url)

    def _serialize_datetime(self, data: Dict) -> Dict:
        """Convert datetime objects to ISO format strings."""
        serialized = data.copy()
        for key, value in serialized.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
        return serialized

    def upsert_bill(self, bill_data: Dict) -> Dict:
        """Insert or update a bill in the database."""
        try:
            # Serialize datetime objects before sending to Supabase
            bill_data = self._serialize_datetime(bill_data)
            
            # First, insert/update the bill
            result = self.client.table("bills").upsert(
                bill_data,
                on_conflict="congress_number,bill_type,bill_number"
            ).execute()
            if result.data:
                logger.info("Successfully upserted bill %s%s", bill_data.get("bill_type"), bill_data.get("bill_number"))
                return result.data[0]
            else:
                raise Exception("No data returned from bill upsert")
        except Exception as e:
            logger.error("Error upserting bill: %s", str(e))
            raise

    def upsert_amendment(self, amendment_data: Dict) -> Dict:
        """Insert or update an amendment in the database."""
        try:
            # Serialize datetime objects before sending to Supabase
            amendment_data = self._serialize_datetime(amendment_data)
            
            # First, insert/update the amendment
            result = self.client.table("amendments").upsert(
                amendment_data,
                on_conflict="congress_number,amendment_type,amendment_number"
            ).execute()
            if result.data:
                logger.info("Successfully upserted amendment %s", amendment_data.get("amendment_number"))
                return result.data[0]
            else:
                raise Exception("No data returned from amendment upsert")
        except Exception as e:
            logger.error("Error upserting amendment: %s", str(e))
            raise

    def upsert_ai_summary(self, summary_data: Dict) -> Dict:
        """Insert or update an AI summary in the database."""
        try:
            # Serialize datetime objects before sending to Supabase
            summary_data = self._serialize_datetime(summary_data)
            
            # First, check if the target exists
            target_type = summary_data.get("target_type")
            target_id = summary_data.get("target_id")
            
            if not target_type or not target_id:
                raise ValueError("Missing target_type or target_id in summary data")
            
            # Validate target exists before attempting to create summary
            try:
                if target_type == "bill":
                    target = self.client.table("bills").select("id").eq("id", target_id).single().execute()
                elif target_type == "amendment":
                    target = self.client.table("amendments").select("id").eq("id", target_id).single().execute()
                else:
                    raise ValueError(f"Invalid target_type: {target_type}")
                
                if not target.data:
                    raise ValueError(f"Target {target_type} with ID {target_id} does not exist in the database")
            except Exception as e:
                logger.error(f"Error validating {target_type} existence: {str(e)}")
                raise ValueError(f"Failed to validate {target_type} existence: {str(e)}")
            
            # Then, insert/update the AI summary
            result = self.client.table("ai_summaries").upsert(
                summary_data,
                on_conflict="target_id,target_type"
            ).execute()
            
            if result.data:
                logger.info("Successfully upserted AI summary for %s %s", target_type, target_id)
                return result.data[0]
            else:
                raise Exception("No data returned from AI summary upsert")
        except Exception as e:
            logger.error("Error upserting AI summary: %s", str(e))
            raise

    def update_processing_status(self, status_data: Dict) -> Dict:
        """Update the processing status of a bill or amendment."""
        try:
            # Serialize datetime objects before sending to Supabase
            status_data = self._serialize_datetime(status_data)
            
            # First, check if the target exists
            target_type = status_data.get("target_type")
            target_id = status_data.get("target_id")
            
            if target_type == "bill":
                target = self.client.table("bills").select("id").eq("id", target_id).single().execute()
            else:  # target_type == "amendment"
                target = self.client.table("amendments").select("id").eq("id", target_id).single().execute()
            
            if not target.data:
                raise Exception(f"Target {target_type} with ID {target_id} not found")
            
            # Then, insert/update the processing status
            result = self.client.table("processing_status").upsert(
                status_data,
                on_conflict="target_id,target_type"
            ).execute()
            if result.data:
                logger.info("Successfully updated processing status for %s %s", target_type, target_id)
                return result.data[0]
            else:
                raise Exception("No data returned from processing status upsert")
        except Exception as e:
            logger.error("Error updating processing status: %s", str(e))
            raise

    def get_bills_for_processing(self, limit: int = 100) -> List[Dict]:
        """Get bills that need to be processed or updated."""
        try:
            result = (self.client.table("bills")
                    .select("*")
                    .order("updated_at", desc=True)
                    .limit(limit)
                    .execute())
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting bills for processing: {str(e)}")
            raise

    def get_amendments_for_processing(self, limit: int = 100) -> List[Dict]:
        """Get amendments that need to be processed or updated."""
        try:
            result = (self.client.table("amendments")
                    .select("*")
                    .order("updated_at", desc=True)
                    .limit(limit)
                    .execute())
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting amendments for processing: {str(e)}")
            raise

    def get_bill_with_summaries(self, congress: int, bill_type: str, bill_number: int) -> Optional[Dict]:
        """Get a bill with its AI summaries and amendments."""
        try:
            # First, get the bill
            result = (self.client.table("bills")
                    .select("*")
                    .eq("congress_number", congress)
                    .eq("bill_type", bill_type)
                    .eq("bill_number", bill_number)
                    .single()
                    .execute())
            
            if not result.data:
                return None
            
            bill = result.data
            
            # Then, get the AI summaries for the bill
            summaries = (self.client.table("ai_summaries")
                      .select("*")
                      .eq("target_id", bill["id"])
                      .eq("target_type", "bill")
                      .execute())
            
            # Finally, get the amendments for the bill
            amendments = (self.client.table("amendments")
                       .select("*")
                       .eq("bill_id", bill["id"])
                       .execute())
            
            # Combine the results
            bill["ai_summaries"] = summaries.data if summaries.data else []
            bill["amendments"] = amendments.data if amendments.data else []
            
            return bill
        except Exception as e:
            logger.error("Error getting bill with summaries: %s", str(e))
            return None

    def get_amendment_with_summaries(self, congress: int, amendment_type: str, amendment_number: int) -> Optional[Dict]:
        """Get an amendment with its AI summaries."""
        try:
            result = (self.client.table("amendments")
                    .select("*, ai_summaries(*)")
                    .eq("congress_number", congress)
                    .eq("amendment_type", amendment_type)
                    .eq("amendment_number", amendment_number)
                    .single()
                    .execute())
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error getting amendment with summaries: {str(e)}")
            return None

    def get_recent_summaries(self, limit: int = 10) -> List[Dict]:
        """Get the most recent AI summaries with their associated bills or amendments."""
        try:
            # Get the most recent AI summaries
            result = (self.client.table("ai_summaries")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute())
            
            if not result.data:
                return []
            
            # For each summary, get its associated bill or amendment
            summaries = []
            for summary in result.data:
                if summary["target_type"] == "bill":
                    target = (self.client.table("bills")
                           .select("*")
                           .eq("id", summary["target_id"])
                           .single()
                           .execute())
                    if target.data:
                        summary["bill"] = target.data
                else:  # target_type == "amendment"
                    target = (self.client.table("amendments")
                           .select("*")
                           .eq("id", summary["target_id"])
                           .single()
                           .execute())
                    if target.data:
                        summary["amendment"] = target.data
                summaries.append(summary)
            
            return summaries
        except Exception as e:
            logger.error("Error getting recent summaries: %s", str(e))
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