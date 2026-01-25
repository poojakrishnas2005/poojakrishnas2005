
import csv
import os

# Get the absolute path to the project root
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
weights_csv = os.path.join(PROJECT_ROOT, "weights.csv")
transactions_csv = os.path.join(PROJECT_ROOT, "transactions.csv")
public_dir = os.path.join(PROJECT_ROOT, "public")
output_html = os.path.join(public_dir, "output.html")

weights = {}

with open(weights_csv, newline='') as file:
    reader = csv.DictReader(file)
    for row in reader:
        weights[row["category"]] = float(row["weight"])

total_score = 0

with open(transactions_csv, newline='') as file:
    reader = csv.DictReader(file)
    for row in reader:
        amount = float(row["amount"])
        category = row["category"]
        score = amount * weights[category]
        total_score += score

# Ensure public folder exists
os.makedirs(public_dir, exist_ok=True)

with open(output_html, "w", encoding="utf-8") as f:

    f.write(f"""
    <html>
    <head>
        <title>Eco Wallet Result</title>
    </head>
    <body style="font-family: Arial; text-align:center; margin-top:50px;">
        <h1>🌱 Eco Wallet</h1>
        <h2>Your Eco Impact Score</h2>
        <h1 style="color:green;">{total_score}</h1>
    </body>
    </html>
    """)

print("Output generated successfully!")
