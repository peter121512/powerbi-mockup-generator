"""Generate realistic synthetic customer data for the Customer Performance dashboard.

Creates a Customer table with ~2,000 customers and realistic distributions:
- CustomerID, CustomerName
- JoinDate (spread across 2021-2023)
- Segment (Enterprise, SMB, Consumer, Public Sector)
- AcquisitionChannel (Direct, Referral, Online, Partner, Events)
- Region (London, Scotland — matching existing model)
- IsActive (boolean — ~85% active for realistic retention)
- ChurnDate (for churned customers)
- AnnualValue (realistic revenue per customer)

Also creates a CustomerMetrics table with monthly snapshots for time-series analysis.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

output_dir = Path("data/customer")
output_dir.mkdir(parents=True, exist_ok=True)

# ─── Configuration ───────────────────────────────────────────────────────────

TOTAL_CUSTOMERS = 2000
SEGMENTS = ["Enterprise", "SMB", "Consumer", "Public Sector"]
SEGMENT_WEIGHTS = [0.20, 0.35, 0.30, 0.15]
CHANNELS = ["Direct", "Referral", "Online", "Partner", "Events"]
CHANNEL_WEIGHTS = [0.25, 0.20, 0.30, 0.15, 0.10]
REGIONS = ["London", "Scotland"]
REGION_WEIGHTS = [0.6, 0.4]

# Value ranges by segment (annual £)
SEGMENT_VALUES = {
    "Enterprise": (50000, 200000),
    "SMB": (10000, 50000),
    "Consumer": (500, 5000),
    "Public Sector": (30000, 150000),
}

# Churn probability by segment (annual)
SEGMENT_CHURN = {
    "Enterprise": 0.08,
    "SMB": 0.15,
    "Consumer": 0.25,
    "Public Sector": 0.05,
}

START_DATE = date(2021, 1, 1)
END_DATE = date(2023, 12, 31)
REFERENCE_DATE = date(2023, 12, 31)

# ─── Generate customers ──────────────────────────────────────────────────────

first_names = ["James", "Emma", "Oliver", "Sophia", "William", "Isabella", "Henry", "Mia",
               "Thomas", "Charlotte", "George", "Amelia", "Harry", "Olivia", "Jack", "Lily",
               "Daniel", "Grace", "Alexander", "Chloe", "Samuel", "Emily", "Benjamin", "Hannah",
               "Matthew", "Jessica", "David", "Sophie", "Joseph", "Lucy"]
last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson",
              "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin", "Lee", "Harris",
              "Clark", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright",
              "Scott", "Green", "Baker", "Hall", "Adams", "Nelson"]
company_suffixes = ["Ltd", "Group", "Solutions", "Services", "Corp", "Holdings", "Partners", "International"]

customers = []
for i in range(1, TOTAL_CUSTOMERS + 1):
    segment = random.choices(SEGMENTS, SEGMENT_WEIGHTS)[0]
    channel = random.choices(CHANNELS, CHANNEL_WEIGHTS)[0]
    region = random.choices(REGIONS, REGION_WEIGHTS)[0]

    # Join date — weighted toward earlier dates (more established base)
    days_range = (END_DATE - START_DATE).days
    join_offset = int(random.betavariate(2, 3) * days_range)
    join_date = START_DATE + timedelta(days=join_offset)

    # Name
    if segment in ("Enterprise", "Public Sector"):
        name = f"{random.choice(last_names)} {random.choice(company_suffixes)}"
    else:
        name = f"{random.choice(first_names)} {random.choice(last_names)}"

    # Annual value
    val_min, val_max = SEGMENT_VALUES[segment]
    annual_value = round(random.uniform(val_min, val_max), 2)

    # Churn
    churn_prob = SEGMENT_CHURN[segment]
    # Scale by tenure (newer customers churn more)
    tenure_days = (REFERENCE_DATE - join_date).days
    tenure_factor = max(0.5, 1.0 - tenure_days / 1500)
    adjusted_churn = min(0.5, churn_prob * tenure_factor * (tenure_days / 365))

    is_active = random.random() > adjusted_churn
    churn_date = ""
    if not is_active:
        # Churn happened sometime after joining
        min_tenure = 30
        max_churn_days = min(tenure_days, (REFERENCE_DATE - join_date).days)
        if max_churn_days > min_tenure:
            churn_offset = random.randint(min_tenure, max_churn_days)
            churn_date = (join_date + timedelta(days=churn_offset)).isoformat()

    customers.append({
        "CustomerID": f"C{i:04d}",
        "CustomerName": name,
        "JoinDate": join_date.isoformat(),
        "Segment": segment,
        "AcquisitionChannel": channel,
        "Region": region,
        "IsActive": is_active,
        "ChurnDate": churn_date,
        "AnnualValue": annual_value,
    })

# ─── Write Customer.csv ──────────────────────────────────────────────────────

csv_path = output_dir / "Customer.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=customers[0].keys())
    writer.writeheader()
    writer.writerows(customers)

# ─── Summary stats ───────────────────────────────────────────────────────────

active = sum(1 for c in customers if c["IsActive"])
churned = TOTAL_CUSTOMERS - active
segments = {}
channels = {}
regions = {}
for c in customers:
    segments[c["Segment"]] = segments.get(c["Segment"], 0) + 1
    channels[c["AcquisitionChannel"]] = channels.get(c["AcquisitionChannel"], 0) + 1
    regions[c["Region"]] = regions.get(c["Region"], 0) + 1

print(f"Generated {TOTAL_CUSTOMERS} customers → {csv_path}")
print(f"  Active: {active} ({active/TOTAL_CUSTOMERS*100:.1f}%)")
print(f"  Churned: {churned} ({churned/TOTAL_CUSTOMERS*100:.1f}%)")
print(f"  Segments: {segments}")
print(f"  Channels: {channels}")
print(f"  Regions: {regions}")
print(f"  Total annual value: £{sum(c['AnnualValue'] for c in customers):,.0f}")
print(f"  Avg LTV (active): £{sum(c['AnnualValue'] for c in customers if c['IsActive'])/active:,.0f}")
