from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
import requests
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bills.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'sponsor': self.sponsor,
            'status': self.status,
            'introduced_date': self.introduced_date.isoformat() if self.introduced_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'category': self.category
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 