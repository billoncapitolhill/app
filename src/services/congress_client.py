import os
from datetime import datetime
from typing import Dict, List, Optional, Union

import requests
from requests.exceptions import RequestException

class CongressClient:
    """Client for interacting with the Congress.gov API."""
    
    def __init__(self, api_key: str = None):
        self.base_url = "https://api.congress.gov/v3"
        self.api_key = api_key or os.getenv("CONGRESS_API_KEY")
        if not self.api_key:
            raise ValueError("Congress.gov API key is required")
        
        self.session = requests.Session()
        self.session.params = {"format": "json"}
        self.session.headers.update({"X-API-Key": self.api_key})

    def _make_request(self, endpoint: str) -> Dict:
        """Make a request to the Congress.gov API."""
        try:
            response = self.session.get(f"{self.base_url}/{endpoint}")
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            raise Exception(f"Error fetching data from Congress.gov: {str(e)}")

    def get_recent_bills(self, congress: int, bill_type: Optional[str] = None) -> List[Dict]:
        """Get recent bills from Congress.gov."""
        endpoint = f"bill/{congress}"
        if bill_type:
            endpoint = f"{endpoint}/{bill_type}"
        return self._make_request(endpoint)

    def get_bill_details(self, congress: int, bill_type: str, bill_number: int) -> Dict:
        """Get detailed information about a specific bill."""
        endpoint = f"bill/{congress}/{bill_type}/{bill_number}"
        return self._make_request(endpoint)

    def get_bill_amendments(self, congress: int, bill_type: str, bill_number: int) -> List[Dict]:
        """Get amendments for a specific bill."""
        endpoint = f"bill/{congress}/{bill_type}/{bill_number}/amendments"
        return self._make_request(endpoint)

    def get_amendment_details(self, congress: int, amendment_type: str, amendment_number: int) -> Dict:
        """Get detailed information about a specific amendment."""
        endpoint = f"amendment/{congress}/{amendment_type}/{amendment_number}"
        return self._make_request(endpoint)

    def get_updates_since(self, date: Union[datetime, str]) -> List[Dict]:
        """Get bills and amendments updated since the given date."""
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        endpoint = f"bill?fromDateTime={date}"
        return self._make_request(endpoint) 