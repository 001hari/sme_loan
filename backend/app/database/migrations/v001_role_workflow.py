"""Additive migration for authentication and role-based loan workflows."""

VERSION = "001_role_workflow"

UP = (
    """CREATE TABLE IF NOT EXISTS users (
        user_id BIGSERIAL PRIMARY KEY,
        full_name VARCHAR(200) NOT NULL CHECK (length(trim(full_name)) > 0),
        email VARCHAR(320) NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        phone_number VARCHAR(32) NOT NULL,
        role VARCHAR(32) NOT NULL CHECK (role IN ('SME_APPLICANT', 'RELATIONSHIP_MANAGER', 'LOAN_OFFICER')),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS sme_applicants (
        user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS relationship_managers (
        user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS loan_officers (
        user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS applicant_id BIGINT",
    "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS business_age_years NUMERIC(7,1)",
    "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS employee_count INTEGER",
    """DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'businesses_applicant_id_fkey' AND conrelid = 'businesses'::regclass) THEN
            ALTER TABLE businesses ADD CONSTRAINT businesses_applicant_id_fkey
                FOREIGN KEY (applicant_id) REFERENCES sme_applicants(user_id);
        END IF;
    END $$""",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS rm_id BIGINT",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS loan_officer_id BIGINT",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS application_status VARCHAR(40) NOT NULL DEFAULT 'SUBMITTED'",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS decision_remarks TEXT",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS decided_at TIMESTAMPTZ",
    "UPDATE loan_applications SET submitted_at = created_at WHERE submitted_at IS NULL",
    "ALTER TABLE loan_applications ALTER COLUMN submitted_at SET DEFAULT CURRENT_TIMESTAMP",
    "ALTER TABLE loan_applications ALTER COLUMN submitted_at SET NOT NULL",
    """DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'loan_applications_rm_id_fkey' AND conrelid = 'loan_applications'::regclass) THEN
            ALTER TABLE loan_applications ADD CONSTRAINT loan_applications_rm_id_fkey
                FOREIGN KEY (rm_id) REFERENCES relationship_managers(user_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'loan_applications_loan_officer_id_fkey' AND conrelid = 'loan_applications'::regclass) THEN
            ALTER TABLE loan_applications ADD CONSTRAINT loan_applications_loan_officer_id_fkey
                FOREIGN KEY (loan_officer_id) REFERENCES loan_officers(user_id);
        END IF;
    END $$""",
    "CREATE INDEX IF NOT EXISTS idx_businesses_applicant_id ON businesses(applicant_id)",
    "CREATE INDEX IF NOT EXISTS idx_loan_applications_status_submitted ON loan_applications(application_status, submitted_at)",
    """CREATE TABLE IF NOT EXISTS application_info_requests (
        request_id BIGSERIAL PRIMARY KEY,
        loan_application_id BIGINT NOT NULL REFERENCES loan_applications(loan_application_id),
        requested_by BIGINT NOT NULL REFERENCES relationship_managers(user_id),
        request_text TEXT NOT NULL CHECK (length(trim(request_text)) > 0),
        applicant_response TEXT,
        request_status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (request_status IN ('OPEN', 'RESPONDED')),
        requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        responded_at TIMESTAMPTZ
    )""",
    """CREATE TABLE IF NOT EXISTS predictions (
        prediction_id BIGSERIAL PRIMARY KEY,
        loan_application_id BIGINT NOT NULL REFERENCES loan_applications(loan_application_id),
        loan_officer_id BIGINT NOT NULL REFERENCES loan_officers(user_id),
        risk_score NUMERIC(7, 4) NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
        risk_category VARCHAR(10) NOT NULL CHECK (risk_category IN ('LOW', 'MEDIUM', 'HIGH')),
        suggested_decision VARCHAR(32) NOT NULL CHECK (suggested_decision IN ('SUGGESTED_APPROVE', 'MANUAL_REVIEW', 'SUGGESTED_REJECT')),
        prediction_method VARCHAR(100) NOT NULL,
        predicted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_info_requests_application ON application_info_requests(loan_application_id, requested_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_predictions_application ON predictions(loan_application_id, predicted_at DESC, prediction_id DESC)",
)
