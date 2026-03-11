import numpy as np
import os
import csv

def load_baselines():
    """Loads baseline footprints from weights.csv"""
    baselines = {}
    try:
        # Assuming weights.csv is in the project root (parent of backend)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, 'weights.csv')
        if os.path.exists(csv_path):
            with open(csv_path, mode='r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    baselines[row['category'].lower()] = float(row['baseline_footprint'])
    except Exception as e:
        print(f"Error loading baselines: {e}")
    return baselines

def calculate_impact(item_name, amount, category, baselines=None):
    """Calculates carbon footprint and eco points for a single transaction."""
    if baselines is None:
        baselines = load_baselines()
    
    item_lower = str(item_name).lower()
    cat_lower = str(category).lower().strip()
    amount = float(amount)

    # Hardcoded user factors (could be moved to config)
    user_factors = {"food": 0.2, "transport": 0.8, "shopping": 0.4}
    user_factor = user_factors.get(cat_lower, 0.2)
    
    # 1. Carbon Footprint
    footprint = amount * user_factor

    # 2. Eco Points Calculation
    baseline_factor = baselines.get(cat_lower, 0.5)
    baseline_emission = amount * baseline_factor
    
    raw_saving = max(0, baseline_emission - footprint)
    # Initial points based on saving
    points = round(raw_saving * 0.0001, 2)

    # Rule 1: Sustainable keywords bonus
    if any(k in item_lower for k in ['organic', 'farmers', 'thrift']):
        points += 0.2

    # Rule 2: Minimum reward for low-carbon ratio (< 25% of amount)
    if footprint < (0.25 * amount) and points < 0.1:
        points = 0.1

    return round(footprint, 2), round(points, 2)

def calculate_eco_score(transactions):
    baselines = load_baselines()
    return 0.0, 0.0
