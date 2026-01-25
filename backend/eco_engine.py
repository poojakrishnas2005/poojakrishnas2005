def calculate_eco_score(transactions):
    score = 0
    for t in transactions:
        score += t["amount"] * t["emission_factor"]
    return round(score, 2)
