import os
import logging
from datetime import datetime
from typing import Dict, Optional, List
import requests
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)

class CongressClient:
    """Client for interacting with the Congress.gov API."""

    def __init__(self, api_key: str = None):
        self.base_url = "https://api.congress.gov/v3"
        self.api_key = api_key or os.getenv("CONGRESS_API_KEY")
        
        if not self.api_key:
            logger.error("Congress.gov API key is required")
            raise ValueError("Congress.gov API key is required")
        
        logger.info("Successfully initialized Congress.gov API client with base URL: %s", self.base_url)

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the Congress.gov API."""
        try:
            # Ensure params dictionary exists
            params = params or {}
            
            # Add API key and format to params
            params.update({
                "api_key": self.api_key,
                "format": "json"
            })
            
            url = f"{self.base_url}/{endpoint}"
            logger.info("Making request to Congress.gov API: %s with params: %s", url, {k: v for k, v in params.items() if k != 'api_key'})
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info("Successfully received response from Congress.gov API for endpoint: %s", endpoint)
            logger.debug("Response data: %s", data)
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching data from Congress.gov: %s", str(e))
            logger.error("Failed URL: %s", url)
            logger.error("Response status code: %s", getattr(e.response, 'status_code', 'N/A'))
            logger.error("Response text: %s", getattr(e.response, 'text', 'N/A'))
            raise

    def get_recent_bills(self, congress: int, limit: int = 20) -> Dict:
        """Get recent bills for a specific Congress."""
        logger.info("Fetching recent bills for Congress %d with limit %d", congress, limit)
        return self._make_request(f"bill/{congress}", {"limit": limit})

    def get_bill_details(self, congress: int, bill_type: str, bill_number: int) -> Dict:
        """Get detailed information about a specific bill."""
        logger.info("Fetching details for bill %s%d in Congress %d", bill_type, bill_number, congress)
        return self._make_request(f"bill/{congress}/{bill_type}/{bill_number}")

    def get_bill_amendments(self, congress: int, bill_type: str, bill_number: str) -> Optional[List[Dict]]:
        """Fetch all amendments for a specific bill."""
        logger.info("Fetching amendments for bill %s%s in Congress %d", bill_type, bill_number, congress)
        # First, fetch the bill details to get amendment links or identifiers
        bill_endpoint = f"bill/{congress}/{bill_type.lower()}/{bill_number}"
        try:
            bill_response = self._make_request(bill_endpoint)
            bill_data = bill_response.get("bill", {})
            amendments = bill_data.get("amendments", [])
            
            if not amendments:
                logger.info("No amendments found for bill %s%s in Congress %d", bill_type, bill_number, congress)
                return []

            amendment_details = []
            for amendment in amendments:
                amendment_type = amendment.get("type")
                amendment_number = amendment.get("number")
                if not (amendment_type and amendment_number):
                    logger.warning("Amendment missing type or number: %s", amendment)
                    continue
                amendment_endpoint = f"amendment/{congress}/{amendment_type}/{amendment_number}"
                try:
                    amendment_response = self._make_request(amendment_endpoint)
                    amendment_data = amendment_response.get("amendment", {})
                    amendment_details.append(amendment_data)
                except HTTPError as http_err:
                    if http_err.response.status_code == 404:
                        logger.warning("Amendment %s%s not found in Congress %d", amendment_type, amendment_number, congress)
                        continue
                    else:
                        logger.error("HTTP error occurred while fetching amendment %s%s: %s",
                                     amendment_type, amendment_number, http_err)
                        continue
                except Exception as err:
                    logger.error("An error occurred while fetching amendment %s%s: %s",
                                 amendment_type, amendment_number, err)
                    continue

            return amendment_details

        except HTTPError as http_err:
            if http_err.response.status_code == 404:
                logger.warning("Bill %s%s not found in Congress %d", bill_type, bill_number, congress)
                return None
            else:
                logger.error("HTTP error occurred while fetching bill %s%s: %s", bill_type, bill_number, http_err)
                return None
        except Exception as err:
            logger.error("An error occurred while fetching bill %s%s: %s", bill_type, bill_number, err)
            return None

    def get_amendment_details(self, congress: int, amendment_type: str, amendment_number: int) -> Dict:
        """Get detailed information about a specific amendment."""
        logger.info("Fetching details for amendment %s%d in Congress %d", amendment_type, amendment_number, congress)
        return self._make_request(f"amendment/{congress}/{amendment_type}/{amendment_number}")

    def get_updates_since(self, since_date: datetime) -> Dict:
        """Get bills and amendments updated since a specific date."""
        formatted_date = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info("Fetching updates since %s", formatted_date)
        return self._make_request("bill", {"fromDateTime": formatted_date}) 