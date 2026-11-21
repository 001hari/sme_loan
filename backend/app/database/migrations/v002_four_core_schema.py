"""In-place, data-preserving alignment with the four-core-table schema."""

VERSION = "002_four_core_schema"

UP = (
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM businesses WHERE business_id !~ '^[0-9]+$')
           OR EXISTS (SELECT 1 FROM loan_applications WHERE business_id !~ '^[0-9]+$') THEN
            RAISE EXCEPTION 'Business IDs contain values that cannot be converted to BIGINT';
        END IF;
        IF EXISTS (SELECT 1 FROM businesses WHERE length(business_name)>200 OR length(sector)>100 OR length(legal_status)>100 OR length(city)>100 OR length(state)>100) THEN
            RAISE EXCEPTION 'Business text values exceed the target schema lengths';
        END IF;
        IF EXISTS (SELECT 1 FROM users WHERE length(full_name)>150 OR length(email)>255 OR length(phone_number)>20 OR length(role)>30) THEN
            RAISE EXCEPTION 'User values exceed the target schema lengths';
        END IF;
        IF EXISTS (SELECT 1 FROM loan_applications WHERE business_age_years<>round(business_age_years,2) OR abs(business_age_years)>=1000) THEN
            RAISE EXCEPTION 'Application business age cannot be represented by NUMERIC(5,2)';
        END IF;
        IF EXISTS (SELECT 1 FROM businesses WHERE business_age_years IS NOT NULL AND (business_age_years<>round(business_age_years,2) OR abs(business_age_years)>=1000)) THEN
            RAISE EXCEPTION 'Business age cannot be represented by NUMERIC(5,2)';
        END IF;
        IF EXISTS (SELECT 1 FROM loan_applications WHERE abs(annual_revenue)>=10000000000000 OR abs(previous_year_revenue)>=10000000000000 OR abs(annual_profit)>=10000000000000 OR abs(monthly_expenses)>=10000000000000 OR abs(total_liabilities)>=10000000000000 OR abs(loan_amount)>=10000000000000) THEN
            RAISE EXCEPTION 'Loan amounts exceed target NUMERIC(15,2) capacity';
        END IF;
        IF EXISTS (SELECT 1 FROM loan_applications WHERE revenue_growth_rate<>round(revenue_growth_rate,2) OR abs(revenue_growth_rate)>=100000000 OR debt_to_revenue_ratio<>round(debt_to_revenue_ratio,4) OR loan_to_revenue_ratio<>round(loan_to_revenue_ratio,4) OR profit_margin<>round(profit_margin,4) OR dscr<>round(dscr,4) OR abs(debt_to_revenue_ratio)>=1000000 OR abs(loan_to_revenue_ratio)>=1000000 OR abs(profit_margin)>=1000000 OR abs(dscr)>=1000000) THEN
            RAISE EXCEPTION 'Existing financial ratios cannot be represented at target precision without rounding';
        END IF;
        IF EXISTS (SELECT 1 FROM loan_applications WHERE late_payment_history NOT IN (0,1)) THEN
            RAISE EXCEPTION 'Late payment history contains values other than 0 or 1';
        END IF;
        IF EXISTS (SELECT 1 FROM loan_applications WHERE length(application_status)>50 OR length(approval_result)>50 OR length(loan_purpose)>200 OR length(cash_flow_stability)>50) THEN
            RAISE EXCEPTION 'Application outcome values exceed target VARCHAR(50) capacity';
        END IF;
        IF EXISTS (SELECT 1 FROM businesses b WHERE b.applicant_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM sme_applicants s JOIN users u USING(user_id)
            WHERE s.user_id=b.applicant_id AND u.role='SME_APPLICANT')) THEN
            RAISE EXCEPTION 'Existing business applicant links do not resolve to SME_APPLICANT users';
        END IF;
        IF EXISTS (SELECT 1 FROM loan_applications la WHERE la.rm_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM relationship_managers rm JOIN users u USING(user_id)
            WHERE rm.user_id=la.rm_id AND u.role='RELATIONSHIP_MANAGER')) THEN
            RAISE EXCEPTION 'Existing RM links do not resolve to RELATIONSHIP_MANAGER users';
        END IF;
        IF EXISTS (SELECT 1 FROM loan_applications la WHERE la.loan_officer_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM loan_officers lo JOIN users u USING(user_id)
            WHERE lo.user_id=la.loan_officer_id AND u.role='LOAN_OFFICER')) THEN
            RAISE EXCEPTION 'Existing loan officer links do not resolve to LOAN_OFFICER users';
        END IF;
    END $$""",
    "ALTER TABLE loan_applications DROP CONSTRAINT loan_applications_business_id_fkey",
    "ALTER TABLE loan_applications DROP CONSTRAINT loan_applications_loan_officer_id_fkey",
    "ALTER TABLE loan_applications RENAME COLUMN loan_application_id TO application_id",
    "ALTER TABLE predictions RENAME COLUMN loan_application_id TO application_id",
    "ALTER TABLE businesses ALTER COLUMN business_id TYPE BIGINT USING business_id::BIGINT",
    "ALTER TABLE loan_applications ALTER COLUMN business_id TYPE BIGINT USING business_id::BIGINT",
    "ALTER TABLE loan_applications ADD CONSTRAINT loan_applications_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id)",
    "ALTER TABLE businesses ALTER COLUMN business_name TYPE VARCHAR(200) USING business_name::VARCHAR(200)",
    "ALTER TABLE businesses ALTER COLUMN sector TYPE VARCHAR(100) USING sector::VARCHAR(100)",
    "ALTER TABLE businesses ALTER COLUMN legal_status TYPE VARCHAR(100) USING legal_status::VARCHAR(100)",
    "ALTER TABLE businesses ALTER COLUMN city TYPE VARCHAR(100) USING city::VARCHAR(100)",
    "ALTER TABLE businesses ALTER COLUMN state TYPE VARCHAR(100) USING state::VARCHAR(100)",
    "ALTER TABLE businesses ALTER COLUMN business_age_years TYPE NUMERIC(5,2) USING business_age_years::NUMERIC(5,2)",
    "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS applicant_user_id BIGINT",
    "UPDATE businesses SET applicant_user_id=applicant_id WHERE applicant_user_id IS NULL AND applicant_id IS NOT NULL",
    "ALTER TABLE businesses ADD CONSTRAINT businesses_applicant_user_id_fkey FOREIGN KEY (applicant_user_id) REFERENCES users(user_id)",
    "ALTER TABLE users ALTER COLUMN full_name TYPE VARCHAR(150) USING full_name::VARCHAR(150)",
    "ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(255) USING email::VARCHAR(255)",
    "ALTER TABLE users ALTER COLUMN phone_number TYPE VARCHAR(20) USING phone_number::VARCHAR(20)",
    "ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(30) USING role::VARCHAR(30)",
    "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS relationship_manager_id BIGINT",
    "UPDATE loan_applications SET relationship_manager_id=rm_id WHERE relationship_manager_id IS NULL AND rm_id IS NOT NULL",
    "ALTER TABLE loan_applications ADD CONSTRAINT loan_applications_relationship_manager_id_fkey FOREIGN KEY (relationship_manager_id) REFERENCES users(user_id)",
    "ALTER TABLE loan_applications ADD CONSTRAINT loan_applications_loan_officer_id_fkey FOREIGN KEY (loan_officer_id) REFERENCES users(user_id)",
    "ALTER TABLE loan_applications ALTER COLUMN business_age_years TYPE NUMERIC(5,2) USING business_age_years::NUMERIC(5,2)",
    "ALTER TABLE loan_applications ALTER COLUMN annual_revenue TYPE NUMERIC(15,2) USING annual_revenue::NUMERIC(15,2)",
    "ALTER TABLE loan_applications ALTER COLUMN previous_year_revenue TYPE NUMERIC(15,2) USING previous_year_revenue::NUMERIC(15,2)",
    "ALTER TABLE loan_applications ALTER COLUMN annual_profit TYPE NUMERIC(15,2) USING annual_profit::NUMERIC(15,2)",
    "ALTER TABLE loan_applications ALTER COLUMN monthly_expenses TYPE NUMERIC(15,2) USING monthly_expenses::NUMERIC(15,2)",
    "ALTER TABLE loan_applications ALTER COLUMN total_liabilities TYPE NUMERIC(15,2) USING total_liabilities::NUMERIC(15,2)",
    "ALTER TABLE loan_applications ALTER COLUMN business_credit_score TYPE INTEGER USING business_credit_score::INTEGER",
    """DO $$ DECLARE item RECORD; BEGIN
        FOR item IN SELECT conname FROM pg_constraint
                    WHERE conrelid='loan_applications'::regclass AND contype='c'
                      AND pg_get_constraintdef(oid) ILIKE '%late_payment_history%'
        LOOP EXECUTE format('ALTER TABLE loan_applications DROP CONSTRAINT %I', item.conname); END LOOP;
    END $$""",
    "ALTER TABLE loan_applications ALTER COLUMN late_payment_history TYPE BOOLEAN USING late_payment_history<>0",
    "ALTER TABLE loan_applications ALTER COLUMN loan_amount TYPE NUMERIC(15,2) USING loan_amount::NUMERIC(15,2)",
    "ALTER TABLE loan_applications ALTER COLUMN loan_tenure_months TYPE INTEGER USING loan_tenure_months::INTEGER",
    "ALTER TABLE loan_applications ALTER COLUMN loan_purpose TYPE VARCHAR(200) USING loan_purpose::VARCHAR(200)",
    "ALTER TABLE loan_applications ALTER COLUMN cash_flow_stability TYPE VARCHAR(50) USING cash_flow_stability::VARCHAR(50)",
    "ALTER TABLE loan_applications ALTER COLUMN revenue_growth_rate TYPE NUMERIC(10,2) USING revenue_growth_rate::NUMERIC(10,2)",
    "ALTER TABLE loan_applications ALTER COLUMN debt_to_revenue_ratio TYPE NUMERIC(10,4) USING debt_to_revenue_ratio::NUMERIC(10,4)",
    "ALTER TABLE loan_applications ALTER COLUMN loan_to_revenue_ratio TYPE NUMERIC(10,4) USING loan_to_revenue_ratio::NUMERIC(10,4)",
    "ALTER TABLE loan_applications ALTER COLUMN profit_margin TYPE NUMERIC(10,4) USING profit_margin::NUMERIC(10,4)",
    "ALTER TABLE loan_applications ALTER COLUMN dscr TYPE NUMERIC(10,4) USING dscr::NUMERIC(10,4)",
    "ALTER TABLE loan_applications ALTER COLUMN application_status TYPE VARCHAR(50) USING application_status::VARCHAR(50)",
    "ALTER TABLE loan_applications ADD COLUMN IF NOT EXISTS final_decision VARCHAR(50)",
    "UPDATE loan_applications SET final_decision=approval_result WHERE final_decision IS NULL AND approval_result IS NOT NULL",
    "ALTER TABLE loan_applications ALTER COLUMN submitted_at TYPE TIMESTAMP WITHOUT TIME ZONE USING submitted_at AT TIME ZONE 'UTC'",
    "ALTER TABLE predictions RENAME COLUMN prediction_method TO model_name",
    "ALTER TABLE predictions ALTER COLUMN model_name TYPE VARCHAR(100) USING model_name::VARCHAR(100)",
    "ALTER TABLE predictions ALTER COLUMN risk_score TYPE NUMERIC(8,4) USING risk_score::NUMERIC(8,4)",
    "ALTER TABLE predictions ALTER COLUMN risk_category TYPE VARCHAR(50) USING risk_category::VARCHAR(50)",
    "ALTER TABLE predictions ALTER COLUMN suggested_decision TYPE VARCHAR(50) USING suggested_decision::VARCHAR(50)",
    "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS model_version VARCHAR(50)",
    "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS prediction_confidence NUMERIC(8,4)",
    "ALTER TABLE predictions ALTER COLUMN predicted_at TYPE TIMESTAMP WITHOUT TIME ZONE USING predicted_at AT TIME ZONE 'UTC'",
)

# Rollback is deliberately additive: no data/table/column is dropped. It restores
# the old identifier names and compatible widths/types while retaining new fields.
DOWN = (
    "ALTER TABLE loan_applications DROP CONSTRAINT loan_applications_relationship_manager_id_fkey",
    "ALTER TABLE loan_applications DROP CONSTRAINT loan_applications_loan_officer_id_fkey",
    "ALTER TABLE loan_applications DROP CONSTRAINT loan_applications_business_id_fkey",
    "ALTER TABLE loan_applications ALTER COLUMN loan_officer_id TYPE BIGINT USING loan_officer_id::BIGINT",
    "ALTER TABLE loan_applications ADD CONSTRAINT loan_applications_loan_officer_id_fkey FOREIGN KEY (loan_officer_id) REFERENCES loan_officers(user_id)",
    "ALTER TABLE loan_applications ALTER COLUMN business_id TYPE VARCHAR(32) USING business_id::VARCHAR(32)",
    "ALTER TABLE businesses ALTER COLUMN business_id TYPE VARCHAR(32) USING business_id::VARCHAR(32)",
    "ALTER TABLE loan_applications ADD CONSTRAINT loan_applications_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id)",
    "ALTER TABLE loan_applications ALTER COLUMN late_payment_history TYPE SMALLINT USING CASE WHEN late_payment_history THEN 1 ELSE 0 END",
    "ALTER TABLE loan_applications ADD CONSTRAINT loan_applications_late_payment_history_check CHECK (late_payment_history IN (0,1))",
    "ALTER TABLE loan_applications ALTER COLUMN business_age_years TYPE NUMERIC(7,1) USING business_age_years::NUMERIC(7,1)",
    "ALTER TABLE businesses ALTER COLUMN business_age_years TYPE NUMERIC(7,1) USING business_age_years::NUMERIC(7,1)",
    "ALTER TABLE loan_applications ALTER COLUMN annual_revenue TYPE NUMERIC(18,2) USING annual_revenue::NUMERIC(18,2)",
    "ALTER TABLE loan_applications ALTER COLUMN previous_year_revenue TYPE NUMERIC(18,2) USING previous_year_revenue::NUMERIC(18,2)",
    "ALTER TABLE loan_applications ALTER COLUMN annual_profit TYPE NUMERIC(18,2) USING annual_profit::NUMERIC(18,2)",
    "ALTER TABLE loan_applications ALTER COLUMN monthly_expenses TYPE NUMERIC(18,2) USING monthly_expenses::NUMERIC(18,2)",
    "ALTER TABLE loan_applications ALTER COLUMN total_liabilities TYPE NUMERIC(18,2) USING total_liabilities::NUMERIC(18,2)",
    "ALTER TABLE loan_applications ALTER COLUMN loan_amount TYPE NUMERIC(18,2) USING loan_amount::NUMERIC(18,2)",
    "ALTER TABLE loan_applications ALTER COLUMN revenue_growth_rate TYPE NUMERIC(12,6) USING revenue_growth_rate::NUMERIC(12,6)",
    "ALTER TABLE loan_applications ALTER COLUMN debt_to_revenue_ratio TYPE NUMERIC(12,6) USING debt_to_revenue_ratio::NUMERIC(12,6)",
    "ALTER TABLE loan_applications ALTER COLUMN loan_to_revenue_ratio TYPE NUMERIC(12,6) USING loan_to_revenue_ratio::NUMERIC(12,6)",
    "ALTER TABLE loan_applications ALTER COLUMN profit_margin TYPE NUMERIC(12,6) USING profit_margin::NUMERIC(12,6)",
    "ALTER TABLE loan_applications ALTER COLUMN dscr TYPE NUMERIC(12,6) USING dscr::NUMERIC(12,6)",
    "ALTER TABLE loan_applications ALTER COLUMN application_status TYPE VARCHAR(40) USING application_status::VARCHAR(40)",
    "ALTER TABLE loan_applications ALTER COLUMN loan_purpose TYPE TEXT USING loan_purpose::TEXT",
    "ALTER TABLE loan_applications ALTER COLUMN cash_flow_stability TYPE TEXT USING cash_flow_stability::TEXT",
    "ALTER TABLE loan_applications ALTER COLUMN submitted_at TYPE TIMESTAMP WITH TIME ZONE USING submitted_at AT TIME ZONE 'UTC'",
    "ALTER TABLE predictions ALTER COLUMN predicted_at TYPE TIMESTAMP WITH TIME ZONE USING predicted_at AT TIME ZONE 'UTC'",
    "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'",
    "ALTER TABLE users ALTER COLUMN full_name TYPE VARCHAR(200) USING full_name::VARCHAR(200)",
    "ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(320) USING email::VARCHAR(320)",
    "ALTER TABLE users ALTER COLUMN phone_number TYPE VARCHAR(32) USING phone_number::VARCHAR(32)",
    "ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(32) USING role::VARCHAR(32)",
    "ALTER TABLE businesses ALTER COLUMN business_name TYPE TEXT USING business_name::TEXT",
    "ALTER TABLE businesses ALTER COLUMN sector TYPE TEXT USING sector::TEXT",
    "ALTER TABLE businesses ALTER COLUMN legal_status TYPE TEXT USING legal_status::TEXT",
    "ALTER TABLE businesses ALTER COLUMN city TYPE TEXT USING city::TEXT",
    "ALTER TABLE businesses ALTER COLUMN state TYPE TEXT USING state::TEXT",
    "ALTER TABLE predictions ALTER COLUMN model_name TYPE VARCHAR(100) USING model_name::VARCHAR(100)",
    "ALTER TABLE predictions RENAME COLUMN model_name TO prediction_method",
    "ALTER TABLE predictions RENAME COLUMN application_id TO loan_application_id",
    "ALTER TABLE loan_applications RENAME COLUMN application_id TO loan_application_id",
)
