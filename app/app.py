from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from datetime import datetime
import requests
import time
import logging
from sqlalchemy import text
import socket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize SQLAlchemy without binding to app
db = SQLAlchemy()

def get_database_url():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable is not set")
        return None
        
    # If the URL starts with postgres://, replace it with postgresql://
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        # Add SSL parameters
        if '?' not in db_url:
            db_url += '?'
        elif not db_url.endswith('&') and not db_url.endswith('?'):
            db_url += '&'
            
        ssl_params = [
            'sslmode=require',
            'application_name=bill-tracker',
            'client_encoding=utf8',
            'connect_timeout=10'
        ]
        
        for param in ssl_params:
            if param.split('=')[0] not in db_url:
                db_url += param + '&'
        
        if db_url.endswith('&'):
            db_url = db_url[:-1]
            
    except Exception as e:
        logger.error(f"Error configuring database URL: {str(e)}")
        
    # Log the final URL (without credentials)
    safe_url = db_url.split('@')[1] if '@' in db_url else 'unknown'
    logger.info(f"Final database connection string: ...@{safe_url}")
    return db_url

def test_db_connection(db_url):
    try:
        # Parse the URL to get host and port
        parts = db_url.split('@')[1].split('/')[0].split(':')
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 5432
        
        # Try to create a socket connection
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        logger.info(f"TCP connection to {host}:{port} successful")
        return True
    except Exception as e:
        logger.error(f"TCP connection failed: {str(e)}")
        return False

def wait_for_db(app, max_retries=5, retry_interval=5):
    retries = 0
    while retries < max_retries:
        try:
            logger.info(f"Attempting database connection (attempt {retries + 1}/{max_retries})")
            
            # First test raw TCP connection
            db_url = get_database_url()
            if db_url and not test_db_connection(db_url):
                raise Exception("Cannot establish TCP connection to database")
            
            with app.app_context():
                db.create_all()
                # Test the connection with a simple query using proper SQLAlchemy syntax
                db.session.execute(text('SELECT 1'))
                db.session.commit()
                logger.info("Database connection successful")
                return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            retries += 1
            if retries < max_retries:
                logger.info(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
    logger.error("Failed to connect to database after maximum retries")
    return False

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Database configuration
    db_url = get_database_url()
    if not db_url:
        logger.error("Failed to get database URL")
        # Use SQLite as fallback
        db_url = 'sqlite:///bills.db'
        logger.info("Using SQLite as fallback database")

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,  # Enable connection health checks
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'connect_args': {
            'sslmode': 'require',  # Changed from verify-full to require
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'client_encoding': 'utf8',
            'application_name': 'bill-tracker',
            'options': '-c timezone=UTC'
        }
    }

    # Initialize extensions
    db.init_app(app)

    @app.before_request
    def before_request():
        try:
            # Verify database connection before each request
            db.session.execute(text('SELECT 1'))
            db.session.commit()
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            db.session.rollback()
            return jsonify({
                "error": "Database connection error",
                "details": str(e)
            }), 500

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

    @app.route('/api/health', methods=['GET'])
    def health_check():
        try:
            # Get database URL for connection testing
            db_url = get_database_url()
            tcp_connection = test_db_connection(db_url) if db_url else False
            
            # Test database query
            db.session.execute(text('SELECT 1')).scalar()
            db.session.commit()
            
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "database_url": db_url.split('@')[1] if db_url else "not configured",
                "tcp_connection": "successful" if tcp_connection else "failed"
            })
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "database_url": get_database_url().split('@')[1] if get_database_url() else "not configured",
                "tcp_connection": "failed"
            }), 500

    @app.route('/api/health/connection', methods=['GET'])
    def connection_test():
        try:
            db_url = get_database_url()
            if not db_url:
                return jsonify({
                    "status": "error",
                    "message": "DATABASE_URL not configured"
                }), 500

            # Parse connection details
            host = db_url.split('@')[1].split('/')[0].split(':')[0]
            
            # Basic DNS test
            try:
                ip_addr = socket.gethostbyname(host)
                dns_status = "success"
                dns_ip = ip_addr
            except socket.gaierror as e:
                dns_status = "failed"
                dns_ip = str(e)

            # TCP connection test
            try:
                sock = socket.create_connection((host, 5432), timeout=5)
                sock.close()
                tcp_status = "success"
            except Exception as e:
                tcp_status = f"failed: {str(e)}"

            # Database query test
            try:
                result = db.session.execute(text('SELECT version()')).scalar()
                db.session.commit()
                db_status = "success"
                db_version = result
            except Exception as e:
                db_status = f"failed: {str(e)}"
                db_version = None

            return jsonify({
                "status": "complete",
                "tests": {
                    "dns_resolution": {
                        "status": dns_status,
                        "resolved_ip": dns_ip
                    },
                    "tcp_connection": {
                        "status": tcp_status,
                        "port": 5432
                    },
                    "database_query": {
                        "status": db_status,
                        "version": db_version
                    }
                }
            })
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500

    # Initialize database
    if not wait_for_db(app):
        logger.warning("Application starting without database connection")
    
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