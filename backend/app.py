from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from models import db, Expense, User
from eco_engine import calculate_eco_score
from collections import defaultdict
from datetime import datetime
import pandas as pd
import numpy as np
import os
from werkzeug.utils import secure_filename
import traceback
import hashlib
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
frontend_path = os.path.join(PROJECT_ROOT, "frontend")
db_path = os.path.join(PROJECT_ROOT, "backend", "eco_wallet.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=frontend_path, static_url_path="")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = os.environ.get('SECRET_KEY', 'enterprise_eco_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Initialize database with app
db.init_app(app)

# Create database tables with app context
with app.app_context():
    try:
        from sqlalchemy import inspect
        db.drop_all()
        db.create_all()
        # Debug: Verify database columns
        inspector = inspect(db.engine)
        if inspector.has_table("expense"):
            columns = [col['name'] for col in inspector.get_columns("expense")]
            print(f"✅ Database Check: 'expense' table columns: {columns}")
    except Exception as e:
        print(f"Error creating database tables: {e}")

def generate_tx_hash(name, amount, category, user_id):
    """Generates a SHA-256 hash for a transaction to check for duplicates."""
    # Ensure consistent data types for hashing
    hash_string = f"{str(name).strip()}-{float(amount)}-{str(category).strip()}-{int(user_id)}"
    return hashlib.sha256(hash_string.encode()).hexdigest()

@app.route("/")
def index():
    if 'user_id' in session:
        return send_from_directory(frontend_path, "index.html")
    return redirect(url_for('login_page'))

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(frontend_path, filename)

@app.route("/login.html")
def login_page():
    return send_from_directory(frontend_path, "login.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    # Simple session-based login (Auto-register for demo purposes)
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
    elif user.password != password:
        return jsonify({"error": "Invalid credentials"}), 401
    
    session['user_id'] = user.id
    return jsonify({"message": "Login successful", "user_id": user.id})

@app.route("/api/logout")
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out"})

@app.route("/eco-score")
def eco_score():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        user_id = session.get('user_id')
        query_result = db.session.query(db.func.sum(Expense.carbon_impact), db.func.sum(Expense.eco_points)).filter(Expense.user_id == int(user_id)).first()
        
        total_impact = query_result[0] or 0.0
        total_points = query_result[1] or 0.0
        
        # The Emergency Brake:
        if total_points > 500:
            total_points = 0.0
            
        return jsonify({
            'eco_score': round(total_impact, 2), 
            'eco_points': round(total_points, 2)
        })
    except Exception as e:
        print(f"Error in eco_score: {e}")
        traceback.print_exc()
        return jsonify({
            "eco_score": 0,
            "eco_points": 0,
            "error": "Failed to calculate score"
        }), 500


@app.route("/api/monthly-expenses")
def monthly_expenses():
    if 'user_id' not in session:
        return jsonify({"labels": [], "values": []})

    monthly_data = defaultdict(float)
    
    try:
        # Fetch all expenses from the database
        all_expenses = Expense.query.filter_by(user_id=session['user_id']).all()
        
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
    if 'user_id' not in session:
        return jsonify({"labels": [], "values": []})

    category_totals = defaultdict(float)
    
    try:
        # Fetch all expenses from the database
        all_expenses = Expense.query.filter_by(user_id=session['user_id']).all()
        
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

@app.route("/api/spending-data")
def spending_data():
    if 'user_id' not in session:
        return jsonify({"labels": [], "values": []})

    spending_totals = defaultdict(float)
    
    try:
        # Use SQLAlchemy to sum amount_in_inr by category
        results = db.session.query(
            Expense.category, 
            db.func.sum(Expense.amount_in_inr)
        ).filter_by(user_id=session['user_id']).group_by(Expense.category).all()
        
        for category, total in results:
            spending_totals[category] = total
    except Exception as e:
        print(f"Error querying database for spending: {e}")
        traceback.print_exc()
        return jsonify({"labels": [], "values": []}), 500
    
    # If no data, return empty
    if not spending_totals:
        return jsonify({"labels": [], "values": []})
    
    labels = list(spending_totals.keys())
    values = list(spending_totals.values())
    
    return jsonify({
        "labels": labels,
        "values": values
    })

@app.route("/api/transactions", methods=['GET', 'POST'])
@app.route("/api/add-transaction", methods=['POST'])
def transactions():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == 'POST':
        # Validate required fields in form data
        if 'itemName' not in request.form or 'amount' not in request.form or 'category' not in request.form:
            return jsonify({"error": "Missing required fields: itemName, amount, category"}), 400
        
        try:
            item_name = request.form['itemName']
            amount = float(request.form['amount'])
            category = request.form['category']
            user_id = session['user_id']

            # Generate hash and check for duplicates
            tx_hash = generate_tx_hash(item_name, amount, category, user_id)
            existing_expense = Expense.query.filter_by(transaction_hash=tx_hash).first()
            if existing_expense:
                return jsonify({"error": "Duplicate transaction detected"}), 409

            # Handle file upload - proof is REQUIRED
            proof_path = None
            if 'proof' in request.files:
                file = request.files['proof']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    # Add timestamp to filename to avoid conflicts
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
                    filename = timestamp + filename
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    proof_path = filename  # Store only the filename, not the full path
            
            # Create new expense
            new_expense = Expense(
                item_name=item_name,
                amount_in_inr=amount,
                category=category,
                carbon_impact=float(request.form.get('carbon_impact', 0.0)),
                eco_points=int(request.form.get('eco_points', 0)),
                proof_path=proof_path,
                user_id=user_id,
                transaction_hash=tx_hash
            )
            
            db.session.add(new_expense)
            db.session.commit()
            
            # Calculate total eco_points
            total_eco_points = db.session.query(db.func.sum(Expense.eco_points)).filter_by(user_id=user_id).scalar() or 0
            
            return jsonify({
                "status": "success",
                "eco_points": total_eco_points,
                "proof_path": proof_path
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400
    
    else:  # GET request
        try:
            all_expenses = Expense.query.filter_by(user_id=session['user_id']).all()
            return jsonify([e.to_dict() for e in all_expenses]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400

# Calculation Engine: Bulk CSV Processor
@app.route("/api/upload-csv", methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Please upload a CSV file"}), 400
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        impact_data = calculate_batch_impact_pandas(file, session['user_id'])
        return jsonify(impact_data)
    except Exception as e:
        print(f"Error in upload_csv: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def calculate_batch_impact_pandas(file_stream, user_id):
    # Read CSV using Pandas
    try:
        df = pd.read_csv(file_stream)
    except Exception as e:
        return {"error": f"Failed to read CSV: {str(e)}"}
    
    # 1. Normalize Columns: Strip whitespace and lowercase
    df.columns = df.columns.str.strip().str.lower()
    
    # 2. Drop the ID column if it exists to prevent database conflicts
    df = df.drop(columns=['id'], errors='ignore')
    
    # 3. Map Column Names (Flexible Mapping)
    # Ensure it looks for 'merchant' -> 'item_name', 'date' -> 'created_at', etc.
    column_mapping = {
        'merchant': 'item_name',
        'date': 'created_at',
        'date_time': 'created_at'
    }
    df.rename(columns=column_mapping, inplace=True)

    # Basic Schema Validation: Allow for flexibility, but need Amount & Category
    if 'amount' not in df.columns or 'category' not in df.columns:
        if 'item_name' not in df.columns:
             return {"error": "CSV must contain 'item_name' (or 'merchant'), 'amount', and 'category'"}

    # Load Baselines
    weights_path = os.path.join(PROJECT_ROOT, "weights.csv")
    baselines = {}
    if os.path.exists(weights_path):
        try:
            baseline_df = pd.read_csv(weights_path)
            baselines = dict(zip(baseline_df['category'].str.lower(), baseline_df['baseline_footprint']))
        except Exception:
            pass

    user_factors = {"food": 0.2, "transport": 0.8, "shopping": 0.4}
    
    # Fetch existing hashes to prevent duplicates
    existing_hashes = {
        res[0] for res in db.session.query(Expense.transaction_hash)
        .filter(Expense.user_id == user_id)
        .all()
    }

    new_expenses = []
    total_impact = 0.0
    total_points = 0.0

    # 4. Loop with Silent Error Handling
    for index, row in df.iterrows():
        try:
            item_name = str(row.get('item_name', 'Unknown')).strip()
            category = str(row.get('category', 'General')).strip()
            
            # Flexible amount parsing (remove currency symbols)
            raw_amount = str(row.get('amount', 0)).replace('$', '').replace(',', '')
            amount = float(raw_amount)
            if amount <= 0: continue

            # Generate Hash
            tx_hash = generate_tx_hash(item_name, amount, category, user_id)
            
            if tx_hash in existing_hashes:
                continue
            
            existing_hashes.add(tx_hash) # Mark as seen

            # Calculation Logic
            cat_lower = category.lower()
            user_factor = user_factors.get(cat_lower, 0.2)
            baseline_factor = baselines.get(cat_lower, 0.5)
            
            footprint = amount * user_factor
            baseline_emission = amount * baseline_factor
            
            raw_saving = max(0, baseline_emission - footprint)
            points = min(1.0, round(raw_saving * 0.0001, 2))
            
            # Optional: Handle date if present
            created_at = datetime.utcnow()
            if 'created_at' in row and pd.notna(row['created_at']):
                try:
                    created_at = pd.to_datetime(row['created_at']).to_pydatetime()
                except:
                    pass # Fallback to utcnow

            # 5. User ID (Explicitly cast as requested)
            new_expense = Expense(
                item_name=item_name,
                amount_in_inr=amount,
                category=category,
                carbon_impact=footprint,
                eco_points=points,
                transaction_hash=tx_hash,
                user_id=int(user_id),
                created_at=created_at
            )
            
            new_expenses.append(new_expense)
            total_impact += footprint
            total_points += points

        except Exception as e:
            # Silent error handling: skip bad rows without crashing
            print(f"Skipping row {index}: {e}")
            continue

    if not new_expenses:
        return {
            "total_impact": 0,
            "eco_points": 0,
            "message": "No new valid transactions found.",
            "breakdown": {"labels": [], "values": []},
            "spending_breakdown": {"labels": [], "values": []}
        }

    # Bulk Save
    db.session.bulk_save_objects(new_expenses)
    db.session.commit()

    # Prepare Response Data
    added_df = pd.DataFrame([{
        'category': e.category,
        'footprint': e.carbon_impact,
        'amount': e.amount_in_inr
    } for e in new_expenses])

    breakdown = added_df.groupby('category')['footprint'].sum()
    spending = added_df.groupby('category')['amount'].sum()
    
    return {
        "total_impact": round(total_impact, 2),
        "eco_points": round(total_points, 2),
        "breakdown": {
            "labels": breakdown.index.tolist(),
            "values": breakdown.values.tolist()
        },
        "spending_breakdown": {
            "labels": spending.index.tolist(),
            "values": spending.values.tolist()
        }
    }

@app.route('/api/debug/reset-db')
def reset_db():
    """Temporary debug route to clear all expenses."""
    try:
        num_rows_deleted = db.session.query(Expense).delete()
        db.session.commit()
        return jsonify({"message": f"Success! Deleted {num_rows_deleted} rows from the Expense table."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to reset database.", "details": str(e)}), 500

if __name__ == "__main__":
    # Get port from environment variable, or default to 5000 for local testing
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' is required for cloud deployment
    app.run(host='0.0.0.0', port=port, debug=False)