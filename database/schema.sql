-- Legacy pre-v002 bootstrap schema retained for migration compatibility.
-- Apply the explicit versioned migrations with:
--   python -m backend.app.database.migrate
-- The four-core-table schema and current applicant identity are reached by
-- migrations 002-004; do not treat
-- this historical baseline as the current target schema.
CREATE TABLE IF NOT EXISTS users (
    user_id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL CHECK (length(trim(full_name)) > 0),
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    phone_number VARCHAR(32) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('SME_APPLICANT','RELATIONSHIP_MANAGER','LOAN_OFFICER')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sme_applicants (user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS relationship_managers (user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS loan_officers (user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS businesses (
    business_id VARCHAR(32) PRIMARY KEY,
    applicant_id BIGINT REFERENCES sme_applicants(user_id),
    business_name TEXT NOT NULL CHECK (length(trim(business_name)) > 0),
    city TEXT NOT NULL CHECK (length(trim(city)) > 0),
    state TEXT NOT NULL CHECK (length(trim(state)) > 0),
    sector TEXT NOT NULL CHECK (length(trim(sector)) > 0),
    legal_status TEXT NOT NULL CHECK (length(trim(legal_status)) > 0),
    business_age_years NUMERIC(7,1),
    employee_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS loan_applications (
    loan_application_id BIGSERIAL PRIMARY KEY,
    business_id VARCHAR(32) NOT NULL REFERENCES businesses(business_id),
    rm_id BIGINT REFERENCES relationship_managers(user_id),
    loan_officer_id BIGINT REFERENCES loan_officers(user_id),
    business_age_years NUMERIC(7,1) NOT NULL CHECK (business_age_years >= 0),
    employee_count INTEGER NOT NULL CHECK (employee_count >= 1),
    annual_revenue NUMERIC(18,2) NOT NULL CHECK (annual_revenue > 0),
    previous_year_revenue NUMERIC(18,2) NOT NULL CHECK (previous_year_revenue > 0),
    annual_profit NUMERIC(18,2) NOT NULL,
    monthly_expenses NUMERIC(18,2) NOT NULL CHECK (monthly_expenses >= 0),
    total_liabilities NUMERIC(18,2) NOT NULL CHECK (total_liabilities >= 0),
    business_credit_score SMALLINT NOT NULL CHECK (business_credit_score BETWEEN 300 AND 900),
    prior_loan_count INTEGER NOT NULL CHECK (prior_loan_count >= 0),
    late_payment_history SMALLINT NOT NULL CHECK (late_payment_history IN (0,1)),
    missed_payments_12m SMALLINT NOT NULL CHECK (missed_payments_12m BETWEEN 0 AND 6),
    loan_purpose TEXT NOT NULL CHECK (length(trim(loan_purpose)) > 0),
    loan_amount NUMERIC(18,2) NOT NULL CHECK (loan_amount > 0),
    loan_tenure_months SMALLINT NOT NULL CHECK (loan_tenure_months IN (12,18,24,36,48,60,72)),
    cash_flow_stability TEXT NOT NULL CHECK (cash_flow_stability IN ('Stable','Moderate','Unstable')),
    revenue_growth_rate NUMERIC(12,6) NOT NULL,
    debt_to_revenue_ratio NUMERIC(12,6) NOT NULL,
    loan_to_revenue_ratio NUMERIC(12,6) NOT NULL,
    profit_margin NUMERIC(12,6) NOT NULL,
    dscr NUMERIC(12,6) NOT NULL,
    application_status VARCHAR(40) NOT NULL DEFAULT 'SUBMITTED',
    decision_remarks TEXT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMPTZ,
    risk_predicted_score NUMERIC(12,6),
    approval_result TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_loan_applications_business_id ON loan_applications(business_id);
CREATE INDEX IF NOT EXISTS idx_loan_applications_status_submitted ON loan_applications(application_status,submitted_at);
CREATE TABLE IF NOT EXISTS application_info_requests (
    request_id BIGSERIAL PRIMARY KEY,
    loan_application_id BIGINT NOT NULL REFERENCES loan_applications(loan_application_id),
    requested_by BIGINT NOT NULL REFERENCES relationship_managers(user_id),
    request_text TEXT NOT NULL CHECK (length(trim(request_text)) > 0),
    applicant_response TEXT,
    request_status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (request_status IN ('OPEN','RESPONDED')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id BIGSERIAL PRIMARY KEY,
    loan_application_id BIGINT NOT NULL REFERENCES loan_applications(loan_application_id),
    loan_officer_id BIGINT NOT NULL REFERENCES loan_officers(user_id),
    risk_score NUMERIC(7,4) NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_category VARCHAR(10) NOT NULL CHECK (risk_category IN ('LOW','MEDIUM','HIGH')),
    suggested_decision VARCHAR(32) NOT NULL,
    prediction_method VARCHAR(100) NOT NULL,
    predicted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(100) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
