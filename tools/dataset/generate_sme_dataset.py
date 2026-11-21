
from pathlib import Path

import numpy as np
import pandas as pd

from faker import Faker
from sklearn.model_selection import train_test_split


# ==========================================================
# 1. CONFIGURATION
# ==========================================================

N_RECORDS = 50_000
RANDOM_STATE = 42
TEST_SIZE = 0.20

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "dataset"

DATASET_DIR.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(RANDOM_STATE)

fake = Faker("en_IN")
Faker.seed(RANDOM_STATE)


# ==========================================================
# 2. SME REFERENCE DATA
# ==========================================================

STATES_AND_CITIES = {
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Sambalpur"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik"],
    "Karnataka": ["Bengaluru", "Mysuru", "Mangaluru", "Hubli"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem"],
    "Telangana": ["Hyderabad", "Warangal", "Karimnagar"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
    "Delhi": ["New Delhi", "Dwarka", "Rohini"],
    "West Bengal": ["Kolkata", "Durgapur", "Siliguri"],
    "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Noida", "Agra"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur"],
    "Madhya Pradesh": ["Indore", "Bhopal", "Gwalior"]
}

SECTORS = [
    "Manufacturing",
    "Retail",
    "Wholesale",
    "Information Technology",
    "Agriculture",
    "Food Processing",
    "Healthcare",
    "Construction",
    "Transportation",
    "Hospitality"
]

SECTOR_MARGIN = {
    "Manufacturing": 0.13,
    "Retail": 0.09,
    "Wholesale": 0.08,
    "Information Technology": 0.22,
    "Agriculture": 0.12,
    "Food Processing": 0.14,
    "Healthcare": 0.18,
    "Construction": 0.11,
    "Transportation": 0.12,
    "Hospitality": 0.10
}

SECTOR_REVENUE_MULTIPLIER = {
    "Manufacturing": 1.5,
    "Retail": 0.8,
    "Wholesale": 1.4,
    "Information Technology": 1.2,
    "Agriculture": 0.7,
    "Food Processing": 1.0,
    "Healthcare": 1.3,
    "Construction": 1.5,
    "Transportation": 1.1,
    "Hospitality": 0.9
}

LEGAL_STATUSES = [
    "Proprietorship",
    "Partnership",
    "Private Limited",
    "LLP"
]

LOAN_PURPOSES = [
    "Working Capital",
    "Business Expansion",
    "Equipment Purchase",
    "Inventory Purchase",
    "Infrastructure",
    "Debt Refinancing"
]


# ==========================================================
# 3. GENERATE BUSINESS PROFILE
# ==========================================================

print("\nGenerating SME business profiles...")

business_ids = [
    f"SME{number:06d}"
    for number in range(1, N_RECORDS + 1)
]

business_names = [
    fake.company()
    for _ in range(N_RECORDS)
]

states = rng.choice(
    list(STATES_AND_CITIES.keys()),
    N_RECORDS
)

cities = [
    rng.choice(STATES_AND_CITIES[state])
    for state in states
]

sectors = rng.choice(SECTORS, N_RECORDS)

legal_status = rng.choice(
    LEGAL_STATUSES,
    N_RECORDS,
    p=[0.45, 0.25, 0.20, 0.10]
)

business_age = np.clip(
    rng.gamma(shape=2.5, scale=3.0, size=N_RECORDS),
    0.5,
    30
)

business_age = np.round(business_age, 1)

employee_count = np.clip(
    rng.lognormal(mean=2.0, sigma=0.9, size=N_RECORDS),
    1,
    500
).astype(int)


# ==========================================================
# 4. GENERATE BUSINESS REVENUE
# ==========================================================

print("Generating financial information...")

multipliers = np.array([
    SECTOR_REVENUE_MULTIPLIER[sector]
    for sector in sectors
])

annual_revenue = (
    rng.lognormal(
        mean=15.0,
        sigma=0.8,
        size=N_RECORDS
    )
    * multipliers
    * np.sqrt(employee_count)
)

annual_revenue = np.clip(
    annual_revenue,
    300_000,
    500_000_000
)

annual_revenue = np.round(annual_revenue, 2)


# ==========================================================
# 5. REVENUE GROWTH
# ==========================================================

revenue_growth_rate = rng.normal(
    loc=0.08,
    scale=0.15,
    size=N_RECORDS
)

revenue_growth_rate = np.clip(
    revenue_growth_rate,
    -0.60,
    0.60
)

previous_year_revenue = (
    annual_revenue / (1 + revenue_growth_rate)
)

previous_year_revenue = np.round(
    previous_year_revenue,
    2
)


# ==========================================================
# 6. CREDIT AND REPAYMENT HISTORY
# ==========================================================

prior_loan_count = rng.poisson(
    lam=np.clip(business_age / 4, 0.2, 6)
)

prior_loan_count = np.clip(
    prior_loan_count,
    0,
    15
)

missed_payments_12m = rng.poisson(
    lam=np.clip(
        0.15 + (business_age < 2) * 0.15,
        0.05,
        0.5
    ),
    size=N_RECORDS
)

missed_payments_12m = np.clip(
    missed_payments_12m,
    0,
    6
)

late_payment_history = (
    rng.random(N_RECORDS)
    < np.clip(
        0.08
        + missed_payments_12m * 0.13
        + (business_age < 2) * 0.05,
        0.03,
        0.90
    )
).astype(int)

business_credit_score = (
    760
    - missed_payments_12m * 28
    - late_payment_history * 35
    + np.minimum(prior_loan_count, 8) * 5
    + rng.normal(0, 30, N_RECORDS)
)

business_credit_score = np.clip(
    business_credit_score,
    300,
    900
).astype(int)


# ==========================================================
# 7. BUSINESS PROFIT AND EXPENSES
# ==========================================================

base_margins = np.array([
    SECTOR_MARGIN[sector]
    for sector in sectors
])

profit_margin_actual = (
    base_margins
    + rng.normal(0, 0.07, N_RECORDS)
    - missed_payments_12m * 0.008
)

profit_margin_actual = np.clip(
    profit_margin_actual,
    -0.25,
    0.40
)

annual_profit = (
    annual_revenue * profit_margin_actual
)

annual_profit = np.round(
    annual_profit,
    2
)

monthly_expenses = (
    (annual_revenue - annual_profit) / 12
)

monthly_expenses = np.round(
    monthly_expenses,
    2
)

profit_margin = (
    annual_profit / annual_revenue
)


# ==========================================================
# 8. LIABILITIES AND LOAN DETAILS
# ==========================================================

debt_to_revenue_ratio = (
    rng.beta(2.0, 4.0, N_RECORDS) * 1.5
)

debt_to_revenue_ratio += (
    missed_payments_12m * 0.025
)

debt_to_revenue_ratio = np.clip(
    debt_to_revenue_ratio,
    0.02,
    1.80
)

total_liabilities = (
    annual_revenue * debt_to_revenue_ratio
)

total_liabilities = np.round(
    total_liabilities,
    2
)

loan_to_revenue_ratio = rng.uniform(
    0.05,
    0.65,
    N_RECORDS
)

loan_amount = (
    annual_revenue * loan_to_revenue_ratio
)

loan_amount = np.round(
    loan_amount,
    2
)

loan_tenure_months = rng.choice(
    [12, 18, 24, 36, 48, 60, 72],
    N_RECORDS,
    p=[0.08, 0.07, 0.18, 0.25, 0.18, 0.16, 0.08]
)

loan_purpose = rng.choice(
    LOAN_PURPOSES,
    N_RECORDS
)


# ==========================================================
# 9. CASH FLOW STABILITY
# ==========================================================

stability_score = (
    profit_margin_actual * 3
    + revenue_growth_rate * 0.8
    - missed_payments_12m * 0.08
    - debt_to_revenue_ratio * 0.15
    + rng.normal(0, 0.15, N_RECORDS)
)

cash_flow_stability = np.where(
    stability_score > 0.35,
    "Stable",
    np.where(
        stability_score > 0.05,
        "Moderate",
        "Unstable"
    )
)


# ==========================================================
# 10. DEBT SERVICE COVERAGE RATIO (DSCR)
# ==========================================================

existing_annual_debt_service = (
    total_liabilities * 0.18
)

requested_annual_debt_service = (
    loan_amount * 12 / loan_tenure_months * 1.15
)

total_annual_debt_service = (
    existing_annual_debt_service
    + requested_annual_debt_service
)

operating_cash_flow = (
    annual_profit
    + annual_revenue * 0.03
)

dscr = (
    operating_cash_flow
    / np.maximum(total_annual_debt_service, 1)
)

dscr = np.clip(
    dscr,
    -3,
    5
)

dscr = np.round(dscr, 3)


# ==========================================================
# 11. DEBT AND LOAN RATIOS
# ==========================================================

debt_to_revenue_ratio = np.round(
    debt_to_revenue_ratio,
    4
)

loan_to_revenue_ratio = (
    loan_amount / annual_revenue
)

loan_to_revenue_ratio = np.round(
    loan_to_revenue_ratio,
    4
)

revenue_growth_rate = np.round(
    revenue_growth_rate,
    4
)

profit_margin = np.round(
    profit_margin,
    4
)


# ==========================================================
# 12. CALCULATE SYNTHETIC RISK SCORE
# ==========================================================

print("Calculating synthetic risk scores...")

risk_score = (
    -2.0
    + ((680 - business_credit_score) / 100) * 0.9
    + missed_payments_12m * 0.45
    + late_payment_history * 0.65
    + debt_to_revenue_ratio * 1.5
    + loan_to_revenue_ratio * 1.2
    - np.minimum(business_age, 15) * 0.035
    - profit_margin * 2
    - np.clip(dscr, -2, 3) * 0.45
    + np.where(
        cash_flow_stability == "Moderate",
        0.25,
        0
    )
    + np.where(
        cash_flow_stability == "Unstable",
        0.80,
        0
    )
    - np.maximum(revenue_growth_rate, 0) * 1.5
)

probability = 1 / (
    1 + np.exp(-np.clip(risk_score, -20, 20))
)

# Keep probabilities valid for binomial sampling.
probability = np.clip(
    probability,
    0.0,
    1.0
)


# ==========================================================
# 13. PROBABILISTIC TARGET GENERATION
# ==========================================================
print("Generating probabilistic default labels...")

# Desired dataset distribution
TARGET_DEFAULT_RATIO = 0.25

# Convert original probabilities into logits
# Then find an offset that produces the desired average
# default probability.

epsilon = 1e-10

original_probability = np.clip(
    probability,
    epsilon,
    1 - epsilon
)

original_logits = np.log(
    original_probability / (1 - original_probability)
)

# Binary search for the probability adjustment
low = -20.0
high = 20.0

for _ in range(100):
    offset = (low + high) / 2

    adjusted_probability = 1 / (
        1 + np.exp(
            -np.clip(original_logits + offset, -30, 30)
        )
    )

    if adjusted_probability.mean() < TARGET_DEFAULT_RATIO:
        low = offset
    else:
        high = offset

# Final adjusted probability
risk_probability = 1 / (
    1 + np.exp(
        -np.clip(original_logits + (low + high) / 2, -30, 30)
    )
)

# Generate probabilistic default labels
default = rng.binomial(
    n=1,
    p=risk_probability,
    size=N_RECORDS
)

if len(np.unique(default)) != 2:
    raise ValueError("Target contains only one class.")

print("\nTarget generation completed.")

print(
    "Average default probability:",
    round(risk_probability.mean() * 100, 2), "%"
)

print(
    "Actual generated default percentage:",
    round(default.mean() * 100, 2), "%"
)
# ==========================================================
# 14. CREATE FINAL DATAFRAME
# ==========================================================

print("Creating final SME dataset...")

df = pd.DataFrame({

    "business_id": business_ids,

    "business_name": business_names,

    "city": cities,

    "state": states,

    "sector": sectors,

    "legal_status": legal_status,

    "business_age_years": business_age,

    "employee_count": employee_count,

    "annual_revenue": annual_revenue,

    "previous_year_revenue": previous_year_revenue,

    "annual_profit": annual_profit,

    "monthly_expenses": monthly_expenses,

    "total_liabilities": total_liabilities,

    "business_credit_score": business_credit_score,

    "prior_loan_count": prior_loan_count,

    "late_payment_history": late_payment_history,

    "missed_payments_12m": missed_payments_12m,

    "loan_purpose": loan_purpose,

    "loan_amount": loan_amount,

    "loan_tenure_months": loan_tenure_months,

    "cash_flow_stability": cash_flow_stability,

    "revenue_growth_rate": revenue_growth_rate,

    "debt_to_revenue_ratio": debt_to_revenue_ratio,

    "loan_to_revenue_ratio": loan_to_revenue_ratio,

    "profit_margin": profit_margin,

    "dscr": dscr,

    "default": default

})


# ==========================================================
# 15. DATA VALIDATION
# ==========================================================

print("\nValidating dataset...")

assert len(df) == N_RECORDS
assert df["business_id"].is_unique
assert df["default"].isin([0, 1]).all()
assert df["annual_revenue"].gt(0).all()
assert df["loan_amount"].gt(0).all()
assert df["employee_count"].ge(1).all()
assert df["previous_year_revenue"].gt(0).all()
assert not df.isnull().any().any()
assert len(df.columns) == 27

print("DATA VALIDATION PASSED")


# ==========================================================
# 16. STRATIFIED TRAIN TEST SPLIT
# ==========================================================

print("\nSplitting dataset into training and testing data...")

train_df, test_df = train_test_split(
    df,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=df["default"]
)

# Save ONLY training and testing CSV files.

train_path = DATASET_DIR / "sme_train.csv"
test_path = DATASET_DIR / "sme_test.csv"

train_df.to_csv(
    train_path,
    index=False
)

test_df.to_csv(
    test_path,
    index=False
)


# ==========================================================
# 17. DISPLAY RESULTS
# ==========================================================

print("\n" + "=" * 60)
print("SME DATASET GENERATION COMPLETED")
print("=" * 60)

print("\nFull dataset shape (in memory):", df.shape)

print("Training dataset shape:", train_df.shape)

print("Testing dataset shape:", test_df.shape)

print("\nOverall default distribution:")

print(
    df["default"].value_counts().sort_index()
)

print("\nOverall default percentage:")

print(
    (df["default"].value_counts(normalize=True) * 100)
    .sort_index()
    .round(2)
)

print("\nTraining target distribution:")

print(
    train_df["default"].value_counts()
)

print("\nTraining target percentage:")

print(
    (train_df["default"].value_counts(normalize=True) * 100)
    .round(2)
)

print("\nTesting target distribution:")

print(
    test_df["default"].value_counts()
)

print("\nTesting target percentage:")

print(
    (test_df["default"].value_counts(normalize=True) * 100)
    .round(2)
)

print("\nDefault probability statistics:")

print(
    pd.Series(probability).describe()
)

print("\nMissing values:")

print(df.isnull().sum().sum())

print("\nSaved files:")

print(train_path)

print(test_path)

print("\nFirst five records:")

print(df.head())

print("\nAll operations completed successfully!")
