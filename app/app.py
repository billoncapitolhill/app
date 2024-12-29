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

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run() 

def fetch_congress_data():
    url = 'https://api.congress.gov/v3/some-endpoint'
    headers = {
        'Authorization': f'Bearer {CONGRESS_API_KEY}'
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    return data 

def update_bills_from_congress():
    try:
        api_data = fetch_congress_data()
        bills = parse_bill_data(api_data)
        store_bills_in_db(bills)
        print("Bills updated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}") 