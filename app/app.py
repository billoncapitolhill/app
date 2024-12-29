from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from datetime import datetime
import requests

# Load environment variables
load_dotenv()

# Initialize SQLAlchemy without binding to app
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bills.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'connect_args': {
            'sslmode': 'require'
        }
    }
    
    # Initialize extensions
    db.init_app(app)

    # Models
    class Bill(db.Model):
        id = db.Column(db.String(50), primary_key=True)
        title = db.Column(db.String(500))
        summary = db.Column(db.Text)
        sponsor = db.Column(db.String(200))
        status = db.Column(db.String(100))
        introduced_date = db.Column(db.DateTime)
        last_updated = db.Column(db.DateTime)
        category = db.Column(db.String(100))
        house_status = db.Column(db.String(100))
        senate_status = db.Column(db.String(100))
        next_vote_date = db.Column(db.DateTime)
        last_action = db.Column(db.String(500))
        
        def to_dict(self):
            return {
                'id': self.id,
                'title': self.title,
                'summary': self.summary,
                'sponsor': self.sponsor,
                'status': self.status,
                'introduced_date': self.introduced_date.isoformat() if self.introduced_date else None,
                'last_updated': self.last_updated.isoformat() if self.last_updated else None,
                'category': self.category,
                'house_status': self.house_status,
                'senate_status': self.senate_status,
                'next_vote_date': self.next_vote_date.isoformat() if self.next_vote_date else None,
                'last_action': self.last_action
            }

    # Routes
    @app.route('/api/bills', methods=['GET'])
    def get_bills():
        category = request.args.get('category')
        status = request.args.get('status')
        
        query = Bill.query
        
        if category:
            query = query.filter_by(category=category)
        if status:
            query = query.filter_by(status=status)
            
        bills = query.all()
        print(f"Retrieved {len(bills)} bills from database")  # Debug log
        return jsonify([bill.to_dict() for bill in bills])

    @app.route('/api/bills/<bill_id>', methods=['GET'])
    def get_bill(bill_id):
        bill = Bill.query.get_or_404(bill_id)
        return jsonify(bill.to_dict())

    @app.route('/api/bills/search', methods=['GET'])
    def search_bills():
        query = request.args.get('q', '')
        bills = Bill.query.filter(Bill.title.ilike(f'%{query}%')).all()
        return jsonify([bill.to_dict() for bill in bills])

    @app.route('/bills', methods=['GET'])
    def display_bills():
        bills = Bill.query.all()
        return jsonify([bill.to_dict() for bill in bills])

    @app.route('/api/bills/fetch', methods=['POST'])
    def trigger_fetch_bills():
        try:
            fetch_and_store_bills()
            return jsonify({"message": "Bills fetched and stored successfully"}), 200
        except Exception as e:
            print(f"Error in fetch_bills: {str(e)}")
            return jsonify({"error": str(e)}), 500

    with app.app_context():
        db.create_all()
        # Check if database is empty and fetch initial data
        if Bill.query.count() == 0:
            print("Database is empty, fetching initial bills...")
            fetch_and_store_bills()

    return app

app = create_app()

if __name__ == '__main__':
    app.run() 

def fetch_congress_data():
    # Correct endpoint for fetching bills
    url = 'https://api.congress.gov/v3/bill'
    headers = {
        'Authorization': f'Bearer {os.getenv("CONGRESS_API_KEY")}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching data: {e}")
        return None

def update_bills_from_congress():
    try:
        api_data = fetch_congress_data()
        bills = parse_bill_data(api_data)
        store_bills_in_db(bills)
        print("Bills updated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}") 

def fetch_and_store_bills():
    base_url = "https://api.congress.gov/v3"
    endpoint = "/bill"
    url = f"{base_url}{endpoint}"
    
    api_key = os.getenv("CONGRESS_API_KEY")
    if not api_key:
        print("Error: CONGRESS_API_KEY environment variable not set")
        return
        
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    
    try:
        print(f"Fetching bills from {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # This will raise an exception for 4XX/5XX status codes
        
        bills_data = response.json()
        if not bills_data.get('bills'):
            print("Warning: No bills found in API response")
            return
            
        print(f"Retrieved {len(bills_data['bills'])} bills from API")
        
        for bill in bills_data.get('bills', []):
            try:
                # Assuming 'bills' is the key in the JSON response
                # Create or update Bill objects in the database
                bill_obj = Bill(
                    id=bill['bill_id'],
                    title=bill['title'],
                    summary=bill.get('summary', ''),
                    sponsor=bill.get('sponsor', ''),
                    status=bill.get('status', ''),
                    introduced_date=datetime.strptime(bill['introduced_date'], '%Y-%m-%d'),
                    last_updated=datetime.strptime(bill['last_updated'], '%Y-%m-%d'),
                    category=bill.get('category', ''),
                    house_status=bill.get('house_status', ''),
                    senate_status=bill.get('senate_status', ''),
                    next_vote_date=datetime.strptime(bill['next_vote_date'], '%Y-%m-%d') if bill.get('next_vote_date') else None,
                    last_action=bill.get('last_action', '')
                )
                db.session.merge(bill_obj)
                
            except KeyError as e:
                print(f"Error processing bill: Missing required field {str(e)}")
                continue
            except ValueError as e:
                print(f"Error processing bill: Invalid date format - {str(e)}")
                continue
                
        db.session.commit()
        print("Bills fetched and stored successfully.")
        
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        db.session.rollback()
        raise