import requests
import os
from datetime import datetime
from typing import Dict, List, Optional

class CongressAPI:
    def __init__(self):
        self.base_url = "https://api.congress.gov/v3"
        self.api_key = os.getenv('CONGRESS_API_KEY')
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the Congress.gov API"""
        if params is None:
            params = {}
            
        params['api_key'] = self.api_key
        
        response = requests.get(f"{self.base_url}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_recent_bills(self, limit: int = 20) -> List[Dict]:
        """Get recent bills from Congress.gov"""
        try:
            response = self._make_request('bill', {
                'limit': limit,
                'format': 'json'
            })
            
            bills = []
            for bill in response.get('bills', []):
                processed_bill = {
                    'id': bill.get('billNumber'),
                    'title': bill.get('title'),
                    'summary': bill.get('summary', {}).get('text'),
                    'sponsor': bill.get('sponsor', {}).get('name'),
                    'status': bill.get('latestAction', {}).get('text'),
                    'introduced_date': datetime.strptime(
                        bill.get('introducedDate', ''), 
                        '%Y-%m-%d'
                    ) if bill.get('introducedDate') else None,
                    'last_updated': datetime.now(),
                    'category': self._categorize_bill(bill.get('title', ''))
                }
                bills.append(processed_bill)
                
            return bills
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching bills: {str(e)}")
            return []
            
    def _categorize_bill(self, title: str) -> str:
        """Simple categorization based on keywords in the title"""
        categories = {
            'healthcare': ['health', 'medical', 'medicare', 'medicaid'],
            'education': ['education', 'school', 'student', 'learning'],
            'environment': ['environment', 'climate', 'energy', 'pollution'],
            'economy': ['tax', 'budget', 'economic', 'finance'],
            'security': ['defense', 'security', 'military', 'veterans']
        }
        
        title_lower = title.lower()
        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
                
        return 'other'
        
    def get_bill_details(self, bill_id: str) -> Optional[Dict]:
        """Get detailed information about a specific bill"""
        try:
            response = self._make_request(f'bill/{bill_id}')
            bill = response.get('bill', {})
            
            return {
                'id': bill.get('billNumber'),
                'title': bill.get('title'),
                'summary': bill.get('summary', {}).get('text'),
                'sponsor': bill.get('sponsor', {}).get('name'),
                'status': bill.get('latestAction', {}).get('text'),
                'introduced_date': datetime.strptime(
                    bill.get('introducedDate', ''), 
                    '%Y-%m-%d'
                ) if bill.get('introducedDate') else None,
                'last_updated': datetime.now(),
                'category': self._categorize_bill(bill.get('title', '')),
                'full_text_url': bill.get('textVersions', [{}])[0].get('url'),
                'actions': bill.get('actions', [])
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching bill details: {str(e)}")
            return None 