from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Expense(db.Model):
    __tablename__ = 'expense'
    
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    amount_in_inr = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    carbon_impact = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'item_name': self.item_name,
            'amount_in_inr': self.amount_in_inr,
            'category': self.category,
            'carbon_impact': self.carbon_impact,
            'created_at': self.created_at.isoformat()
        }
