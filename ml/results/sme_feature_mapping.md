# SME application feature mapping

The live PostgreSQL schema was inspected read-only. The feature names below are the actual table column names. Applicant fields are captured by `RoleBasedConsoleApplication._collect_application`; the repository joins `businesses` with `loan_applications` for Loan Officer assessment.

| Model feature / database column | Table | Live PostgreSQL type | Applicant input or exact mapping |
|---|---|---|---|
| `state` | `businesses` | `character varying` | State prompt; free text constrained to letters/spaces |
| `sector` | `businesses` | `character varying` | `Business.VALID_SECTORS` |
| `legal_status` | `businesses` | `character varying` | `Business.VALID_LEGAL_STATUSES` |
| `business_age_years` | `loan_applications` | `numeric` | Applicant input; also stored in `businesses` |
| `employee_count` | `loan_applications` | `integer` | Applicant input; also stored in `businesses` |
| `annual_revenue` | `loan_applications` | `numeric` | Applicant input |
| `previous_year_revenue` | `loan_applications` | `numeric` | Applicant input |
| `annual_profit` | `loan_applications` | `numeric` | Applicant input |
| `monthly_expenses` | `loan_applications` | `numeric` | Applicant input |
| `total_liabilities` | `loan_applications` | `numeric` | Applicant input |
| `business_credit_score` | `loan_applications` | `integer` | Applicant input, validated 300–900 |
| `prior_loan_count` | `loan_applications` | `integer` | Applicant input, minimum 0 |
| `late_payment_history` | `loan_applications` | `boolean` | Applicant's 0/1 response |
| `missed_payments_12m` | `loan_applications` | `integer` | Applicant input, validated 0–6 |
| `loan_purpose` | `loan_applications` | `character varying` | `LoanApplication.VALID_LOAN_PURPOSES` |
| `loan_amount` | `loan_applications` | `numeric` | Applicant input |
| `loan_tenure_months` | `loan_applications` | `integer` | `LoanApplication.VALID_TENURES` |
| `cash_flow_stability` | `loan_applications` | `character varying` | `LoanApplication.VALID_CASH_FLOW_STABILITY` |
| `revenue_growth_rate` | `loan_applications` | `numeric` | Applicant input |
| `debt_to_revenue_ratio` | `loan_applications` | `numeric` | Existing formula: `total_liabilities / annual_revenue` |
| `loan_to_revenue_ratio` | `loan_applications` | `numeric` | Existing formula: `loan_amount / annual_revenue` |
| `profit_margin` | `loan_applications` | `numeric` | Existing formula: `annual_profit / annual_revenue` |
| `dscr` | `loan_applications` | `numeric` | Applicant input; no DSCR formula exists in the application |

**Excluded:** `business_id`, `application_id`, applicant/user IDs, names, email, city (free text/high cardinality), phone/password fields, timestamps, statuses, `risk_predicted_score`, `approval_result`, decisions, and post-assessment predictions. The only synthetic outcome is `default`, generated separately and never included among model inputs.

Every selected feature is available at assessment time. The only synthetic-only calculation is the generator's DSCR formula; at inference, the model uses the applicant-entered `dscr` stored on the loan application, with the same feature name and numeric type.
