# Synthetic SME dataset validation

Generated from the business and loan application schema and application inputs. These rows and labels are simulated, not historical loan outcomes.

- Records: 50,000; features: 23; columns including target: 24
- Seed: 42; target prevalence: 20.17%
- Missing values: 0; exact duplicate rows: 0
- Stratified split: 40,000 train / 10,000 test (80% / 20%)

## Feature schema and types

| Column | Type |
|---|---|
| `state` | `str` |
| `sector` | `str` |
| `legal_status` | `str` |
| `business_age_years` | `float64` |
| `employee_count` | `int64` |
| `annual_revenue` | `float64` |
| `previous_year_revenue` | `float64` |
| `annual_profit` | `float64` |
| `monthly_expenses` | `float64` |
| `total_liabilities` | `float64` |
| `business_credit_score` | `int64` |
| `prior_loan_count` | `int64` |
| `late_payment_history` | `bool` |
| `missed_payments_12m` | `int64` |
| `loan_purpose` | `str` |
| `loan_amount` | `float64` |
| `loan_tenure_months` | `int64` |
| `cash_flow_stability` | `str` |
| `revenue_growth_rate` | `float64` |
| `debt_to_revenue_ratio` | `float64` |
| `loan_to_revenue_ratio` | `float64` |
| `profit_margin` | `float64` |
| `dscr` | `float64` |
| `default` | `int64` |

## Target counts

| Class | Meaning | Count | Share |
|---:|---|---:|---:|
| 0 | Non-default | 39,914 | 79.83% |
| 1 | Default / High Risk | 10,086 | 20.17% |

## Numerical distributions

| Feature | Min | Median | Mean | 99th percentile | Max |
|---|---:|---:|---:|---:|---:|
| `business_age_years` | 0.5 | 7.87 | 8.938 | 26.04 | 40 |
| `employee_count` | 1 | 14 | 20.97 | 107 | 500 |
| `annual_revenue` | 3e+05 | 6.491e+06 | 1.051e+07 | 6.46e+07 | 5.684e+08 |
| `previous_year_revenue` | 2.041e+05 | 6.139e+06 | 1.001e+07 | 6.118e+07 | 4.584e+08 |
| `annual_profit` | -1.035e+07 | 7.184e+05 | 1.36e+06 | 9.95e+06 | 8.206e+07 |
| `monthly_expenses` | 1.814e+04 | 4.703e+05 | 7.629e+05 | 4.746e+06 | 4.589e+07 |
| `total_liabilities` | 1.087e+04 | 2.911e+06 | 5.454e+06 | 3.894e+07 | 2.612e+08 |
| `business_credit_score` | 577 | 760 | 759.7 | 852 | 900 |
| `prior_loan_count` | 0 | 2 | 1.974 | 8 | 15 |
| `late_payment_history` | 0 | 0 | 0.08384 | 1 | 1 |
| `missed_payments_12m` | 0 | 0 | 0.124 | 1 | 4 |
| `loan_amount` | 2.732e+04 | 2.01e+06 | 3.635e+06 | 2.517e+07 | 1.74e+08 |
| `loan_tenure_months` | 12 | 36 | 39.38 | 72 | 72 |
| `revenue_growth_rate` | -0.45 | 0.07 | 0.07049 | 0.42 | 0.55 |
| `debt_to_revenue_ratio` | 0.02 | 0.4875 | 0.5191 | 1.218 | 1.555 |
| `loan_to_revenue_ratio` | 0.05 | 0.3292 | 0.3468 | 0.7572 | 0.9463 |
| `profit_margin` | -0.1754 | 0.1258 | 0.1278 | 0.3137 | 0.4 |
| `dscr` | 0 | 0.582 | 0.7203 | 2.907 | 5 |

## Categorical distributions

### `state`

| Value | Count |
|---|---:|
| Andhra Pradesh | 2,644 |
| Assam | 2,624 |
| Bihar | 2,603 |
| Delhi | 2,611 |
| Gujarat | 2,578 |
| Haryana | 2,664 |
| Jharkhand | 2,561 |
| Karnataka | 2,680 |
| Kerala | 2,655 |
| Madhya Pradesh | 2,619 |
| Maharashtra | 2,559 |
| Odisha | 2,692 |
| Punjab | 2,653 |
| Rajasthan | 2,549 |
| Tamil Nadu | 2,599 |
| Telangana | 2,675 |
| Uttar Pradesh | 2,645 |
| Uttarakhand | 2,735 |
| West Bengal | 2,654 |

### `sector`

| Value | Count |
|---|---:|
| Agriculture | 4,985 |
| Construction | 5,064 |
| Food Processing | 5,001 |
| Healthcare | 5,051 |
| Hospitality | 5,011 |
| Information Technology | 4,906 |
| Manufacturing | 4,975 |
| Retail | 5,050 |
| Transportation | 4,902 |
| Wholesale | 5,055 |

### `legal_status`

| Value | Count |
|---|---:|
| LLP | 9,994 |
| Partnership | 12,563 |
| Private Limited | 4,915 |
| Proprietorship | 22,528 |

### `loan_purpose`

| Value | Count |
|---|---:|
| Business Expansion | 8,315 |
| Debt Refinancing | 8,341 |
| Equipment Purchase | 8,291 |
| Infrastructure | 8,371 |
| Inventory Purchase | 8,455 |
| Working Capital | 8,227 |

### `cash_flow_stability`

| Value | Count |
|---|---:|
| Moderate | 17,073 |
| Stable | 25,682 |
| Unstable | 7,245 |

## Financial consistency checks

- Previous-year revenue is calculated from annual revenue and the rounded growth rate.
- Annual profit is generated from sector-informed margin; monthly expenses satisfy `monthly_expenses = (annual_revenue - annual_profit) / 12` (to currency rounding).
- Total liabilities equal annual revenue multiplied by the debt-to-revenue ratio.
- Loan amount equals annual revenue multiplied by the loan-to-revenue ratio.
- Profit margin equals annual profit divided by annual revenue.
- DSCR uses annual profit divided by existing annual debt service at 18% of liabilities plus requested principal amortized over tenure; it is clipped to 0–5. The application collects DSCR directly and does not define its formula.
- `default` labels are Bernoulli samples from a noisy logistic probability. The intercept targets 20% expected prevalence without forcing an exact realized class ratio.

## Split distributions

- Train target counts: {"0": 31931, "1": 8069}
- Test target counts: {"0": 7983, "1": 2017}
