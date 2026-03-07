import numpy as np
import os
import csv

def load_baselines():
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

def calculate_eco_score(transactions):
    baselines = load_baselines()
    total_footprint = 0
    total_points = 0

    for t in transactions:
        amount = t.get("amount", 0.0)
        factor = t.get("emission_factor", 0.2)
        category = str(t.get("category", "")).lower()

        # 1. Calculate Carbon Footprint
        footprint = amount * factor
        total_footprint += footprint

        # 2. Calculate Eco Reward Points
        # Benchmark Comparison: Get baseline factor for category
        baseline_factor = baselines.get(category, 0.0)
        baseline_emission = amount * baseline_factor
        
        # Formula: max(0, (baseline - carbon_footprint)) * log1p(amount)
        if baseline_emission > footprint:
            points = (baseline_emission - footprint) * np.log1p(amount)
            total_points += points

    return round(total_footprint, 2), round(total_points, 2)
