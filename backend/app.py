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

# Get the absolute path to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
frontend_path = os.path.join(PROJECT_ROOT, "frontend")
db_path = os.path.join(PROJECT_ROOT, "backend", "eco_wallet.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=frontend_path, static_url_path="/static")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = os.environ.get('SECRET_KEY', 'enterprise_eco_secret_key') # Required for session management

# Configure CORS properly
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})


# Database configuration with absolute path
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with app
db.init_app(app)

# Create database tables with app context
with app.app_context():
    try:
        from sqlalchemy import inspect
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
        # 1. Fetch all real expenses from the database
        all_expenses = Expense.query.filter_by(user_id=session['user_id']).all()
        
        # 2. If no expenses, return default score
        if not all_expenses:
            return jsonify({
                "eco_score": 100,
                "eco_points": 0,
                "count": 0,
                "message": "No transactions yet. Start by adding expenses!"
            })
        
        # 3. Convert database data into the format the engine needs
        # Define emission factors
        factors = {"transport": 0.8, "food": 0.2, "shopping": 0.4}
        
        transactions = []
        for e in all_expenses:
            cat_key = e.category.lower() if e.category else ""
            factor = factors.get(cat_key, 0.2) # Default to 0.2 if unknown
            transactions.append({"amount": e.amount_in_inr, "emission_factor": factor, "category": e.category})

        # 4. Calculate the score based on REAL data
        score, points = calculate_eco_score(transactions)

        return jsonify({
            "eco_score": score,
            "eco_points": points,
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
    df = pd.read_csv(file_stream)
    
    # Normalize column names to lower case for easier matching
    df.columns = [c.lower().replace(' ', '_') for c in df.columns]
    
    if 'item_name' not in df.columns or 'amount' not in df.columns or 'category' not in df.columns:
        raise ValueError("CSV must contain 'item_name', 'amount', and 'category' columns")

    # Generate a hash for each row to identify duplicates
    df['transaction_hash'] = df.apply(
        lambda row: generate_tx_hash(row['item_name'], row['amount'], row['category'], user_id),
        axis=1
    )

    # Find which transactions already exist in the database for this user
    existing_hashes = {
        res[0] for res in db.session.query(Expense.transaction_hash)
        .filter(Expense.user_id == user_id)
        .filter(Expense.transaction_hash.in_(df['transaction_hash'].tolist()))
        .all()
    }

    # Filter the DataFrame to get only the new transactions
    new_df = df[~df['transaction_hash'].isin(existing_hashes)].copy()

    if new_df.empty:
        return {
            "total_impact": 0,
            "eco_points": 0,
            "message": "No new transactions to add. All entries were duplicates.",
            "breakdown": {"labels": [], "values": []},
            "spending_breakdown": {"labels": [], "values": []}
        }

    # --- Continue with calculations ONLY on the new_df ---
    # Load Baselines from weights.csv
    weights_path = os.path.join(PROJECT_ROOT, "weights.csv")
    baselines = {}
    if os.path.exists(weights_path):
        try:
            baseline_df = pd.read_csv(weights_path)
            baselines = dict(zip(baseline_df['category'].str.lower(), baseline_df['baseline_footprint']))
        except Exception as e:
            print(f"Error reading weights.csv: {e}")
    
    user_factors = {"food": 0.2, "transport": 0.8, "shopping": 0.4}
    
    new_df['category_lower'] = new_df['category'].astype(str).str.lower()
    new_df['user_factor'] = new_df['category_lower'].map(user_factors).fillna(0.2)
    new_df['baseline_factor'] = new_df['category_lower'].map(baselines).fillna(0.5)

    new_df['footprint'] = new_df['amount'] * new_df['user_factor']

    DIFFICULTY_SCALAR = 0.01
    new_df['baseline_emission'] = new_df['amount'] * new_df['baseline_factor']
    raw_carbon_saving = (new_df['baseline_emission'] - new_df['footprint']).clip(lower=0)
    new_df['points'] = np.log1p(raw_carbon_saving) * DIFFICULTY_SCALAR

    # Save new transactions to the database
    new_expenses = []
    for _, row in new_df.iterrows():
        new_expenses.append(Expense(
            item_name=row['item_name'], amount_in_inr=row['amount'], category=row['category'],
            carbon_impact=row['footprint'], eco_points=row['points'],
            transaction_hash=row['transaction_hash'], user_id=user_id
        ))
    db.session.bulk_save_objects(new_expenses)
    db.session.commit()

    total_impact = float(new_df['footprint'].sum())
    total_points = float(new_df['points'].sum())
    breakdown = new_df.groupby('category')['footprint'].sum()
    spending = new_df.groupby('category')['amount'].sum()
    
    return {
        "total_impact": total_impact,
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

if __name__ == "__main__":
    # Get port from environment variable, or default to 5000 for local testing
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' is required for cloud deployment
    app.run(host='0.0.0.0', port=port, debug=False)