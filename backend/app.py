from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from models import db, Expense
from eco_engine import calculate_eco_score
from collections import defaultdict
from datetime import datetime
import os

# Get the absolute path to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
frontend_path = os.path.join(PROJECT_ROOT, "frontend")
db_path = os.path.join(PROJECT_ROOT, "backend", "eco_wallet.db")

app = Flask(__name__, static_folder=frontend_path, static_url_path="/static")

# Configure CORS properly
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})


# Database configuration with absolute path
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with app
db.init_app(app)

# Create database tables with app context
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Error creating database tables: {e}")

@app.route("/")
def index():
    return send_from_directory(frontend_path, "index.html")

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(frontend_path, filename)

@app.route("/eco-score")
def eco_score():
    try:
        # 1. Fetch all real expenses from the database
        all_expenses = Expense.query.all()
        
        # 2. If no expenses, return default score
        if not all_expenses:
            return jsonify({
                "eco_score": 100,
                "count": 0,
                "message": "No transactions yet. Start by adding expenses!"
            })
        
        # 3. Convert database data into the format the engine needs
        # We'll use a default emission factor of 0.2 for now
        transactions = [
            {"amount": e.amount_in_inr, "emission_factor": 0.2} 
            for e in all_expenses
        ]

        # 4. Calculate the score based on REAL data
        score = calculate_eco_score(transactions)

        return jsonify({
            "eco_score": score,
            "count": len(transactions)
        })
    except Exception as e:
        print(f"Error calculating eco score: {e}")
        return jsonify({
            "eco_score": 100,
            "count": 0,
            "error": str(e)
        }), 500


@app.route("/api/monthly-expenses")
def monthly_expenses():
    monthly_data = defaultdict(float)
    
    try:
        # Fetch all expenses from the database
        all_expenses = Expense.query.all()
        
        # Group expenses by month
        for expense in all_expenses:
            month_key = expense.created_at.strftime("%Y-%m")
            monthly_data[month_key] += expense.amount_in_inr
    except Exception as e:
        print(f"Error querying database: {e}")
        return jsonify({"labels": [], "values": []})
    
    sorted_months = sorted(monthly_data.keys())
    labels = [datetime.strptime(m, "%Y-%m").strftime("%b %y") for m in sorted_months]
    values = [monthly_data[m] for m in sorted_months]
    
    return jsonify({
        "labels": labels,
        "values": values
    })

@app.route("/api/category-data")
def category_data():
    category_totals = defaultdict(float)
    
    try:
        # Fetch all expenses from the database
        all_expenses = Expense.query.all()
        
        # Group by category and sum carbon impact
        for expense in all_expenses:
            category_totals[expense.category] += expense.carbon_impact
    except Exception as e:
        print(f"Error querying database for categories: {e}")
        return jsonify({"labels": [], "values": []}), 500
    
    # If no data, return empty
    if not category_totals:
        return jsonify({"labels": [], "values": []})
    
    labels = list(category_totals.keys())
    values = list(category_totals.values())
    
    return jsonify({
        "labels": labels,
        "values": values
    })

@app.route("/api/transactions", methods=['GET', 'POST'])
def transactions():
    if request.method == 'POST':
        data = request.get_json()
        
        # Validate required fields
        if not data or not all(k in data for k in ['item_name', 'amount_in_inr', 'category']):
            return jsonify({"error": "Missing required fields: item_name, amount_in_inr, category"}), 400
        
        try:
            # Create new expense
            new_expense = Expense(
                item_name=data['item_name'],
                amount_in_inr=float(data['amount_in_inr']),
                category=data['category'],
                carbon_impact=float(data.get('carbon_impact', 0.0))
            )
            
            db.session.add(new_expense)
            db.session.commit()
            
            return jsonify(new_expense.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400
    
    else:  # GET request
        try:
            all_expenses = Expense.query.all()
            return jsonify([e.to_dict() for e in all_expenses]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)