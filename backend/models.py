from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib # 1. ADD THIS IMPORT

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Expense(db.Model):
    __tablename__ = 'expense'
    
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    amount_in_inr = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    
    # 2. ADD THIS COLUMN (unique=True is the "security guard" part)
    transaction_hash = db.Column(db.String(64), unique=True, nullable=False)
    
    carbon_impact = db.Column(db.Float, default=0.0)
    eco_points = db.Column(db.Float, default=0.0)
    proof_path = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # 3. ADD THIS METHOD (to create the hash from data)
    @staticmethod
    def generate_hash(name, amount, category, date_str):
        hash_string = f"{name}-{amount}-{category}-{date_str}"
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def to_dict(self):
        return {
            'id': self.id,
            'item_name': self.item_name,
            'amount_in_inr': self.amount_in_inr,
            'category': self.category,
            'carbon_impact': self.carbon_impact,
            'eco_points': self.eco_points,
            'proof_path': self.proof_path,
            'transaction_hash': self.transaction_hash, # Optional: include in dict
            'created_at': self.created_at.isoformat()
                }