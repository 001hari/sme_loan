"""Generate schema-aligned synthetic SME applications and a stratified split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "dataset"
SEED = 42
RECORDS = 50_000
TARGET = "default"

CATEGORICAL_FEATURES = [
    "state", "sector", "legal_status", "loan_purpose", "cash_flow_stability",
]
NUMERICAL_FEATURES = [
    "business_age_years", "employee_count", "annual_revenue", "previous_year_revenue",
    "annual_profit", "monthly_expenses", "total_liabilities", "business_credit_score",
    "prior_loan_count", "late_payment_history", "missed_payments_12m", "loan_amount",
    "loan_tenure_months", "revenue_growth_rate", "debt_to_revenue_ratio",
    "loan_to_revenue_ratio", "profit_margin", "dscr",
]
FEATURES = [
    "state", "sector", "legal_status", "business_age_years", "employee_count",
    "annual_revenue", "previous_year_revenue", "annual_profit", "monthly_expenses",
    "total_liabilities", "business_credit_score", "prior_loan_count", "late_payment_history",
    "missed_payments_12m", "loan_purpose", "loan_amount", "loan_tenure_months",
    "cash_flow_stability", "revenue_growth_rate", "debt_to_revenue_ratio",
    "loan_to_revenue_ratio", "profit_margin", "dscr",
]

SECTORS = (
    "Manufacturing", "Retail", "Wholesale", "Information Technology", "Agriculture",
    "Food Processing", "Healthcare", "Construction", "Transportation", "Hospitality",
)
SECTOR_MARGIN = {
    "Manufacturing": .13, "Retail": .09, "Wholesale": .08,
    "Information Technology": .22, "Agriculture": .12, "Food Processing": .14,
    "Healthcare": .18, "Construction": .11, "Transportation": .12, "Hospitality": .10,
}
SECTOR_REVENUE_MULTIPLIER = {
    "Manufacturing": 1.5, "Retail": .8, "Wholesale": 1.4,
    "Information Technology": 1.2, "Agriculture": .7, "Food Processing": 1.0,
    "Healthcare": 1.3, "Construction": 1.5, "Transportation": 1.1, "Hospitality": .9,
}
LEGAL_STATUSES = ("Proprietorship", "Partnership", "LLP", "Private Limited")
LOAN_PURPOSES = (
    "Working Capital", "Business Expansion", "Equipment Purchase", "Inventory Purchase",
    "Infrastructure", "Debt Refinancing",
)
CASH_FLOW_STABILITY = ("Stable", "Moderate", "Unstable")
STATES = (
    "Andhra Pradesh", "Assam", "Bihar", "Delhi", "Gujarat", "Haryana", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Odisha", "Punjab",
    "Rajasthan", "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal",
)
TENURES = np.array([12, 18, 24, 36, 48, 60, 72])


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30, 30)))


def generate_dataset(records: int = RECORDS, seed: int = SEED) -> pd.DataFrame:
    if records < 100:
        raise ValueError("At least 100 records are required for a useful stratified split.")
    rng = np.random.default_rng(seed)
    sector = rng.choice(SECTORS, records)
    business_age = np.round(np.clip(rng.gamma(2.8, 3.2, records), .5, 40), 2)
    employee_count = np.clip(rng.lognormal(2.7, .85, records), 1, 500).astype(int)
    multiplier = np.array([SECTOR_REVENUE_MULTIPLIER[value] for value in sector])
    annual_revenue = np.clip(
        np.exp(rng.normal(np.log(6_000_000), .85, records))
        * np.sqrt(employee_count / 15)
        * multiplier,
        300_000,
        5_000_000_000,
    )
    growth = np.round(np.clip(rng.normal(.07, .15, records), -.45, .55), 2)
    previous_revenue = annual_revenue / (1 + growth)

    prior_loans = np.clip(rng.poisson(np.clip(business_age / 4.5, .15, 7)), 0, 15)
    missed = np.clip(rng.poisson(.12 + (business_age < 2) * .18, records), 0, 6)
    late_probability = _sigmoid(-2.5 + .62 * missed + .3 * (business_age < 2))
    late = rng.binomial(1, late_probability).astype(bool)
    credit_score = np.clip(
        760 - missed * 25 - late.astype(int) * 34 + np.minimum(prior_loans, 8) * 3
        + rng.normal(0, 38, records),
        300,
        900,
    ).round().astype(int)

    base_margin = np.array([SECTOR_MARGIN[value] for value in sector])
    profit_margin = np.clip(base_margin + rng.normal(0, .065, records) - missed * .006, -.25, .40)
    annual_profit = annual_revenue * profit_margin
    monthly_expenses = (annual_revenue - annual_profit) / 12

    debt_ratio = np.clip(rng.beta(2, 4, records) * 1.55 + missed * .025, .02, 2.0)
    liabilities = annual_revenue * debt_ratio
    loan_ratio = np.clip(.04 + rng.beta(2, 4, records) * .92, .05, .95)
    loan_amount = annual_revenue * loan_ratio
    tenure = rng.choice(TENURES, records, p=[.08, .07, .18, .25, .18, .16, .08])

    stability_score = (
        profit_margin * 2.2 + growth * .9 - missed * .09 - debt_ratio * .16
        + rng.normal(0, .16, records)
    )
    stability = np.where(stability_score > .24, "Stable",
                         np.where(stability_score > -.04, "Moderate", "Unstable"))

    # Approximate DSCR: annual profit / (existing annual debt service at 18% of
    # liabilities + requested principal amortized over the requested term).
    # The app collects DSCR directly; this explicit definition is used only to
    # create internally coherent synthetic examples.
    annual_debt_service = liabilities * .18 + loan_amount * 12 / tenure
    dscr = np.clip(np.maximum(annual_profit, 0) / np.maximum(annual_debt_service, 1), 0, 5)

    # Match the exact ratios calculated by the applicant console.
    debt_ratio = liabilities / annual_revenue
    loan_ratio = loan_amount / annual_revenue
    profit_margin = annual_profit / annual_revenue

    frame = pd.DataFrame({
        "state": rng.choice(STATES, records),
        "sector": sector,
        "legal_status": rng.choice(LEGAL_STATUSES, records, p=[.45, .25, .20, .10]),
        "business_age_years": business_age,
        "employee_count": employee_count,
        "annual_revenue": np.round(annual_revenue, 2),
        "previous_year_revenue": np.round(previous_revenue, 2),
        "annual_profit": np.round(annual_profit, 2),
        "monthly_expenses": np.round(monthly_expenses, 2),
        "total_liabilities": np.round(liabilities, 2),
        "business_credit_score": credit_score,
        "prior_loan_count": prior_loans.astype(int),
        "late_payment_history": late,
        "missed_payments_12m": missed.astype(int),
        "loan_purpose": rng.choice(LOAN_PURPOSES, records),
        "loan_amount": np.round(loan_amount, 2),
        "loan_tenure_months": tenure.astype(int),
        "cash_flow_stability": stability,
        "revenue_growth_rate": np.round(growth, 2),
        "debt_to_revenue_ratio": np.round(debt_ratio, 4),
        "loan_to_revenue_ratio": np.round(loan_ratio, 4),
        "profit_margin": np.round(profit_margin, 4),
        "dscr": np.round(dscr, 4),
    })

    # Generate noisy Bernoulli outcomes. The intercept is calibrated so the
    # expected prevalence is 20%; sampled labels are not forced to an exact ratio.
    cashflow_risk = np.select([stability == "Unstable", stability == "Moderate"], [.8, .22], 0.0)
    logits = (
        (680 - credit_score) / 95 * .55
        + debt_ratio * .85
        + loan_ratio * .95
        + np.maximum(1.4 - dscr, 0) * .45
        + np.maximum(.08 - profit_margin, 0) * 4.0
        + late.astype(float) * .65
        + missed * .42
        + cashflow_risk
        + np.maximum(-growth, 0) * 2.0
        + np.maximum(.08 - growth, 0) * .6
    )
    low, high = -12.0, 12.0
    for _ in range(80):
        intercept = (low + high) / 2
        if _sigmoid(logits + intercept).mean() < .20:
            low = intercept
        else:
            high = intercept
    default_probability = _sigmoid(logits + (low + high) / 2)
    frame["default"] = rng.binomial(1, default_probability).astype("int64")
    return frame.loc[:, FEATURES + [TARGET]]


def validate_dataset(frame: pd.DataFrame) -> dict:
    expected = FEATURES + [TARGET]
    if list(frame.columns) != expected:
        raise ValueError("Synthetic dataset columns do not match the declared application feature schema.")
    if frame.isna().any().any():
        raise ValueError("Generated dataset contains missing values.")
    if frame.duplicated().any():
        raise ValueError("Generated dataset contains exact duplicate rows.")
    if not set(frame[TARGET].unique()).issubset({0, 1}):
        raise ValueError("Target must contain only 0 (Non-default) and 1 (Default / High Risk).")
    if not frame["business_age_years"].between(.01, 100).all():
        raise ValueError("business_age_years is outside applicant validation bounds.")
    if not frame["business_credit_score"].between(300, 900).all():
        raise ValueError("business_credit_score is outside applicant validation bounds.")
    if not frame["missed_payments_12m"].between(0, 6).all():
        raise ValueError("missed_payments_12m is outside applicant validation bounds.")
    if not frame["loan_tenure_months"].isin(TENURES).all():
        raise ValueError("loan_tenure_months contains unsupported applicant values.")
    if not frame["sector"].isin(SECTORS).all() or not frame["legal_status"].isin(LEGAL_STATUSES).all():
        raise ValueError("Dataset contains a sector or legal status not accepted by the application.")
    if not frame["loan_purpose"].isin(LOAN_PURPOSES).all():
        raise ValueError("Dataset contains an unsupported loan purpose.")
    if not frame["cash_flow_stability"].isin(CASH_FLOW_STABILITY).all():
        raise ValueError("Dataset contains an unsupported cash-flow stability value.")
    if not np.allclose(frame["previous_year_revenue"],
                       frame["annual_revenue"] / (1 + frame["revenue_growth_rate"]), rtol=2e-3):
        raise ValueError("Previous-year revenue and growth rate are inconsistent.")
    if not np.allclose(frame["monthly_expenses"] * 12,
                       frame["annual_revenue"] - frame["annual_profit"], rtol=2e-6, atol=6):
        raise ValueError("Annual profit and monthly expenses are inconsistent.")
    if not np.allclose(frame["debt_to_revenue_ratio"],
                       frame["total_liabilities"] / frame["annual_revenue"], atol=5e-5):
        raise ValueError("Debt-to-revenue ratio does not match the application formula.")
    if not np.allclose(frame["loan_to_revenue_ratio"],
                       frame["loan_amount"] / frame["annual_revenue"], atol=5e-5):
        raise ValueError("Loan-to-revenue ratio does not match the application formula.")
    if not np.allclose(frame["profit_margin"],
                       frame["annual_profit"] / frame["annual_revenue"], atol=5e-5):
        raise ValueError("Profit margin does not match the application formula.")
    prevalence = float(frame[TARGET].mean())
    if not .10 <= prevalence <= .30:
        raise ValueError(f"Sampled default prevalence {prevalence:.3%} is outside the expected range.")
    return {
        "rows": int(len(frame)), "features": len(FEATURES), "columns": list(frame.columns),
        "missing_values": int(frame.isna().sum().sum()), "duplicate_rows": int(frame.duplicated().sum()),
        "target_counts": {str(k): int(v) for k, v in frame[TARGET].value_counts().sort_index().items()},
        "target_prevalence": prevalence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=RECORDS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    frame = generate_dataset(args.records, args.seed)
    summary = validate_dataset(frame)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    full_path = DATASET_DIR / "synthetic_sme_loan_data.csv"
    train_path = DATASET_DIR / "sme_train.csv"
    test_path = DATASET_DIR / "sme_test.csv"
    train, test = train_test_split(
        frame, test_size=.20, random_state=args.seed, stratify=frame[TARGET],
    )
    frame.to_csv(full_path, index=False)
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    results_dir = ROOT / "ml" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "# Synthetic SME dataset validation", "",
        "Generated from the business and loan application schema and application inputs. "
        "These rows and labels are simulated, not historical loan outcomes.", "",
        f"- Records: {len(frame):,}; features: {len(FEATURES)}; columns including target: {len(frame.columns)}",
        f"- Seed: {args.seed}; target prevalence: {summary['target_prevalence']:.2%}",
        f"- Missing values: {summary['missing_values']}; exact duplicate rows: {summary['duplicate_rows']}",
        f"- Stratified split: {len(train):,} train / {len(test):,} test (80% / 20%)", "",
        "## Feature schema and types", "",
        "| Column | Type |", "|---|---|",
    ]
    report_lines.extend(f"| `{column}` | `{dtype}` |" for column, dtype in frame.dtypes.astype(str).items())
    report_lines.extend(["", "## Target counts", "", "| Class | Meaning | Count | Share |", "|---:|---|---:|---:|"])
    for label, meaning in ((0, "Non-default"), (1, "Default / High Risk")):
        count = int((frame[TARGET] == label).sum())
        report_lines.append(f"| {label} | {meaning} | {count:,} | {count / len(frame):.2%} |")
    report_lines.extend(["", "## Numerical distributions", "",
                         "| Feature | Min | Median | Mean | 99th percentile | Max |",
                         "|---|---:|---:|---:|---:|---:|"])
    describe = frame[NUMERICAL_FEATURES].astype(float).describe(percentiles=[.5, .99])
    for column in NUMERICAL_FEATURES:
        row = describe[column]
        report_lines.append(
            f"| `{column}` | {row['min']:.4g} | {row['50%']:.4g} | {row['mean']:.4g} | "
            f"{row['99%']:.4g} | {row['max']:.4g} |"
        )
    report_lines.extend(["", "## Categorical distributions", ""])
    for column in CATEGORICAL_FEATURES:
        report_lines.extend([f"### `{column}`", "", "| Value | Count |", "|---|---:|"])
        report_lines.extend(f"| {value} | {count:,} |" for value, count in frame[column].value_counts().sort_index().items())
        report_lines.append("")
    report_lines.extend([
        "## Financial consistency checks", "",
        "- Previous-year revenue is calculated from annual revenue and the rounded growth rate.",
        "- Annual profit is generated from sector-informed margin; monthly expenses satisfy "
        "`monthly_expenses = (annual_revenue - annual_profit) / 12` (to currency rounding).",
        "- Total liabilities equal annual revenue multiplied by the debt-to-revenue ratio.",
        "- Loan amount equals annual revenue multiplied by the loan-to-revenue ratio.",
        "- Profit margin equals annual profit divided by annual revenue.",
        "- DSCR uses annual profit divided by existing annual debt service at 18% of liabilities "
        "plus requested principal amortized over tenure; it is clipped to 0–5. The application "
        "collects DSCR directly and does not define its formula.",
        "- `default` labels are Bernoulli samples from a noisy logistic probability. The intercept "
        "targets 20% expected prevalence without forcing an exact realized class ratio.",
        "",
        "## Split distributions", "",
        f"- Train target counts: {json.dumps({str(k): int(v) for k, v in train[TARGET].value_counts().sort_index().items()})}",
        f"- Test target counts: {json.dumps({str(k): int(v) for k, v in test[TARGET].value_counts().sort_index().items()})}",
    ])
    (results_dir / "sme_synthetic_dataset_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print({**summary, "train_rows": len(train), "test_rows": len(test),
           "full_dataset": str(full_path), "train_dataset": str(train_path), "test_dataset": str(test_path)})


if __name__ == "__main__":
    main()
