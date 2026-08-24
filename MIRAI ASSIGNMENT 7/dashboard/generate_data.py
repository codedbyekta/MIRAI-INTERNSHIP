"""
generate_data.py
Generates a realistic 14-day synthetic screen-time dataset for the
Life-OS Wellbeing Dashboard and saves it as screentime.csv.

Run once with: python generate_data.py
(Not required at runtime -- screentime.csv is already committed,
this script just documents/reproduces how it was built.)
"""

import random
import pandas as pd
from datetime import datetime, timedelta

random.seed(42)

# App -> Category mapping
APPS = {
    "Instagram": "Social Media",
    "WhatsApp": "Social Media",
    "Twitter/X": "Social Media",
    "YouTube": "Entertainment",
    "Netflix": "Entertainment",
    "Spotify": "Entertainment",
    "VS Code": "Coding",
    "GitHub": "Coding",
    "LeetCode": "Education",
    "Coursera": "Education",
    "Gmail": "Productivity",
    "Google Docs": "Productivity",
}

# Baseline average minutes/day per app (roughly realistic), with weekday/weekend variation
BASELINE = {
    "Instagram": 55,
    "WhatsApp": 40,
    "Twitter/X": 25,
    "YouTube": 70,
    "Netflix": 35,
    "Spotify": 30,
    "VS Code": 90,
    "GitHub": 20,
    "LeetCode": 35,
    "Coursera": 15,
    "Gmail": 15,
    "Google Docs": 20,
}

start_date = datetime(2026, 8, 10)
rows = []

for day_offset in range(14):
    date = start_date + timedelta(days=day_offset)
    is_weekend = date.weekday() >= 5  # Sat/Sun

    for app, base in BASELINE.items():
        category = APPS[app]
        minutes = base

        # Weekend behavior: more entertainment/social, less coding/education
        if is_weekend:
            if category in ("Entertainment", "Social Media"):
                minutes *= random.uniform(1.3, 1.8)
            elif category in ("Coding", "Education", "Productivity"):
                minutes *= random.uniform(0.2, 0.5)
        else:
            # Weekday: slight random noise, occasional "doomscroll" days
            minutes *= random.uniform(0.7, 1.3)
            if category == "Social Media" and random.random() < 0.25:
                minutes *= random.uniform(1.5, 2.2)  # occasional binge day

        minutes = max(0, round(minutes))

        # Skip apps with 0 usage sometimes (not opened that day) to feel realistic
        if minutes == 0 and random.random() < 0.5:
            continue

        rows.append({
            "Date": date.strftime("%Y-%m-%d"),
            "App_Name": app,
            "Category": category,
            "Minutes_Used": minutes,
        })

df = pd.DataFrame(rows)
df.to_csv("screentime.csv", index=False)
print(f"Generated {len(df)} rows across 14 days -> screentime.csv")
print(df.groupby("Date")["Minutes_Used"].sum())
